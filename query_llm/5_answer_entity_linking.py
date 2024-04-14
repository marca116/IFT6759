from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
from datetime import datetime

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj
from qa_utils import print_solved_question,sort_questions, process_question_with_entity_properties, process_question_react, find_answer_entity_id

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format, get_cached_entity_labels_dict, save_cached_entity_labels_dict

# qald_10_train, qald_10_test, original_qald_9_plus_train, original_qald_9_plus_test
dataset_name = "qald_10_test"

input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_filename = f'{dataset_name}_solved_answers(with_answer_entity_linking).json'

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    dataset_questions = json.load(file)

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

root_results_folder = "results_with_react"

output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

# GPT3 : 20240411-142859808335_qald_10_test_solved_answers.json
# GPT4 : 20240411-185356593926_qald_10_test_solved_answers.json
with open("results_with_react/20240411-185356593926_qald_10_test_solved_answers.json", 'r', encoding='utf-8') as file:
    questions = json.load(file)
    questions = questions["solved_questions"]

#questions = questions[:10]

solved_questions = []

total_token_count = 0
start_time = time.time()

def process_question(question):
    global total_token_count

    if len(question["solved_answer"]) == 0:
        solved_questions.append(question)
        return

    first_solved_answer = question["solved_answer"][0]

    if isinstance(first_solved_answer, bool) or (isinstance(first_solved_answer, str) and first_solved_answer.isdigit()) or is_date(first_solved_answer):
        solved_questions.append(question)
        return

    reason = question["reasoning"]
    answers_datatype = question["answers_datatype"]
    extra_info = question["extra_info"]
    react_info = question.get("react_info")

    prompt_config = read_json('prompts.json')
    total_question_token = 0

    answers = []
    answer_linking_objs = []

    for answer_entity in question["solved_answer"]:
        answer_entity_id, entity_linking_reason, entity_linking_tokens_count, result_dicts = find_answer_entity_id(question, answer_entity, prompt_config, reason, extra_info, react_info)
        
        total_question_token += entity_linking_tokens_count
        new_answer = f"http://www.wikidata.org/entity/{answer_entity_id}" if answer_entity_id is not None else answer_entity
        answers.append(new_answer)

        answer_linking_objs.append({
            "entity_linking_reason": entity_linking_reason,
            "wikidata_query_results": result_dicts
        })

    dataset_question = next((dataset_question for dataset_question in dataset_questions if dataset_question["uid"] == question["uid"]), None)
    
    entity_id = question["main_entity_id"]
    ner_entity_info = None

    ner_entity_info = {
        "main_entity": question["main_entity"],
        "main_entity_id": entity_id if entity_id is not None else None
    }

    #answers = default_solved_question["solved_answer"]
    original_answers = question.get("solved_answer")

    solved_question = calc_question_f1_score(dataset_question, answers, original_answers, reason, answers_datatype, extra_info, ner_entity_info, react_info = question.get("react_info"), answer_linking_objs=answer_linking_objs, use_original_answers=True, original_f1_score=question.get("f1"))
    #solved_questions[index] = solved_question

    solved_questions.append(solved_question)

    total_token_count += total_question_token

# for index, question in enumerate(questions):
#     process_question(question)
#     print(f"Processed {index + 1}/{len(questions)} questions")

batch_size = 5 # Might get rate limited above that
start_time = time.time()

# sepparate the data in groups 
batches = [questions[i:i + batch_size] for i in range(0, len(questions), batch_size)]

# process each batch in parallel
for i, batch in enumerate(batches):

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_question, question) for question in batch]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error occurred in sub-thread: {e}")
    
    print(f"Processed {i + 1}/{len(batches)} batches")

# Sort by uid, fix sort for nb < 100 by adding zeros
sort_questions(solved_questions)

if len(solved_questions) == 0:
    print("No questions to process")
    sys.exit()

print(f"Total time taken: {time.time() - start_time}")
print(f"Total token count: {total_token_count}")

# calc macro f1
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)

from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
from datetime import datetime

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj
from qa_utils import print_solved_question,sort_questions, process_question_with_entity_properties, process_question_react

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format, get_cached_entity_labels_dict, save_cached_entity_labels_dict

# qald_10_train, qald_10_test, original_qald_9_plus_train, original_qald_9_plus_test
dataset_name = "react_questions"
use_react = True
directly_from_wikidata = True
add_properties_on_fallback = False # Whether to add all wikidata properties when react fails, or just use pure llm as fallback

input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_filename = f'{dataset_name}_solved_answers.json'

# Default answers when no entity linking is found
no_extra_info_solved_answers_filename = f'{dataset_name}_solved_answers_no_external_info.json'
with open(no_extra_info_solved_answers_filename, 'r', encoding='utf-8') as file:
    question_answers_no_extra_info = json.load(file)

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_with_properties_info" if not use_react else "results_with_react"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

# questions = questions[:10] # First 10 questions only
    
using_wikidata_text = "_using_wikidata" if directly_from_wikidata else ""
ner_file = f"{dataset_name}_NER_both{using_wikidata_text}.json"

# open ner_file
with open(ner_file, 'r', encoding='utf-8') as file:
    both_entities_full_info = json.load(file)

solved_questions = []
total_token_count = 0
total_questions_with_tokens = 0
total_questions_react_failed = 0

info_messages_dir = "info_msg_with_token_count/" + current_time
# Create dir if doesn't exist
if not os.path.exists(info_messages_dir):
    os.makedirs(info_messages_dir)

cached_entity_labels_dict = get_cached_entity_labels_dict()

def process_question(question, use_fallback = False):
    global total_token_count, total_questions_with_tokens, total_questions_react_failed

    # find entity where question uid matches question_id
    ner_entity_info = next((entity for entity in both_entities_full_info if entity["question_id"] == question["uid"]), None)
    entity_id = ner_entity_info["main_entity_id"]

    # Use guessed answers as fallback in case the entity linking failed
    if entity_id is None or (use_fallback and not add_properties_on_fallback):
        #answers = ner_entity_info["guessed_answers"]
        #reason = ner_entity_info["reason"]
        #answers_datatype = extra_info = None
        default_solved_questions = question_answers_no_extra_info["solved_questions"]
        # Find the question in the solved questions
        default_solved_question = next((default_question for default_question in default_solved_questions if default_question["uid"] == question["uid"]), None)
        answers = default_solved_question["solved_answer"]
        original_answers = default_solved_question.get("unmodified_solved_answer")
        reason = default_solved_question["reasoning"]
        answers_datatype = default_solved_question["answers_datatype"]
        extra_info = default_solved_question["extra_info"]
    else:
        # Use react to answer the question (unless it already failed, then use fallback)
        if use_react and not use_fallback:
            answers, original_answers, reason, answers_datatype, extra_info, token_count = process_question_react(question, ner_entity_info, info_messages_dir, cached_entity_labels_dict)
        else:
            answers, original_answers, reason, answers_datatype, extra_info, token_count = process_question_with_entity_properties(question, ner_entity_info, info_messages_dir, directly_from_wikidata)

        total_token_count += token_count

        # Use fallback if an issue occured while processing the question
        if answers is None:
            process_question(question, True)
            total_questions_react_failed += 1
            return
        else:
            total_questions_with_tokens += 1

    solved_question = calc_question_f1_score(question, answers, original_answers, reason, answers_datatype, extra_info, ner_entity_info)
    solved_questions.append(solved_question)

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

# Save the cached entity labels
save_cached_entity_labels_dict(cached_entity_labels_dict)

# # Print questions info
# for question in solved_questions:
#     print_solved_question(question)

if len(solved_questions) == 0:
    print("No questions to process")
    sys.exit()

# Total token count + average token count
print(f"Total token count: {total_token_count}")
print(f"Average token count: {total_token_count / total_questions_with_tokens}")
print(f"Total questions with tokens: {total_questions_with_tokens}")
print(f"Total questions react failed: {total_questions_react_failed}")

# calc macro f1
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1, total_token_count, total_questions_with_tokens, total_questions_react_failed)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)

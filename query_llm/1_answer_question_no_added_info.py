from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj, print_solved_question

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_10_test
dataset_name = "qald_9_plus_train_with_long_answer"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_solved_answers_filename = f'{dataset_name}_solved_answers.json'

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

# prompt
prompt = prompt_config["vanilla_kgqa"]

# Only first 10 questions
#questions = questions[:10]

solved_questions = []

def process_question(question):
    convo_history = [format_msg_oai("user", "User's question: " + question["question"]), format_msg_oai("user", prompt)]
    result = send_open_ai_gpt_message(convo_history, json_mode=True)

    extracted_json = extract_json_from_response("vanilla_kgqa", result["content"])

    reason = extracted_json.get("reason", "")
    gpt_answers = extracted_json.get("answers", [])

    # Check if any of the gpt answers has parenthesis and remove them
    if any("(" in answer for answer in gpt_answers):
        print(f"Removing parenthesis in question {question['uid']}. Original answers: {gpt_answers}")

    # Use regex to remove all parenthesis and their content
    gpt_answers = [re.sub(r'\([^)]*\)', '', answer).strip() for answer in gpt_answers]

    # Remove empty answers
    gpt_answers = [answer for answer in gpt_answers if answer != ""]

    solved_question = calc_question_f1_score(question, gpt_answers, reason)
    solved_questions.append(solved_question)

batch_size = 5
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

# Sort solved questions by uid
solved_questions.sort(key=lambda x: x["uid"])

# Print questions info
for question in solved_questions:
    print_solved_question(question)

print(f"Total time: {time.time() - start_time} seconds")

# Calc macro f1 score
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1)

# Save the solved questions
with open(output_solved_answers_filename, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)
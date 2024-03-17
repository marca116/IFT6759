from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from datetime import datetime
import os

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj
from qa_utils import print_solved_question, format_gpt_answers

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_9_plus_train_with_long_answer, qald_10_test
dataset_name = "qald_10_test"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_solved_answers_filename = f'{dataset_name}_solved_answers.json'

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_ner_guesses_only"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_solved_answers_filename

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

ner_file = f"NER_both.json"

# open ner_file
with open(ner_file, 'r', encoding='utf-8') as file:
    both_entities_full_info = json.load(file)

solved_questions = []

for question in questions:
    # find entity where question uid matches question_id
    entity_info = next((entity for entity in both_entities_full_info if entity["question_id"] == question["uid"]), None)

    original_gpt_answers = entity_info["guessed_answers"]
    #answers_datatype = entity_info.get("datatype")
    reason = entity_info["reason"]

    # Fix answers formatting
    gpt_answers = format_gpt_answers(original_gpt_answers, question['uid']) #, answers_datatype)

    solved_question = calc_question_f1_score(question, gpt_answers, reason)
    solved_questions.append(solved_question)

# print solved questions
for question in solved_questions:
    print_solved_question(question)

# calc macro f1
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)
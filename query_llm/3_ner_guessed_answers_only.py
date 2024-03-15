from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, print_solved_question, get_final_solved_questions_obj

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_10_test
dataset_name = "qald_9_plus_train_with_long_answer"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_solved_answers_filename = f'{dataset_name}_solved_answers_NER.json'

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

    guessed_answers = entity_info["guessed_answers"]
    reason = entity_info["reason"]

    solved_question = calc_question_f1_score(question, guessed_answers, reason)
    solved_questions.append(solved_question)

# print solved questions
for question in solved_questions:
    print_solved_question(question)

# calc macro f1
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1)

with open(output_solved_answers_filename, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)
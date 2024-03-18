from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj
from qa_utils import print_solved_question, create_qa_convo_history, extract_info_qa_response, sort_questions

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_9_plus_train_with_long_answer, qald_10_test
dataset_name = "qald_9_plus_train_with_long_answer"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_filename = f'{dataset_name}_solved_answers.json'

# Add to root to use as default answers in step 4
no_extra_info_solved_answers_filename = f'{dataset_name}_solved_answers_no_external_info.json'

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_no_external_info"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

# Load questions
with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

for question in questions:
    question["uid"] = str(question["uid"])

with open(input_dataset_filename, 'w', encoding='utf-8') as outfile:
    json.dump(questions, outfile, indent=4)

# Only first 10 questions
# questions = questions[:1]

solved_questions = []
total_token_count = 0

def process_question(question):
    global total_token_count
    
    convo_history = create_qa_convo_history(prompt_config, question)
    current_tokens_count = count_tokens(convo_history)
    total_token_count += current_tokens_count

    result = send_open_ai_gpt_message(convo_history, json_mode=True)

    gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info = extract_info_qa_response(result, question)

    solved_question = calc_question_f1_score(question, gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info)
    solved_questions.append(solved_question)

start_time = time.time()

# for index, question in enumerate(questions):
#     process_question(question)
#     print(f"Processed {index + 1}/{len(questions)} questions")

# sepparate the data in groups 
batch_size = 5
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
sort_questions(solved_questions)

# Print questions info
for question in solved_questions:
    print_solved_question(question)

if len(solved_questions) == 0:
    print("No questions to process")
    sys.exit()

# Total token count + average token count
print(f"Total token count: {total_token_count}")
print(f"Average token count: {total_token_count / len(questions)}")
print(f"Total questions with tokens: {len(questions)}")

print(f"Total time: {time.time() - start_time} seconds")

# Calc macro f1 score
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1, total_token_count, len(questions))

# Save the solved questions
with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)

# Use as default answers in step 4
with open(no_extra_info_solved_answers_filename, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)
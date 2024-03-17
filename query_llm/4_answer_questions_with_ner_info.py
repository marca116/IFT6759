from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
from datetime import datetime

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj
from qa_utils import print_solved_question, create_qa_convo_history, extract_info_qa_response, sort_questions

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_9_plus_train_with_long_answer, qald_10_test
dataset_name = "qald_9_plus_train_with_long_answer"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_filename = f'{dataset_name}_solved_answers.json'

# Default answers when no entity linking is found
no_extra_info_solved_answers_filename = f'{dataset_name}_solved_answers_no_external_info.json'
with open(no_extra_info_solved_answers_filename, 'r', encoding='utf-8') as file:
    question_answers_no_extra_info = json.load(file)

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_with_properties_info"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

qald_unique_entities_info_dir = '../qald_unique_entities_info'

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

# questions = questions[:10] # First 10 questions only

ner_file = f"{dataset_name}_NER_both.json"

# open ner_file
with open(ner_file, 'r', encoding='utf-8') as file:
    both_entities_full_info = json.load(file)

solved_questions = []
total_token_count = 0
total_questions_with_tokens = 0

# Properties that makes the token count too high to process (Ex : For Germany (Q183))
    # P530 = diplomatic relation
    # P1448 = official name in it's original language (not that useful anyways)
    # P1549 = demonym (the way to adress the people of the country)
    # P998 = curlie (not that useful + take a bunch of space)
    # P41 = flag image, not really relevant
properties_to_skip = ["P530", "P1448", "P1549", "P998", "P41"]

# Keep only the top 10 instances for these properties
    # P2936 = language used (too many for big countries (USA))
    # P608 = Time zone (too many for big countries)
properties_top_10_only = ["P2936", "P421"]

# Remove some qualfiers that are not that useful
    # P2241 = Reason for deprecation
    # P459 = determination method (could potentially be useful in some context, but takes way too much space (ex : population in canada))
qualifiers_to_skip = ["P2241", "P459"]

# Whether to remove id properties from the output
remove_id_properties = True

info_messages_dir = "info_msg_with_token_count/" + current_time
# Create dir if doesn't exist
if not os.path.exists(info_messages_dir):
    os.makedirs(info_messages_dir)

# Save info messages with token counts (when token count is too high)
def save_info_messages_with_token_counts(info_messages, question, entity_id, info_tokens_count, convo_tokens_count):
    info_msg_with_token_counts = [{"token_count": count_tokens([msg]), "msg_content": msg} for msg in info_messages]
    info_msg_with_token_counts.sort(key=lambda x: x["token_count"], reverse=True)

    root_obj = {
        "question": question["question"],
        "uid": question["uid"],
        "entity_id": entity_id,
        "info_tokens_count": info_tokens_count,
        "convo_total_tokens_count": convo_tokens_count,
        "info_messages": info_msg_with_token_counts
    }

    # save to file
    with open(f"{info_messages_dir}/info_messages_{question['uid']}.json", 'w', encoding='utf-8') as outfile:
        json.dump(root_obj, outfile, indent=4)

def process_question_with_entity_properties(question, ner_entity_info):
    global total_token_count, total_questions_with_tokens

    entity_id = ner_entity_info["main_entity_id"]
    entity_info = {}
     
    with open(f"{qald_unique_entities_info_dir}/{entity_id}.json", 'r', encoding='utf-8') as file:
        entity_info = json.load(file)

    info = f"Wikidata id:{entity_info['id']}, label: {entity_info['label']}, aliases: {', '.join(entity_info.get('aliases', []))}, description: {entity_info['description']}"
    info_messages = [format_msg_oai("user", info)]

    if entity_id == "Q64":
        test = ""

    removed_id_properties = []

    for root_property in entity_info['properties']:
        root_id = root_property["id"]

        if root_id == "P1082":
            test = ""

        # Properties that makes the token count too high to process
        if root_id in properties_to_skip:
            continue

        root_label = root_property["label"]

        # Skip the id properties, not very relevant to questions we want to answer
        if remove_id_properties and (" ID " in root_label or root_label.endswith("ID")):
            removed_id_properties.append(root_label)
            continue

        root_text = f"Property: {root_label} ({root_id})\n"
        instances_texts = []

        for index, property_instance in enumerate(root_property["instances"]):
            # Keep only the top 10 instances for these properties
            if index == 10 and root_id in properties_top_10_only:
                break

            # Skip deprecated rank (-1)
            if property_instance.get("rank") == -1:
                continue

            value = property_instance.get("value_label", property_instance.get("value"))

            # Remove the + at the start
            if property_instance["type"] in ["time", "quantity"]:
                value = value.replace("+", "")

            qualifiers_texts = []

            if property_instance.get("rank") == 1:
                qualifiers_texts.append("current value")

            for qualifier in property_instance.get("qualifiers", []):
                if qualifier["id"] in qualifiers_to_skip:
                    continue

                qualifier_value = qualifier.get("value_label", qualifier.get("value"))

                # Remove the + at the start
                if qualifier["type"] in ["time", "quantity"]:
                    qualifier_value = qualifier_value.replace("+", "")

                qualifiers_texts.append(f"{qualifier['label']}: {qualifier_value}")

            formatted_qualifiers = (" (" + ", ".join(qualifiers_texts) + ")") if len(qualifiers_texts) > 0 else ""

            #value_rank_text = "*" if property_instance.get("rank", 0) == 1 else ""
            #instances_texts.append(f"{value}{value_rank_text}{formatted_qualifiers}")
            instances_texts.append(f"{value}{formatted_qualifiers}")

        root_text += "\n".join(instances_texts)

        info_messages.append(format_msg_oai("user", root_text))
        #info += "\n" + root_text

    #info_messages = [format_msg_oai("user", "")]

    # Save info messages with token counts
    # save_info_messages_with_token_counts(info_messages, question)

    convo_history = create_qa_convo_history(prompt_config, question, True, info_messages)

    info_tokens_count = count_tokens(info_messages)
    current_tokens_count = count_tokens(convo_history)
    total_token_count += current_tokens_count
    total_questions_with_tokens += 1

    # print("--------------------")
    # print(f"Processing question {question['uid']}")
    # print(f"Total convo tokens count: {current_tokens_count}, Info tokens count: {info_tokens_count}, Info user msg count: {len(info_messages)}")

    # Save info messages used for the question with token counts
    save_info_messages_with_token_counts(info_messages, question, entity_id, info_tokens_count, current_tokens_count)

    if current_tokens_count > 16380:
        print(f"Skipping question {question['uid']}, token count too high: {current_tokens_count}")
        return [], "Total tokens count too high"

    #return [], "Success"

    # Send message to API
    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    gpt_answers, reason, answers_datatype, extra_info = extract_info_qa_response(result, question)

    return gpt_answers, reason, answers_datatype, extra_info

def process_question(question):
    # find entity where question uid matches question_id
    ner_entity_info = next((entity for entity in both_entities_full_info if entity["question_id"] == question["uid"]), None)
    entity_id = ner_entity_info["main_entity_id"]

    # Use guessed answers as fallback in case the entity linking failed
    if entity_id is None:
        #answers = ner_entity_info["guessed_answers"]
        #reason = ner_entity_info["reason"]
        #answers_datatype = extra_info = None
        default_solved_questions = question_answers_no_extra_info["solved_questions"]
        # Find the question in the solved questions
        default_solved_question = next((default_question for default_question in default_solved_questions if default_question["uid"] == question["uid"]), None)
        answers = default_solved_question["solved_answer"]
        reason = default_solved_question["reasoning"]
        answers_datatype = default_solved_question["answers_datatype"]
        extra_info = default_solved_question["extra_info"]
    else:
        answers, reason, answers_datatype, extra_info = process_question_with_entity_properties(question, ner_entity_info)

    solved_question = calc_question_f1_score(question, answers, reason, answers_datatype, extra_info)
    solved_questions.append(solved_question)

for index, question in enumerate(questions):
    process_question(question)
    print(f"Processed {index + 1}/{len(questions)} questions")

# batch_size = 2 # Get rate limited above that (160k TPM atm)
# start_time = time.time()

# # sepparate the data in groups 
# batches = [questions[i:i + batch_size] for i in range(0, len(questions), batch_size)]

# # process each batch in parallel
# for i, batch in enumerate(batches):

#     with ThreadPoolExecutor() as executor:
#         futures = [executor.submit(process_question, question) for question in batch]

#         for future in as_completed(futures):
#             try:
#                 future.result()
#             except Exception as e:
#                 print(f"Error occurred in sub-thread: {e}")
    
#     print(f"Processed {i + 1}/{len(batches)} batches")
 
# Sort by uid, fix sort for nb < 100 by adding zeros
sort_questions(solved_questions)

# Print questions info
for question in solved_questions:
    print_solved_question(question)

if len(solved_questions) == 0:
    print("No questions to process")
    sys.exit()

# Total token count + average token count
print(f"Total token count: {total_token_count}")
print(f"Average token count: {total_token_count / total_questions_with_tokens}")
print(f"Total questions with tokens: {total_questions_with_tokens}")

# calc macro f1
macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1, total_token_count, total_questions_with_tokens)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)
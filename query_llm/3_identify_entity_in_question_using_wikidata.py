from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re

from qa_utils import identify_entity, download_entities_info, find_main_entity_id

sys.path.insert(0, "../utils")
from utils import run_sparql_query, get_cached_entity_labels_dict, save_cached_entity_labels_dict

input_dir = '../qald_unique_entities_info'
prompt_config = read_json('prompts.json')

if len(sys.argv) != 2:
    print("Usage: python 3_identify_entity_in_question_using_wikidata.py <dataset_name>")
    sys.exit(1)

dataset_name = sys.argv[1]
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
# output_solved_answers_filename = f'{dataset_name}_solved_answers.json'

using_wikidata = "_using_wikidata"

# Create NER_results folder if it doesn't exist
ner_root_dir = f"NER_results" + using_wikidata
if not os.path.exists(ner_root_dir):
    os.makedirs(ner_root_dir)

wikidata_entities_dir = f"wikidata_entities"
if not os.path.exists(wikidata_entities_dir):
    os.makedirs(wikidata_entities_dir)

# Load questions
with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

#questions = questions[0:1]

found_entities_full_info = []
missing_entities_full_info = []
total_token_count = 0

def process_question(question):
    global total_token_count

    main_entity, side_entities, guessed_answers, identify_entity_reason, identify_entity_tokens_count = identify_entity(question, prompt_config)
    total_token_count += identify_entity_tokens_count

    main_entity_id, entity_linking_reason, entity_linking_tokens_count, result_dicts = find_main_entity_id(question, main_entity, prompt_config)
    total_token_count += entity_linking_tokens_count

    full_info = {
        "question": question["question"],
        "question_id": question["uid"],
        "main_entity": main_entity,
        "main_entity_id": main_entity_id,
        "is_label": False, # Set correctly later
        "side_entities": side_entities,
        "guessed_answers": guessed_answers,
        "identify_entity_reason": identify_entity_reason,
        "wikidata_query_results": result_dicts,
        "entity_linking_reason": entity_linking_reason,
    }

    if main_entity_id is None:
        missing_entities_full_info.append(full_info)
    else:
        found_entities_full_info.append(full_info)

# PROCESSING

# for question in questions:
#     process_question(question)
    
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

if len(questions) == 0:
    print("No questions to process")
    sys.exit()

# Load the cached entity labels
cached_entity_labels_dict = get_cached_entity_labels_dict()

# Download the found entities
found_entity_ids = list(set([question["main_entity_id"].strip() for question in found_entities_full_info]))    
download_entities_info(found_entity_ids, wikidata_entities_dir, cached_entity_labels_dict)

save_cached_entity_labels_dict(cached_entity_labels_dict)

# Total token count + average token count
print(f"Total token count: {total_token_count}")
print(f"Average token count: {total_token_count / len(questions) if len(questions) > 0 else 0}")

# print count
print(f"Found entities: {len(found_entities_full_info)}")
print(f"Missing entities: {len(missing_entities_full_info)}")
print(f"Total questions with tokens: {len(questions)}")

# sort
found_entities_full_info.sort(key=lambda x: x["question_id"].zfill(3)) 
missing_entities_full_info.sort(key=lambda x: x["question_id"].zfill(3)) 

both_entities_full_info = found_entities_full_info + missing_entities_full_info
both_entities_full_info.sort(key=lambda x: x["question_id"].zfill(3)) 

# Create folder with curr time if it doesnt exist
current_time = time.strftime("%Y%m%d-%H%M%S")
ner_results_dir = f"{ner_root_dir}/{current_time}_{dataset_name}"

if not os.path.exists(ner_results_dir):
    os.makedirs(ner_results_dir)

# SAVE TO FILE
with open(f"{ner_results_dir}/NER_count.txt", 'w', encoding='utf-8') as file:
    file.write(f"Found entities: {len(found_entities_full_info)}\n")
    file.write(f"Missing entities: {len(missing_entities_full_info)}\n")
    file.write(f"Total token count: {total_token_count}\n")
    file.write(f"Average token count: {total_token_count / len(questions)}\n")
    file.write(f"Total questions with token: {len(questions)}")

with open(f"{ner_results_dir}/NER_failed.json", 'w', encoding='utf-8') as file:
    json.dump(missing_entities_full_info, file, ensure_ascii=False, indent=4)

with open(f"{ner_results_dir}/NER_success.json", 'w', encoding='utf-8') as file:
    json.dump(found_entities_full_info, file, ensure_ascii=False, indent=4)

with open(f"{ner_results_dir}/NER_both.json", 'w', encoding='utf-8') as file:
    json.dump(both_entities_full_info, file, ensure_ascii=False, indent=4)

print(f"Results saved to {ner_results_dir}")

# Overwrite current NER_both file
with open(f"{dataset_name}_NER_both{using_wikidata}.json", 'w', encoding='utf-8') as file:
    json.dump(both_entities_full_info, file, ensure_ascii=False, indent=4)
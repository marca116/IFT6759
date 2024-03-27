from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from qa_utils import identify_entity

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

input_dir = '../qald_unique_entities_info'

prompt_config = read_json('prompts.json')

# qald_10_train, qald_10_test, original_qald_9_plus_train, original_qald_9_plus_test
dataset_name = "qald_10_test"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_solved_answers_filename = f'{dataset_name}_solved_answers.json'

# Create NER_results folder if it doesn't exist
ner_root_dir = f"NER_results"
if not os.path.exists(ner_root_dir):
    os.makedirs(ner_root_dir)

# Create folder with curr time if it doesnt exist
current_time = time.strftime("%Y%m%d-%H%M%S")
ner_results_dir = f"{ner_root_dir}/{current_time}_{dataset_name}"

if not os.path.exists(ner_results_dir):
    os.makedirs(ner_results_dir)

# Load questions
with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

#questions = questions[:10]
    
# Load entities
all_entity_files = os.listdir(input_dir)
all_entities = []

# load json for each entities
for entity_file in all_entity_files:
    with open(f"{input_dir}/{entity_file}", 'r', encoding='utf-8') as file:
        entity_info = json.load(file)
        all_entities.append(entity_info)

found_entities_full_info = []
missing_entities_full_info = []

# FUNCTION DEFINITIONS

total_token_count = 0

def find_main_entity_id(main_entity_name, all_entities):
    if not main_entity_name:
        return None, False

    # Try to match label in a case insensitive way
    for entity in all_entities:
        if entity["label"].lower() == main_entity_name.lower():
            return entity["id"], True
        
    # Try to match aliases in a case insensitive way
    for entity in all_entities:
        lowercase_aliases = [alias.lower() for alias in entity.get("aliases", [])]
        
        if main_entity_name.lower() in lowercase_aliases:
            return entity["id"], False

    return None, False

def process_question(question):
    global total_token_count

    main_entity, side_entities, guessed_answers, reason, current_tokens_count = identify_entity(question, prompt_config)
    total_token_count += current_tokens_count

    main_entity_id, is_label = find_main_entity_id(main_entity, all_entities)

    full_info = {
        "question": question["question"],
        "question_id": question["uid"],
        "main_entity": main_entity,
        "main_entity_id": main_entity_id,
        "is_label": is_label,
        "side_entities": side_entities,
        "guessed_answers": guessed_answers,
        "reason": reason
    }

    # # Print question, main entity, main entity id, side entities and reasoning
    # print(full_info["question"])
    # print(f"Main entity: {main_entity}")
    # print(f"Main entity id: {main_entity_id}")
    # print(f"Is label: {is_label}")
    # print(f"Side entities: {side_entities}")
    # print(f"Guessed answers: {guessed_answers}")
    # print(f"reason: {reason}")
    # print(f"datatype: {datatype}")
    # print("-------------------")

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

# Total token count + average token count
print(f"Total token count: {total_token_count}")
print(f"Average token count: {total_token_count / len(questions)}")

# print count
print(f"Found entities: {len(found_entities_full_info)}")
print(f"Missing entities: {len(missing_entities_full_info)}")
print(f"Total questions with tokens: {len(questions)}")

# sort
found_entities_full_info.sort(key=lambda x: x["question_id"].zfill(3)) 
missing_entities_full_info.sort(key=lambda x: x["question_id"].zfill(3)) 

both_entities_full_info = found_entities_full_info + missing_entities_full_info
both_entities_full_info.sort(key=lambda x: x["question_id"].zfill(3)) 

# SAVE TO FILE
with open(f"{ner_results_dir}/NER_count.txt", 'w', encoding='utf-8') as file:
    file.write(f"Found entities: {len(found_entities_full_info)}\n")
    file.write(f"Missing entities: {len(missing_entities_full_info)}\n")
    file.write(f"Total token count: {total_token_count}\n")
    file.write(f"Average token count: {total_token_count / len(questions)}\n")
    file.write(f"Total questions with token: {questions}")

with open(f"{ner_results_dir}/NER_failed.json", 'w', encoding='utf-8') as file:
    json.dump(missing_entities_full_info, file, ensure_ascii=False, indent=4)

with open(f"{ner_results_dir}/NER_success.json", 'w', encoding='utf-8') as file:
    json.dump(found_entities_full_info, file, ensure_ascii=False, indent=4)

with open(f"{ner_results_dir}/NER_both.json", 'w', encoding='utf-8') as file:
    json.dump(both_entities_full_info, file, ensure_ascii=False, indent=4)

print(f"Results saved to {ner_results_dir}")

# Overwrite current NER_both file
with open(f"{dataset_name}_NER_both.json", 'w', encoding='utf-8') as file:
    json.dump(both_entities_full_info, file, ensure_ascii=False, indent=4)
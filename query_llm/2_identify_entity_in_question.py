from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

input_dir = '../qald_unique_entities_info'

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_9_plus_train_with_long_answer, qald_10_test
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
    
prompt = prompt_config["identify_entities"]

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

def identify_entity(question):
    global total_token_count

    question_text = question["question"]

    # Examples
    example_question_text = prompt_config["identify_entities_example_question"]
    example_output_text = prompt_config["identify_entities_example_answer"]
    examples_history = [format_msg_oai("user", "History: [" + example_question_text + "]"), format_msg_oai("assistant", "History: [" + example_output_text + "]")]

    # Convo history
    convo_history = [format_msg_oai("user", "Previous user's question: " + question_text), format_msg_oai("user", prompt)]
    convo_history = examples_history + convo_history

    current_tokens_count = count_tokens(convo_history)
    total_token_count += current_tokens_count

    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    extracted_json = extract_json_from_response("identify_entities", result["content"])

    main_entity = extracted_json.get("main_entity_label", "")
    #print(f"Main entity: {main_entity}")

    side_entities = extracted_json.get("side_entities_labels", [])
    #print(f"Side entities: {side_entities}")

    reason = extracted_json.get("reason", "")
    #answers_datatype = extracted_json.get("answers_datatype", "")
    correct_answers = extracted_json.get("correct_answers", [])

    return main_entity, side_entities, correct_answers, reason#, answers_datatype

def find_main_entity_id(main_entity_name, question, all_entities):
    # question_text = question["question"]

    # Try with label
    for entity in all_entities:
        if entity["label"] == main_entity_name:
            return entity["id"], True

    # Try with aliases
    for entity in all_entities:
        if main_entity_name in entity.get("aliases", []):
            return entity["id"], False

    return None, False

def process_question(question):
    #main_entity, side_entities, guessed_answers, reason, datatype = identify_entity(question)
    main_entity, side_entities, guessed_answers, reason = identify_entity(question)
    main_entity_id, is_label = find_main_entity_id(main_entity, question, all_entities)

    full_info = {
        "question": question["question"],
        "question_id": question["uid"],
        "main_entity": main_entity,
        "main_entity_id": main_entity_id,
        "is_label": is_label,
        "side_entities": side_entities,
        "guessed_answers": guessed_answers,
        "reason": reason
        #"datatype": datatype
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
print(f"Total questions with tokens: {len(questions)}")

# print count
print(f"Found entities: {len(found_entities_full_info)}")
print(f"Missing entities: {len(missing_entities_full_info)}")

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
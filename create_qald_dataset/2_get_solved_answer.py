import requests
import os
import json
import time
from urllib.parse import unquote
import csv
import sys

sys.path.insert(0, "../utils")
from utils import get_wikidata_entities_info

dataset_name = 'qald_10_test' # qald_9_plus_train_wikidata and qald_10_test
formatted_dataset = f'{dataset_name}_formatted_and_cleaned.json'
unique_entities_and_url_filename = f'{dataset_name}_answers_unique_entities_and_url.csv'
solved_answers_dataset = f'{dataset_name}_with_solved_answers.json'

with open(formatted_dataset, 'r', encoding='utf-8') as file:
    data = json.load(file)

max_entity_per_group = 50
start_time = time.time()

unique_entities_and_url = []

for q_index, question in enumerate(data):
    answers = question['answer']
    entity_ids = []
    non_entity_answers = []

    for answer in answers:
        if isinstance(answer, str) and answer.startswith("http://www.wikidata.org/entity/"):
            entity_id = answer.split("/")[-1]
            entity_ids.append(entity_id)
        else:
            non_entity_answers.append(answer)

    # combine in groups of entity_per_group (in case higher than max_entity_per_group)
    entity_ids_groups = []
    for x in range(0, len(entity_ids), max_entity_per_group):
        entity_ids_group = entity_ids[x:x+max_entity_per_group]
        entity_ids_groups.append("|".join(entity_ids_group))

    # get the results for each group
    for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
        results = get_wikidata_entities_info(entity_ids_group, allow_fallback_language=True) # Fallback to whatever language is available if label missing

        for result in results:
            entity_id, entity_label, title, wiki_url = result
            question["solved_answer"].append(entity_label)

            # if entityid not already in the unique_entities_and_url list, add the result tuple to it
            if entity_id not in [x[0] for x in unique_entities_and_url]:
                unique_entities_and_url.append((entity_id, entity_label, title, wiki_url))

    # add non-entity answers to solved_answer at the end
    for non_entity_answer in non_entity_answers:
        question["solved_answer"].append(non_entity_answer)

    print(f"Processed {q_index+1}/{len(data)} questions")

# save unique_entities_and_url
for result in unique_entities_and_url:
    entity_id, entity_label, title, wiki_url = result
    with open(unique_entities_and_url_filename, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([entity_id, entity_label, title, wiki_url])

# Save to solved_answers_dataset
with open(solved_answers_dataset, 'w', encoding='utf-8') as outfile:
    json.dump(data, outfile, indent=4)

print(f"Total time: {time.time() - start_time} seconds")
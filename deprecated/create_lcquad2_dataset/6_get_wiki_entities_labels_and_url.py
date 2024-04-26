import requests
import os
import json
import time
from urllib.parse import unquote
import csv
import sys

sys.path.insert(0, "../utils")
from utils import get_wikidata_entities_info

input_filename = 'train_cleaned_only_questions_with_answers.json'
output_filename = 'answer_entities_labels_and_url.csv'

with open(input_filename, 'r', encoding='utf-8') as file:
    data = json.load(file)

entity_ids = []

for question in data:
    answers_obj = question['answer']
    # Shouldn't happen, questions with no answers should have been removed
    if answers_obj is None or len(answers_obj) == 0:
        print(f"Failed to find answer for {question['uid']}: {question['question']}")
        continue

    for answer in answers_obj:
        # continue is not a string
        if not isinstance(answer, str):
            continue

        # Check if the answer is wikidata uri
        if answer.startswith('http://www.wikidata.org/entity/'):
            #print(f"Answer for {question['uid']} is a URI: {answer}")
            answer_id = answer.split('/')[-1]

            # Add to the list if it's not already there
            if answer_id not in entity_ids:
                entity_ids.append(answer_id)

print(f"Total entities: {len(entity_ids)}")

entity_per_group = 50
start_time = time.time()

# combine in groups of entity_per_group
entity_ids_groups = []
for x in range(0, len(entity_ids), entity_per_group):
    entity_ids_group = entity_ids[x:x+entity_per_group]
    entity_ids_groups.append("|".join(entity_ids_group))

total_groups = len(entity_ids_groups)

# create emmpty file output_filename
with open(output_filename, 'w', encoding='utf-8', newline='') as f:
    pass

for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
    results = get_wikidata_entities_info(entity_ids_group)

    for result in results:
        entity_id, entity_label, title, wiki_url = result
        
        with open(output_filename, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([entity_id, entity_label, title, wiki_url])

    print(f"Processed {x}/{total_groups} groups ({entity_per_group} articles each)")

print(f"Total time: {time.time() - start_time} seconds")
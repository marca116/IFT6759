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
missing_entities_ids_name = dataset_name + "_missing_entities_ids.txt"
missing_entities_ids_with_urls_name = dataset_name + "_missing_entities_ids_with_urls.txt"

missing_entities_ids = []

with open(missing_entities_ids_name, 'r', encoding='utf-8') as file:
    lines = file.readlines() 

    for x, line in enumerate(lines, start=1):
        entity_id = line.strip()
        missing_entities_ids.append(entity_id)

max_entity_per_group = 50
start_time = time.time()

missing_entities_and_url = []

# combine in groups of entity_per_group (in case higher than max_entity_per_group)
entity_ids_groups = []
for x in range(0, len(missing_entities_ids), max_entity_per_group):
    entity_ids_group = missing_entities_ids[x:x+max_entity_per_group]
    entity_ids_groups.append("|".join(entity_ids_group))

# get the results for each group
for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
    results = get_wikidata_entities_info(entity_ids_group, allow_fallback_language=True) # Fallback to whatever language is available if label missing

    for result in results:
        entity_id, entity_label, title, wiki_url = result
        missing_entities_and_url.append((entity_id, entity_label, title, wiki_url))

    print(f"Processed {x}/{len(entity_ids_groups)} groups")

# save unique_entities_and_url
for result in missing_entities_and_url:
    entity_id, entity_label, title, wiki_url = result
    with open(missing_entities_ids_with_urls_name, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([entity_id, title, wiki_url]) # skip the label, only need title and url

print(f"Total time: {time.time() - start_time} seconds")
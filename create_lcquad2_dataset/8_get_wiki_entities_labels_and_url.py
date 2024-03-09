import requests
import os
import json
import time
from urllib.parse import unquote
import csv
import sys

sys.path.insert(0, "../utils")
from utils import get_wikidata_entities_info

entity_per_group = 50

start_time = time.time()

with open('train_answer_all_entities.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines() 
    #total_entities = len(lines) 
    entity_ids = []
    for x, line in enumerate(lines, start=1):
        entity_id = line.strip()

        # Skip the first row
        if entity_id == "" or entity_id == "entity":
            continue

        entity_ids.append(entity_id)

    # combine in groups of entity_per_group
    entity_ids_groups = []
    for x in range(0, len(entity_ids), entity_per_group):
        entity_ids_group = entity_ids[x:x+entity_per_group]
        entity_ids_groups.append("|".join(entity_ids_group))

    total_groups = len(entity_ids_groups)

    for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
        results = get_wikidata_entities_info(entity_ids_group)

        for result in results:
            entity_id, entity_label, title, wiki_url = result
            
            with open('answer_entities_labels_and_url.csv', 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([entity_id, entity_label, title, wiki_url])

        print(f"Processed {x}/{total_groups} groups ({entity_per_group} articles each)")

print(f"Total time: {time.time() - start_time} seconds")
import os
import time
import json
import sys

sys.path.insert(0, "../utils")
from utils import get_wikidata_entities_all_info

input_unique_entities = 'qald_unique_entities.txt' # qald_9_plus_train_wikidata and qald_10_test
output_dir = 'qald_unique_entities_info'

# create output_dir if not exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

unique_entity_ids = []

with open(input_unique_entities, 'r', encoding='utf-8') as file:
    unique_entity_ids = file.readlines() 
    unique_entity_ids = [entity_id.strip() for entity_id in unique_entity_ids]

max_entity_per_group = 50
start_time = time.time()

unique_entities_info = []

# combine in groups of entity_per_group (in case higher than max_entity_per_group)
entity_ids_groups = []
for x in range(0, len(unique_entity_ids), max_entity_per_group):
    entity_ids_group = unique_entity_ids[x:x+max_entity_per_group]
    entity_ids_groups.append("|".join(entity_ids_group))

# get the results for each group
for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
    results = get_wikidata_entities_all_info(entity_ids_group)
    unique_entities_info += results

    print(f"Processed {x}/{len(entity_ids_groups)} groups")

print("Saving results...")

# Save each entity to a separate json file
for entity_info in unique_entities_info:
    entity_id = entity_info.get('id', "")

    link = entity_info["sitelinks"]
    del entity_info["sitelinks"]

    # Flatten labels (remove the 'en' level)
    entity_info['labels'] = entity_info['labels']['en']
    entity_info['label'] = entity_info['labels']['value'] # rename labels to label
    del entity_info['labels']

    # aliases
    if entity_info.get('aliases'):
        aliases = entity_info['aliases']['en']
        entity_info['aliases'] = [alias['value'] for alias in aliases]
    else:
        entity_info['aliases'] = []

    # descriptions
    if entity_info.get('descriptions'):
        entity_info['descriptions'] = entity_info['descriptions']['en']
        entity_info['description'] = entity_info['descriptions']['value'] # rename descriptions to description
    else:
        entity_info['description'] = ""
    del entity_info['descriptions']

    if link.get("enwiki") and link.get("enwiki").get("url"):
        entity_info["wiki_link"] = link["enwiki"]["url"] # rename enwiki to wiki_link
    else:
        entity_info["wiki_link"] = ""

    with open(f"{output_dir}/{entity_id}.json", 'w', encoding='utf-8') as file:
        json.dump(entity_info, file, ensure_ascii=False, indent=4)

print(f"Total time: {time.time() - start_time} seconds")
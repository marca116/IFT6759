import os
import time
import json
import sys

sys.path.insert(0, "../utils")
from utils import get_batched_entities_info, format_entity_infos

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

# Get all the given entities full info from wikidata
unique_entities_info = get_batched_entities_info(unique_entity_ids)

# Format the info correctly (ex:  Add labels to properties)
entities_info = format_entity_infos(unique_entities_info)

for entity_info in entities_info:
    entity_id = entity_info['id']
    
    with open(f"{output_dir}/{entity_id}.json", 'w', encoding='utf-8') as file:
        json.dump(entity_info, file, ensure_ascii=False, indent=4)

print(f"Total time: {time.time() - start_time} seconds")
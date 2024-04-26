import json
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

sys.path.insert(0, "../utils")
from utils import run_sparql_query

input_dir = 'qald_unique_entities_info'

def query_sparql_external_relations(entity_id):
	# Skip entities which I know will time out because there are too many external entities linking in
		# scholarly article, english and human
	if entity_id in ["Q13442814", "Q1860", "Q5"]:
		return []

	sparql_query = """
		SELECT DISTINCT ?property ?propertyLabel WHERE {
		?entity ?p wd:""" + entity_id + """ .
		?property wikibase:directClaim ?p .
		
		# Fetching English labels for each property
		SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
		} 
	"""

	properties = run_sparql_query(sparql_query, False)

	# sort properties alphabetically by property id
	external_relations_properties = sorted(properties, key=lambda x: x['propertyLabel'].split('/')[-1])

	return external_relations_properties

def process_question(entity_id):
	# direct_properties, direct_relations = query_sparql_properties(entity_id)
	external_relations_properties = query_sparql_external_relations(entity_id)

	entity_info = {}
	with open(f"{input_dir}/{entity_id}.json", 'r', encoding='utf-8') as file:
		entity_info = json.load(file)

	entity_info['external_relations'] = external_relations_properties

	with open(f"{input_dir}/{entity_id}.json", 'w', encoding='utf-8') as file:
		json.dump(entity_info, file, ensure_ascii=False, indent=4)

# Load all the filesnames in input dir
files = os.listdir(input_dir)
unique_entity_ids = [os.path.splitext(file)[0] for file in files]

# for entity_id in unique_entity_ids:
# 	process_question(entity_id)

batch_size = 5
start_time = time.time()

# sepparate the data in groups 
batches = [unique_entity_ids[i:i + batch_size] for i in range(0, len(unique_entity_ids), batch_size)]

# process each batch in parallel
for i, batch in enumerate(batches):
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_question, entity_id) for entity_id in batch]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error occurred in sub-thread: {e}")

    print(f"Processed {i + 1}/{len(batches)} batches")
    
# Copy qald_unique_entities_info folder to root folder
shutil.copytree(input_dir, '../qald_unique_entities_info')
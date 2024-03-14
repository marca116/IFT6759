import json
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "../utils")
from utils import run_sparql_query

input_dir = 'qald_unique_entities_info'

def get_properties_object(all_properties):
	combined_properties = {}

	for result in all_properties:
		property_id = result['property'].split('/')[-1]
		if property_id not in combined_properties:
			combined_properties[property_id] = {
				'id': property_id,
				'label': result['propertyLabel'],
				'values': []
			}
		# If simple value
		if not result['value'].startswith("http://www.wikidata.org/entity/"):
			combined_properties[property_id]['values'].append(result['value'])
		else:
			combined_properties[property_id]['values'].append({
				'id': result['value'],
				'label': result['valueLabel']
			})

	return combined_properties

def query_sparql_properties(entity_id):
	sparql_query = """
		SELECT ?property ?propertyLabel ?value ?valueLabel WHERE {
			wd:""" + entity_id + """ ?p ?statement .
			?statement ?ps ?value .
			?property wikibase:claim ?p.
			?property wikibase:statementProperty ?ps.
			SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
		}
	"""

	properties = run_sparql_query(sparql_query, False)
	#print(properties)

	# sort properties alphabetically by property id
	properties = sorted(properties, key=lambda x: x['propertyLabel'].split('/')[-1])

	direct_properties = []
	direct_relations = []

	for result in properties:
		if result['value'].startswith("http://www.wikidata.org/entity/"):
			direct_relations.append(result)
		else:
			direct_properties.append(result)

	# Combine all the same properties with the same id together
	direct_properties_objects = get_properties_object(direct_properties)
	direct_relations_objects = get_properties_object(direct_relations)

	return direct_properties_objects, direct_relations_objects

def query_sparql_external_relations(entity_id):
	sparql_query = """
		SELECT DISTINCT ?property ?propertyLabel WHERE {
		?entity ?p wd:""" + entity_id + """ .
		?property wikibase:directClaim ?p .
		
		# Fetching English labels for each property
		SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
		} 
	"""

	properties = run_sparql_query(sparql_query, False)
	#print(properties)

	# sort properties alphabetically by property id
	external_relations_properties = sorted(properties, key=lambda x: x['propertyLabel'].split('/')[-1])

	return external_relations_properties

def process_question(entity_id):
	direct_properties, direct_relations = query_sparql_properties(entity_id)
	external_relations_properties = query_sparql_external_relations(entity_id)

	entity_info = {}
	with open(f"{input_dir}/{entity_id}.json", 'r', encoding='utf-8') as file:
		entity_info = json.load(file)

	entity_info['properties'] = direct_properties
	entity_info['direct_relations'] = direct_relations
	entity_info['external_relations'] = external_relations_properties

	with open(f"{input_dir}/{entity_id}.json", 'w', encoding='utf-8') as file:
		json.dump(entity_info, file, ensure_ascii=False, indent=4)

# Load all the filesnames in an array
files = os.listdir(input_dir)

# Get the filename withotu extension in an array
unique_entity_ids = [os.path.splitext(file)[0] for file in files]

# for entity_id in unique_entity_ids:
# 	process_question(entity_id)

batch_size = 4
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
import json
import re
import sys

if len(sys.argv) < 2:
    print("Usage: python 4_extract_all_unique_entities.py <dataset_name_1> <dataset_name_2>...")
    sys.exit(1)

dataset_names = sys.argv[1:]
output = 'qald_unique_entities.txt'

questions = []

for dataset_name in dataset_names:
    with open(f'../datasets/{dataset_name}_final.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        questions += data

unique_entity_all = []

for question_index, question in enumerate(questions):
    # Finding all matches of the regex in the SPARQL query
    entity_ids = re.findall(r"(?:wd:|http://www\.wikidata\.org/entity/)(Q\d+)", question['sparql_wikidata'])
    #entity_ids_cleaned = [match.split(":")[1] for match in entity_ids]

    # remove the wd: part
    entities = list(set(entity_ids))

    for entity in entities:
        if entity not in unique_entity_all:
            unique_entity_all.append(entity)

    # Print every 100 questions
    if question_index % 10 == 0:
        print(f"Processed {question_index}/{len(questions)} questions")

# unique_missing_entity_ids
print(f"Total unique entities: {len(unique_entity_all)}")

with open(output, 'w') as outfile:
    for entity in unique_entity_all:
        outfile.write(entity + "\n")
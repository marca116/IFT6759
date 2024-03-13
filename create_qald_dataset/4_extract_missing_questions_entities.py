import json
import csv
import re

#qald_9_plus_train_wikidata_with_solved_answers.json, qald_10_test_with_solved_answers.json
dataset_name = "qald_10_test"
vital_entities_name = "vital_articles_entities_2019"
missing_entities_ids_name = dataset_name + "_missing_entities_ids.txt"

with open(dataset_name + '_with_solved_answers.json', 'r', encoding='utf-8') as file:
    questions = json.load(file)

vital_articles_entities = []
with open(vital_entities_name + '.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        entity_id, title, wiki_url = row
        vital_articles_entities.append((entity_id, title, wiki_url))

unique_missing_entity_all = []

for question_index, question in enumerate(questions):
    # Finding all matches of the regex in the SPARQL query
    entity_ids = re.findall(r"wd:Q\d+", question['sparql_wikidata'])
    entity_ids_cleaned = [match.split(":")[1] for match in entity_ids]

    # remove the wd: part
    entities = list(set(entity_ids_cleaned))

    for entity in entities:
        # Find the entity's index in vital_articles_entities
        vital_entity_index = next((i for i, x in enumerate(vital_articles_entities) if x[0] == entity), None)
        vital_entity_id = vital_articles_entities[vital_entity_index][0] if vital_entity_index is not None else None

        if vital_entity_id is None:
            if entity not in unique_missing_entity_all:
                unique_missing_entity_all.append(entity)

    # Print every 100 questions
    if question_index % 100 == 0:
        print(f"Processed {question_index}/{len(questions)} questions")

# unique_missing_entity_ids
print(f"Total unique missing entities: {len(unique_missing_entity_all)}")

with open(missing_entities_ids_name, 'w') as outfile:
    for entity in unique_missing_entity_all:
        outfile.write(entity + "\n")
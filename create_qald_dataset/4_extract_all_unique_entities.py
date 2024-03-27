import json
import re

input_qald9_train = '../datasets/original_qald_9_plus_train_wikidata_final.json'
input_qald9_test = '../datasets/original_qald_9_plus_test_wikidata_final.json'
input_qald10_train = '../datasets/qald_9_plus_train_with_long_answer_final.json'
input_qald10_test = '../datasets/qald_10_test_final.json'

output = 'qald_unique_entities.txt'

with open(input_qald9_train, 'r', encoding='utf-8') as file:
    q9_train_questions = json.load(file)

with open(input_qald9_test, 'r', encoding='utf-8') as file:
    q9_test_questions = json.load(file)

with open(input_qald10_train, 'r', encoding='utf-8') as file:
    q10_train_questions = json.load(file)

with open(input_qald10_test, 'r', encoding='utf-8') as file:
    q10_test_questions = json.load(file)

questions = q9_train_questions + q9_test_questions + q10_train_questions + q10_test_questions
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
    if question_index % 100 == 0:
        print(f"Processed {question_index}/{len(questions)} questions")

# unique_missing_entity_ids
print(f"Total unique entities: {len(unique_entity_all)}")

with open(output, 'w') as outfile:
    for entity in unique_entity_all:
        outfile.write(entity + "\n")
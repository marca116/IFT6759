import json
import re

input_qald9 = '../datasets/qald_9_plus_train_with_long_answer_final.json'
input_qald10 = '../datasets/qald_10_test_final.json'
output = 'qald_unique_entities.txt'

with open(input_qald9, 'r', encoding='utf-8') as file:
    q9_questions = json.load(file)

with open(input_qald10, 'r', encoding='utf-8') as file:
    q10_question = json.load(file)

questions = q9_questions + q10_question
unique_entity_all = []

for question_index, question in enumerate(questions):
    # Finding all matches of the regex in the SPARQL query
    entity_ids = re.findall(r"wd:Q\d+", question['sparql_wikidata'])
    entity_ids_cleaned = [match.split(":")[1] for match in entity_ids]

    # remove the wd: part
    entities = list(set(entity_ids_cleaned))

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
import json
import csv
import re

input_questions_file = 'train_with_simplified_query.json'
input_vital_articles_entities_file = 'vital_articles_entities_2019_q9_q10.csv'

removed_questions_file = 'train_removed_missing_question_entities.json'
output_file = 'train_cleaned_no_missing_entities.json'

with open(input_questions_file, 'r', encoding='utf-8') as file:
    questions = json.load(file)

vital_articles_entities = []

with open(input_vital_articles_entities_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        vital_articles_entities.append(row)

remaining_questions = questions.copy()
removed_questions_final = []

unique_missing_entity_all = []

for question_index, question in enumerate(questions):
    # Finding all matches of the regex in the SPARQL query
    entity_ids = re.findall(r"wd:Q\d+", question['sparql_wikidata'])
    entity_ids_cleaned = [match.split(":")[1] for match in entity_ids]

    # remove the wd: part
    entities = list(set(entity_ids_cleaned))

    removed_an_entity = False

    for entity in entities:
        # Find the entity's index in vital_articles_entities
        vital_entity_index = next((i for i, x in enumerate(vital_articles_entities) if x[0] == entity), None)
        vital_entity_id = vital_articles_entities[vital_entity_index][0] if vital_entity_index is not None else None

        if vital_entity_id is None:
            if entity not in unique_missing_entity_all:
                unique_missing_entity_all.append(entity)

            removed_an_entity = True

    if removed_an_entity:
        removed_questions_final.append(question)

    if question_index % 100 == 0:
        print(f"Processed {question_index}/{len(questions)} questions")

for question in removed_questions_final:
    remaining_questions.remove(question)

# questions removed
print(f"Total questions removed: {len(questions) - len(remaining_questions)}")

# unique_missing_entity_ids
print(f"Total unique missing entities: {len(unique_missing_entity_all)}")

# Count the nb of questions per templates (template_id) for the remaining questions
remaining_templates_count = {}
for question in remaining_questions:
    if question['template_id'] in remaining_templates_count:
        remaining_templates_count[question['template_id']] += 1
    else:
        remaining_templates_count[question['template_id']] = 1

print("Remaining templates count:" , remaining_templates_count)
with open('count_remaining_questions_per_template.json', 'w', encoding='utf-8') as outfile:
    json.dump(remaining_templates_count, outfile, indent=4)

# Count the nb of questions per templates (template_id) for the removed questions
removed_templates_count = {}
for question in removed_questions_final:
    if question['template_id'] in removed_templates_count:
        removed_templates_count[question['template_id']] += 1
    else:
        removed_templates_count[question['template_id']] = 1

print("Removed templates count:" , removed_templates_count)
with open('count_removed_questions_per_template.json', 'w', encoding='utf-8') as outfile:
    json.dump(removed_templates_count, outfile, indent=4)

# Calculate the ratio of removed questions per template vs the total questions per template
templates_ratio = {}
for template in remaining_templates_count:
    if template in removed_templates_count:
        templates_ratio[template] = removed_templates_count[template] / (removed_templates_count[template] + remaining_templates_count[template])
    else:
        templates_ratio[template] = 0

    templates_ratio[template] = f"{templates_ratio[template]:.4%} ({removed_templates_count.get(template, 0)}/{removed_templates_count.get(template, 0) + remaining_templates_count[template]})"

print("Templates ratio:" , templates_ratio)
with open('count_removed_vs_all_questions_templates_ratio.json', 'w', encoding='utf-8') as outfile:
    json.dump(templates_ratio, outfile, indent=4)

# Save removed questions
with open(removed_questions_file, 'w', encoding='utf-8') as outfile:
    json.dump(removed_questions_final, outfile, indent=4)

# Save cleaned questions
with open(output_file, 'w', encoding='utf-8') as outfile:
    json.dump(remaining_questions, outfile, indent=4)
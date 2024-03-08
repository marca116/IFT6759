import json

with open('train_with_simplified_query.json', 'r', encoding='utf-8') as file:
    questions = json.load(file)

with open('lcquad_missing_entities.txt', 'r') as file:
    missing_entities = file.read().splitlines()

removed_questions_count = []
remaining_questions = questions.copy()
removed_questions_final = []

# remove matching questions
for entity in missing_entities:
    removed_count = 0
    questions_to_remove = []

    for question in remaining_questions:
        if entity + " " in question['sparql_wikidata']: # Need to add a space after, otherwise will also remove any entity with an id that contains it (ex : Q67, Q677, etc.)
            #print("Removed:", question['question'])
            questions_to_remove.append(question)
            removed_count += 1

    for question in questions_to_remove:
        remaining_questions.remove(question)
        removed_questions_final.append(question)

    if removed_count > 0:
        removed_questions_count.append((entity, removed_count))
        print(f"Total questions removed for {entity}: {removed_count}")

# objects removed
print(f"Total questions removed: {len(questions) - len(remaining_questions)}")

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
with open('train_removed.json', 'w', encoding='utf-8') as outfile:
    json.dump(removed_questions_final, outfile, indent=4)

# Sort the removed_questions_count list and save it
removed_questions_count.sort(key=lambda x: x[1], reverse=True)
with open('removed_lcquad_questions_count.txt', 'w') as outfile:
    for item in removed_questions_count:
        outfile.write(f"{item[0]}: {item[1]}\n")

# Save cleaned questions
with open('train_cleaned.json', 'w', encoding='utf-8') as outfile:
    json.dump(remaining_questions, outfile, indent=4)
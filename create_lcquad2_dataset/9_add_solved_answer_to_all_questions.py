import json
import os
import csv

with open('train_cleaned_only_questions_with_answers.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

answer_entities_labels = []

with open('answer_entities_labels_and_url.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        entity_id, entity_label, title, wiki_url = row
        answer_entities_labels.append((entity_id, entity_label, title, wiki_url))

removed_questions = []
processed_question_nb = 0

for question in data:
    answers_obj = question['answer']

    solved_answers = []

    for answer in answers_obj:
        # Check if the answer is wikidata uri
        if isinstance(answer, str) and answer.startswith('http://www.wikidata.org/entity/'):
            answer_id = answer.split('/')[-1]

            # Find the entity in answer_entities_labels
            entity = next((x for x in answer_entities_labels if x[0] == answer_id), None)

            # Should not happen, all entities should be in the csv file
            if entity is None:
                print(f"Failed to find entity {answer_id} for {question['uid']}: {question['question']}")
                continue

            entity_id, entity_label, title, wiki_url = entity

            # Remove questions with answers with missing labels (happens if the answer is only in another language)
            if entity_label == "":
                print(f"Failed to find label for {answer_id} for {question['uid']}: {question['question']}")
                removed_questions.append(question)
                break
            
            solved_answers.append(entity_label)
        else:
            solved_answers.append(answer)

    question["solved_answer"] = solved_answers

    processed_question_nb += 1
    if processed_question_nb % 100 == 0:
        print(f"Processed {processed_question_nb}/{len(data)} questions")

# remove questions with missing labels from data
for question in removed_questions:
    data.remove(question)

print(f"Removed questions: {len(removed_questions)}")
print(f"Remaining questions: {len(data)}")
    
# Save to train_final_all_with_solved_answers.json
with open('train_lcquad2_final.json', 'w', encoding='utf-8') as outfile:
    json.dump(data, outfile, indent=4)
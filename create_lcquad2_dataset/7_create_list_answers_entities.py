import json
import os

wikipedia_entities_folder = "covered_entities_wiki_articles"
all_answer_entity_filename = "train_answer_all_entities.txt"

with open('train_cleaned_only_questions_with_answers.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

all_entities = []
missing_entities = []
processed_question_nb = 0 

for question in data:
    answers_obj = question['answer']
    # Shouldn't happen, questions with no answers should have been removed
    if answers_obj is None or len(answers_obj) == 0:
        print(f"Failed to find answer for {question['uid']}: {question['question']}")
        continue

    for answer in answers_obj:
        # continue is not a string
        if not isinstance(answer, str):
            continue

        # Check if the answer is wikidata uri
        if answer.startswith('http://www.wikidata.org/entity/'):
            #print(f"Answer for {question['uid']} is a URI: {answer}")
            answer_id = answer.split('/')[-1]

            # Add to the list if it's not already there
            if answer_id not in all_entities:
                all_entities.append(answer_id)
    
    processed_question_nb += 1
    if processed_question_nb % 100 == 0:
        print(f"Processed {processed_question_nb}/{len(data)} questions")

print(f"Total entities: {len(all_entities)}")
    
# Save all entities
with open(all_answer_entity_filename, 'w', encoding='utf-8') as outfile:
    for entity in all_entities:
        outfile.write(f"{entity}\n")
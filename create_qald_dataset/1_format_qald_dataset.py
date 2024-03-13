import json

remove_long_answers = False # False for qald_9_train, True for qald_10_test
dataset_name = "qald_10_test" # qald_9_plus_train_wikidata and qald_10_test

original_dataset = f'{dataset_name}.json'
formatted_dataset = f'{dataset_name}_formatted_and_cleaned.json'

with open(f'../original_datasets/{original_dataset}', 'r', encoding='utf-8') as file:
    data = json.load(file)

lcquad_formatted_questions = []
lcquad_removed_questions = []

nb_answers_count = {}

# Iterate over the questions in the QALD dataset
for question in data['questions']:
    # Create a new dictionary for the LC-QuAD format
    lcquad_question = {
        "NNQT_question": question['question'][0]['string'], 
        "uid": question['id'],
        "subgraph": "", 
        "template_index": "",  
        "question": question['question'][0]['string'], 
        "sparql_wikidata": question['query']['sparql'],
        "sparql_dbpedia18": "",
        "template": "", 
        "answer": [],
        "template_id": "",
        "simplified_query": "", 
        "solved_answer": [] 
    }

    if len(question['answers']) == 0:
        print(f"Question {lcquad_question['uid']} has 0 answer. Skipping...")
        continue
    elif len(question['answers']) > 1:
        print(f"Question {lcquad_question['uid']} has more than 1 answer. Skipping...")
        continue

    skip_question = False
    question_answer = question['answers'][0]

    if question_answer.get("boolean") is not None:
        lcquad_question['answer'].append(question_answer['boolean'])
    else:
        for binding in question['answers'][0]['results']['bindings']:
            for property in binding:
                value = binding[property]['value']
                lcquad_question['answer'].append(value)

                # Remove statement answer (only one, don't need to support it for now)
                if isinstance(value, str) and value.startswith("http://www.wikidata.org/entity/statement/"):
                    print(f"Question {lcquad_question['uid']} has statement answer. Skipping question...")
                    skip_question = True

    nb_answers = len(lcquad_question['answer'])
    
    # Remove questions with more than 25 answers
    if (remove_long_answers and nb_answers > 25) or skip_question:
        lcquad_removed_questions.append(lcquad_question)
    else:
        # Append the reformatted question to the list
        lcquad_formatted_questions.append(lcquad_question)
        nb_answers_count[str(nb_answers)] = nb_answers_count.get(str(nb_answers), 0) + 1

print(f"Number of questions in QALD dataset: {len(data['questions'])}")
print(f"Number of questions in LC-QuAD formatted dataset: {len(lcquad_formatted_questions)}")
print(f"Number of removed questions: {len(lcquad_removed_questions)}")
      
# Sort nb_answers_count
nb_answers_count = {k: v for k, v in sorted(nb_answers_count.items(), key=lambda item: int(item[0]))}
print(f"Number of answers per question: {nb_answers_count}")

# Save to train_lcquad2_final.json
with open(formatted_dataset, 'w', encoding='utf-8') as outfile:
    json.dump(lcquad_formatted_questions, outfile, indent=4)
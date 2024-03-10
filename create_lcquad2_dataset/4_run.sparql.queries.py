import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os

input_file = "train_cleaned_no_missing_entities.json"
output_file = "train_cleaned_with_answers.json"

output_dir = 'questions_with_answers_json' 
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_dir_errors = 'questions_with_answers_json_errors'
if not os.path.exists(output_dir_errors):
    os.makedirs(output_dir_errors)

output_dir_errors_path_exists = 'questions_with_answers_json_errors_path_exists'
if not os.path.exists(output_dir_errors_path_exists):
    os.makedirs(output_dir_errors_path_exists)

# Function to run a SPARQL query against Wikidata
def run_query(query):
    endpoint_url = "https://query.wikidata.org/sparql"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/sparql-results+json"}
    try:
        response = requests.get(endpoint_url, headers=headers, params={'query': query})
        response.raise_for_status()  
        data = response.json()

        answers = []

        if data.get("boolean") is not None:
            answers.append(data['boolean'])
        else:
            for binding in data['results']['bindings']:
                for answer_name in binding:
                    answer = binding[answer_name]
                    
                    if answer is not None and answer.get('value') is not None:
                        answers.append(answer['value'])
                    else:
                        print(f"Unknown binding: {binding}")
        return answers
    except Exception as e:
        print(f"Error running query: {e}")
        return []

def save_question_to_file(question, folder_path):
    filename = question['uid']

    # print error if filename already exists
    if os.path.exists(os.path.join(folder_path, f'{filename}.json')):
        print(f"Error: {filename}.json already exists in {folder_path}")
        folder_path = output_dir_errors_path_exists

    with open(os.path.join(folder_path, f'{filename}.json'), 'w', encoding='utf-8') as file:
        json.dump(question, file, ensure_ascii=False, indent=4)

def process_question(question):
    # retry after 1 min if fails
    for i in range(5):
        try:
            answers = run_query(question['sparql_wikidata'])
            question['answer'] = answers
            save_question_to_file(question, output_dir)
            return question
        except Exception as e:
            print(f"Error running query: {e}")
            time.sleep(60)
    
    print(f"Failed to run query for question {question['uid']}")
    save_question_to_file(question, output_dir_errors)
    return question

# Load JSON data
with open(input_file, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Process the data in batches
batch_size = 4
start_time = time.time()

# sepparate the data in groups of 3
batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
total_processed = 0

for i, batch in enumerate(batches):

    with ThreadPoolExecutor() as executor:
        future_to_question = {executor.submit(process_question, question): question for question in batch}

        for i, future in enumerate(as_completed(future_to_question)):
            question = future_to_question[future]
            try:
                future.result() 
            except Exception as exc:
                print(f"Question {question['uid']} generated an exception: {exc}")
    
    total_processed += len(batch)
    print(f"Processed {total_processed}/{len(data)} questions")

# Save the modified data back to a file
with open(output_file, 'w', encoding='utf-8') as outfile:
    json.dump(data, outfile, indent=4)

print(f"Update complete in", time.time() - start_time, "seconds")

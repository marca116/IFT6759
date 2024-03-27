import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import sys

sys.path.insert(0, "../utils")
from utils import run_sparql_query

dataset_name = "original_qald_9_plus_test_wikidata" 
input_file = f"{dataset_name}_formatted_and_cleaned.json"
output_file = f"{dataset_name}_updated_answers.json"

def process_question(question):
    # retry after 1 min if fails
    for i in range(5):
        try:
            answers = run_sparql_query(question['sparql_wikidata'])
            question['answer'] = answers
            return question
        except Exception as e:
            print(f"Error running query: {e}")
            time.sleep(60)
    
    print(f"Failed to run query for question {question['uid']}")
    return question

# Load JSON data
with open(input_file, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Process the data in batches
batch_size = 5
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

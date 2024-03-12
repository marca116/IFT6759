from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

prompt_config = read_json('prompts.json')

# qald_9_plus_train, qald_10_test
dataset_name = "qald_9_plus_train_with_long_answer"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_solved_answers_filename = f'{dataset_name}_solved_answers.json'

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

# prompt
prompt = prompt_config["vanilla_kgqa"]

# Only first 10 questions
#questions = questions[:10]

solved_questions = []

def process_question(question):
    question_text = question["question"]

    convo_history = [format_msg_oai("user", "User's question: " + question_text), format_msg_oai("user", prompt)]
    result = send_open_ai_gpt_message(convo_history, json_mode=True)

    extracted_json = extract_json_from_response("vanilla_kgqa", result["content"])

    reason = extracted_json["reason"]
    gpt_answers = extracted_json["answers"]

    # Check if any of the gpt answers has parenthesis and remove them
    if any("(" in answer for answer in gpt_answers):
        print(f"Removing parenthesis in question {question['uid']}. Original answers: {gpt_answers}")

    # Use regex to remove all parenthesis and their content
    gpt_answers = [re.sub(r'\([^)]*\)', '', answer).strip() for answer in gpt_answers]

    # Validate the answer
    correct_answers = []
    missed_answers = []
    false_positives = []

    # TRUE POSITIVES AND FALSE NEGATIVES
        # For every solved answer's labels in the gold answers, check if it matches the gpt answer (case insensisitve)
        # Add the gpt label to correct_answers if it matches, add it to the missed_answers if it doesn't
    for answer in question["solved_answer"]:
        # Answers are lists if the answer was a wikidata entity, but it's a primitive otheriwse
        if isinstance(answer, list):
            answer_labels = answer
            match_label = ""

            for label in answer_labels:
                if case_insensitive_elem_in_list(label, gpt_answers): # case insensitive
                    match_label = label

            if match_label != "":
                correct_answers.append(match_label)
            else:
                missed_answers.append(answer_labels[0] if len(answer_labels) > 0 else "") # First label is main label
        else:
            if case_insensitive_elem_in_list(answer, gpt_answers): 
                correct_answers.append(answer)
            else:
                missed_answers.append(answer)

    # FALSE POSITIVES
        # All gpt answers not present in any of the gold answers' labels are false positives
    for gpt_answer in gpt_answers:
        match_label = ""
        for answer in question["solved_answer"]:
            # Answers are lists if the answer was a wikidata entity, but it's a primitive otheriwse
            if isinstance(answer, list):
                answer_labels = answer
                if case_insensitive_elem_in_list(gpt_answer, answer_labels): # case insensitive
                    match_label = gpt_answer
            else:
                if case_insensitive_equals(gpt_answer, answer): # case insensitive
                    match_label = gpt_answer

        if match_label == "":
            false_positives.append(gpt_answer)

    # Calc F1 Score
    precision = len(correct_answers) / len(gpt_answers) if len(gpt_answers) > 0 else 0
    recall = len(correct_answers) / len(question["solved_answer"]) if len(question["solved_answer"]) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0

    solved_question = {
        "uid": question["uid"],
        "question": question_text,
        "solved_answer": gpt_answers,
        "reasoning": reason,
        "gold_answers": question["answer"],
        "gold_solved_answers": question["solved_answer"],
        "TP Answers": correct_answers,
        "FN Answers": missed_answers,
        "FP Answers": false_positives,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

    solved_questions.append(solved_question)

batch_size = 5
start_time = time.time()

# sepparate the data in groups 
batches = [questions[i:i + batch_size] for i in range(0, len(questions), batch_size)]

# process each batch in parallel
for i, batch in enumerate(batches):

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_question, question) for question in batch]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error occurred in sub-thread: {e}")
    
    print(f"Processed {i + 1}/{len(batches)} question batches")

# Sort solved questions by uid
solved_questions.sort(key=lambda x: x["uid"])

# Print questions info
for question in solved_questions:
    print(f"Question {question['uid']}: {question['question']}")
    print(f"Gold answers: {question['gold_answers']}")
    print(f"GPT answers: {question['solved_answer']}")
    print("-------------------")
    print(f"TP answers: {question['TP Answers']}")
    print(f"FN answers: {question['FN Answers']}")
    print(f"FP answers: {question['FP Answers']}")
    print(f"Precision: {question['precision']}")
    print(f"Recall: {question['recall']}")
    print(f"F1 score: {question['f1']}")
    print(f"Reasoning: {question['reasoning']}")
    print("")

print(f"Total time: {time.time() - start_time} seconds")

# Calc macro f1 score
macro_f1 = sum([x["f1"] for x in solved_questions]) / len(solved_questions)
print(f"Macro F1 score: {macro_f1}")

# Save the solved questions
with open(output_solved_answers_filename, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions, outfile, indent=4)
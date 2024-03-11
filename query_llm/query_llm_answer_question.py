from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response
import json

prompt_config = read_json('prompts.json')

dataset_name = "qald_9_plus_train"
qald_9_plus_train_final = "../datasets/" + dataset_name + "_final.json"

with open(qald_9_plus_train_final, 'r', encoding='utf-8') as file:
    questions = json.load(file)

# Get the first question
question = questions[1]
question_text = question["question"]

# prompt
prompt = prompt_config["vanilla_kgqa"]

msg_content = prompt 

convo_history = [format_msg_oai("user", "User's question: " + question_text), format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history, json_mode=True)

# question
print("Question : " + question_text)
#print(result)

extracted_json = extract_json_from_response("vanilla_kgqa", result["content"])

reason = extracted_json["reason"]
print("Reasoning: " + reason)

gpt_answers = extracted_json["answers"]
print(f"Answers: {gpt_answers}")

# Validate the answer
correct_answers = []
incorrect_answers = []

for answer in question["solved_answer"]:
    if answer in gpt_answers:
        correct_answers.append(answer)
    else:
        incorrect_answers.append(answer)

print("Correct answers: " + str(correct_answers))
print("Failed answers: " + str(incorrect_answers))

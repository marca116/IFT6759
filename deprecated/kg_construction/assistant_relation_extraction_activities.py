from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response

prompt_config = read_json('prompts_multiple_steps.json')
convo_history = read_json('test_message_history/bill_fritz.json')

# Add specification of which is the user msg and which is the history
for idx, msg in enumerate(convo_history):
    if idx < len(convo_history) - 1:
        msg["content"] = "history: [" + msg["content"] + "]"
    else:
        msg["content"] = "Last user message: [" + msg["content"] + "]"

# Insert the prompt intro
convo_history.insert(0, format_msg_oai("system", prompt_config['activity_extractor_intro']))

# convo_history.insert(1, format_msg_oai("user", prompt_config['relations']))
convo_history.insert(1, format_msg_oai("user", prompt_config['activities']))
# prompt_config = read_json('prompts_old.json')

# prompt = prompt_config['relation_extractor_body'] + prompt_config['relation_extractor_json'] + prompt_config['relation_extractor_conclusion']
        
prompt = prompt_config['activity_extractor_body'] + prompt_config['activity_extractor_json']

# Add specification person currently speaking is an entity
# prompt += prompt_config["currently_speaking"]

convo_history = convo_history + [format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history, json_mode=True)

obj_result = extract_json_from_response("activity_extractor", result["content"])
print(obj_result)
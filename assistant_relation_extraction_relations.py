from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response

prompt_config = read_json('prompts_relations.json')
convo_history = read_json('test_message_history/bill_fritz.json')

prev_entities = "Last user message entities: [{'name': 'Bill Frist', 'type': 'person', 'attributes': ['Senate majority leader']}, {'name': 'Tennessee', 'type': 'state'}, {'name': 'telling stories', 'type': 'hobby'}, {'name': 'heart surgeon', 'type': 'job'}]"

# Add specification of which is the user msg and which is the history
for idx, msg in enumerate(convo_history):
    if idx < len(convo_history) - 1:
        msg["content"] = "history: [" + msg["content"] + "]"
    else:
        msg["content"] = "previous user message: [" + msg["content"] + "], " + prev_entities

# Insert the prompt intro
convo_history.insert(0, format_msg_oai("system", prompt_config['extractor_intro']))

convo_history.insert(1, format_msg_oai("user", prompt_config['relations']))
# prompt_config = read_json('prompts_old.json')

# prompt = prompt_config['relation_extractor_body'] + prompt_config['relation_extractor_json'] + prompt_config['relation_extractor_conclusion']
        
prompt = prompt_config['extractor_body'] + prompt_config['extractor_json']

# Add specification person currently speaking is an entity
# prompt += prompt_config["currently_speaking"]

convo_history = convo_history + [format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history, json_mode=True)

obj_result = extract_json_from_response("extractor", result["content"])
print(obj_result)
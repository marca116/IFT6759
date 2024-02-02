from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response

prompt_config = read_json('prompts_attributes.json')
convo_history = read_json('test_message_history/billy_mays.json')

# Add specification of which is the user msg and which is the history
for idx, msg in enumerate(convo_history):
    if idx < len(convo_history) - 1:
        msg["content"] = "history: [" + msg["content"] + "]"
    else:
        msg["content"] = "previous user message: [" + msg["content"] + "]"

entities_prev_user_msg = [{'name': 'Billy Mays', 'type': 'person'}, {'name': 'Tampa', 'type': 'city'}, {'name': 'Fla', 'type': 'state'}, {'name': 'Sunday, March 23, 2024', 'type': 'date'}, {'name': 'Christian', 'type': 'religion'}, {'name': 'Catherine', 'type': 'person'}]
convo_history[-1]["content"] += f", previous user message entities: {entities_prev_user_msg}"

relations_prev_user_msg = [{'subject': 'Billy Mays', 'predicate': 'died_in_location', 'object': 'Tampa'}, {'subject': 'Billy Mays', 'predicate': 'resides_in_location', 'object': 'Tampa'}, {'subject': 'Billy Mays', 'predicate': 'follow_religion', 'object': 'Christian'}, {'subject': 'Billy Mays', 'predicate': 'date_of_death', 'object': 'Sunday, March 23, 2024'}, {'subject': 'Billy Mays', 'predicate': 'parent_of', 'object': 'Catherine'}]
convo_history[-1]["content"] += f", previous user message relations: {relations_prev_user_msg}"

# Insert the prompt intro
convo_history.insert(0, format_msg_oai("system", prompt_config['extractor_intro']))

# convo_history.insert(1, format_msg_oai("user", prompt_config['relations']))
# convo_history.insert(1, format_msg_oai("user", prompt_config['entities']))
# convo_history.insert(2, format_msg_oai("user", prompt_config['entities_subtypes']))
# convo_history.insert(3, format_msg_oai("user", prompt_config['activities']))
# prompt_config = read_json('prompts_old.json')

# prompt = prompt_config['relation_extractor_body'] + prompt_config['relation_extractor_json'] + prompt_config['relation_extractor_conclusion']
        
prompt = prompt_config['extractor_body'] + prompt_config['extractor_json']

# Add specification person currently speaking is an entity
# prompt += prompt_config["currently_speaking"]

convo_history = convo_history + [format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history, json_mode=True)

obj_result = extract_json_from_response("extractor", result["content"])
print(obj_result)
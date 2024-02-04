import json
import datetime
from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response
from datetime import datetime

# ENTITIES
print("Extract entities and activities from a conversation")

prompt_config = read_json('prompts_entities.json')
convo_history = read_json('test_message_history/blade_runner_user_entity_long.json')
convo_history_final = []

# Add specification of which is the user msg and which is the history
for idx, msg in enumerate(convo_history):
    if idx < len(convo_history) - 1:
        msg["content"] = "history: [" + msg["content"] + "]"
    else:
        msg["content"] = "previous user message: [" + msg["content"] + "]"

convo_history_final = convo_history.copy() 

# Insert the prompt intro
convo_history_final.insert(0, format_msg_oai("system", prompt_config['extractor_intro']))
convo_history_final.insert(1, format_msg_oai("user", prompt_config['entities']))
# convo_history_final.insert(2, format_msg_oai("user", prompt_config['entities_subtypes']))
#convo_history_final.insert(3, format_msg_oai("user", prompt_config['activities']))
        
prompt = prompt_config['extractor_body'] + "\n" + prompt_config['extractor_json']

convo_history_final = convo_history_final + [format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history_final, json_mode=True)

obj_result_entities = extract_json_from_response("extractor", result["content"])
print("Entities result")
print(obj_result_entities)

# RELATIONS
print("Extract relations from a conversation")

prompt_config = read_json('prompts_relations.json')

entities_prev_user_msg = obj_result_entities["entities"]
convo_history_final = convo_history.copy() # Reset to original convo history

modified_prev_user_msg = convo_history[-1]["content"] + f", previous user message entities: {entities_prev_user_msg}"
convo_history_final[-1] = format_msg_oai("user", modified_prev_user_msg) # Careful about modifiying the original ref

convo_history_final.insert(0, format_msg_oai("system", prompt_config['extractor_intro']))
convo_history_final.insert(1, format_msg_oai("user", prompt_config['relations']))

prompt = prompt_config['extractor_body'] + "\n" + prompt_config['extractor_json']

convo_history_final = convo_history_final + [format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history_final, json_mode=True)

print("Relations result")
obj_result_relations = extract_json_from_response("extractor", result["content"])
print(obj_result_relations)

# Attributes
print("Extract attributes from a conversation")

prompt_config = read_json('prompts_attributes.json')

relations_prev_user_msg = obj_result_relations["relations"] # Extracted from previous step
convo_history_final = convo_history.copy() # Reset to original convo history

modified_prev_user_msg += f", previous user message relations: {relations_prev_user_msg}"
convo_history_final[-1] = format_msg_oai("user", modified_prev_user_msg) # Careful about modifiying the original ref

convo_history_final.insert(0, format_msg_oai("system", prompt_config['extractor_intro']))
prompt = prompt_config['extractor_body'] + "\n" + prompt_config['extractor_json']

convo_history_final = convo_history_final + [format_msg_oai("user", prompt)]
result = send_open_ai_gpt_message(convo_history_final, json_mode=True)

print("Attributes result")
obj_result_attributes = extract_json_from_response("extractor", result["content"])
print(obj_result_attributes)

# Save the results to a file
filename = f'{datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]}'
with open(f'results/{filename}.json', 'w') as f:
    f.write("Conversation history:\n")
    json.dump(convo_history, f)
    f.write("\n\nEntities:\n")
    json.dump(obj_result_entities, f)
    f.write("\n\nRelations:\n")
    json.dump(obj_result_relations, f)
    f.write("\n\nAttributes:\n")
    json.dump(obj_result_attributes, f)
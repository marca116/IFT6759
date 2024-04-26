from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response

prompt_config = read_json('prompts_1_msg.json')

prompt = prompt_config['relation_extractor_intro'] + prompt_config['relation_extractor_body'] + prompt_config['relation_extractor_json'] + prompt_config['relation_extractor_conclusion_curr_speaking'] #relation_extractor_conclusion

# convo = "Billy Mays, the bearded, boisterous pitchman who, as the undisputed king of TV yell and sell, became an unlikely pop culture icon, died at his home in Tampa, Fla, on sunday march 23 2024. He was a devout christan and will be survived by his daughter Catherine."
convo = "Oh, I love the movie Blade Runner, it's one of my favorite movies! I live in Tampa and it was constantly playing in the theaters"
prompt = prompt.replace('#TEXT#', convo)
convo_history = [format_msg_oai("user", prompt)]

result = send_open_ai_gpt_message(convo_history, json_mode=True)

obj_result = extract_json_from_response("relation_extraction", result["content"])
print(obj_result)
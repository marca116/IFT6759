from openai_requests_utils import send_open_ai_gpt_message, format_msg_oai, extract_json_from_response, count_tokens, read_json
import sys
import re
from datetime import datetime
import json
import os

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format, get_batched_entities_info, format_entity_infos, run_sparql_query

def download_entities_info(orig_entity_ids, wikidata_entities_dir, cached_entity_labels_dict):
    # Already downloaded entities
    files = os.listdir(wikidata_entities_dir)

    already_downloaded_entity_ids = [os.path.splitext(file)[0] for file in files]

    # Remove already downloaded entities
    new_entity_ids = [entity_id for entity_id in orig_entity_ids if entity_id not in already_downloaded_entity_ids]

    # Get all the given entities full info from wikidata
    unique_entities_info_unvalidated = get_batched_entities_info(new_entity_ids)

    # Don't include missing entities (has the field 'missing')
    unique_entities_info = []
    for entity_info in unique_entities_info_unvalidated:
        if 'missing' not in entity_info:
            unique_entities_info.append(entity_info)
        else:
            print(f"Entity {entity_info.get('id')} not found")

    # Format the info correctly (ex:  Add labels to properties)
    formatted_entities_info = format_entity_infos(unique_entities_info, cached_entity_labels_dict)

    for entity_info in formatted_entities_info:
        entity_id = entity_info['id']
        
        with open(f"{wikidata_entities_dir}/{entity_id}.json", 'w', encoding='utf-8') as file:
            json.dump(entity_info, file, ensure_ascii=False, indent=4)

def print_solved_question(question):
    print(f"Question {question['uid']}: {question['question']}")
    print(f"Gold answers: {question['gold_answers']}")
    print(f"GPT answers: {question['solved_answer']}")
    if question.get("unmodified_solved_answer"):
        print(f"Unmodified GPT answers: {question['unmodified_solved_answer']}")
    print("-------------------")
    print(f"TP answers: {question['TP_answers']}")
    print(f"FN answers: {question['FN_answers']}")
    print(f"FP answers: {question['FP_answers']}")
    print(f"Precision: {question['precision']}")
    print(f"Recall: {question['recall']}")
    print(f"F1 score: {question['f1']}")
    print(f"Reasoning: {question['reasoning']}")

    if question.get("answers_datatype"):
        print(f"Answers datatype: {question['answers_datatype']}")
    
    if question.get("additional_information"):
        print(f"Additional information: {question['additional_information']}")

    print("")

def text_is_boolean(value):
    if not isinstance(value, str):
        return False

    return value.lower() in ["yes", "no", "true", "false"]

def convert_to_boolean(value):
    if not isinstance(value, str):
        return value

    if value.lower() in ["yes", "true"]:
        return True
    elif value.lower() in ["no", "false"]:
        return False
    else:
        return value

def format_gpt_answers(original_gpt_answers, question_uid, answers_datatype = None):
    # Fix answers formatting
    gpt_answers = []
    removed_parenthesis = False

    if not isinstance(original_gpt_answers, list):
        print(f"Error: original_gpt_answers is not a list. Question {question_uid}. Original answers: {original_gpt_answers}")
        original_gpt_answers = [gpt_answers]

    for answer in original_gpt_answers:
        # Skip empty answers
        if answer == "":
            continue

        # Convert boolean text (yes, no) to boolean
        if text_is_boolean(answer):
            answer = convert_to_boolean(answer)

        # If the answer is a boolean, just append it
        if isinstance(answer, bool):
            #print(f"Boolean answer: {answer}")
            gpt_answers.append(answer)
            continue

        answer = str(answer) # Convert to string (ex: if obj, number, etc)

        # Check if any of the gpt answers has parenthesis and remove them
        if "(" in answer:
            removed_parenthesis = True

        # Use regex to remove all parenthesis and their content
        formatted_answer =  re.sub(r'\([^)]*\)', '', answer).strip()

        # Clean numbers so they are in the same format as wikidata's query output (no commas, no spaces)
        if answers_datatype == "quantity":
            formatted_answer = clean_number(formatted_answer)

        # Wiki data queries always return iso format dates
        if is_date(formatted_answer):
            formatted_answer = format_date_iso_format(formatted_answer)

        # Urls always start with https
        if formatted_answer.startswith("http://"):
            formatted_answer = formatted_answer.replace("http://", "https://")
            if formatted_answer[-1] == "/":
                formatted_answer = formatted_answer[:-1]

        # Remove empty answers
        gpt_answers.append(formatted_answer)

    if removed_parenthesis:
        print(f"Removing parenthesis in question {question_uid}. Original answers: {original_gpt_answers}")

    return gpt_answers

def find_main_entity_id(question, main_entity_name, prompt_config):
    if not main_entity_name:
        print(f"Error: Main entity name is empty. Question {question['uid']}")
        return None, "", 0, []

    sparql_query = """
        SELECT DISTINCT ?item ?itemLabel ?itemDescription WHERE {
        { 
            ?item rdfs:label \"""" + main_entity_name + """\"@en. 
        } UNION { 
            ?item skos:altLabel \"""" + main_entity_name + """\"@en. 
        }
        ?article schema:about ?item .
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }    
        }
    """

    # dict = {item, itemLabel, itemDescription}
    result_dicts = run_sparql_query(sparql_query, False)
    results_text = "Wikidata items:\n"
    
    # If no results found for the entity linking, return None
    if len(result_dicts) == 0:  
        return None, "", 0, []
    
    for result_dict in result_dicts:
        text = f"Id: {result_dict['item']}, label: {result_dict['itemLabel']}"

        if result_dict.get('itemDescription'):
            text += f", description: {result_dict['itemDescription']}"

        results_text += text + "\n"

    wikidata_results_msg = [format_msg_oai("user", results_text)]

    question_and_main_entity = "Main entity: " + main_entity_name + ", Question: " + question["question"]

    # Convo history
    convo_history = [format_msg_oai("user", question_and_main_entity), format_msg_oai("user", prompt_config["disambiguate_entities"])]
    convo_history = wikidata_results_msg + convo_history

    current_tokens_count = count_tokens(convo_history)

    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    extracted_json = extract_json_from_response("link_entities", result["content"])

    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return None, "", current_tokens_count, []

    main_entity_item_id = extracted_json.get("main_entity_item_id", None)
    main_entity_item_id = main_entity_item_id.split("/")[-1].strip() if main_entity_item_id else None # Remove the url if necessary

    # Validate if starts with Q + a string of numbers (no letters) using a regex
    if main_entity_item_id and (not main_entity_item_id.startswith("Q") or not re.match(r'^Q\d+$', main_entity_item_id)):
        print(f"Error: Main entity item id is invalid: {main_entity_item_id}. Question {question['uid']}. Response: {result['content']}")
        main_entity_item_id = None

    reason = extracted_json.get("reason", "")

    # print(f"Main entity: {main_entity_name}, main entity item id: {main_entity_item_id}, reason: {reason}")

    return main_entity_item_id, reason, current_tokens_count, result_dicts

def find_answer_entity_id(question, answer_entity_name, prompt_config, reasoning, extra_info, react_info):
    if not answer_entity_name:
        print(f"Error: Main entity name is empty. Question {question['uid']}")
        return None, "", 0, []

    sparql_query = """
        SELECT DISTINCT ?item ?itemLabel ?itemDescription WHERE {
        { 
            ?item rdfs:label \"#answer_entity_name#\"@en. 
        } UNION { 
            ?item skos:altLabel \"#answer_entity_name#\"@en. 
        }
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }    
        }
    """

    sparql_query_normal = sparql_query.replace("#answer_entity_name#", answer_entity_name)
    result_dicts_normal = run_sparql_query(sparql_query_normal, False) # dict = {item, itemLabel, itemDescription}

    answer_entity_name_lower = answer_entity_name.lower()
    sparql_query_lower = sparql_query.replace("#answer_entity_name#", answer_entity_name_lower)
    result_dicts_lower = run_sparql_query(sparql_query_lower, False) # dict = {item, itemLabel, itemDescription}

    result_dicts = result_dicts_lower + result_dicts_normal

    # Remove disambiguation pages
    result_dicts = [result_dict for result_dict in result_dicts if "disambiguation page" not in result_dict.get("itemDescription", "").lower()]

    results_text = "Wikidata items:\n"
    
    # If no results found for the entity linking, return None
    if len(result_dicts) == 0:  
        return None, "", 0, []
    
    for result_dict in result_dicts:
        text = f"Id: {result_dict['item']}, label: {result_dict['itemLabel']}"

        if result_dict.get('itemDescription'):
            text += f", description: {result_dict['itemDescription']}"

        results_text += text + "\n"

    wikidata_results_msg = [format_msg_oai("user", results_text)]

    react_explanation = ""
    react_query_msg = []
    if react_info is not None:
        child_properties = react_info.get("child_properties")
        child_properties = child_properties.get("child_properties", []) if child_properties else []

        # del "property" for each child_property (info already contained in instances)
        for child_property in child_properties:
            if "property" in child_property:
                del child_property["property"]

        react_query_msg.append(format_msg_oai("user", f"Step by step process: {react_info}"))
        react_explanation = prompt_config["react_explanation"]
    
    disambiguate_entities_prompt = prompt_config["disambiguate_entities_answer_linking"].replace("#react_explanation#", react_explanation)

    question_and_main_entity = "Question: " + question["question"] + ", Reasoning: " + reasoning + ", Extra info: " + extra_info + ", Answer entity: '" + answer_entity_name + "'"

    # Convo history
    convo_history = [format_msg_oai("user", question_and_main_entity), format_msg_oai("user", disambiguate_entities_prompt)]
    convo_history = wikidata_results_msg + react_query_msg + convo_history

    current_tokens_count = count_tokens(convo_history)
    if current_tokens_count > 14635:
        print(f"Skipping question {question['uid']}, token count too high: {current_tokens_count}")
        return None, "", current_tokens_count, []

    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    extracted_json = extract_json_from_response("link_entities", result["content"])

    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return None, "", current_tokens_count, []

    answer_entity_item_id = extracted_json.get("answer_entity_item_id", None)
    answer_entity_item_id = answer_entity_item_id.split("/")[-1].strip() if answer_entity_item_id else None # Remove the url if necessary

    # Validate if starts with Q + a string of numbers (no letters) using a regex
    if answer_entity_item_id and (not answer_entity_item_id.startswith("Q") or not re.match(r'^Q\d+$', answer_entity_item_id)):
        print(f"Error: Main entity item id is invalid: {answer_entity_item_id}. Question {question['uid']}. Response: {result['content']}")
        answer_entity_item_id = None

    reason = extracted_json.get("reason", "")

    # print(f"Main entity: {main_entity_name}, main entity item id: {answer_entity_item_id}, reason: {reason}")

    return answer_entity_item_id, reason, current_tokens_count, result_dicts

def create_qa_convo_history(question, use_external_info = False, info_messages = None):
    if info_messages is None:
        info_messages = []

    prompt_config = read_json('prompts.json')

    # system message (current date)
    system_messages = [format_msg_oai("system", f"Current date: {datetime.now().strftime('%Y-%m-%d')}\n{prompt_config['qa_system_msg']} {prompt_config['qa_system_yes_no_msg']}")]

    # Examples
    example_question_text = prompt_config["qa_example_question"]
    example_output_text = prompt_config["qa_example_answer"]
    examples_history = [format_msg_oai("user", "Example question: [" + example_question_text + "]"), format_msg_oai("assistant", "Example answer: [" + example_output_text + "]")]

    previous_info = " " + prompt_config["qa_use_previous_info"] if use_external_info else ""
    prompt = f'{prompt_config["qa_intro"]}{previous_info} {prompt_config["qa_content"]}'

    convo_history = [format_msg_oai("user", "Question: " + question["question"]), format_msg_oai("user", prompt)]
    convo_history = system_messages + examples_history + info_messages + convo_history

    return convo_history

def extract_info_qa_response(result, question):
    extracted_json = extract_json_from_response("qa", result["content"])
    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return [], [], "", "", ""

    reason = extracted_json.get("reason", "")
    answers_datatype = extracted_json.get("answers_datatype", "")
    #answer_present_in_provided_information = extracted_json.get("answer_present_in_provided_information", "")
    extra_info = extracted_json.get("additional_information", "")
    original_gpt_answers = extracted_json.get("answers", [])

    #print(extracted_json)

    # Fix answers formatting
    gpt_answers = format_gpt_answers(original_gpt_answers, question['uid'], answers_datatype)

    return gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info

def create_choose_entity_convo_history(question, info_messages, current_step, entities_name):
    prompt_config = read_json('prompts.json')

    # system message (current date)
    system_messages = [format_msg_oai("system", f"Current date: {datetime.now().strftime('%Y-%m-%d')}\n{prompt_config['qa_system_msg']}")]

    prompt = prompt_config["choose_entity_property_intro"]
    prompt += " " + (prompt_config['choose_entity_property_first_step'] if current_step == 1 else prompt_config['choose_entity_property_step_x'].replace('#entities_name#', ", ".join(entities_name)))
    prompt += " " + prompt_config["choose_entity_property_content"]

    question_history = [format_msg_oai("user", "Question: " + question["question"])]
    convo_history = system_messages + question_history + info_messages + [format_msg_oai("user", prompt)]

    return convo_history

def extract_choose_entity_response(result, question, react_info):
    extracted_json = extract_json_from_response("qa", result["content"])
    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return [], [], "", "", ""

    information_requested = extracted_json.get("information_requested", "")
    property_name = extracted_json.get("property_name", "")
    property_id = extracted_json.get("property_id", "")
    property_id = property_id if property_id is not None and isinstance(property_id, str) else "" # set to "" if was set to None

    # If propertyId doesn't start with a P, but is a number, add "P" at the start
    if property_id.isdigit():
        property_id = "P" + property_id

    react_info_field_name = "choose_property" if "choose_property" not in react_info else "choose_property_2"
    react_info_property_obj = {
        "information_requested": information_requested,
        "property_name": property_name,
        "property_id": property_id,
        "reason": extracted_json.get("reason", "")
    }
    react_info[react_info_field_name] = react_info_property_obj

    print(extracted_json)

    return information_requested, property_name, property_id

def create_is_question_answered_convo_history(question, tentative_answer, info_messages):
    prompt_config = read_json('prompts.json')

    # system message (current date)
    system_messages = [format_msg_oai("system", f"Current date: {datetime.now().strftime('%Y-%m-%d')}\n{prompt_config['qa_system_msg']}")]

    prompt = f'{prompt_config["has_enough_information"]}'

    question_history = [format_msg_oai("user", "Question: " + question["question"]), format_msg_oai("user", "Tentative answer: " + tentative_answer)]
    convo_history = system_messages + info_messages + question_history + [format_msg_oai("user", prompt)]

    return convo_history

def extract_is_question_answered(result, question, react_info):
    extracted_json = extract_json_from_response("qa", result["content"])
    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return [], [], "", "", ""

    answer_status = extracted_json.get("answer_status", "") # True if question was correctly answered with the given info
    reason = extracted_json.get("reason", "")
    additional_details_required = extracted_json.get("additional_details_required", "")
   
    is_question_answered = answer_status == "correct"

    print(extracted_json)

    react_info_question_is_answered_obj = {
        "answer_status": answer_status,
        "reason": reason,
        "additional_details_required": additional_details_required
    }

    if not additional_details_required:
        del react_info_question_is_answered_obj["additional_details_required"]

    react_info["question_is_answered"] = react_info_question_is_answered_obj

    return is_question_answered

def sort_questions(questions):
    questions.sort(key=lambda x: x["uid"].zfill(3)) 

# Save info messages with token counts (when token count is too high)
def save_info_messages_with_token_counts(info_messages, question, entity_id, info_tokens_count, convo_tokens_count, info_messages_dir):
    info_msg_with_token_counts = [{"token_count": count_tokens([msg]), "msg_content": msg} for msg in info_messages]
    info_msg_with_token_counts.sort(key=lambda x: x["token_count"], reverse=True)

    root_obj = {
        "question": question["question"],
        "uid": question["uid"],
        "entity_id": entity_id,
        "info_tokens_count": info_tokens_count,
        "convo_total_tokens_count": convo_tokens_count,
        "info_messages": info_msg_with_token_counts
    }

    # save to file
    with open(f"{info_messages_dir}/info_messages_{question['uid']}.json", 'w', encoding='utf-8') as outfile:
        json.dump(root_obj, outfile, indent=4)

def get_instances_text(root_property, root_id):
    # Keep only the top 10 instances for these properties
        # P2936 = language used (too many for big countries (USA))
        # P608 = Time zone (too many for big countries)
    properties_top_10_only = ["P2936", "P421"]

    # Remove some qualfiers that are not that useful
        # P2241 = Reason for deprecation
        # P459 = determination method (could potentially be useful in some context, but takes way too much space (ex : population in canada))
    qualifiers_to_skip = ["P2241", "P459"]

    instances_texts = []

    for index, property_instance in enumerate(root_property["instances"]):
        # Keep only the top 10 instances for these properties
        if index == 10 and root_id in properties_top_10_only:
            break

        # Skip deprecated rank (-1)
        if property_instance.get("rank") == -1:
            continue

        value = property_instance.get("value_label", property_instance.get("value"))

        # Remove the + at the start
        if property_instance["type"] in ["time", "quantity"]:
            value = value.replace("+", "")

        qualifiers_texts = []

        if property_instance.get("rank") == 1:
            qualifiers_texts.append("current value")

        for qualifier in property_instance.get("qualifiers", []):
            if qualifier["id"] in qualifiers_to_skip:
                continue

            qualifier_value = qualifier.get("value_label", qualifier.get("value"))

            # Remove the + at the start
            if qualifier["type"] in ["time", "quantity"]:
                qualifier_value = qualifier_value.replace("+", "")

            qualifiers_texts.append(f"{qualifier['label']}: {qualifier_value}")

        formatted_qualifiers = (" (" + ", ".join(qualifiers_texts) + ")") if len(qualifiers_texts) > 0 else ""

        #value_rank_text = "*" if property_instance.get("rank", 0) == 1 else ""
        #instances_texts.append(f"{value}{value_rank_text}{formatted_qualifiers}")
        instances_texts.append(f"{value}{formatted_qualifiers}")

    return instances_texts

def answer_qa_question(question, info_messages, entity_id, info_messages_dir, initial_token_count = 0, react_info = None):
    convo_history = create_qa_convo_history(question, True, info_messages)

    info_tokens_count = count_tokens(info_messages)
    convo_token_count = count_tokens(convo_history)

    # Save info messages used for the question with token counts
    save_info_messages_with_token_counts(info_messages, question, entity_id, info_tokens_count, convo_token_count, info_messages_dir)
    current_tokens_count = initial_token_count + convo_token_count
    
    # Take into account the token limit for ggpt 3.5 (16385 - 1750 max output tokens count)
    if convo_token_count > 14635:
        print(f"Skipping question {question['uid']}, token count too high: {convo_token_count}")
        return None, None, None, None, None, current_tokens_count, react_info

    # Send message to API
    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info = extract_info_qa_response(result, question)

    return gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info, current_tokens_count, react_info

# Filters for entity properties
def entity_property_filters():
    # Properties that makes the token count too high to process (Ex : For Germany (Q183))
    # P530 = diplomatic relation
    # P1448 = official name in it's original language (not that useful anyways)
    # P1549 = demonym (the way to adress the people of the country)
    # P998 = curlie (not that useful + take a bunch of space)
    # P41 = flag image, not really relevant
    properties_to_skip = ["P530", "P1448", "P1549", "P998", "P41"]

    return properties_to_skip

def process_question_with_entity_properties(question, ner_entity_info, info_messages_dir, directly_from_wikidata = False):
    entity_id = ner_entity_info["main_entity_id"]
    entity_info = {}

    qald_unique_entities_info_dir = '../qald_unique_entities_info' if not directly_from_wikidata else "wikidata_entities"
    with open(f"{qald_unique_entities_info_dir}/{entity_id}.json", 'r', encoding='utf-8') as file:
        entity_info = json.load(file)

    info = f"Wikidata id:{entity_info['id']}, label: {entity_info['label']}, aliases: {', '.join(entity_info.get('aliases', []))}, description: {entity_info['description']}"
    info_messages = [format_msg_oai("user", info)]

    properties_to_skip = entity_property_filters()
    removed_id_properties = []

    for root_property in entity_info['properties']:
        root_id = root_property["id"]

        # Properties that makes the token count too high to process
        if root_id in properties_to_skip:
            continue

        root_label = root_property["label"]

        # Skip the id properties, not very relevant to questions we want to answer
        if " ID " in root_label or root_label.endswith("ID"):
            removed_id_properties.append(root_label)
            continue

        root_text = f"Property: {root_label} ({root_id})\n"

        instances_texts = get_instances_text(root_property, root_id)
        root_text += "\n".join(instances_texts)

        info_messages.append(format_msg_oai("user", root_text))

    return answer_qa_question(question, info_messages, entity_id, info_messages_dir)

def analyze_question_property(question, entity_info, info_messages, react_info, current_step = 1, property_entity_names = None):
    properties_to_skip = entity_property_filters()
    removed_id_properties = []

    list_of_properties = []
    for root_property in entity_info['properties']:
        root_id = root_property["id"]

        # Properties that makes the token count too high to process
        if root_id in properties_to_skip:
            continue

        root_label = root_property["label"]

        # Skip the id properties, not very relevant to questions we want to answer
        if " ID " in root_label or root_label.endswith("ID"):
            removed_id_properties.append(root_label)
            continue

        list_of_properties.append(f"{root_label} ({root_id})")
    
    list_of_properties_text = "List of properties"
    if property_entity_names is not None:
        list_of_properties_text += f" for {', '.join(property_entity_names)}"

    info_messages.append(format_msg_oai("user", f"{list_of_properties_text}: " + ", ".join(list_of_properties)))

    convo_history = create_choose_entity_convo_history(question, info_messages, current_step, property_entity_names)
    current_tokens_count = count_tokens(convo_history)

    # Send message to API
    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    information_requested, property_name, property_id = extract_choose_entity_response(result, question, react_info)

    return information_requested, property_name, property_id, current_tokens_count

def get_question_property(question, main_entity_id, react_info, info_messages = None, current_step = 1, property_entity_names = None):
    if info_messages is None:
        info_messages = []

    with open(f"wikidata_entities/{main_entity_id}.json", 'r', encoding='utf-8') as file:
        entity_info = json.load(file)

    if current_step == 1:
        info = f"Current entity: {entity_info['label']} ({entity_info['id']}), aliases: {', '.join(entity_info.get('aliases', []))}, description: {entity_info['description']}"
        info_messages += [format_msg_oai("user", info)] 

    information_requested, property_name, property_id, token_count = analyze_question_property(question, entity_info, info_messages, react_info, current_step, property_entity_names)

    # Find the property
    properties = entity_info["properties"]
    property = next((prop for prop in properties if prop["id"] == property_id), None)

    if property is None:
        print(f"Property {property_name}({property_id}) not found for the entity {entity_info['label']}({main_entity_id})")

    return property, information_requested, property_id, token_count

def validate_if_question_answered(question, information_requested, ner_entity_info, property, react_info):
    # Step 1 msg : 
    step1_text = f"Step 1 : {information_requested}"
    info_messages = [format_msg_oai("user", step1_text)]

    step1_results = [f'{instance["value_label"]}' for instance in property["instances"] if instance["type"] == "wikibase-entityid"]

    # Add the query
    info_messages += [format_msg_oai("user", f"Query: {ner_entity_info['main_entity']} => {property['label']} ({property['id']})")]

    # Add the results
    str_results = '[\n ' + '\n '.join(step1_results) + '\n]'
    info_messages += [format_msg_oai("user", f"Entity: {ner_entity_info['main_entity']}, Property {property['label']} ({property['id']}): {str_results}]")]

    tentative_answer = ", ".join(step1_results)

    if "how many" in question["question"].lower() and len(step1_results) > 1:
        tentative_answer += " (Answer count: " + str(len(step1_results)) + ")"

    convo_history = create_is_question_answered_convo_history(question, tentative_answer, info_messages)
    current_tokens_count = count_tokens(convo_history)

    # Send message to API
    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    is_question_answered = extract_is_question_answered(result, question, react_info)

    return is_question_answered, current_tokens_count

def process_child_entities_react(question, information_requested_step_1, property, ner_entity_info, child_entity_ids, info_messages_dir, original_token_count, react_info):
    step1_text = f"Step 1 : {information_requested_step_1}"
    info_messages = [format_msg_oai("user", step1_text)]

    main_property_name = property["label"]
    main_property_id = property["id"]

    child_entity_labels = [f'{instance["value_label"]} ({instance["value"]})' for instance in property["instances"] if instance["type"] == "wikibase-entityid"]

    info_messages += [format_msg_oai("user", f"Query: {ner_entity_info['main_entity']} => {main_property_name} ({main_property_id})")]

    str_results = '[\n '+ '\n '.join(child_entity_labels) + '\n]'
    info_messages += [format_msg_oai("user", f"Entity: {ner_entity_info['main_entity']}, Property: {main_property_name} ({main_property_id}): {str_results}")]

    # Determine which of the first child entity's properties to use to answer the question
    first_child_property, information_requested, child_property_id, token_count = get_question_property(question, child_entity_ids[0], react_info, info_messages, 2, child_entity_labels) # step 2

    react_info_child_properties_obj = {
        "information_requested": information_requested,
        "first_child_property": first_child_property
    }

    total_token_count = original_token_count + token_count

    if first_child_property is None:
        return None, None, None, None, None, total_token_count, react_info

    react_info_child_properties_obj["child_properties"] = []
    total_answer_count = 0

    for child_entity_id in child_entity_ids:
        with open(f"wikidata_entities/{child_entity_id}.json", 'r', encoding='utf-8') as file:
            child_entity_info = json.load(file)

        child_property = next((prop for prop in child_entity_info["properties"] if prop["id"] == child_property_id), None)

        if child_property is not None:
            # Get all of the child entity's properties values
            instances_texts = get_instances_text(child_property, child_property_id)

            react_info_child_properties_obj["child_properties"].append({
                "child_property_id": child_property_id,
                "property": child_property,
                "instances_texts": instances_texts
            })

            # Get all of the properties values and associate them to each of the child entities
            root_text = f"Entity: {child_entity_info['label']} ({child_entity_id}), Property: {child_property['label']} ({child_property_id}): [\n "
            root_text += "\n ".join(instances_texts) + "\n]"
            
            info_messages.append(format_msg_oai("user", root_text))

            total_answer_count += len(instances_texts)
        else:
            print(f"Property {child_property_id} not found for the entity {child_entity_info['label']}({child_entity_id})")

            react_info_child_properties_obj["child_properties"].append({
                "child_property_id": child_property_id,
                "property": None
            })

    react_info["child_properties"] = react_info_child_properties_obj

    if "how many" in question["question"].lower() and total_answer_count > 1:
        info_messages.append(format_msg_oai("user", f"Count: {total_answer_count}"))

    # Remove the info message that starts with "List of properties"
    info_messages = [msg for msg in info_messages if not msg["content"].startswith("List of properties")]

    # Answer the question
    return answer_qa_question(question, info_messages, child_entity_id, info_messages_dir, total_token_count, react_info)

def process_question_react(question, ner_entity_info, info_messages_dir, cached_entity_labels_dict):
    react_info = {}
    main_entity_id = ner_entity_info["main_entity_id"]

    # Determine which of the main entity's properties to use to answer the question
    property, information_requested, property_id, token_count = get_question_property(question, main_entity_id, react_info)

    if property is None:
        return None, None, None, None, None, token_count, react_info

    react_info["property"] = property

    child_entity_ids = []
    is_question_answered = False

    # Check if any of the property's instances are of type wikibase-entityid
    property_instances_are_wikibase_entity = any(instance["type"] == "wikibase-entityid" and instance.get("value", "").startswith("Q") for instance in property["instances"])

    # Validate if the question can already be answered with the property's values
    if property_instances_are_wikibase_entity:
        child_entity_ids = [instance["value"] for instance in property["instances"] if instance["type"] == "wikibase-entityid"] # All wikibase-entityid properties
        download_entities_info(child_entity_ids, "wikidata_entities", cached_entity_labels_dict)

        is_question_answered, new_token_count = validate_if_question_answered(question, information_requested, ner_entity_info, property, react_info)
        token_count += new_token_count

    # Answer question with the property's values directly
    if not property_instances_are_wikibase_entity or is_question_answered:
        instances_texts = get_instances_text(property, property_id)

        root_text = f"Entity: {ner_entity_info['main_entity']}, Property: {property['label']} ({property_id}): [\n "
        root_text += "\n ".join(instances_texts) + "\n]"

        react_info["properties_instances"] = instances_texts
        
        info_messages = [format_msg_oai("user", root_text)]

        if "how many" in question["question"].lower() and len(instances_texts) > 1:
            #tentative_answer += " (count: " + str(len(step1_results)) + ")"
            info_messages.append(format_msg_oai("user", f"Answer count: {len(instances_texts)}"))

        # Answer the question
        return answer_qa_question(question, info_messages, main_entity_id, info_messages_dir, token_count, react_info)
    else:
        # Find out which child-entity's property to use to answer the question
        return process_child_entities_react(question, information_requested, property, ner_entity_info, child_entity_ids, info_messages_dir, token_count, react_info)

def identify_entity(question, prompt_config):
    question_text = question["question"]

    # Examples
    example_question_text = prompt_config["identify_entities_example_question"]
    example_output_text = prompt_config["identify_entities_example_answer"]
    examples_history = [format_msg_oai("user", "History: [" + example_question_text + "]"), format_msg_oai("assistant", "History: [" + example_output_text + "]")]

    # Convo history
    convo_history = [format_msg_oai("user", "Previous user's question: " + question_text), format_msg_oai("user", prompt_config["identify_entities"])]
    convo_history = examples_history + convo_history

    current_tokens_count = count_tokens(convo_history)

    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    extracted_json = extract_json_from_response("identify_entities", result["content"])

    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return None, [], [], "", current_tokens_count

    main_entity = extracted_json.get("main_entity_label", "")
    side_entities = extracted_json.get("side_entities_labels", [])

    reason = extracted_json.get("reason", "")
    correct_answers = extracted_json.get("correct_answers", [])

    return main_entity, side_entities, correct_answers, reason, current_tokens_count

def process_question_with_rag_context(question, contexts, info_messages_dir, prompt_config):
    contexts = list(map(lambda t: format_msg_oai("user", t), contexts))
    convo_history = create_qa_convo_history(question, True, contexts)
    current_tokens_count = count_tokens(convo_history)
    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info = extract_info_qa_response(result, question)

    return gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info, current_tokens_count
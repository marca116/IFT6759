from openai_requests_utils import send_open_ai_gpt_message, format_msg_oai, extract_json_from_response, count_tokens, read_json
import sys
import re
from datetime import datetime
import json

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format

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

        # Remove empty answers
        gpt_answers.append(formatted_answer)

    if removed_parenthesis:
        print(f"Removing parenthesis in question {question_uid}. Original answers: {original_gpt_answers}")

    return gpt_answers

def create_qa_convo_history(prompt_config, question, use_external_info = False, info_messages = []):
    # system message (current date)
    system_messages = [format_msg_oai("system", f"Current date: {datetime.now().strftime('%Y-%m-%d')}\n{prompt_config['qa_system_msg']}")]

    # Examples
    example_question_text = prompt_config["qa_example_question"]
    example_output_text = prompt_config["qa_example_answer"]
    examples_history = [format_msg_oai("user", "Example question: [" + example_question_text + "]"), format_msg_oai("assistant", "Example answer: [" + example_output_text + "]")]

    previous_info = " " + prompt_config["qa_use_previous_info"] if use_external_info else ""
    prompt = f'{prompt_config["qa_intro"]}{previous_info} {prompt_config["qa_content"]}'

    convo_history = [format_msg_oai("user", "Question: " + question["question"]), format_msg_oai("user", prompt)]
    convo_history = system_messages + info_messages + examples_history + convo_history

    return convo_history

def extract_info_qa_response(result, question):
    extracted_json = extract_json_from_response("qa", result["content"])
    if extracted_json is None:
        print(f"Error: Could not extract json from response, empty answer given. Question {question['uid']}. Response: {result['content']}")
        return [], [], "", "", ""

    reason = extracted_json.get("reason", "")
    answers_datatype = extracted_json.get("answers_datatype", "")
    extra_info = extracted_json.get("additional_information", "")
    original_gpt_answers = extracted_json.get("answers", [])

    # Fix answers formatting
    gpt_answers = format_gpt_answers(original_gpt_answers, question['uid'], answers_datatype)

    return gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info

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

# Filters for entity properties
def entity_property_filters():
    # Properties that makes the token count too high to process (Ex : For Germany (Q183))
    # P530 = diplomatic relation
    # P1448 = official name in it's original language (not that useful anyways)
    # P1549 = demonym (the way to adress the people of the country)
    # P998 = curlie (not that useful + take a bunch of space)
    # P41 = flag image, not really relevant
    properties_to_skip = ["P530", "P1448", "P1549", "P998", "P41"]

    # Keep only the top 10 instances for these properties
        # P2936 = language used (too many for big countries (USA))
        # P608 = Time zone (too many for big countries)
    properties_top_10_only = ["P2936", "P421"]

    # Remove some qualfiers that are not that useful
        # P2241 = Reason for deprecation
        # P459 = determination method (could potentially be useful in some context, but takes way too much space (ex : population in canada))
    qualifiers_to_skip = ["P2241", "P459"]

    # Whether to remove id properties from the output
    remove_id_properties = True

    return properties_to_skip, properties_top_10_only, qualifiers_to_skip, remove_id_properties

def process_question_with_entity_properties(question, ner_entity_info, info_messages_dir, directly_from_wikidata = False):
    entity_id = ner_entity_info["main_entity_id"]
    entity_info = {}

    qald_unique_entities_info_dir = '../qald_unique_entities_info' if not directly_from_wikidata else "wikidata_entities"
    with open(f"{qald_unique_entities_info_dir}/{entity_id}.json", 'r', encoding='utf-8') as file:
        entity_info = json.load(file)

    info = f"Wikidata id:{entity_info['id']}, label: {entity_info['label']}, aliases: {', '.join(entity_info.get('aliases', []))}, description: {entity_info['description']}"
    info_messages = [format_msg_oai("user", info)]

    properties_to_skip, properties_top_10_only, qualifiers_to_skip, remove_id_properties = entity_property_filters()
    removed_id_properties = []

    for root_property in entity_info['properties']:
        root_id = root_property["id"]

        # Properties that makes the token count too high to process
        if root_id in properties_to_skip:
            continue

        root_label = root_property["label"]

        # Skip the id properties, not very relevant to questions we want to answer
        if remove_id_properties and (" ID " in root_label or root_label.endswith("ID")):
            removed_id_properties.append(root_label)
            continue

        root_text = f"Property: {root_label} ({root_id})\n"
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

        root_text += "\n".join(instances_texts)

        info_messages.append(format_msg_oai("user", root_text))

    prompt_config = read_json('prompts.json')
    convo_history = create_qa_convo_history(prompt_config, question, True, info_messages)

    info_tokens_count = count_tokens(info_messages)
    current_tokens_count = count_tokens(convo_history)

    # print("--------------------")
    # print(f"Processing question {question['uid']}")
    # print(f"Total convo tokens count: {current_tokens_count}, Info tokens count: {info_tokens_count}, Info user msg count: {len(info_messages)}")

    # Save info messages used for the question with token counts
    save_info_messages_with_token_counts(info_messages, question, entity_id, info_tokens_count, current_tokens_count, info_messages_dir)

    if current_tokens_count > 16380:
        print(f"Skipping question {question['uid']}, token count too high: {current_tokens_count}")
        return [], "Total tokens count too high"

    #return [], "Success"

    # Send message to API
    result = send_open_ai_gpt_message(convo_history, json_mode=True)
    gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info = extract_info_qa_response(result, question)

    return gpt_answers, original_gpt_answers, reason, answers_datatype, extra_info, current_tokens_count

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
    #print(f"Main entity: {main_entity}")

    side_entities = extracted_json.get("side_entities_labels", [])
    #print(f"Side entities: {side_entities}")

    reason = extracted_json.get("reason", "")
    correct_answers = extracted_json.get("correct_answers", [])

    return main_entity, side_entities, correct_answers, reason, current_tokens_count
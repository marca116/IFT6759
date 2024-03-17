from openai_requests_utils import format_msg_oai, extract_json_from_response
import sys
import re
from datetime import datetime

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format

def print_solved_question(question):
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

    if question.get("answers_datatype"):
        print(f"Answers datatype: {question['answers_datatype']}")
    
    if question.get("additional_information"):
        print(f"Additional information: {question['additional_information']}")

    print("")

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
    system_messages = [format_msg_oai("system", f"Current date: {datetime.now().strftime('%Y-%m-%d')}")]

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
    reason = extracted_json.get("reason", "")
    answers_datatype = extracted_json.get("answers_datatype", "")
    extra_info = extracted_json.get("additional_information", "")
    original_gpt_answers = extracted_json.get("answers", [])

    # Fix answers formatting
    gpt_answers = format_gpt_answers(original_gpt_answers, question['uid'], answers_datatype)

    return gpt_answers, reason, answers_datatype, extra_info

def sort_questions(questions):
    questions.sort(key=lambda x: x["uid"].zfill(3)) 
import sys

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

def calc_question_f1_score(question, gpt_answers, reason):
    golden_answers = question["solved_answer"]

    # Validate the answer
    true_positives = []
    false_negatives = []
    false_positives = []

    # TRUE POSITIVES AND FALSE NEGATIVES
        # For every solved answer's labels in the gold answers, check if it matches the gpt answer (case insensisitve)
        # Add the gpt label to correct_answers if it matches, add it to the missed_answers if it doesn't
    for answer in golden_answers:
        # Answers are lists if the answer was a wikidata entity, but it's a primitive otheriwse
        if isinstance(answer, list):
            answer_labels = answer
            match_label = ""

            for label in answer_labels:
                if case_insensitive_elem_in_list(label, gpt_answers): # case insensitive
                    match_label = label

            if match_label != "":
                true_positives.append(match_label)
            else:
                false_negatives.append(answer_labels[0] if len(answer_labels) > 0 else "") # First label is main label
        else:
            if case_insensitive_elem_in_list(answer, gpt_answers): 
                true_positives.append(answer)
            else:
                false_negatives.append(answer)

    # FALSE POSITIVES
        # All gpt answers not present in any of the gold answers' labels are false positives
    for gpt_answer in gpt_answers:
        match_label = ""
        for answer in golden_answers:
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
            
    # Special case f1 score when the correct gold answer is an empty list (as explained in the Qald10 paper)
    if len(golden_answers) == 0:
        precision = recall = f1 = 1 if len(gpt_answers) == 0 else 0
    else:
        precision = len(true_positives) / (len(true_positives) + len(false_positives)) if len(true_positives) + len(false_positives) > 0 else 0
        recall = len(true_positives) / (len(true_positives) + len(false_negatives)) if len(true_positives) + len(false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0

    #return correct_answers, missed_answers, false_positives, precision, recall, f1

    solved_question = {
        "uid": question["uid"],
        "question": question["question"],
        "solved_answer": gpt_answers,
        "reasoning": reason,
        "gold_answers": question["answer"],
        "gold_solved_answers": question["solved_answer"],
        "TP Answers": true_positives,
        "FN Answers": false_negatives,
        "FP Answers": false_positives,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

    return solved_question

def calc_question_macro_f1_score(solved_questions):
    # Calc macro f1 score
    macro_f1 = sum([x["f1"] for x in solved_questions]) / len(solved_questions)
    return macro_f1

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

def get_final_solved_questions_obj(solved_questions, macro_f1_score, total_token_count = None, total_questions_with_tokens = None):
    question_obj = {
        "macro_f1_score": round(macro_f1_score, 4)
    }

    if total_token_count is not None and total_questions_with_tokens is not None:
        question_obj["total_token_count"] = total_token_count
        question_obj["total_questions_with_tokens"] = total_token_count
        question_obj["average_token_count"] = round(total_token_count / total_questions_with_tokens, 2)

    question_obj["solved_questions"] = solved_questions
    return question_obj
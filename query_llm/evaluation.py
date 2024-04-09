import sys
import re

sys.path.insert(0, "../utils")
from utils import case_insensitive_equals, case_insensitive_elem_in_list

def calc_question_f1_score(question, gpt_answers, original_gpt_answers, reason, answers_datatype = None, extra_info = None, ner_entity_info = None):
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
        "main_entity": ner_entity_info["main_entity"] if ner_entity_info else None,
        "main_entity_id": ner_entity_info["main_entity_id"] if ner_entity_info else None,
        "solved_answer": gpt_answers,
        "unmodified_solved_answer": original_gpt_answers,
        "gold_answers": question["answer"],
        "gold_solved_answers": question["solved_answer"],
        "reasoning": reason,
        "answers_datatype": answers_datatype,
        "extra_info": extra_info,
        "TP_answers": true_positives,
        "FN_answers": false_negatives,
        "FP_answers": false_positives,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

    if answers_datatype is None:
        del solved_question["answers_datatype"]
    if extra_info is None:
        del solved_question["extra_info"]
    if ner_entity_info is None:
        del solved_question["main_entity"]
        del solved_question["main_entity_id"]

    if original_gpt_answers is not None and not isinstance(original_gpt_answers, list):
        original_gpt_answers = [original_gpt_answers]

    if original_gpt_answers is None or all([original_answer in gpt_answers for original_answer in original_gpt_answers]):
        del solved_question["unmodified_solved_answer"]

    is_different = any([gold_answer not in question["solved_answer"] for gold_answer in question["answer"]])
    if not is_different:
        del solved_question["gold_solved_answers"]

    return solved_question

def calc_question_macro_f1_score(solved_questions):
    # Calc macro f1 score
    macro_f1 = sum([x["f1"] for x in solved_questions]) / len(solved_questions)
    return macro_f1

def get_final_solved_questions_obj(solved_questions, macro_f1_score, total_token_count = None, total_questions_with_tokens = None, total_questions_react_failed = None):
    question_obj = {
        "macro_f1_score": round(macro_f1_score, 4)
    }

    if total_token_count is not None and total_questions_with_tokens is not None:
        question_obj["total_token_count"] = total_token_count
        question_obj["average_token_count"] = round(total_token_count / total_questions_with_tokens, 2)
        question_obj["total_questions_with_tokens"] = total_questions_with_tokens

    if total_questions_react_failed is not None:
        question_obj["total_questions_react_failed"] = total_questions_react_failed

    question_obj["solved_questions"] = solved_questions
    return question_obj

def normalize_text(s):
    """Removing articles and punctuation, and standardizing whitespace are all typical text processing steps."""
    import string, re

    def remove_articles(text):
        regex = re.compile(r"\b(a|an|the)\b", re.UNICODE)
        return re.sub(regex, " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def compute_exact_match(prediction, truth):
    return int(normalize_text(prediction) == normalize_text(truth))


def compute_relaxed_f1(prediction, truth):
    pred_tokens = normalize_text(prediction).split()
    truth_tokens = normalize_text(truth).split()

    # if either the prediction or the truth is no-answer then f1 = 1 if they agree, 0 otherwise
    if len(pred_tokens) == 0 or len(truth_tokens) == 0:
        return int(pred_tokens == truth_tokens)

    common_tokens = set(pred_tokens) & set(truth_tokens)

    # if there are no common tokens then f1 = 0
    if len(common_tokens) == 0:
        return 0

    prec = len(common_tokens) / len(pred_tokens)
    rec = len(common_tokens) / len(truth_tokens)

    return 2 * (prec * rec) / (prec + rec)


def relaxed_f1_score(sq):
    return sum(
        [max([compute_f1(sa, ga) for gas in sq.get('gold_solved_answers', [['']]) for ga in gas]) for sa in sq['solved_answer']]
    ) / (len(sq['solved_answer']) + .001)



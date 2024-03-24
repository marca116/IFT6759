from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, \
    count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
from datetime import datetime

from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj
from qa_utils import print_solved_question, sort_questions, process_question_with_entity_properties

import numpy as np
import torch
from datasets import load_from_disk
from transformers import (
    RagRetriever,
    RagSequenceForGeneration,
    RagTokenizer,
)


torch.set_grad_enabled(False)
device = "cuda" if torch.cuda.is_available() else "cpu"

encoder_model_name = 'facebook/dpr-ctx_encoder-multiset-base'
rag_model_name = 'facebook/rag-sequence-nq'

passages_path = os.path.join('..', 'rag', 'data', 'models', "wikipedia_kb_dataset")
index_path = os.path.join('..', 'rag', 'data', 'models', "wikipedia_kb_index.faiss")

passages_path = '/Users/oscarcuellar/ocn/mila/amlp/rag/data/models/wikipedia_kb_dataset'
index_path = '/Users/oscarcuellar/ocn/mila/amlp/rag/data/models/wikipedia_kb_index.faiss'
##############################
# LOAD DATASET AND INDEX #####
##############################

dataset = load_from_disk(passages_path)
dataset.load_faiss_index("embeddings", index_path)
#########################


# LOAD MODELS ################
##############################

retriever = RagRetriever.from_pretrained(
    rag_model_name, index_name="custom", indexed_dataset=dataset
)
model = RagSequenceForGeneration.from_pretrained(rag_model_name, retriever=retriever)
tokenizer = RagTokenizer.from_pretrained(rag_model_name)

# '\n\n\n'.join([dataset[int(t)]['text'] for t in indices[0] if cos_sim(dataset[int(t)]['embeddings'], encoded_question[0]) > .48])

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format

# qald_9_plus_train, qald_9_plus_train_with_long_answer, qald_10_test
dataset_name = "qald_9_plus_train_with_long_answer"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_filename = f'{dataset_name}_solved_answers.json'

# Default answers when no entity linking is found
no_extra_info_solved_answers_filename = f'{dataset_name}_solved_answers_no_external_info.json'
with open(no_extra_info_solved_answers_filename, 'r', encoding='utf-8') as file:
    question_answers_no_extra_info = json.load(file)

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_with_rag"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

solved_questions = []
total_token_count = 0
total_questions_with_tokens = 0

info_messages_dir = "info_msg_with_token_count/" + current_time
# Create dir if doesn't exist
if not os.path.exists(info_messages_dir):
    os.makedirs(info_messages_dir)

cos_sim = lambda a, b: np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

prompt_config = read_json('prompts.json')


def process_question_rag(question, rag_model):
    global total_token_count, total_questions_with_tokens

    encoded_question = rag_model.question_encoder(
        **tokenizer.question_encoder(question['question'], return_tensors="pt")
    )[0].numpy()

    indices, _ = rag_model.retriever.index.get_top_docs(encoded_question, 40)  # ITS NOT NECESSARILY PERFECTLY SORTED

    contexts = sorted(
        [(dataset[int(t)]['text'], cos_sim(dataset[int(t)]['embeddings'], encoded_question[0])) for t in indices[0]],
        key=lambda k: -k[1]
    )[:10]

    contexts = [t[0] for t in contexts]

    answers, original_answers, reason, answers_datatype, extra_info, token_count = process_question_with_rag_context(
        question, contexts, info_messages_dir, prompt_config)

    total_token_count += token_count
    total_questions_with_tokens += 1

    solved_question = calc_question_f1_score(question, answers, original_answers, reason, answers_datatype, extra_info)
    solved_questions.append(solved_question)


for i, q in enumerate(questions):
    if i % 10 == 0:
        print(i)
    process_question_rag(q, model)

sort_questions(solved_questions)

# # Print questions info
# for question in solved_questions:
#     print_solved_question(question)

if len(solved_questions) == 0:
    print("No questions to process")
    sys.exit()

# Total token count + average token count
print(f"Total token count: {total_token_count}")
print(f"Average token count: {total_token_count / total_questions_with_tokens}")
print(f"Total questions with tokens: {total_questions_with_tokens}")

# calc macro f1
macro_f1 = calc_question_macro_f1_score(solved_questions)

print(f"Macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1, total_token_count,
                                                      total_questions_with_tokens)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)

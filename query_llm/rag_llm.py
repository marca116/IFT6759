from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, \
    count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
from datetime import datetime

from scipy import io
from sklearn.neighbors import KDTree
from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj, relaxed_f1_score
from qa_utils import print_solved_question, sort_questions, process_question_with_entity_properties, process_question_with_rag_context

import numpy as np
from datasets import load_from_disk

passages_path = os.path.join('..', 'rag', 'data', 'models', "wikipedia_kb_dataset")
index_path = os.path.join('..', 'rag', 'data', 'models', "wikipedia_kb_index.faiss")

passages_path = '/Users/oscarcuellar/ocn/mila/amlp/rag/data/models/wikipedia_kb_dataset'
index_path = '/Users/oscarcuellar/ocn/mila/amlp/rag/data/models/wikipedia_kb_index.faiss'

##############################
# LOAD DATASET AND INDEX #####
##############################

dataset = load_from_disk(passages_path)
dataset.load_faiss_index("embeddings", index_path)
df = dataset.to_pandas()

#########################
from openai import OpenAI
client = OpenAI()

compute_embedding_db = False

if compute_embedding_db:
    oai_embeddings = dict()

    def get_embedding(obj, model="text-embedding-3-small"):
        text = obj['text']
        idx = obj['idx']
        if not idx in oai_embeddings:
            text = text.replace("\n", " ")
            e = client.embeddings.create(input=[text], model=model).data[0].embedding
            oai_embeddings[idx] = np.array(e)
        return

    computed = set(oai_embeddings.keys())

    texts = [title + ' - ' + txt for title, txt in zip(df.title.tolist(), df.text.tolist())]
    texts = [{'text': t, 'idx': i} for i, t in enumerate(texts) if i not in computed]

    batch_size = 10
    start_time = time.time()

    # sepparate the data in groups
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]

    # process each batch in parallel
    for i, batch in enumerate(batches):

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_embedding, txt) for txt in batch]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error occurred in sub-thread: {e}")
        if i % 1000 == 0:
            print(f"Processed {i + 1}/{len(batches)} batches")

    embeddings = np.array([oai_embeddings[t] for t in range(len(oai_embeddings))])
    savebatch = int(len(embeddings) / 10) + 1
    for i in range(10):
        print('saving', i)
        io.savemat(f'/Users/oscarcuellar/ocn/mila/amlp/IFT6759/datasets/oai_embeddings/emb_{i}',
                           mdict={
                               'text_emb': embeddings[i*savebatch:(i+1)*savebatch],
                           },
                           do_compression=True)
else:
    for i in range(2):
        print('loading', i)
        c_emb = io.loadmat(f'/Users/oscarcuellar/ocn/mila/amlp/IFT6759/datasets/oai_embeddings/emb_{i}')['text_emb']
        if i == 0:
            embeddings = c_emb
        else:
            embeddings = np.concatenate((embeddings, c_emb))

kd_index = KDTree(embeddings)
titles = dict(zip(range(len(df)), df.title))

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format

# qald_9_plus_train, qald_9_plus_train_with_long_answer, qald_10_test
dataset_name = "qald_10_train"
input_dataset_filename = "../datasets/" + dataset_name + "_final.json"
output_filename = f'{dataset_name}_solved_answers.json'

# current date time format with fractions of seconds
current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_with_rag_oai"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

questions[101]['solved_answer'] = ['1888']
questions[101]['answer'] = ['1888']

solved_questions = []
total_token_count = 0
total_questions_with_tokens = 0

info_messages_dir = "info_msg_with_token_count/" + current_time
# Create dir if doesn't exist
if not os.path.exists(info_messages_dir):
    os.makedirs(info_messages_dir)

cos_sim = lambda a, b: np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

prompt_config = read_json('prompts.json')

encoded_questions = dict()
def process_question_rag(question, model="text-embedding-3-small"):
    global total_token_count, total_questions_with_tokens, all_contexts

    if question['uid'] not in encoded_questions:
        encoded_question = client.embeddings.create(input=[question['NNQT_question']], model=model).data[0].embedding
        encoded_question = np.array(encoded_question)[np.newaxis, :]
        encoded_questions[question['uid']] = encoded_question
    else:
        encoded_question = encoded_questions[question['uid']]

    d, indices = kd_index.query(encoded_question, k=10)
    contexts = [(titles[int(t)] + ' - ' + dataset[int(t)]['text'], cos_sim(embeddings[int(t)], encoded_question[0])) for t in indices[0]]

    contexts = [t[0] for t in contexts[:5]]

    answers, original_answers, reason, answers_datatype, extra_info, token_count = process_question_with_rag_context(
        question, contexts, info_messages_dir, prompt_config)

    total_token_count += token_count
    total_questions_with_tokens += 1

    solved_question = calc_question_f1_score(question, answers, original_answers, reason, answers_datatype, extra_info)
    solved_questions.append(solved_question)


for i, q in enumerate(questions):
    if i % 10 == 0:
        print(i)
    process_question_rag(q, "text-embedding-3-small")

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

#########################################################
# COMPUTE RELAXED F1 SCORE ##############################
for q in solved_questions:
    q['_f1'] = q['f1']
    q['f1'] = relaxed_f1_score(q)

macro_f1 = calc_question_macro_f1_score(solved_questions)
print(f"Relaxed macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1, total_token_count, total_questions_with_tokens)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)




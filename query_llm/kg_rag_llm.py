from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, \
    count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
import pandas as pn
from datetime import datetime

from scipy import io
from sklearn.neighbors import KDTree
from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj, relaxed_f1_score
from qa_utils import print_solved_question, sort_questions, process_question_with_entity_properties, process_question_with_rag_context

import numpy as np
from datasets import load_from_disk

passages_path = os.path.join('..', 'rag', 'data', "wikipedia_kb_dataset.csv")
embeddings_path = os.path.join('..', 'datasets/oai_embeddings')

##############################
# LOAD DATASET AND INDEX #####
##############################

df = pn.read_csv(passages_path)

#########################
from openai import OpenAI
client = OpenAI()

compute_embedding_db = not os.path.exists(embeddings_path)

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

    os.makedirs(embeddings_path)
    for i in range(10):
        # Can't save the whole matrix at once: too big
        print('saving', i)
        io.savemat(os.path.join(embeddings_path, f'/emb_{i}'),
                           mdict={
                               'text_emb': embeddings[i*savebatch:(i+1)*savebatch],
                           },
                           do_compression=True)
else:
    for i in range(10):
        print('loading', i)
        c_emb = io.loadmat(f'/Users/oscarcuellar/ocn/mila/amlp/IFT6759/datasets/oai_embeddings/emb_{i}')['text_emb']
        if i == 0:
            embeddings = c_emb
        else:
            embeddings = np.concatenate((embeddings, c_emb))

########################################
# Full index ###########################

full_kd_index = KDTree(embeddings)

########################################
# Build an index for each article ######

df['idx'] = range(len(df))
entityid_chunkidx = dict(df.groupby('id')['idx'].agg(lambda t: t.tolist()).reset_index().values)

indices_map = dict()
kdtrees = dict()
k = 0
for ent_id, chunks in entityid_chunkidx.items():
    kdtrees[ent_id] = KDTree(embeddings[chunks])
    for idx, chunkid in enumerate(chunks):
        indices_map[(ent_id, idx)] = chunkid
    k += 1

titles = dict(zip(range(len(df)), df.title))

##############################
# LOAD DATA #####

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

if dataset_name == "qald_10_train":
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

f = open(f'{dataset_name}_NER_both_using_wikidata.json', 'r', encoding='utf8')
both_entities_full_info = json.load(f)
f.close()

encoded_questions = dict()
def process_question_grag(question, model="text-embedding-3-small"):
    global total_token_count, total_questions_with_tokens, all_contexts

    if question['uid'] not in encoded_questions:
        encoded_question = client.embeddings.create(input=[question['NNQT_question']], model=model).data[0].embedding
        encoded_question = np.array(encoded_question)[np.newaxis, :]
        encoded_questions[question['uid']] = encoded_question
    else:
        encoded_question = encoded_questions[question['uid']]

    entities_info = [t for t in both_entities_full_info if t['question_id'] == question['uid']]

    entities_ids = [
        ent_info['main_entity_id'] for ent_info in entities_info
        if 'main_entity_id' in ent_info and ent_info['main_entity_id'] is not None
    ]

    if len(entities_ids):

        contexts = []
        for entity_id in entities_ids:
            kd_index = kdtrees[entity_id]
            d, indices = kd_index.query(encoded_question, k=3)

            for t in indices[0]:

                contexts.append(
                    (
                        titles[indices_map[(entity_id, t)]] + ' - ' + df.iloc[indices_map[(entity_id, t)]]['text']
                    )
                )
    else:
        # Todo: Default to full index?
        d, indices = full_kd_index.query(encoded_question, k=5)
        contexts = [titles[t] + ' - ' + df.iloc[int(t)]['text'] for t in indices[0]]

    answers, original_answers, reason, answers_datatype, extra_info, token_count = process_question_with_rag_context(
        question, contexts, info_messages_dir, prompt_config)

    total_token_count += token_count
    total_questions_with_tokens += 1

    solved_question = calc_question_f1_score(question, answers, original_answers, reason, answers_datatype, extra_info)
    solved_questions.append(solved_question)


for i, q in enumerate(questions):
    if i % 10 == 0:
        print(i)
    process_question_grag(q, "text-embedding-3-small")

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
    q['strict_f1'] = q['f1']
    q['f1'] = relaxed_f1_score(q)

macro_f1 = calc_question_macro_f1_score([t for t in solved_questions if t['f1'] is not None])
print(f"Relaxed macro F1 score: {macro_f1}")

solved_questions_obj = get_final_solved_questions_obj(solved_questions, macro_f1, total_token_count, total_questions_with_tokens)

with open(output_solved_answers_filepath, 'w', encoding='utf-8') as outfile:
    json.dump(solved_questions_obj, outfile, indent=4)




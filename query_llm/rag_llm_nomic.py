import pandas as pd
import numpy as np
from functools import partial
import torch
from datasets import Features, Sequence, Value, load_dataset,Dataset, load_from_disk, DatasetDict

from nomic import embed
from openai_requests_utils import send_open_ai_gpt_message, read_json, format_msg_oai, extract_json_from_response, count_tokens
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
from datetime import datetime
from sklearn.neighbors import KDTree
from evaluation import calc_question_f1_score, calc_question_macro_f1_score, get_final_solved_questions_obj,relaxed_f1_score
from qa_utils import print_solved_question, sort_questions, process_question_with_entity_properties, process_question_with_rag_context

sys.path.insert(0, "../utils")
from utils import clean_number, is_date, format_date_iso_format

if len(sys.argv) != 2:
    print("Usage: python rag_llm_nomic.py <dataset_name>")
    sys.exit(1)

dataset_name = sys.argv[1]
# dataset_name = "qald_10_train_short"

#nomic login "ESPECIFY KEY"
#os.environ['OPENAI_API_KEY'] = 
#Get Nomic embeddings **************************

df = pd.read_csv("../create_qald_dataset/qald_articles_chunks.csv",encoding='utf-32')
from tqdm import tqdm

list_nomic=[]
for i in tqdm(df.index):
  output = embed.text(
    texts=[
        df["text"][i]
    ], model='nomic-embed-text-v1',task_type='search_query')
  list_nomic.append(np.array(output["embeddings"][0]))
  dic_nomic = dict()

dic_nomic["embeddings"] = list_nomic

df_new_embedding = pd.DataFrame(dic_nomic)
df = pd.merge(df,df_new_embedding,left_index=True, right_index=True)
df['embeddings'] = df['embeddings'].apply(lambda x: x.tolist())

# Save DataFrame to CSV
df.to_csv('nomic_emb.csv', index=False)
#****************************

df = pd.read_csv("nomic_emb.csv")

def convert_numpy(string_list):
  values = string_list.strip('[]').split(',')
  array = np.array([float(value) for value in values])
  return array

df["embeddings"] = df["embeddings"].apply( lambda x: convert_numpy(x))
df["embeddings"] = df["embeddings"].apply( lambda x: x.astype(np.float32))

dataset = Dataset.from_pandas(df)
embeddings = np.vstack(df["embeddings"].values)

embeddings.shape

kd_index = KDTree(embeddings)

titles = dict(zip(range(len(df)), df.title))

# PROCESS QUESTIONS

input_dataset_filename = "../datasets/" + dataset_name + "_final.json" #
output_filename = f'{dataset_name}_solved_answers.json'

current_time = datetime.now().strftime("%Y%m%d-%H%M%S%f")

# create dir if doesn't exist
root_results_folder = "results_with_rag_nomic"
if not os.path.exists(root_results_folder):
    os.makedirs(root_results_folder)
output_solved_answers_filepath = root_results_folder + "/" + current_time + "_" + output_filename

with open(input_dataset_filename, 'r', encoding='utf-8') as file:
    questions = json.load(file)

# Todo: save this to disk
encoded_questions = dict()

total_token_count = 0
total_questions_with_tokens = 0

info_messages_dir = "info_msg_with_token_count/" + current_time
# Create dir if doesn't exist
if not os.path.exists(info_messages_dir):
    os.makedirs(info_messages_dir)

cos_sim = lambda a, b: np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

prompt_config = read_json('prompts.json')



solved_questions = []
def process_question_rag(question, model="nomic-embed-text-v1"):
    global total_token_count, total_questions_with_tokens, all_contexts

    if question['uid'] not in encoded_questions:
       
        output = embed.text(
    texts=[question['NNQT_question'] ], model=model,task_type='search_query')
        encoded_question = np.array(output["embeddings"][0])[np.newaxis, :]
        encoded_questions[question['uid']] = encoded_question
    else:
        encoded_question = encoded_questions[question['uid']]

    d, indices = kd_index.query(encoded_question, k=5)
    contexts = [titles[int(t)] + ' - ' + df.iloc[int(t)]['text'] for t in indices[0]]

    answers, original_answers, reason, answers_datatype, extra_info, token_count = process_question_with_rag_context(
        question, contexts, info_messages_dir, prompt_config)

    total_token_count += token_count
    total_questions_with_tokens += 1

    solved_question = calc_question_f1_score(question, answers, original_answers, reason, answers_datatype, extra_info)
    solved_questions.append(solved_question)

questions[0]['NNQT_question']

print("Processing questions")

for i, q in enumerate(questions):
    if i % 10 == 0:
        print(f"Processed {i}/{len(questions)} questions")
    process_question_rag(q, "nomic-embed-text-v1")

sort_questions(solved_questions)

if len(solved_questions) == 0:
    print("No questions to process")
    #sys.exit()

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


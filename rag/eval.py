
import os

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

passages_path = os.path.join('data', 'models', "wikipedia_kb_dataset")
index_path = os.path.join('data', 'models', "wikipedia_kb_index.faiss")

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

question = "what is the "

encoded_question = model.question_encoder(**tokenizer.question_encoder(question, return_tensors="pt"))[0].numpy()
model.retriever.index.get_top_docs(encoded_question, 10)











import os
from functools import partial

import faiss
import torch
from datasets import Features, Sequence, Value, load_dataset

from transformers import (
    DPRContextEncoder,
    DPRContextEncoderTokenizerFast,
)

torch.set_grad_enabled(False)
device = "cuda" if torch.cuda.is_available() else "cpu"


def embed(documents: dict, ctx_encoder: DPRContextEncoder, ctx_tokenizer: DPRContextEncoderTokenizerFast) -> dict:
    """Compute embeddings of document passages"""
    input_ids = ctx_tokenizer(
        documents["title"], documents["text"], truncation=True, padding="longest", return_tensors="pt"
    )["input_ids"]
    embeddings = ctx_encoder(input_ids.to(device=device), return_dict=True).pooler_output
    return {"embeddings": embeddings.detach().cpu().numpy()}


# CSV DATASET WITH CHUNKS #########################
kb_dataset = 'data/wiki_articles_chunks_noh.csv'
###################################################

encoder_model_name = 'facebook/dpr-ctx_encoder-multiset-base'

batch_size = 128

passages_path = os.path.join('data', 'models', "wikipedia_kb_dataset")
index_path = os.path.join('data', 'models', "wikipedia_kb_index.faiss")

gen_dataset = not os.path.exists(passages_path)

########################################
# CREATES CHUNKS DATASET AND EMBEDDINGS
########################################

if gen_dataset:

    dataset = load_dataset(
        "csv", data_files=[kb_dataset], split='train', delimiter=",", column_names=['id', "text", "title", 'url']
    )

    ctx_encoder = DPRContextEncoder.from_pretrained(encoder_model_name).to(device=device)
    ctx_tokenizer = DPRContextEncoderTokenizerFast.from_pretrained(encoder_model_name)

    new_features = Features(
        {
            "text": Value("string"),
            "title": Value("string"),
            "id": Value("string"),
            "url": Value("string"),
            "embeddings": Sequence(Value("float32"))  # OJO: FLOAT 32
        }
    )

    dataset = dataset.map(
        partial(embed, ctx_encoder=ctx_encoder, ctx_tokenizer=ctx_tokenizer),
        batched=True,
        batch_size=batch_size,
        features=new_features,
    )
    os.makedirs(passages_path)

    dataset.save_to_disk(passages_path)
else:
    from datasets import load_from_disk
    dataset = load_from_disk(passages_path)  # to reload the dataset


#############################
# GEN NDEX ##################
#############################

gen_index = not os.path.exists(index_path)

if gen_index:
    index = faiss.IndexHNSWFlat(768, 128, faiss.METRIC_INNER_PRODUCT)
    dataset.add_faiss_index("embeddings", custom_index=index)

    dataset.get_index("embeddings").save(index_path)
else:
    dataset.load_faiss_index("embeddings", index_path)  # to reload the index



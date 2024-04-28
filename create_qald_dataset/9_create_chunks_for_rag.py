import numpy as np
import pandas as pd
import os
import json
import re
from spacy.lang.en import English

path_qald10_entities = "qald_entities_articles"

# geta list of all file names
file_names = os.listdir(path_qald10_entities)

file_names= [i for i in file_names if ".json" in i]

df = pd.DataFrame(columns=['id', "text", "title", 'url'])
for i, json_file in enumerate(file_names):
    with open(os.path.join(path_qald10_entities, json_file), 'r', encoding='utf-8') as file:
        json_data = json.load(file)
        
    df.loc[i,"id"] = json_data["wikidata_id"]
    df.loc[i,"text"] = json_data["extract"]
    df.loc[i,"title"] = json_data["title"]
    df.loc[i,"url"] = json_data["wikipedia_url"]

df["text"] = df["text"].str.replace("==\n\n\n===","")
df["text"] = df["text"].str.replace("===\n","")
df["text"] = df["text"].str.replace("\n\n\n==","")
df["text"] = df["text"].str.replace("==\n","")
df["text"] = df["text"].str.replace("\n","")



nlp = English()
# Add a sentencizer pipeline, see https://spacy.io/api/sentencizer 
nlp.add_pipe("sentencizer")

extracts_id_dict = []

for i in df.index.values:
    extracts_id_dict.append({"id": df.loc[i ,"id" ], 
                             "text": df.loc[i ,"text" ]})    

for item in extracts_id_dict:
    item["sentences"] = list(nlp(item["text"]).sents)
    item["sentences"] = [str(sentence) for sentence in item["sentences"]]
    
    # Count the sentences 
    item["page_sentence_count_spacy"] = len(item["sentences"])


#Reference of function: https://github.com/mrdbourke/simple-local-rag
# Define split size to turn groups of sentences into chunks

num_sentence_chunk_size = 3

# Create a function that recursively splits a list into desired sizes
def split_list(input_list: list, 
               slice_size: int) -> list[list[str]]:
    """
    Splits the input_list into sublists of size slice_size (or as close as possible).

    For example, a list of 17 sentences would be split into two lists of [[10], [7]]
    """
    return [input_list[i:i + slice_size] for i in range(0, len(input_list), slice_size)]

# Loop through pages and texts and split sentences into chunks
for item in extracts_id_dict:
    item["sentence_chunks"] = split_list(input_list=item["sentences"],
                                         slice_size=num_sentence_chunk_size)
    item["num_chunks"] = len(item["sentence_chunks"])


# Split each chunk into its own item
extracts_id_dict1 = []
for item in extracts_id_dict:
    for sentence_chunk in item["sentence_chunks"]:
        chunk_dict = {}
        chunk_dict["id"] = item["id"]
        
        # Join the sentences together into a paragraph-like structure, aka a chunk (so they are a single string)
        joined_sentence_chunk = "".join(sentence_chunk).replace("  ", " ").strip()
        joined_sentence_chunk = re.sub(r'\.([A-Z])', r'. \1', joined_sentence_chunk) # ".A" -> ". A" for any full-stop/capital letter combo 
        chunk_dict["sentence_chunk"] = joined_sentence_chunk
        # Get some stats on our chunks
        
        chunk_dict["chunk_word_count"] = len([word for word in joined_sentence_chunk.split(" ")])
        extracts_id_dict1.append(chunk_dict)



df_chunks = pd.DataFrame(extracts_id_dict1)


#Keep chunks that are equal or smaller than 300 
smaller_chuncks1 = df_chunks.loc[df_chunks["chunk_word_count"]<=300,["id","sentence_chunk"]]
#We keep working on splitting these ones:
more_300 = df_chunks[df_chunks["chunk_word_count"]>300] 

dict_300 = []

for i in more_300.index.values:
    dict_300.append({"id": more_300.loc[i ,"id" ], 
                             "text": more_300.loc[i ,"sentence_chunk" ]})   



for item in dict_300:
    item["sentences"] = list(nlp(item["text"]).sents)
    item["sentences"] = [str(sentence) for sentence in item["sentences"]]
    
    #Count the sentences 
    item["page_sentence_count_spacy"] = len(item["sentences"])

for item in dict_300:
    item["sentence_chunks"] = split_list(input_list=item["sentences"],slice_size = num_sentence_chunk_size)
    item["num_chunks"] = len(item["sentence_chunks"])


# Split each chunk into its own item
dict_300_2 = []
for item in dict_300:
    for sentence_chunk in item["sentence_chunks"]:
        chunk_dict = {}
        chunk_dict["id"] = item["id"]
        
        # Join the sentences together into a paragraph-like structure, aka a chunk (so they are a single string)
        joined_sentence_chunk = "".join(sentence_chunk).replace("  ", " ").strip()
        joined_sentence_chunk = re.sub(r'\.([A-Z])', r'. \1', joined_sentence_chunk) # ".A" -> ". A" for any full-stop/capital letter combo 
        chunk_dict["sentence_chunk"] = joined_sentence_chunk
        # Get some stats on our chunks
        
        chunk_dict["chunk_word_count"] = len([word for word in joined_sentence_chunk.split(" ")])
        
        dict_300_2.append(chunk_dict)


pd.DataFrame(dict_300_2).describe()

df_chunks_2 = pd.DataFrame(dict_300_2)


#We still have chunks bigger than 300
#aAfter inspecting the remaining articles with bigger chunks, we proceed to split them \
# using the function split_text isntead of split_list as before 
smaller_chuncks2 = df_chunks_2.loc[df_chunks_2["chunk_word_count"]<=300,["id","sentence_chunk"]]
more_300_2 = df_chunks_2[df_chunks_2["chunk_word_count"]>300] 

extracts_id_dict = []

for i in more_300_2.index.values:
    extracts_id_dict.append({"id": more_300_2.loc[i ,"id" ], 
                             "text": more_300_2.loc[i ,"sentence_chunk" ]})    

def split_text(input_text: str, 
               slice_size: str) -> list[list[str]]:
  
    text_list = input_text.split(" ")
    return [text_list[i:i + slice_size] for i in range(0, len(text_list), slice_size)]

for item in extracts_id_dict:
    item["sentences"] = split_text(item["text"],300)
       
extracts_id_dict1 = []
for item in extracts_id_dict:
    for sentence_chunk in item["sentences"]:
        chunk_dict = {}
        chunk_dict["id"] = item["id"]

extracts_id_dict1 = []
for item in extracts_id_dict:
    for sentence_chunk in item["sentences"]:
        chunk_dict = {}
        chunk_dict["id"] = item["id"]
        
        # Join the sentences together into a paragraph-like structure, aka a chunk (so they are a single string)
        joined_sentence_chunk = " ".join(sentence_chunk).replace("  ", " ").strip()
        joined_sentence_chunk = re.sub(r'\.([A-Z])', r'. \1', joined_sentence_chunk) # ".A" -> ". A" for any full-stop/capital letter combo 
        chunk_dict["sentence_chunk"] = joined_sentence_chunk
        # Get some stats on our chunks
        
        chunk_dict["chunk_word_count"] = len([word for word in joined_sentence_chunk.split(" ")])
        extracts_id_dict1.append(chunk_dict)



smaller_chuncks3=pd.DataFrame(extracts_id_dict1)[["id","sentence_chunk"]]

#Now concatenate all the chunks:
concatenated_df = pd.concat([smaller_chuncks1, smaller_chuncks2, smaller_chuncks3])
concatenated_df.reset_index(drop=True, inplace=True)


concatenated_df=concatenated_df.merge(df,on="id")
concatenated_df.drop(labels=["text"],axis=1,inplace=True)
concatenated_df.rename(columns={"sentence_chunk":"text"},inplace=True)
concatenated_df.to_csv("qald_articles_chunks.csv",index=False,encoding='utf-32')
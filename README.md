# IFT6759

## Installation

Tested on python version 3.10

### Install the conda environment
conda create --name IFT6759_tests python=3.10

conda activate IFT6759_tests

pip install -r requirements.txt

### OpenAI

This project uses the openAI api to query either gpt3.5 or gpt4, an OpenAI account is thus required to use our system. To use the OpenAI API, create an environment variable called "OPENAI_API_KEY" containing your full API key.

To choose which model to use, edit query_llm/oai_config.json and change the model field to either "gpt-3.5-turbo" or "gpt-4-turbo".

## Installation (RAG part only)

### Install pytorch
Follow the download instructions on the official pytorch download page (version 2.3.0) : https://pytorch.org/get-started/locally/

### Install Nomic
Follow the download instructions specified at the official nomic repository page: https://github.com/nomic-ai/nomic

## Run the system with a short example

The following scripts can be run to test the system from end to end on the qald_10_train_short dataset. This contains the first 10 questions of the qald_10_train dataset.

### Create the dataset files

cd create_qald_dataset

python .\1_format_qald_dataset.py qald_10_train_short

python .\2_update_dataset_answers.py qald_10_train_short

python .\3_get_solved_answer.py qald_10_train_short

python .\4_extract_all_unique_entities.py qald_10_train_short

python .\5_get_unique_entities_labels_and_urls.py

python .\6_download_wiki_articles_json.py

python .\7_query_unique_entities_info.py

python .\8_add_properties_and_relations_to_entities.py

python .\9_create_chunks_for_rag.py

### Query the LLM (baseline)

cd ../query_llm

python .\1_answer_question_no_added_info.py qald_10_train_short

### Link the question's main entity

python .\2_identify_entity_in_question.py qald_10_train_short

python .\3_identify_entity_in_question_using_wikidata.py qald_10_train_short

### Query the LLM (using the previously downloaded question entities)

python .\4_answer_questions_with_ner_info.py qald_10_train_short False False

python .\5_answer_entity_linking.py qald_10_train_short False False

### Query the LLM (using wikidata directly)

python .\4_answer_questions_with_ner_info.py qald_10_train_short True False

python .\5_answer_entity_linking.py qald_10_train_short True False

### Query the LLM (ReACT)

python .\4_answer_questions_with_ner_info.py qald_10_train_short True True

python .\5_answer_entity_linking.py qald_10_train_short True True

### Perform RAG:

python .\DPR_rag.py qald_10_train_short

python .\rag_llm.py qald_10_train_short

python .\rag_llm_nomic.py qald_10_train_short

## Datasets

The final versions of all datasets is in the "datasets" folder. By final, we mean that these files were created by running all the scripts in the previous create_qald_dataset folder.

## Documentation

### Update the dataset files: create_qald_dataset folder

1_format_qald_dataset.py : Modify the format of the dataset to only keep the information relevant for our use case and make it easier to work with different datasets in the future.

2_update_dataset_answers.py : Update the answers in all datasets by relaunching the sparql queries.

3_get_solved_answer.py : Modify both dataset to fetch every answer's english label and place it in the "solved_answer" field. Create a corresponding <dataset name>_final.json in the datasets folder.

4_extract_all_unique_entities.py : Go through all questions in all the datasets given as parameters (ex: qald_10_train and qald_10_test) and save all the unique entities present in the questions (not the answers) in qald_unique_entities.txt. 

5_get_unique_entities_labels_and_urls.py : Fetch the corresponding wikipedia article title and url for every entities in qald_unique_entities.

6_download_wiki_articles_json.py : Download all the full wikipedia articles in plaintext for each url located in qald_X_unique_entities_with_urls. Add each article as a json file in the folder "qald_10_entities_articles".

7_query_unique_entities_info.py : Go through all the entities in qald_unique_entities.txt and download all of the wikidata object's information (except the claims). Save each in json format in the qald_unique_entities_info folder.

8_add_properties_and_relations_to_entities.py : Go through all the entities in the qald_unique_entities_info folder and download all of their properties and relations (properties and relations (claims) directly attatched to the entities + external relations linking in (only the name of the relation). Add all this information to the already existing .json files in the folder.

9_create_chunks_for_rag : Creates the text qald_articles_chunks.csv which contains the chunked wikipedia articles, which are used for the RAG part of the project.

## Query the LLM to answer the dataset's questions: query_llm folder

1_answer_question_no_added_info.py : Go through all questions in the given dataset and attempt to answer each question using only the LLM to answer it (no added info). Save the results to <dataset_name>_solved_answers.json

2_identify_entity_in_question.py : Query the LLM to identify the main entity for the question and make a guess as to what the true answer could be. Attempt to link that entity with one of the entities in the "qald_unique_entities_info" folder by doing an exact match on either the entities labels or aliases. Save the results in NER_both.json.

3_identify_entity_in_question_using_wikidata.py : Alternative to the step 2 above (just use one or the other, not both). Query the LLM to identify the main entity for the question and make a guess as to what the true answer could be. Attempt to link that entity with a wikidata entity by querying the api directly and doing an exact match on either the entities labels or aliases. If the query returns more than one entity, ask the LLM to chose the correct entity in order to disambiguate the results. Save the results in NER_both.json.

4_answer_questions_with_ner_info.py : Use the LLM to answer each questions, appending all of information linked to the entity found in the previous step (either from the entity folder or directly from wikidata). If the entity linking failed in step 2 for that question, use the answer found in step 1 (LLM only, no added information).

5_answer_entity_linking : Use the LLM to link every answer given in step 3 that is not a boolean, a number or a date to the corresponding entity in wikidata. Recalculate the f1 score by matching the found wikidata entity url on both sides, instead of doing an exact match on the labels and aliases of the answer entity.

# IFT6759

## Installation

### Install the conda environment
conda create --name IFT6759_tests python=3.10

conda activate IFT6759_tests

pip install -r requirements.txt

### Install pytorch
Follow the download instructions on the official pytorch download page: https://pytorch.org/get-started/locally/
Note : Only used for the RAG part of the project.

## Modify qald9_plus and qald10 datasets

The qald9_plus is used as a training set for the qald10 dataset. Qald_X can refer to either the Qald9 or 10 dataset

1_format_qald_dataset.py : Modify the format of the dataset to only keep the information relevant for our use case and make it easier to work with different datasets in the future. For the qald9 dataset, we remove all questions with over 25 answers (most of the size of the file is otherwise occupied by those questions, and that's not really what we want to test). The qald10 dataset is kept as is (only one question with many answers anyways). Save as qald_9_train_formatted_and_cleaned.json and qald_10_test_formatted_and_cleaned.json.

2_update_dataset_answers.py : Update the answers in all datasets by relaunching the sparql queries. Save the result as qald_9_train_updated_answers.json and qald_10_test_updated_answers.json.

3_get_solved_answer.py : Modify both dataset to fetch every answer's english label and place it in the "solved_answer" field. Save the result as qald_X_train_with_solved_answers.json.

4_extract_all_unique_entities.py : Go through all questions in both the qald9 and qald10 dataset and save all the unique entities present in the questions (not the answers) in qald_unique_entities.txt. 

5_get_unique_entities_labels_and_urls.py : Fetch the corresponding wikipedia article title and url for every entities in qald_unique_entities. Save as qald_X_train_missing_entities_ids_with_urls.txt.

6_download_wiki_articles_json.py : Download all the full wikipedia articles in plaintext for each url located in qald_X_unique_entities_with_urls. Add each article as a json file in the folder "qald_X_entities_articles".

7_query_unique_entities_info.py : Go through all the entities in qald_unique_entities.txt and download all of the wikidata object's information (except the claims). Save each in json format in the qald_unique_entities_info folder.

8_add_properties_and_relations_to_entities.py : Go through all the emtotoes in the qald_unique_entities_info folder and download all of their properties and relations (properties and relations (claims) directly attatched to the entities + external relations linking in (only the name of the relation). Add all this information to the already existing .json files in the folder.

## Query LLM

1_answer_question_no_added_info.py : Go through all questions in the given dataset and attempt to answer each question using only the LLM to answer it (no added info). Save the results to qald_X_train_solved_answers.json

2_identify_entity_in_question.py : Query the LLM to identify the main entity for the question and make a guess as to what the true answer could be. Attempt to link that entity with one of the entities in the "qald_unique_entities_info" folder by doing an exact match on either the entities labels or aliases. Save the results in NER_both.json.

2_identify_entity_in_question_using_wikidata.py : Query the LLM to identify the main entity for the question and make a guess as to what the true answer could be. Attempt to link that entity with a wikidata entity by querying the api directly and doing an exact match on either the entities labels or aliases. If the query returns more than one entity, ask the LLM to chose the correct entity in order to disambiguate the results. Save the results in NER_both.json.

4_answer_questions_with_ner_info.py : Use the LLM to answer each questions, appending all of information linked to the entity found in the previous step (either from the entity folder or directly from wikidata). If the entity linking failed in step 2 for that question, use the answer found in step 1 (LLM only, no added information).

5_answer_entity_linking : Use the LLM to link every answer given in step 4 that is not a boolean, a number or a date to the corresponding entity in wikidata. Recalculate the f1 score by matching the found wikidata entity url on both sides, instead of doing an exact match on the labels and aliases of the answer entity.

## Final

The final versions of all datasets is in the "datasets" folder.
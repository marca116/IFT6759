# IFT6759

# Modify qald9_plus and qald10 datasets

The qald9_plus is used as a training set for the qald10 dataset. Qald_X can refer to either the Qald9 or 10 dataset

1_format_qald_dataset.py : Modify the format of the dataset so it's the same as LCQuad2 (so both can be used in the same manner). For the qald9 dataset, we remove all questions with over 25 answers (most of the size of the file is otherwise occupied by those questions, and that's not really what we want to test). The qald10 dataset is kept as is (only one question with many answers anyways). Save as qald_9_train_formatted_and_cleaned.json and qald_10_test_formatted_and_cleaned.json.

2_update_dataset_answers.py : Update the answers in all datasets by relaunching the sparql queries. Save the result as qald_9_train_updated_answers.json and qald_10_test_updated_answers.json.

3_get_solved_answer.py : Modify both dataset to fetch every answer's english label and place it in the "solved_answer" field. Save the result as qald_X_train_with_solved_answers.json.

4_extract_all_unique_entities.py : Go through all questions in both the qald9 and qald10 dataset and save all the unique entities present in the questions (not the answers) in qald_unique_entities.txt. 

5_get_unique_entities_labels_and_urls.py : Fetch the corresponding wikipedia article title and url for every entities in qald_unique_entities. Save as qald_X_train_missing_entities_ids_with_urls.txt.

6_download_wiki_articles_json.py : Download all the full wikipedia articles in plaintext for each url located in qald_X_unique_entities_with_urls. Add each article as a json file in the folder "qald_X_entities_articles".

7_query_unique_entities_info.py : Go through all the entities in qald_unique_entities.txt and download all of the wikidata object's information (except the claims). Save each in json format in the qald_unique_entities_info folder.

8_add_properties_and_relations_to_entities.py : Go through all the emtotoes in the qald_unique_entities_info folder and download all of their properties and relations (properties and relations (claims) directly attatched to the entities + external relations linking in (only the name of the relation). Add all this information to the already existing .json files in the folder.

# Query LLM

1_answer_question_no_added_info.py : Go through all questions in the given dataset and attempt to answer each question using only the LLM to answer it (no added info). Save the results to qald_X_train_solved_answers.json

2_identify_entity_in_question.py : Query the LLM to identify the main entity for the question and make a guess as to what the true answer could be. Attempt to link that entity with one of the entities in the "qald_unique_entities_info" folder by doing an exact match on either the entities labels or aliases. Save the results in NER_both.json.

2_identify_entity_in_question_using_wikidata.py : Query the LLM to identify the main entity for the question and make a guess as to what the true answer could be. Attempt to link that entity with a wikidata entity by querying the api directly and doing an exact match on either the entities labels or aliases. If the query returns more than one entity, ask the LLM to chose the correct entity in order to disambiguate the results. Save the results in NER_both.json.

4_answer_questions_with_ner_info.py : Use the LLM to answer each questions, appending all of information linked to the entity found in the previous step (either from the entity folder or directly from wikidata). If the entity linking failed in step 2 for that question, use the answer found in step 1 (LLM only, no added information).

# Final

The final versions of all datasets is in the "datasets" folder.

# DEPRECATED

# Vital articles wikipedia extracts
https://drive.google.com/file/d/1ddp1dq3zzKZ-qhBqGHTvNBT2fItHko0p/view

# Create list of vital articles

1_download_urls_vital_articles.py : Extract all the links in the list of all vital articles on wikipedia : https://en.wikipedia.org/w/index.php?title=Wikipedia:Vital_articles/List_of_all_articles&oldid=928962928. Save as vital_articles_2019.txt

2_download_wiki_entity_ids.py : For each vital articles, fetch the corresponding wikipedia page title and url. Save as vital_articles_entities_2019.csv.

# Modify LCQuad2 dataset

1_download_covered_entities_wiki_articles_json.py : Download all the full wikipedia articles in plaintext for each url located in vital_articles_entities_2019.csv (created in vital article section). Add each article as a json file in the folder "vital_articles_wiki_extract".

2_add_simplified_queries.py : Update train.txt to include the simplified queries associated with each question's sparql queries. Used the lc_quad2-sparqltotext dataset from huggingface (https://huggingface.co/datasets/OrangeInnov/lc_quad2-sparqltotext). Save as train_with_simplified_query.json.
Note : Couldn't use the answers included in this dataset since they are out of date, need to be recalculated in the next step.

3_remove_missing_entities_from_lcquad_questions.py : Go through train_with_simplified_query.json and remove all the questions that contains entities not included in either vital_articles_entities_2019.csv, qald_9_plus_train_missing_entities_ids_with_urls.txt, or qald_10_test_missing_entities_ids_with_urls.txt. This is in order to make sure every questions can actually be answered with the vector database of wikipedia articles. Save as train_cleaned_no_missing_entities.json. 

4_run.sparql.queries.py : Use the wikidata query api to obtain the answer to every remaining questions in train_cleaned_no_missing_entities.json (field = "sparql_wikidata"). Save the updated data as train_cleaned_with_answers.json. Query api : https://query.wikidata.org.

5_remove_questions_invalid_answers.py : Go through every questions in train_cleaned_with_answers.json and remove any questions where the answer couldn't be calculated. Also remove all questions with > 25 answers (bad question if that many answers). Also remove any other kind of invalid questions (Ex: questions with paraphrased questions > 300 chars is usually a mistake). Save result in train_cleaned_only_questions_with_answers.json.

6_get_wiki_entities_labels_and_url.py: Go through all the questions in train_cleaned_only_questions_with_answers and extract every wikidata entity id. Then, go through each entity id and use wikidata query api to query the label and it's wikipedia article title and url, if it exists. Add all this info to answer_entities_labels_and_url.csv.

7_add_solved_answer_to_all_questions.py : Go through all the questions in train_cleaned_only_questions_with_answers.json, replacing every wikidata entity id in every answer with it's corresponding label from answer_entities_labels_and_url.csv. Include the result in a new property to the question called 'solved_answer'. Save to train_lcquad2_with_solved_answers.json.

8_remove_duplicated_answers.py : Go through all the questions in train_lcquad2_with_solved_answers, and remove all answers that are duplicated (happens the Sparql asks for 2 parts to the answer, the first part is duplicated for each second part). Do the same for both answer and solved_answer. Save to train_lcquad2_final.json.

9_shrink_and_balance_dataset.py : Shrink train_lcquad2_final.json down to a more managable size (ex:  1.4k), while keeping the same template ratio as the original dataset (train.json). 


# IFT6759

#Creating the dataset

1_download_lcquad_entities_wiki_links.py : Download the wikipedia article's url associated with each wikidata entity that was included entities_covered.txt (from the LC-Quad2 dataset). Save the result in lcquad_entities_url.txt. If no wikipedia url is found for that entity, save it's id in lcquad_missing_entities.txt (question will be removed in step 4)

2_download_covered_entities_wiki_articles_json.py : Download all the full wikipedia articles in plaintext for each url located in lcquad_entities_url.txt (created at the previous set). Add each article as a json file in the folder "covered_entities_wiki_articles".

3_add_simplified_queries.py : Update train.txt to include the simplified queries associated with each question's sparql queries. Used the lc_quad2-sparqltotext dataset from huggingface (https://huggingface.co/datasets/OrangeInnov/lc_quad2-sparqltotext). Save as train_with_simplified_query.json.
Note : Couldn't use the answers included in this dataset since they are out of date, need to be recalculated in the next step.

4_remove_missing_entities_from_lcquad_questions.py : Go through train_with_simplified_query.json and remove all the questions that references entities in lcquad_missing_entities.txt, in order to make sure every questions can actually be answered with the vector database of wikipedia articles. Save as train_cleaned.json. 

5_run.sparql.queries.py : Use the wikidata query api to obtain the answer to every questions in train_cleaned.json (field = "sparql_wikidata"). Save the updated data as train_cleaned_with_answers.json. Query api : https://query.wikidata.org

6_remove_questions_invalid_answers.py : Go through every questions in train_cleaned_with_answers.json and remove any questions where the answer couldn't be calculated. Also remove all questions with > 25 answers (bad question if that many answers). Save result in train_cleaned_only_questions_with_answers.json.

7_create_list_answers_entities.py : Go through all the questions in train_cleaned_only_questions_with_answers and add every answers' wikidata entity id to train_answer_all_entities.txt.

8_get_wiki_entities_labels_and_url.py: Go through each wikidata entity id from train_answer_all_entities.txt and use wikidata query api to query the label and it's wikipedia article title and url, if it exists. Add all this info to answer_entities_labels_and_url.csv.

9_add_solved_answer_to_all_questions.py : Go through all the questions in train_cleaned_only_questions_with_answers, replacing every wikidata entity id in every answer with it's corresponding label from answer_entities_labels_and_url.csv. Include the result in a new properyty to the question called 'solved_answer'.
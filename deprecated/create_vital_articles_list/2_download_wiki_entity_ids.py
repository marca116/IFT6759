# NOT TESTED

import csv
from urllib.parse import unquote
import sys

sys.path.insert(0, "../utils")
from utils import get_wikidata_entity_from_wikipedia

skip_existing = True
max_group_size = 50


vital_articles_filename = 'vital_articles_2019.txt'
vital_articles_entities_filename = 'vital_articles_entities_2019.csv'
urls = []

with open(vital_articles_filename, 'r', encoding='utf-8') as file:
    urls = file.readlines() 

# combine in groups of entity_per_group (in case higher than max_entity_per_group)
titles_groups = []
for x in range(0, len(urls), max_group_size):
    group = urls[x:x+max_group_size]
    # unquote the titles
    for i, url in enumerate(group):
        formatted_title = url.strip().split('/')[-1]
        group[i] = unquote(formatted_title)

    titles_groups.append("|".join(group))

# get the results for each group
for x, titles_group in enumerate(titles_groups, start=1):
    results = get_wikidata_entity_from_wikipedia(titles_group) # Fallback to whatever language is available if label missing

    for result in results:
        entity_id, title, url = result

        with open(vital_articles_entities_filename, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([entity_id, title, url])

    print(f"Processed {x} out of {len(titles_groups)} groups")

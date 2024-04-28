import requests
import os
import json
import time
import csv
import sys
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "../utils")
from utils import download_article_json, get_filename

skip_existing = True
output_dir = 'qald_entities_articles' 
articles_filename = 'qald_unique_entities_with_urls'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Download the given vital article's extract
def process_article(vital_article):
    entity_id = vital_article[0]
    wiki_title = unquote(vital_article[1].strip())
    wiki_url = vital_article[2].strip()

    # Skip if url missing (some quad9 and 10 questions)
    if wiki_title == "":
        print(f"Skipping {entity_id} as it has no url")
        return

    # Skip if already exists
    if skip_existing:
        filename = get_filename(wiki_url, entity_id)

        if os.path.exists(os.path.join(output_dir, f'{filename}.json')):
            print(f"Skipping {filename} as it already exists")
            return

    for i in range(5):
        try:
            download_article_json(wiki_title, wiki_url, output_dir, entity_id)
            return
        except Exception as e:
            print(f"Error running query: {e}")
            time.sleep(60)
    
vital_articles = []

with open(articles_filename + '.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        vital_articles.append(row)

# Process the data in batches
batch_size = 4
start_time = time.time()

# sepparate the data in groups of 3
batches = [vital_articles[i:i + batch_size] for i in range(0, len(vital_articles), batch_size)]

for i, batch in enumerate(batches):

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_article, article) for article in batch]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error occurred in sub-thread: {e}")
    
    print(f"Processed {i + 1}/{len(batches)} article batches")

print(f"Total time: {time.time() - start_time} seconds")
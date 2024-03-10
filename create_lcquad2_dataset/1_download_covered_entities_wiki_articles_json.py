import requests
import os
import json
import time
import csv
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

skip_existing = True
output_dir = 'vital_articles_wiki_extract' 
articles_filename = 'q9_q10'

wiki_main_url = "https://en.wikipedia.org/w/api.php"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def get_filename(wikipedia_url, wikidata_id):
    return wikipedia_url.strip().split('/')[-1].replace('*', '#STAR#') + "_" + wikidata_id

def download_article_json(entity_id, wiki_title, wiki_url):
    params = {
        'action': 'query',
        'prop': 'extracts',
        'titles': wiki_title, # Max limit = 1 for extracts
        'explaintext': 1,
        'redirects': 1,
        'format': 'json'
    }

    response = requests.get(wiki_main_url, params=params)
    if response.status_code == 200:
        json_obj = response.json()

        if json_obj.get('query') is None or json_obj['query'].get('pages') is None:
            print(f"Failed to download {wiki_title}, no page found.")
            return None
        
        query = json_obj['query']
        pages = query['pages']
        redirects = query.get('redirects')

        # Should always have only 1 page
        if len(pages) > 1:
            print(f"Failed to download {wiki_title}, multiple pages found.")
            return None

        # Go through each property
        for page_id in pages:
            page = pages[page_id]
            title = page.get('title')

            new_entity_obj = {
                "title": title
            }

            # If was redirected, need to get what the original title was
            if redirects is not None:
                for redirect in redirects:
                    if redirect.get("to") == title:
                        print(f"Redirected from {title} to {redirect['to']}")
                        new_entity_obj["redirected_from"] = redirect['from']

            # Set the properties
            new_entity_obj["pageid"] = page.get('pageid')
            new_entity_obj["ns"] = page.get('ns')
            new_entity_obj["wikidata_id"] = entity_id
            new_entity_obj["wikipedia_url"] = wiki_url
            new_entity_obj["extract"] = page.get('extract')

            file_name = get_filename(wiki_url, entity_id)

            with open(os.path.join(output_dir, f'{file_name}.json'), 'w', encoding='utf-8') as file:
                json.dump(new_entity_obj, file, ensure_ascii=False, indent=4)

    else:
        print(f"Failed to download {wiki_title}")

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
            download_article_json(entity_id, wiki_title, wiki_url)
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
import requests
import os
import json
import time
from urllib.parse import unquote

skip_existing = True
output_dir = 'covered_entities_wiki_articles' 
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

            # get the wikidata id
            # index = wiki_titles_group.index(original_title)

            # if index == -1:
            #     print(f"Failed to find entity id for {title}")
            #     continue

            # wikidata_id = entity_ids_group[index]
            # wikipedia_url = wiki_urls_group[index]

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

start_time = time.time()

with open('lcquad_entities_url.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines() 
    #total_entities = len(lines) 
    entity_ids = []
    wiki_titles = []
    wiki_urls = []

    for x, line in enumerate(lines, start=1):
        split_line = line.strip().split(";")

        entity_id = split_line[0]
        wiki_title = unquote(split_line[1].strip())
        wiki_url = split_line[2].strip()

        # Skip if already exists
        if skip_existing:
            filename = get_filename(wiki_url, entity_id)

            if os.path.exists(os.path.join(output_dir, f'{filename}.json')):
                print(f"Skipping {filename} as it already exists")
                continue

        download_article_json(entity_id, wiki_title, wiki_url)
        print(f"Processed {x}/{len(lines)} articles")
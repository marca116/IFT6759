import requests
import os
import json
import time
from urllib.parse import unquote

entity_per_group = 50

def get_entity_urls(entity_ids):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetentities',
        "format": "json",
        'props': 'sitelinks/urls',
        'ids': entity_ids,
        'sitefilter': 'enwiki'
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        json_obj = response.json()

        if json_obj.get('entities') is None:
            print(f"Failed to download {entity_ids}, no entity found.")
            return None
        
        # Go through each property
        for entity_id in json_obj['entities']:
            entity = json_obj['entities'][entity_id]
            #entity = json_obj['entities'][entity_id]
            redirects = entity.get('redirects')
            if redirects and redirects.get("to"):
                print(f"Redirected from {entity_id} to {redirects['to']}")
                get_entity_urls(redirects["to"])

            if entity.get("sitelinks") is None or entity["sitelinks"].get("enwiki") is None:
                print(f"Failed to download {entity_id} missing url.")

                with open('lcquad_missing_entities.txt', 'a') as f:
                    f.write(entity_id + '\n')

                continue

            link_en = entity["sitelinks"]["enwiki"]
            title = link_en["title"]
            wiki_url = link_en["url"]
            with open('lcquad_entities_url.txt', 'a', encoding='utf-8') as f:
                f.write(entity_id + ";" + title + ";" + wiki_url + '\n')
    else:
        print(f"Failed to download {entity_id}")

# # Create the files
# with open('lcquad_entities_url.txt', 'w') as f:
#     pass
# with open('lcquad_missing_entities.txt', 'w') as f:
#     pass

start_time = time.time()

with open('entities_covered.txt', 'r', encoding='utf-8') as file:
    lines = file.readlines() 
    #total_entities = len(lines) 
    entity_ids = []
    for x, line in enumerate(lines, start=1):
        entity_id = line.strip()

        # Skip the first row
        if entity_id == "" or entity_id == "entity":
            continue

        entity_ids.append(entity_id)

    # combine in groups of entity_per_group
    entity_ids_groups = []
    for x in range(0, len(entity_ids), entity_per_group):
        entity_ids_group = entity_ids[x:x+entity_per_group]
        entity_ids_groups.append("|".join(entity_ids_group))

    total_groups = len(entity_ids_groups)

    for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
        get_entity_urls(entity_ids_group)
        print(f"Processed {x}/{total_groups} groups ({entity_per_group} articles each)")

print(f"Total time: {time.time() - start_time} seconds")
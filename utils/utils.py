import requests
import json
import os

def get_wikidata_entities_info(entity_ids, allow_fallback_language=False):
    wiki_api_url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetentities',
        "format": "json",
        'props': 'labels|aliases|sitelinks/urls',
        'ids': entity_ids,
        'sitefilter': 'enwiki'
    }

    if not allow_fallback_language:
        params['languages'] = "en"

    response = requests.get(wiki_api_url, params=params)
    if response.status_code == 200:
        json_obj = response.json()

        if json_obj.get('entities') is None:
            print(f"Failed to download {entity_ids}, no entity found.")
            return None
        
        results = []

        # Go through each property
        for entity_id in json_obj['entities']:
            entity = json_obj['entities'][entity_id]
            #entity = json_obj['entities'][entity_id]
            redirects = entity.get('redirects')
            if redirects and redirects.get("to"):
                print(f"Redirected from {entity_id} to {redirects['to']}")
                redirect_results = get_wikidata_entities_info(redirects["to"])

                # Should always be 1 result
                if len(redirect_results) >= 1:
                    results.append(redirect_results[0])
                    continue
                else:
                    print(f"Failed to download {entity_id} redirected to {redirects['to']}")
                
            entity_labels = []
            label_language_obj = None

            if entity.get("labels") is not None:
                label_language_obj = entity["labels"].get("en")

            # Default to first available language if no language is set
            if entity.get("labels") is not None and label_language_obj is None and allow_fallback_language:
                label_language_objs = list(entity["labels"].values())
                if len(label_language_objs) > 0:
                    label_language_obj = label_language_objs[0]
                    print(f"En language label missing for entity {entity_id}, using language '{label_language_obj['language']}' instead.")

            if label_language_obj is None:
                print(f"Failed to download {entity_id} missing label.")
                with open('answer_entities_missing_label.txt', 'a') as f:
                    f.write(entity_id + '\n')
            else:
                entity_labels.append(label_language_obj["value"])

            if entity.get("aliases") is not None and entity["aliases"].get("en") is not None:
                # Add all eng aliases
                for alias in entity["aliases"]["en"]:
                    entity_labels.append(alias["value"])

            title = ""
            wiki_url = ""
            
            if entity.get("sitelinks") is None or entity["sitelinks"].get("enwiki") is None:
                print(f"Failed to download {entity_id} missing url.")
                with open('answer_entities_missing_url.txt', 'a') as f:
                    f.write(entity_id + '\n')
            else:
                link_en = entity["sitelinks"]["enwiki"]
                title = link_en["title"]
                wiki_url = link_en["url"]

            results.append((entity_id, entity_labels, title, wiki_url))

        return results
    else:
        print(f"Failed to download {entity_id}")

def get_wikidata_entity_from_wikipedia(titles):
    wiki_api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'prop': 'pageprops|info',
        'inprop': 'url',
        'ppprop': 'wikibase_item',
        'titles': titles, 
        'redirects': 1,
        'format': 'json'
    }

    response = requests.get(wiki_api_url, params=params)
    if response.status_code == 200:
        json_obj = response.json()

        if json_obj.get('query') is None or json_obj['query'].get('pages') is None:
            print(f"Failed to download {titles}, no page found.")
            return None
        
        query = json_obj['query']
        pages = query['pages']
        #redirects = query.get('redirects')

        results = []

        # Go through each property
        for page_id in pages:
            page = pages[page_id]
            title = page.get('title')
            url = page.get('fullurl')
            if page.get('pageprops') is None or page['pageprops'].get('wikibase_item') is None:
                print(f"Failed to download {title}, no wikibase_item found.")
                with open('missing_wikibase_items.txt', 'a') as f:
                    f.write(title + '\n')
            else:
                entity_id = page['pageprops']['wikibase_item']
                results.append((entity_id, title, url))

        return results

    else:
        print(f"Failed to download {titles}")

def get_filename(wikipedia_url, wikidata_id = None):
    return wikipedia_url.strip().split('/')[-1].replace('*', '#STAR#') + ("_" + wikidata_id if wikidata_id else "")

def download_article_json(wiki_title, wiki_url, output_dir, entity_id = None):
    wiki_main_url = "https://en.wikipedia.org/w/api.php"

    params = {
        'action': 'query',
        'prop': 'extracts',
        'titles': wiki_title, # Max limit = 1 for extracts
        'explaintext': 1,
        'redirects': 1,
        'format': 'json'
    }

    response = requests.get(wiki_main_url, params=params)
    wiki_main_url

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

# Function to run a SPARQL query against Wikidata
def run_sparql_query(query, flatten_answers = True):
    endpoint_url = "https://query.wikidata.org/bigdata/namespace/wdq/sparql" # alt : https://query.wikidata.org/sparql
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/sparql-results+json"}
    try:
        response = requests.get(endpoint_url, headers=headers, params={'query': query})
        response.raise_for_status()  
        data = response.json()

        answers = []

        if data.get("boolean") is not None:
            answers.append(data['boolean'])
        else:
            for binding in data['results']['bindings']:
                # Add all the answer objects properties individually to the list of answer when flattening
                if flatten_answers:
                    for answer_name in binding:
                        answer = binding[answer_name]
                        
                        if answer is not None and answer.get('value') is not None:
                            answers.append(answer['value'])
                        else:
                            print(f"Unknown binding: {binding}")
                else:
                    answer = {}
                    for key in binding:
                        answer[key] = binding[key]['value']
                    answers.append(answer)
                
        return answers
    
    except Exception as e:
        print(f"Error running query: {e}")
        return []

# Case insensitive comparison
def case_insensitive_equals(a, b):
    if isinstance(a, str) and isinstance(b, str):
        return a.lower() == b.lower()
    else:
        return a == b
    
# If both item and element are strings, compare them case-insensitively
def case_insensitive_elem_in_list(element, lst):
    for item in lst:
        if isinstance(element, str) and isinstance(item, str):
            if element.lower() == item.lower():
                return True
        elif element == item:
            return True
    return False
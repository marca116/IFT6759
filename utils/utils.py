import requests

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
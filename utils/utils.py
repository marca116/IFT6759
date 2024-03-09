import requests

def get_wikidata_entities_info(entity_ids, allow_fallback_language=False):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetentities',
        "format": "json",
        'props': 'labels|sitelinks/urls',
        'ids': entity_ids,
        'sitefilter': 'enwiki'
    }

    if not allow_fallback_language:
        params['languages'] = "en"

    response = requests.get(url, params=params)
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
                
            entity_label = ""
            label_language_obj = None

            if entity.get("labels") is not None:
                label_language_obj = entity["labels"].get("en")

            # Default to first available language if no language is set
            if entity.get("labels") is not None and label_language_obj is None and allow_fallback_language:
                label_language_obj = list(entity["labels"].values())[0]
                print(f"En language label missing for entity {entity_id}l, using language '{label_language_obj['language']}' instead.")

            if label_language_obj is None:
                print(f"Failed to download {entity_id} missing label.")
                with open('answer_entities_missing_label.txt', 'a') as f:
                    f.write(entity_id + '\n')
            else:
                entity_label = label_language_obj["value"] 

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

            results.append((entity_id, entity_label, title, wiki_url))

        return results
    else:
        print(f"Failed to download {entity_id}")
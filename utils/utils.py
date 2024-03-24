import requests
import json
import os
import time
import re
from dateutil.parser import parse
from datetime import datetime

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
        print(f"Failed to download {entity_ids}")
        return []

def get_wikidata_entities_all_info(entity_ids, properties = None):
    wiki_api_url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetentities',
        "format": "json",
        'ids': entity_ids,
        "languages": "en",
        'sitefilter': 'enwiki'
    }

    # Get everything (including sitelinks url) by default
    if properties is None:
        params['props'] = 'info|descriptions|labels|aliases|sitelinks/urls|claims'
    else:
        params['props'] = properties
    
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
                redirect_results = get_wikidata_entities_all_info(redirects["to"])

                # Should always be 1 result
                if len(redirect_results) >= 1:
                    results.append(redirect_results[0])
                    continue
                else:
                    print(f"Failed to download {entity_id} redirected to {redirects['to']}")
                
            results.append(entity)

        return results
    else:
        print(f"Failed to download {entity_ids}")
        return []

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

def get_batched_entities_info(entity_ids, properties = None, max_entity_per_group = 50):
    entities_info = []

    # combine in groups of entity_per_group (in case higher than max_entity_per_group)
    entity_ids_groups = []
    for x in range(0, len(entity_ids), max_entity_per_group):
        entity_ids_group = entity_ids[x:x+max_entity_per_group]
        entity_ids_groups.append("|".join(entity_ids_group))

    # get the results for each group
    for x, entity_ids_group in enumerate(entity_ids_groups, start=1):
        results = get_wikidata_entities_all_info(entity_ids_group, properties)
        entities_info += results

        print(f"Processed {x}/{len(entity_ids_groups)} groups")

    return entities_info

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

def get_id_from_url(url):
    return url.split("/")[-1]

wikidata_quantities_dict = {}

# Return the unit value based on the unit id
def get_unit_value(unit_id):
    if unit_id == "1": # No unit (ex : population)
        return ""
    # Hardcode a few common units abreviations
    elif unit_id == "Q42289":
        return "F"
    elif unit_id == "Q25267":
        return "C"
    elif unit_id == "Q11570":
        return "kg"
    elif unit_id == "Q828224":
        return "km"
    elif unit_id == "Q11573":
        return "m"
    elif unit_id == "Q174728":
        return "cm"
    elif unit_id == "Q174789":
        return "mm"
    elif unit_id == "Q25517":
        return "cubic m"
    else:
        # find the ItemLabel in wikidata_properties based on the ItemId
        quantity_label = wikidata_quantities_dict.get(unit_id)
        if quantity_label is not None:
            return quantity_label
            
        print(f"Unknown unit id: {unit_id}")
        return ""

def process_datavalue(datavalue):
    value_type = datavalue.get('type')
    value_obj = datavalue.get('value')

    actual_value = None

    if value_type is None or value_obj is None:
        print(f"Missing value type or value obj: {datavalue}")
    # Primitive types
    elif not isinstance(value_obj, dict):
        actual_value = value_obj
    # Relations to other entities
    elif value_type == 'wikibase-entityid':
        actual_value = value_obj['id']
    elif value_type == 'time':
        time_value = value_obj['time']
        # keep only the year if everything else is empty
        formatted_time = time_value.split("T")[0] if time_value.endswith("T00:00:00Z") else time_value
        formatted_time = formatted_time.replace("-00-00", "") # remove month and day if they are 0
        actual_value = formatted_time
    elif value_type == "quantity":
        amount = value_obj["amount"]
        unit_id = get_id_from_url(value_obj.get('unit', ""))
        unit_text = get_unit_value(unit_id)

        actual_value = amount + (" " + unit_text if unit_text else "")
    elif value_type == "globecoordinate":
        latitude = value_obj.get('latitude', "")
        longitude = value_obj.get('longitude', "")
        actual_value = f"{latitude}, {longitude}"
    # Often just called value
    elif value_obj.get("value") is not None:
        actual_value = value_obj['value']
    elif value_obj.get("text") is not None:
        actual_value = value_obj['text']
    else:
        print(f"Unknown value type: {datavalue}")
    
    return actual_value, value_type

def process_qualifier(qualifier_property):
    datavalue = qualifier_property.get('datavalue')
    value = None
    type = None

    if datavalue:
        value, type = process_datavalue(datavalue)

    return qualifier_property.get('property'), value, type

def process_property(main_property):
    main_value = None
    main_type = None

    if main_property.get('mainsnak'):
        datavalue = main_property['mainsnak'].get('datavalue')

        if datavalue:
            main_value, main_type = process_datavalue(datavalue)

    # qualifiers
    qualifiers = []

    if main_property.get('qualifiers'):
        for qualifier_property_id in main_property['qualifiers']:
            qualifier_property_instances = main_property['qualifiers'][qualifier_property_id]

            if len(qualifier_property_instances) > 1:
                print(f"Multiple qualifier instances for {qualifier_property_id}")

            for qualifier_property_instance in qualifier_property_instances:
                qualifier_id, qualifier_value, qualifier_type = process_qualifier(qualifier_property_instance)
                qualifiers.append({"id": qualifier_id, "label": None, "value": qualifier_value, "value_label": None, "type": qualifier_type})

    #formatted_qualifiers = ", ".join(formatted_qualifier_values) if len(formatted_qualifier_values) > 0 else ""
    return main_value, qualifiers, main_type

def format_entity_info(entity_info):
    claims = entity_info["claims"]

    properties = []
    properties_entity_ids = []

    for property_id in claims:
        root_property = claims[property_id]
        property_instances = []

        for orig_property_instance in root_property:
            main_value, qualifiers, main_type = process_property(orig_property_instance)
            new_property_instance = {"value": main_value, "value_label": None, "type": main_type}

            if main_type == "wikibase-entityid":
                properties_entity_ids.append(main_value)

            # Add quantifiers
            if len(qualifiers) > 0:
                new_property_instance["qualifiers"] = qualifiers

            for qualifier in qualifiers:
                if qualifier["type"] == "wikibase-entityid":
                    properties_entity_ids.append(qualifier["value"])

            # Add only the rank for the preferred option, or the deprecated rank (otherwise it's implied to be normal rank)
            if orig_property_instance.get("rank", "") == "preferred":
                new_property_instance["rank"] = 1
            elif orig_property_instance.get("rank", "") == "deprecated":
                new_property_instance["rank"] = -1

            property_instances.append(new_property_instance)

        properties.append({"id": property_id, "label": None, "instances": property_instances})

    entity_info["properties"] = properties
    del entity_info["claims"]

    link = entity_info["sitelinks"]
    del entity_info["sitelinks"]

    # Flatten labels (remove the 'en' level)
    entity_info['labels'] = entity_info['labels']['en']
    entity_info['label'] = entity_info['labels']['value'] # rename labels to label
    del entity_info['labels']

    # aliases
    if entity_info.get('aliases'):
        aliases = entity_info['aliases']['en']
        entity_info['aliases'] = [alias['value'] for alias in aliases]
    else:
        entity_info['aliases'] = []

    # descriptions
    if entity_info.get('descriptions'):
        entity_info['descriptions'] = entity_info['descriptions']['en']
        entity_info['description'] = entity_info['descriptions']['value'] # rename descriptions to description
    else:
        entity_info['description'] = ""
    del entity_info['descriptions']

    if link.get("enwiki") and link.get("enwiki").get("url"):
        entity_info["wiki_link"] = link["enwiki"]["url"] # rename enwiki to wiki_link
    else:
        entity_info["wiki_link"] = ""

    return entity_info, properties_entity_ids

# def update_entity_labels(entity_infos, property_id, property_label):
#     entity_info['labels'] = new_labels
#     entity_info['label'] = new_labels['value'] # rename labels to label
#     return entity_info

def format_entity_infos(entity_infos):
    all_properties_entity_ids = []

    # Load the wikidata quantity properties dictionary
    global wikidata_quantities_dict
    wikidata_properties_dir = "../wikidata_properties"
    with open(f"{wikidata_properties_dir}/quantities_dict.json", 'r', encoding='utf-8') as file:
        wikidata_quantities_dict = json.load(file)

    print(f"Formatting {len(entity_infos)} entities")

    # Format the info correctly + get all property entity ids
    for entity_info in entity_infos:
        entity_info, properties_entity_ids = format_entity_info(entity_info)
        all_properties_entity_ids += properties_entity_ids

    unique_properties_entity_ids = list(set(all_properties_entity_ids))

    print(f"{len(unique_properties_entity_ids)} entity properties to get label for. Loading cached labels...")

    # Load the cached entity labels
    cached_entity_labels_filename = "../utils/cached_entity_labels.json"
    cached_entity_labels_dict = {}

    if os.path.exists(cached_entity_labels_filename):
        with open(cached_entity_labels_filename, 'r', encoding='utf-8') as file:
            cached_entity_labels_dict = json.load(file)

    # Use cached entity labels if possible
    property_entities_to_update_dict = {}
    non_cached_unique_properties_entity_ids = list(unique_properties_entity_ids)

    for entity_id in unique_properties_entity_ids: # copy the list to avoid modifying it while iterating
        cached_label = cached_entity_labels_dict.get(entity_id)

        if cached_label is not None:
            property_entities_to_update_dict[entity_id] = cached_label
            non_cached_unique_properties_entity_ids.remove(entity_id)

    # Download the labels for every property's entity
    print(f"Downloading {len(non_cached_unique_properties_entity_ids)} properties")            
    properties_entity_infos = get_batched_entities_info(non_cached_unique_properties_entity_ids, "labels")

    print(f"Updating {len(entity_infos)} entities with {len(unique_properties_entity_ids)} property entities")

    # Put each label in a dictionary for easy access
    for property_entity_info in properties_entity_infos:
        if property_entity_info.get("labels") is not None:
            prop_id = property_entity_info['id']

            prop_label = ""
            if property_entity_info.get("labels") is not None and property_entity_info['labels'].get('en') is not None:
                prop_label = property_entity_info['labels']['en']['value']

            property_entities_to_update_dict[prop_id] = prop_label
            cached_entity_labels_dict[prop_id] = prop_label # cache the label

    # Save the cached entity labels
    with open(cached_entity_labels_filename, 'w', encoding='utf-8') as file:
        json.dump(cached_entity_labels_dict, file, ensure_ascii=False, indent=4)

    # Load the wikidata properties dictionary
    wikidata_properties_dict = {}
    with open(f"{wikidata_properties_dir}/properties_dict.json", 'r', encoding='utf-8') as file:
        wikidata_properties_dict = json.load(file)

    # Go through all the entity_infos properties and update the labels
    for entity_info in entity_infos:
        aliases = entity_info.get("aliases", [])
        properties = entity_info["properties"]

        # Move the aliases and properties to the end of the dictionary
        del entity_info["aliases"]
        del entity_info["properties"]
        entity_info["aliases"] = aliases
        entity_info["properties"] = properties

        # Update the labels for each property
        for property in entity_info["properties"]:
            property_id = property["id"]
            
            # Set property label
            existing_property = wikidata_properties_dict.get(property_id)
            property["label"] = existing_property["label"] if existing_property is not None else ""

            if existing_property is None:
                print(f"Missing property: {property_id}")

            property_instances = property["instances"]

            for property_instance in property_instances:
                # Set value entity label for the property
                if property_instance["type"] == "wikibase-entityid":
                    property_value_label = property_entities_to_update_dict.get(property_instance["value"])
                    property_instance["value_label"] = property_value_label
                else:
                    del property_instance["value_label"]

                # Same as above, but for qualifiers
                qualifiers = property_instance.get("qualifiers", [])
                for qualifier in qualifiers:
                    qualifier_id = qualifier["id"]
                    # Set qualifier label
                    qualifier["label"] = wikidata_properties_dict[qualifier_id]["label"]

                    if qualifier["type"] == "wikibase-entityid":
                        qualifier["value_label"] = property_entities_to_update_dict.get(qualifier["value"])
                    else:
                        del qualifier["value_label"]

    return entity_infos

# Clean numbers so they are in the same format as wikidata's query output (no commas, no spaces)
def clean_number(text):
    clean_number = ""

    pattern = r"^\D*([\d,.\s]+)"
    match = re.search(pattern, text)

    if match:
        number_at_start = match.group(1)
        clean_number = number_at_start.replace(",", "").replace(" ", "")

    return clean_number

def is_date(text):
    try:
        datetime.strptime(text, '%Y-%m-%d')
        return True 
    except Exception as e:
        return False 
    
def format_date_iso_format(text):
    try:
        parsed_date = parse(text)
        formatted_date = parsed_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        return formatted_date
    except Exception as e:
        return text
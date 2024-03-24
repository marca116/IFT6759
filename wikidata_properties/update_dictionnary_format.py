import json

wikidata_quantities = []
with open("quantities.json", 'r', encoding='utf-8') as file:
	wikidata_quantities = json.load(file)
	
wikidata_quantities_dict = {}
for quantity in wikidata_quantities:
    wikidata_quantities_dict[quantity['id']] = quantity['label']

with open("quantities_dict.json", 'w', encoding='utf-8') as file:
    json.dump(wikidata_quantities_dict, file, ensure_ascii=False, indent=4)

wikidata_properties = []
with open("properties.json", 'r', encoding='utf-8') as file:
	wikidata_properties = json.load(file)
	
wikidata_properties_dict = {}
for property in wikidata_properties:
    wikidata_properties_dict[property['id']] = {"label": property['label'], "description": property['description']}

with open("properties_dict.json", 'w', encoding='utf-8') as file:
    json.dump(wikidata_properties_dict, file, ensure_ascii=False, indent=4)
import json

with open('train_plus_valid_new_hf_dataset.json', 'r', encoding='utf-8') as file:
    train_plus_valid = json.load(file)

# Create a mapping from uid for quick lookup
simplified_query_map = {item['uid']: item['simplified_query'] for item in train_plus_valid}

with open('train.json', 'r', encoding='utf-8') as file:
    train_data = json.load(file)

failed_items = []
for item in train_data:
    uid = item['uid']
    if uid in simplified_query_map:
        item['simplified_query'] = simplified_query_map[uid]
    else:
        failed_items.append(uid)
        print(f"Failed to find simplified query for uid {uid}")

print(f"Failed to find simplified queries for {len(failed_items)} uids.")

# Remove the simplified queries that failed to be added
train_data = [item for item in train_data if item['uid'] not in failed_items]

with open('train_with_simplified_query.json', 'w', encoding='utf-8') as file:
    json.dump(train_data, file, indent=4)

print("Simplified queries have been added successfully.")
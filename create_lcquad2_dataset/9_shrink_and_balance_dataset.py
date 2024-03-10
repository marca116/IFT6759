import json
from collections import defaultdict

randomize_data = True

input_file_train_original = 'train.json'
input_file_lcquad2_final = 'train_lcquad2_final_full.json'

output_file_shrunk_final = 'train_lcquad2_final_1k.json'

with open(input_file_train_original) as file:
    train_data = json.load(file)

with open(input_file_lcquad2_final) as file:
    lcquad_data = json.load(file)

# Convert template_id to string
for item in train_data:
    item['template_id'] = str(item['template_id'])
for item in lcquad_data:
    item['template_id'] = str(item['template_id'])

# Separate questions by template ID
def separate_by_template(data):
    grouped_data = defaultdict(list)
    for item in data:
        template_id = item['template_id']
        grouped_data[template_id].append(item)
    return grouped_data

train_grouped = separate_by_template(train_data)
lcquad_grouped = separate_by_template(lcquad_data)

# Create tempalte ID ratios
def calculate_ratios(grouped_data):
    total = sum(len(items) for items in grouped_data.values())
    ratios = {template_id: len(items)/total for template_id, items in grouped_data.items()}
    return dict(sorted(ratios.items()))  # Sort

train_ratios = calculate_ratios(train_grouped)
lcquad_ratios = calculate_ratios(lcquad_grouped)

# Print the template ratios
def print_ratios(ratios, dataset_name):
    print(f"Template Ratios in {dataset_name}:")
    for template_id, ratio in ratios.items():
        print(f"Template ID: {template_id}, Ratio: {ratio:.4f}")

print("Train Ratios:")
print_ratios(train_ratios, 'train.json')

print("\nLC-QuAD Ratios:")
print_ratios(lcquad_ratios, 'lcquad_final.json')

print("\nShrink Dataset:")

# Create a shrinking function
def shrink_dataset(target_size, template_ratios, data_grouped):
    shrunk_data = []
    for template_id, ratio in template_ratios.items():
        num_items = int(target_size * ratio)
        if num_items < 1 and ratio > 0:
            num_items = 1

        # If dataset size would be > target size, shrink the number of items
        if len(shrunk_data) + num_items > target_size:
            num_items = target_size - len(shrunk_data)

        print(f"Template ID: {template_id}, Target: {num_items}, Actual: {len(data_grouped[template_id])}")

        shrunk_data.extend(data_grouped[template_id][:num_items])

    return shrunk_data

# Shrink lcquad_final.json
final_target_size = 1400 
remaining_target_size = final_target_size

shrunk_lcquad = []
x = 0

while len(shrunk_lcquad) < final_target_size:
    print(f"Loop number: {x+1}, Current size: {len(shrunk_lcquad)}")

    temp_shrunk_lcquad = shrink_dataset(remaining_target_size, train_ratios, lcquad_grouped)
    shrunk_lcquad += temp_shrunk_lcquad

    # Remove data from lcquad_grouped that was added to final_shrunk_lcquad
    for item in temp_shrunk_lcquad:
        lcquad_grouped[item['template_id']].remove(item)

    remaining_target_size -= len(temp_shrunk_lcquad)
    x += 1
        
print(f"Final size: {len(shrunk_lcquad)}")

# Compare the ratios of the shrunk dataset vs the original dataset
shrunk_lcquad_grouped = separate_by_template(shrunk_lcquad)
shrunk_lcquad_ratios = calculate_ratios(shrunk_lcquad_grouped)

print("\nShrunk LC-QuAD Ratios:")
print_ratios(shrunk_lcquad_ratios, 'shrunk_lcquad')

def print_compare_ratios(shrunk_ratios, train_ratios, lcquad_ratios, dataset_name):
    print(f"\nTemplate Ratios in {dataset_name} (New Ratio, Original_ratio, Original_lcquad2_cleaned_ratio):")
    for template_id, ratio in shrunk_ratios.items():
        original_ratio = train_ratios.get(template_id, 'N/A')
        lcquad_ratio = lcquad_ratios.get(template_id, 'N/A')
        print(f"Template ID: {template_id}, N:{ratio:.4f} --- O:{original_ratio:.4f} --- L:{lcquad_ratio:.4f}")

print_compare_ratios(shrunk_lcquad_ratios, train_ratios, lcquad_ratios, 'shrunk_lcquad')

# Save the shrunk dataset to a new file
with open(output_file_shrunk_final, 'w') as f:
    json.dump(shrunk_lcquad, f, indent=4)
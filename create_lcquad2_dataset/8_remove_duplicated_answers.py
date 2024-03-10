import json

with open('train_lcquad2_with_solved_answers.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

answer_entities_labels = []
processed_question_nb = 0

for question in data:
    answer_obj = question['answer']
    solved_answer_obj = question['solved_answer']

    answers = []
    solved_answers = []

    # Create a list of lists, with each list containing the indexes of all of the same duplicated answers
    for i, solved_answer in enumerate(solved_answer_obj):
        if solved_answer not in solved_answers:
            solved_answers.append(solved_answer)
            answer = answer_obj[i]
            answers.append(answer)

    question['answer'] = answers
    question['solved_answer'] = solved_answers

    processed_question_nb += 1
    if processed_question_nb % 100 == 0:
        print(f"Processed {processed_question_nb}/{len(data)} questions")
    
# Save to train_final_all_with_solved_answers.json
with open('train_lcquad2_final.json', 'w', encoding='utf-8') as outfile:
    json.dump(data, outfile, indent=4)
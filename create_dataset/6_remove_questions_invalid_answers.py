import json

with open('train_cleaned_with_answers.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

questions_with_no_answers = []
questions_with_too_many_answers = []
questions_with_answers = []

for question in data:
    if question['answer'] is None or len(question['answer']) == 0:
        print(f"Failed to find answer for {question['uid']}: {question['question']}")
        questions_with_no_answers.append(question)
    # No question should have more than 25 answers
    elif len(question['answer']) > 25:
        print(f"Too many answers for {question['uid']}: {question['question']}")
        questions_with_too_many_answers.append(question)
    else:
        questions_with_answers.append(question)

print(f"Questions with no answers: {len(questions_with_no_answers)}")
print(f"Questions with too many answers: {len(questions_with_too_many_answers)}")
print(f"Questions with valid answers: {len(questions_with_answers)}")

# Save the questions with answers
with open('train_cleaned_only_questions_with_answers.json', 'w', encoding='utf-8') as outfile:
    json.dump(questions_with_answers, outfile, indent=4)

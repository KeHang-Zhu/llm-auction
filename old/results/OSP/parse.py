import json
import csv
import re

def extract_value(text):
    match = re.search(r"Your value towards to the money prize is (\d+) now\.", text)
    if match:
        return int(match.group(1))
    return None



def parse_multiple_jsonl_to_csv(input_files, output_file):
    data = []
    
    for input_file in input_files:
        with open(input_file, 'r') as f:
            for line in f:
                json_obj = json.loads(line)
                for key, value in json_obj.items():
                    system_prompt = value['system_prompt']
                    user_prompt = value['user_prompt']
                    output = json.loads(value['output'])
                    content = json.loads(output['choices'][0]['message']['content'])
                    answer = content['answer']
                    comment = content['comment']
                    
                    value_info = extract_value(user_prompt)
                    
                    data.append({
                        'system_prompt': system_prompt,
                        'user_prompt': user_prompt,
                        'answer': answer,
                        'comment': comment,
                        'value': value_info
                    })
    
    # Write to CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['system_prompt', 'user_prompt', 'answer', 'comment','value'])
        writer.writeheader()
        writer.writerows(data)

# Usage
input_files = [
    "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-23_19-53-29.jsonl",
    "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-23_19-56-40.jsonl",
    "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-23_19-59-12.jsonl",
    "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-23_20-01-41.jsonl",
    "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-23_20-04-53.jsonl"
]
output_file = 'output_SP.csv'  # Replace with your desired output file name

parse_multiple_jsonl_to_csv(input_files, output_file)
print(f"Data has been successfully parsed and saved to {output_file}")


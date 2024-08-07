import json
import csv
import re
import os

def parse_string(text):
    answer_match = re.search(r'"answer":\s*(\d+)', text)
    answer = int(answer_match.group(1)) if answer_match else None

    # Find the comment content
    comment_match = re.search(r'"comment":\s*"(.*?)"', text)
    comment = comment_match.group(1) if comment_match else None

    # 3. Get the bidder name
    bidder_match = re.search(r'You are (Bidder \d+)', text)
    bidder = bidder_match.group(1) if bidder_match else None

    # 4. Get the value of the money prize
    value_match = re.search(r'Your value towards to the money prize is (\d+) now', text)
    value = int(value_match.group(1)) if value_match else None

    # 5. Get the current price
    price_match = re.search(r'The current price is (\d+)', text)
    price = int(price_match.group(1)) if price_match else None

    return {
        'answer': answer,
        'comment': comment,
        'bidder': bidder,
        'value': value,
        'price': price
    }
    

def process_file(input_file, output_file):
    with open(input_file, 'r') as f:
        strings = f.readlines()

    results = []
    for string in strings:

        result = parse_string(f'''{string}''')
        results.append(result)

    with open(output_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['answer', 'comment', 'bidder', 'value', 'price'])
        writer.writeheader()
        for result in results:
            writer.writerow(result)

# Example usage
input_files = [
    "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_open/raw_output__2024-05-22_18-15-59.txt",
"/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_open/raw_output__2024-05-22_19-19-57.txt"
]
output_file = 'output_results.csv'
for input_file in input_files:
    process_file(input_file, output_file)


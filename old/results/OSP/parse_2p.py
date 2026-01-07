# file_paths_2p = [
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-31-47.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-33-21.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-34-48.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-36-14.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-37-37.json"]

# jsonl_path_2p = [
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/raw_output_2024-05-27_13-31-47.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/raw_output_2024-05-27_13-33-21.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/raw_output_2024-05-27_13-34-48.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/raw_output_2024-05-27_13-36-14.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/raw_output_2024-05-27_13-37-37.json"]

# import json
# import csv
# import os

# def extract_output(jsonl_path):
#     outputs = []
#     with open(jsonl_path, 'r') as file:
#         for line in file:
#             data = json.loads(line)
#             # Get the first (and only) key from the outer dictionary
#             outer_key = next(iter(data))
            
#             # Extract relevant information
#             output_data = json.loads(data[outer_key]['output'])
#             content = output_data['choices'][0]['message']['content']
#             inner_data = json.loads(content)
            
#             # Extract answer and comment
#             answer = inner_data['answer']
#             comment = inner_data['comment']
            
#             # Extract bidder information from user_prompt
#             user_prompt = data[outer_key]['user_prompt']
#             bidder_info = [line.strip() for line in user_prompt.split('\n') if line.strip().startswith('You are Bidder')]
#             bidder = bidder_info[0] if bidder_info else 'Unknown Bidder'
            
#             # Extract value information
#             value_info = [line.strip() for line in user_prompt.split('\n') if 'Your value towards to the money prize is' in line]
#             value = value_info[0].split('is')[-1].strip() if value_info else 'Unknown Value'
            
#             outputs.append({
#                 'Bidder': bidder,
#                 'Value': value,
#                 'Bid': answer,
#                 'Comment': comment
#             })
    
#     return outputs

# def save_to_csv(data, csv_path):
#     keys = data[0].keys()
#     with open(csv_path, 'w', newline='') as output_file:
#         dict_writer = csv.DictWriter(output_file, keys)
#         dict_writer.writeheader()
#         dict_writer.writerows(data)

# # File paths
# jsonl_path = '/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-27_13-54-26.jsonl'
# csv_path = '/Users/wonderland/Desktop/auction/llm-auction/results/OSP/output_summary.csv'

# # Ensure the directory for the CSV file exists
# os.makedirs(os.path.dirname(csv_path), exist_ok=True)

# # Extract data and save to CSV
# outputs = extract_output(jsonl_path)
# save_to_csv(outputs, csv_path)

# print(f"Data has been extracted and saved to {csv_path}")





# import json
# import csv
# import os

# def read_jsonl(file_path):
#     data = []
#     with open(file_path, 'r') as file:
#         for line in file:
#             entry = json.loads(line)
#             key = next(iter(entry))
#             output = json.loads(entry[key]['output'])
#             content = json.loads(output['choices'][0]['message']['content'])
            
#             # Extract bidder information
#             user_prompt_lines = entry[key]['user_prompt'].split('\n')
#             bidder_line = next((line for line in user_prompt_lines if line.strip().startswith('You are Bidder')), None)
#             bidder = bidder_line.strip().split()[-1] if bidder_line else 'Unknown'
            
#             data.append({
#                 'bidder': bidder,  # This will now be in the format '0.', '1.', etc.
#                 'bid': int(content['answer']),
#                 'reason': content['comment']
#             })
#     return data

# def process_data(json_data, jsonl_data):
#     combined_data = []
#     for round_key, round_data in json_data.items():
#         if round_key.startswith('round_'):
#             round_number = int(round_key.split('_')[1])
#             for i, (value, bid_info) in enumerate(zip(round_data['value'], round_data['history']['bidding history'])):
#                 bidder = f"Bidder {i}"
#                 bid_value = int(bid_info['bid'])
                
#                 # Find the matching entry in jsonl_data
#                 matching_entry = next((item for item in jsonl_data 
#                                        if item['bidder'].rstrip('.') == str(i)
#                                        and item['bid'] == bid_value), None)
                
#                 reason = matching_entry['reason'] if matching_entry else "No reason found"
                
#                 combined_data.append({
#                     'Round': round_number,
#                     'Bidder': bidder,
#                     'Value': value,
#                     'Bid': bid_value,
#                     'Overbid': bid_value > value,
#                     'Underbid': bid_value < value,
#                     'Type': 'Second',
#                     'Reason': reason
#                 })
#     return combined_data

# def save_to_csv(data, csv_path):
#     fieldnames = ['Round', 'Bidder', 'Value', 'Bid', 'Overbid', 'Underbid', 'Type', 'Reason']
#     with open(csv_path, 'w', newline='') as file:
#         writer = csv.DictWriter(file, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(data)

# # File paths
# json_path = '/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/result_10_2024-05-27_13-54-26.json'
# jsonl_path = '/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-27_13-54-26.jsonl'
# csv_path = '/Users/wonderland/Desktop/auction/llm-auction/results/OSPcombined_output.csv'

# # Ensure the directory for the CSV file exists
# os.makedirs(os.path.dirname(csv_path), exist_ok=True)

# # Read and process data
# with open(json_path, 'r') as file:
#     json_data = json.load(file)
# jsonl_data = read_jsonl(jsonl_path)
# combined_data = process_data(json_data, jsonl_data)


# print(f"Number of entries in combined_data: {len(combined_data)}")
# print("Sample entry:")
# print(combined_data[0])

# save_to_csv(combined_data, csv_path)

# print(f"Combined data has been saved to {csv_path}")
import json
import csv
import os

def read_jsonl(file_path):
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            entry = json.loads(line)
            key = next(iter(entry))
            output = json.loads(entry[key]['output'])
            content = json.loads(output['choices'][0]['message']['content'])
            
            # Extract bidder information
            user_prompt_lines = entry[key]['user_prompt'].split('\n')
            bidder_line = next((line for line in user_prompt_lines if line.strip().startswith('You are Bidder')), None)
            bidder = bidder_line.strip().split()[-1] if bidder_line else 'Unknown'
            
            data.append({
                'bidder': bidder,  # This will be in the format '0.', '1.', etc.
                'bid': int(content['answer']),
                'reason': content['comment']
            })
    return data

def process_data(json_data, jsonl_data):
    combined_data = []
    for round_key, round_data in json_data.items():
        if round_key.startswith('round_'):
            round_number = int(round_key.split('_')[1])
            for i, (value, bid_info) in enumerate(zip(round_data['value'], round_data['history']['bidding history'])):
                bidder = f"Bidder {i}"
                bid_value = int(bid_info['bid'])
                
                # Find the matching entry in jsonl_data
                matching_entry = next((item for item in jsonl_data 
                                       if item['bidder'].rstrip('.') == str(i)
                                       and item['bid'] == bid_value), None)
                
                reason = matching_entry['reason'] if matching_entry else "No reason found"
                
                combined_data.append({
                    'Round': round_number,
                    'Bidder': bidder,
                    'Value': value,
                    'Bid': bid_value,
                    'Overbid': bid_value > value,
                    'Underbid': bid_value < value,
                    'Type': 'Second',
                    'Reason': reason
                })
    return combined_data

def save_to_csv(data, csv_path):
    fieldnames = ['Round', 'Bidder', 'Value', 'Bid', 'Overbid', 'Underbid', 'Type', 'Reason']
    with open(csv_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# File paths
file_paths_2p = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-31-47.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-33-21.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-34-48.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-36-14.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-37-37.json"
]

jsonl_path_2p = "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/raw_output__2024-05-27_13-37-37.jsonl"

# Read JSONL data
jsonl_data = read_jsonl(jsonl_path_2p)

# Process each JSON file and combine with JSONL data
all_combined_data = []
for json_path in file_paths_2p:
    with open(json_path, 'r') as file:
        json_data = json.load(file)
    
    combined_data = process_data(json_data, jsonl_data)
    all_combined_data.extend(combined_data)

# Save all combined data to CSV
csv_path = '/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/combined_output.csv'
os.makedirs(os.path.dirname(csv_path), exist_ok=True)
save_to_csv(all_combined_data, csv_path)

print(f"Combined data from all files has been saved to {csv_path}")
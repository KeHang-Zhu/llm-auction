import json
import numpy as np
import matplotlib.pyplot as plt

def calculate_value_for_file(path_folders):
    bids = []
    values = []
    
    for file_path in path_folders:
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        value = data['round_0']['value']
        # Extract bids
        bid = [int(bid['bid']) for bid in data['round_0']['history']['bidding history']] 
        values.extend(value) 
        bids.extend(bid) 

    return bids, values

path_folders = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-36-20.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-36-34.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-36-47.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-37-00.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-37-13.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-37-22.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-37-29.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-37-39.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-37-52.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_private_close/result_1_2024-05-28_15-38-03.json"
]
path_folders2 = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-38-31.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-38-41.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-38-51.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-01.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-11.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-19.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-26.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-36.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-45.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_first_private_close/result_1_2024-05-28_15-39-57.json"
]

bids, values = calculate_value_for_file(path_folders=path_folders)

bids2, values2 = calculate_value_for_file(path_folders=path_folders2)

# Plot the extracted values and bids
plt.plot(values, bids, marker='o', linestyle='', color='blue', label='LLM SPSB')

print(values, bids)

plt.plot(values, bids, marker='.', linestyle='', color='red', label='LLM SPSB')

# Plot the theoretical prediction where values = bids
max_value = max(max(values), max(bids))
plt.plot([0, max_value], [0, max_value], linestyle='--', color='black', label='Theory SPSB')

max_value = max(max(values), max(bids))
max_bid = 2/3*max_value
plt.plot([0, max_value], [0, max_bid], linestyle='-', color='black', label='Theory FPSB')

plt.xlabel('Values')
plt.ylabel('Bids')
# plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()



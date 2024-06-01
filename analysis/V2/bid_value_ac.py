import json
import numpy as np
import matplotlib.pyplot as plt

name_to_letter = {
    "Andy": 'A',
    "Betty": 'B',
    "Charles": 'C'
}

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
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-06-05.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-07-40.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-09-13.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-10-52.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-12-22.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-13-51.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-15-22.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-16-54.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-18-30.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-31_00-30-51.json"
]


bids, values = calculate_value_for_file(path_folders=path_folders)

values2 = [26, 23, 26, 19, 15, 13, 27, 17, 16, 19, 25, 28, 27, 16, 23, 32, 39, 35, 35, 21]
bids2 = [26, 23, 27, 19, 16, 13, 27, 18, 16, 20, 26, 29, 27, 17, 23, 32, 40, 35, 35, 22]


# Plot the extracted values and bids
plt.plot(values, bids, marker='o', linestyle='', color='blue', label='LLM 2P')
plt.plot(values2, bids2, marker='.', linestyle='', color='red', label='LLM AC')

# Plot the theoretical prediction where values = bids
max_value = max(max(values), max(bids))
plt.plot([0, max_value], [0, max_value], linestyle='--', color='black', label='Theory')

plt.xlabel('Values')
plt.ylabel('Bids')
# plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()

    
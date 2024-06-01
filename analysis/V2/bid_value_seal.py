import json
import numpy as np
import matplotlib.pyplot as plt

def calculate_value_for_file(path_folders):
    bids = []
    values = []
    
    for file_path in path_folders:
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        value = data['round_9']['value']
        # Extract bids
        bid = [int(bid['bid']) for bid in data['round_9']['history']['bidding history']] 
        values.extend(value) 
        bids.extend(bid) 

    return bids, values


# path_folders_1P = [
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-29-42.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-29-52.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-01.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-11.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-21.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-29.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-38.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-44.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-30-54.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-31-03.json"
# ]
# path_folders_2P = [
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-32-12.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-32-22.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-32-32.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-32-42.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-32-51.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-33-01.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-33-09.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-33-14.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-33-23.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-33-32.json"
# ]
path_folders_1P = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-43-58.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-44-18.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-44-35.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-44-51.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-45-11.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-45-32.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-45-48.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-45-53.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-46-06.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_1_2024-05-30_21-46-21.json"
]

path_folders_2P = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-40-59.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-41-18.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-41-35.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-41-51.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-42-07.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-42-23.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-42-38.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-42-44.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-42-58.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_1_2024-05-30_21-43-15.json"
]


path_folders_1P= [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-28-26.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-35-08.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-36-49.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-38-32.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-40-15.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-41-55.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-43-37.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-45-14.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-46-58.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-48-35.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__first_private_close/result_10_2024-05-30_23-50-11.json"
]

path_folders_2P = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-34-06.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-35-56.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-37-34.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-39-13.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-40-56.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-42-40.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-44-21.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-45-59.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-47-37.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-49-18.json"
]
        

bids_1p, values_1p = calculate_value_for_file(path_folders=path_folders_1P)

bids_2p, values_2p = calculate_value_for_file(path_folders=path_folders_2P)

# Plot the extracted values and bids
plt.plot(values_1p, bids_1p, marker='o', linestyle='', color='blue', label='LLM FPSB')

# print(values, bids)

plt.plot(values_2p, bids_2p, marker='.', linestyle='', color='red', label='LLM SPSB')

# Plot the theoretical prediction where values = bids
max_value = max(max(values_2p), max(bids_2p))
plt.plot([0, max_value], [0, max_value], linestyle='--', color='black', label='Theory SPSB')

max_value = max(max(values_1p), max(bids_1p))
max_bid = 2/3*max_value
plt.plot([0, max_value], [0, max_bid], linestyle='-', color='black', label='Theory FPSB')

plt.xlabel('Values')
plt.ylabel('Bids')
plt.title('Comparison between First Price and Second Price Seal Bid Auction')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()



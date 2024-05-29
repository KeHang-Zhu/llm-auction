import json
import numpy as np
import matplotlib.pyplot as plt

def calculate_value_for_file(path_folders):
    all_bids = []
    all_values = []
    
    for file_path in path_folders:
        with open(file_path, 'r') as file:
            data = json.load(file)
            
        values = data['round_0']['value']
        bids_2 = np.zeros_like(values)
        # Extract bids
        bid = [int(bid['bid']) for bid in data['round_0']['history']['bidding history']]
        
        for bid in data['round_0']['history']['bidding history']:
            bidder_index = ord(bid['agent'].split()[-1]) - ord('A')
            bids_2[bidder_index] = int(bid['bid'])
        winner_bidder =data['round_0']['history']['winner']['winner']
        winner_index =  ord(winner_bidder.split()[-1]) - ord('A')
        
        # Remove the winner's bid and corresponding value
        values = np.delete(values, winner_index)
        bids_2 = np.delete(bids_2, winner_index)
        
        # Convert to lists before extending
        values = values.tolist()
        bids_2 = bids_2.tolist()
        
        all_values.extend(values)
        all_bids.extend(bids_2)

    return all_bids, all_values



path_folders = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-19-51.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-21-37.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-24-50.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-27-41.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-28-24.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-28-57.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-29-50.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-33-59.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-35-49.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/clock_ascend_first_private_open/result_1_2024-05-28_16-36-16.json"
]

bids, values = calculate_value_for_file(path_folders=path_folders)

values2 = [16, 12, 6, 4, 28, 30, 12, 23, 22, 2, 4, 10, 2, 10, 3, 6, 10, 6, 30, 25, 27, 3, 15, 12, 0, 3, 18, 22, 6, 28] 
bids2 = [15, 11, 5, 3, 27, 29, 11, 22, 21, 1, 3, 9, 1, 9, 2, 5, 9, 5, 29, 24, 26, 2, 14, 11, 0, 2, 17, 21, 5, 27]
# Plot the extracted values and bids
plt.plot(values, bids, marker='o', linestyle='', color='blue', label='LLM AC')
plt.plot(values2, bids2, marker='.', linestyle='', color='red', label='LLM 2P')

# Plot the theoretical prediction where values = bids
max_value = max(max(values2), max(bids2))
plt.plot([0, max_value], [0, max_value], linestyle='--', color='black', label='Theory')

plt.xlabel('Values')
plt.ylabel('Bids')
# plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()

    
import json
import numpy as np
import matplotlib.pyplot as plt

# Load the JSON file
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_11-26-44.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/clock_ascend_second_common_open/result_10_2024-05-22_18-15-59.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/clock_ascend_second_common_open/result_10_2024-05-22_19-19-57.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/clock_ascend_second_common_blind/result_10_2024-05-22_22-10-31.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/clock_ascend_second_common_blind/result_10_2024-05-22_22-28-27.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/clock_ascend_second_common_blind/result_10_2024-05-22_22-51-42.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/clock_ascend_second_common_blind/result_10_2024-05-22_23-34-41.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/clock_ascend_second_common_blind/result_10_2024-05-22_23-56-20.json"
# file_path= "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_12-55-50.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/clock_ascend_second_common_open/result_10_2024-05-27_14-51-06.json"

with open(file_path, 'r') as file:
    data = json.load(file)

rounds = []
mad_values = []

for i in range(10):
    round_key = f"round_{i}"
    round_data = data[round_key]
    values = np.array(round_data['value'])
    
    # Initialize an array to hold bids in the correct order
    bids = np.zeros_like(values)
    
    # Map each bid to the corresponding bidder
    for bid in round_data['history']['bidding history']:
        bidder_index = int(bid['agent'].split()[-1])
        bids[bidder_index] = int(bid['bid'])
    
    winner_bidder = round_data['history']['winner']['winner']
    
    if winner_bidder == 'NA':
        mad = np.mean(np.abs(bids - values))
    else:
        winner_index = int(winner_bidder.split()[-1])
        
        # Remove the winner's bid and corresponding value
        values = np.delete(values, winner_index)
        bids = np.delete(bids, winner_index)
        
        mad = np.mean(np.abs(bids - values))
    
    rounds.append(i)
    mad_values.append(mad)
    print([mad_values])
    

# Plot Mean Absolute Deviation of Bids from Values vs Round
plt.plot(rounds, mad_values, marker='o', linestyle='-', color='blue')
plt.xlabel('Round')
plt.ylabel('Mean Absolute Deviation')
plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.grid(True)
plt.show()

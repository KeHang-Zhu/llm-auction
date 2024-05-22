import json
import numpy as np
import matplotlib.pyplot as plt

# Load the JSON file
file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_11-26-44.json"
with open(file_path, 'r') as file:
    data = json.load(file)

rounds = []
mad_values = []

# Iterate over each round to calculate MAD
for i in range(10):
    round_key = f"round_{i}"
    round_data = data[round_key]
    values = np.array(round_data['value'])
    bids = np.array([int(bid['bid']) for bid in round_data['history']['bidding history']])
    mad = np.mean(np.abs(bids - values))
    
    rounds.append(i)
    mad_values.append(mad)

# Plot Mean Absolute Deviation of Bids from Values vs Round
plt.plot(rounds, mad_values, marker='o', linestyle='-', color='blue')
plt.xlabel('Round')
plt.ylabel('Mean Absolute Deviation')
plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.grid(True)
plt.show()

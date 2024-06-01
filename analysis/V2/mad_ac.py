import json
import numpy as np
import matplotlib.pyplot as plt

file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/clock_ascend__private_open/result_10_2024-05-30_23-47-48.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/clock_ascend__private_blind/result_10_2024-05-31_00-03-53.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/clock_ascend__private_open/result_10_2024-05-30_23-47-48.json"

all_v=[]
all_b=[]
name_to_letter = {
    "Andy": 'A',
    "Betty": 'B',
    "Charles": 'C'
}

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
        bidder_name = bid['agent'].split()[-1]
        bidder_letter = name_to_letter[bidder_name]
        bidder_index = ord(bidder_letter) - ord('A')
        bids[bidder_index] = int(bid['bid'])
    
    winner_bidder = round_data['history']['winner']['winner'].replace("Bidder ", "")
    winner_letter = name_to_letter[winner_bidder]
    winner_index = ord(winner_letter) - ord('A')
    
    # Remove the winner's bid and corresponding value
    values = np.delete(values, winner_index)
    bids = np.delete(bids, winner_index)
    
    all_v.extend(values)
    all_b.extend(bids)
    
    mad = np.mean(np.abs(bids - values))
    
    rounds.append(i)
    mad_values.append(mad)
    print([mad_values])
    
print(all_v)
print(all_b)
# Plot Mean Absolute Deviation of Bids from Values vs Round
plt.plot(rounds, mad_values, marker='o', linestyle='-', color='blue')
plt.xlabel('Round')
plt.ylabel('Mean Absolute Deviation')
plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.grid(True)
plt.show()

import pandas as pd
import matplotlib.pyplot as plt
import json

file_path ="/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V4/seal__first_private_close/result_15_2024-06-01_12-47-20.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V4/seal__second_common_close/result_15_2024-06-01_12-39-14.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V4/seal__first_private_close/result_15_2024-06-01_12-47-20.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V4/seal__first_private_close/result_15_2024-05-31_14-57-25.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V4/seal__first_private_close/result_15_2024-05-31_14-16-30.json"
with open(file_path, 'r') as file:
    data = json.load(file)


rounds = range(15)
bidders = ["Bidder Andy", "Bidder Betty", "Bidder Charles"]
values = {bidder: [] for bidder in bidders}
bids = {bidder: [] for bidder in bidders}
deviations = {bidder: [] for bidder in bidders}

for rnd in data.values():
    for bid in rnd["history"]["bidding history"]:
        bids[bid["agent"]].append(int(bid["bid"]))
    for i, val in enumerate(rnd["value"]):
        values[bidders[i]].append(val)
        deviations[bidders[i]].append(val - int(rnd["history"]["bidding history"][i]["bid"]))

fig, ax = plt.subplots(figsize=(12, 6))
for bidder in bidders:
    ax.plot(rounds, deviations[bidder], marker='o', label=bidder)

ax.set_xlabel("Rounds")
ax.set_ylabel("Deviation (Value - Bid)")
ax.set_title("Deviation of Each Bidder's Value and Bid Over Rounds")
ax.legend()
plt.grid(True)
plt.show()

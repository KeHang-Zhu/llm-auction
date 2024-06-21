import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_17-29-04.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_17-17-00.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_17-04-17.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_16-51-17.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_16-38-01.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_16-19-29.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_23-35-47.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_23-18-08.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_23-09-21.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_22-57-04.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_21-31-30.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_11-01-32.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_10-28-51.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_10-24-14.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_21-58-35.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_09-43-55.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-17_09-52-03.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_21-39-01.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_25_2024-06-16_23-05-44.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_25_2024-06-16_22-54-57.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_21-58-35.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_21-39-01.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_21-39-19.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_21-32-45.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_20-10-09.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_19-28-28.json"
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-16_17-49-05.json"

with open(file_path, 'r') as file:
    data = json.load(file)


rounds = range(15)
bidders = ["Bidder Andy", "Bidder Betty", "Bidder Charles"]
values = {bidder: [] for bidder in bidders}
bids = {bidder: [] for bidder in bidders}
deviations = {bidder: [] for bidder in bidders}
round_averages = []

for rnd in data.values():
    round_devs = []
    for bid in rnd["history"]["bidding history"]:
        bids[bid["agent"]].append(float(bid["bid"]))
    for i, val in enumerate(rnd["value"]):
        values[bidders[i]].append(val)
        deviations[bidders[i]].append((float(rnd["history"]["bidding history"][i]["bid"])- val))
        deviation = abs((float(rnd["history"]["bidding history"][i]["bid"]) - val))
        round_devs.append(abs(deviation))
    round_averages.append(np.mean(round_devs))

fig, ax = plt.subplots(figsize=(12, 6))
for bidder in bidders:
    ax.plot(rounds, deviations[bidder], marker='o', label=bidder)

ax.plot(rounds, round_averages, marker='.', label="Average")

ax.set_xlabel("Rounds")
ax.set_ylabel("Deviation Ratio(Bid-Value)/Value")
ax.set_title("Deviation of Each Bidder's Value and Bid Over Rounds")
ax.legend()
plt.grid(True)
plt.show()

import json
import numpy as np
import matplotlib.pyplot as plt
import glob
from statsmodels.nonparametric.smoothers_lowess import lowess

file_paths = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-980826.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982049.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982140.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982255.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982367.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-983239.json"]

bidders = ["Bidder Andy", "Bidder Betty", "Bidder Charles"]
values = {bidder: [] for bidder in bidders}
bids = {bidder: [] for bidder in bidders}
deviations = {bidder: [[] for _ in range(15)] for bidder in bidders}
round_averages = [[] for _ in range(15)]

for file_path in file_paths:
    with open(file_path, 'r') as file:
        data = json.load(file)

    for rnd_idx, rnd in enumerate(data.values()):
        if rnd_idx >= 15:
            break
        round_devs = []
        for bid in rnd["history"]["bidding history"]:
            bids[bid["agent"]].append(float(bid["bid"]))
        for i, val in enumerate(rnd["value"]):
            values[bidders[i]].append(val)
            deviation = abs((float(rnd["history"]["bidding history"][i]["bid"]) - val*2/3))
            deviations[bidders[i]][rnd_idx].append(deviation)
            round_devs.append(deviation)
        round_averages[rnd_idx].append(np.mean(round_devs))


average_deviations_per_round = {bidder: [np.mean(deviations[bidder][i]) for i in range(15)] for bidder in bidders}
overall_average_deviations_per_round = [np.mean(round_averages[i]) for i in range(15)]
overall_std_error_per_round = [np.std(round_averages[i]) / np.sqrt(len(round_averages[i])) for i in range(15)]
# 绘制图表
fig, ax = plt.subplots(figsize=(12, 6))
rounds = range(15)
# for bidder in bidders:
#     ax.plot(rounds, average_deviations_per_round[bidder], marker='o', label=bidder)

ax.errorbar(rounds, overall_average_deviations_per_round, yerr=overall_std_error_per_round, fmt='.-', label="Average", capsize=5)

# ax.plot(rounds, overall_average_deviations_per_round, marker='.', label="Average")

ax.set_xlabel("Rounds")
ax.set_ylabel("Deviation: Bid - Value")
ax.set_title("Deviation of Each Bidder's Value and Bid Over Rounds")
ax.set_ylim([0,30])
ax.legend()
plt.grid(True)
plt.show()

print("Average Deviations per Round:")
for i in range(15):
    print(f"Round {i + 1}:")
    for bidder in bidders:
        print(f"  {bidder}: {average_deviations_per_round[bidder][i]}")
    print(f"  Overall Average: {overall_average_deviations_per_round[i]}")
    


values = []
bids = []

for file_path in file_paths:
    with open(file_path, 'r') as file:
        data = json.load(file)

    for rnd in data.values():
        for i, val in enumerate(rnd["value"]):
            bid = float(rnd["history"]["bidding history"][i]["bid"])
            values.append(val)
            bids.append(bid)

values = np.array(values)
bids = np.array(bids)

smoothed = lowess(bids, values, frac=0.1)  

fig, ax = plt.subplots(figsize=(12, 6))
ax.scatter(values, bids, alpha=0.5, label='Original Data')
ax.plot(smoothed[:, 0], smoothed[:, 1], color='red', label='Smoothed Data (LOESS)')

value_range = np.linspace(min(values), max(values), 500)
theoretical_bid = 2 / 3 * value_range
ax.plot(value_range, theoretical_bid, color='green', linestyle='--', label=r'Theoretical Line: $bid = \frac{2}{3} \times value$')

ax.plot(value_range, value_range, color='blue', linestyle=':', label='Reference Line: $bid = value$')


ax.set_xlabel("Value")
ax.set_ylabel("Bid")
ax.set_title("Bids vs Values with LOESS Smoothing")
ax.legend()
plt.grid(True)
plt.show()
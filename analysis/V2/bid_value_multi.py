import json
import numpy as np
import matplotlib.pyplot as plt

name_to_letter = {
    "Andy": 'A',
    "Betty": 'B',
    "Charles": 'C'
}


def calculate_value_for_file(path_folders):
    all_values = []
    all_bids = []
    rounds = []
    
    for file_path in path_folders:
        print(file_path)
        rounds, values, bids = get_value_for_file(file_path)
        all_values.append(values)
        all_bids.append(bids)
    
    print(all_values)
    return rounds, all_bids, all_values

def get_value_for_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    rounds = []
    all_bids = []
    all_values = []

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
        
        all_values.append(values)
        all_bids.append(bids)
        rounds.append(i)
    
    return rounds, all_values, all_bids

path_folders = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_21-57-42.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_21-59-22.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-01-03.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-02-50.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-04-34.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-06-17.json"
]

rounds, all_bids, all_values = calculate_value_for_file(path_folders)
# Plotting example for the first set of data (you can loop through all sets if needed)
# Plotting all groups for specific rounds (0, 4, 9)
# colors = ['red','red', 'blue','blue', 'green','green']
# round_indices = [0,1, 3,4, 8,9]
colors = ['red', 'blue', 'green']
round_indices = [0, 4, 9]

# Initialize lists for grouping data
group_values = {round_idx: [] for round_idx in round_indices}
group_bids = {round_idx: [] for round_idx in round_indices}

# Collect data for the specific rounds
for group_idx in range(len(all_values)):
    for round_idx in round_indices:
        group_values[round_idx].extend(all_values[group_idx][round_idx])
        group_bids[round_idx].extend(all_bids[group_idx][round_idx])

# Prepare the plot
plt.figure(figsize=(10, 6))

# Plot data for each round with shading
for i, round_idx in enumerate(round_indices):
    values = np.array(group_values[round_idx])
    bids = np.array(group_bids[round_idx])
    
    mean_values = np.mean(values)
    std_values = np.std(values)
    mean_bids = np.mean(bids)
    std_bids = np.std(bids)
    
    plt.plot(values, bids, marker='.', linestyle='', color=colors[i], label=f'round {round_idx}')
    # plt.fill_betweenx(bids, values - std_values, values + std_values, color=colors[i], alpha=0.2)
    # plt.fill_between(values, bids - std_bids, bids + std_bids, color=colors[i], alpha=0.2)
    #Polynomial fit
    p = np.polyfit(values, bids, 2)  # Fit a 2nd degree polynomial
    fit_values = np.linspace(min(values), max(values), 100)
    fit_bids = np.polyval(p, fit_values)
    
    # Calculate the residuals
    residuals = bids - np.polyval(p, values)
    std_residuals = np.std(residuals)
    
    
    # Plot the polynomial fit
    plt.plot(fit_values, fit_bids, linestyle='-', color=colors[i], alpha=0.6)
    
    # Plot the uncertainty area (shading)
    plt.fill_between(fit_values, fit_bids - 0.5*std_residuals, fit_bids + 0.5*std_residuals, color=colors[i], alpha=0.2)


# for i, round_idx in enumerate(round_indices):
#     for group_idx in range(len(all_values)):
#         plt.plot(all_values[group_idx][round_idx], all_bids[group_idx][round_idx], 
#                  marker='.', linestyle='', color=colors[i], label=f'round {round_idx}' if group_idx == 0 else "")

# Plot the theoretical prediction where values = bids
max_value = max(np.max(all_values), np.max(all_bids))

plt.plot([0, max_value], [0, max_value], linestyle='--', color='black', label='Theory SPSB')

plt.xlabel('Values')
plt.ylabel('Bids')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()
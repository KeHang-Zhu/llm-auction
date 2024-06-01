import json
import numpy as np
import matplotlib.pyplot as plt

name_to_letter = {
    "Andy": 'A',
    "Betty": 'B',
    "Charles": 'C'
}

def calculate_mad_for_file(file_path):
    """Calculate MAD values for a single JSON file."""
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

        # winner_bidder = round_data['history']['winner']['winner']

        # if winner_bidder == 'NA':
        #     mad = np.mean(np.abs(bids - values))
        # else:
        #     winner_index = ord(winner_bidder.split()[-1]) - ord('A')

        #     # Remove the winner's bid and corresponding value
        #     values = np.delete(values, winner_index)
        #     bids = np.delete(bids, winner_index)

            mad = np.mean(np.abs(bids - values))

        rounds.append(i)
        mad_values.append(mad)
    
    return rounds, mad_values

def calculate_average_mad(file_paths):
    """Calculate the average MAD values across multiple JSON files."""
    all_mad_values = []
    rounds = None

    for file_path in file_paths:
        file_rounds, mad_values = calculate_mad_for_file(file_path)
        all_mad_values.append(mad_values)
        
        if rounds is None:
            rounds = file_rounds

    # Convert list of lists to a NumPy array for easier mean calculation
    all_mad_values = np.array(all_mad_values)
    
    # Calculate the mean MAD values across all files for each round
    average_mad_values = np.mean(all_mad_values, axis=0)
    
    return rounds, average_mad_values


# file_paths = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_12-41-29.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_12-55-50.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_12-57-19.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_12-58-52.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-00-17.json", 
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-09-53.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-11-20.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-12-45.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-14-09.json",
#               "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-15-39.json"]

# file_paths = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-31-47.json","/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-33-21.json","/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-34-48.json",
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-36-14.json",
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_13-37-37.json"]
# file_paths0 = [
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-33-21.json"
# ]
# file_paths0 =
# file_paths1 = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_20-29-50.json"]
file_paths2=[
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_21-57-42.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_21-59-22.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-01-03.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-02-50.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-04-34.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_22-06-17.json"
]
# file_paths = [
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-34-06.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-35-56.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-37-34.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-39-13.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-40-56.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-42-40.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-44-21.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-45-59.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-47-37.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V2/seal__second_private_close/result_10_2024-05-30_23-49-18.json"
# ]

file_paths = [
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

ac = [0.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5, 0.0, 0.5, 0.5]
# ac_b = [1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.5, 0.0, 1.0, 0.0]
# list1 = [0.0, 3.5, 5.0, 1.0, 1.0, 3.0, 0.5, 2.5, 2.5, 2.0]
# list2 = [2.0, 2.5, 2.0, 1.0, 2.0, 2.0, 1.0, 2.0, 2.0, 1.5]
# list3 = [2.0, 2.0, 1.5, 0.3333333333333333, 3.5, 0.5, 0.5, 3.0, 1.5, 2.0]
# list4 = [1.5, 1.0, 2.0, 1.0, 3.0, 2.0, 4.5, 2.3333333333333335, 0.5, 1.5]
# list5 = [0.5, 2.5, 2.0, 0.5, 1.3333333333333333, 1.0, 1.0, 2.0, 0.5, 0.0]

# Calculating the mean of the combined lists
# acb = np.mean([list1, list2, list3, list4, list5], axis=0)
# file_paths4=["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_20-47-43.json"]
rounds, ave_mad_values= calculate_average_mad(file_paths)
rounds2, ave_mad_values2= calculate_average_mad(file_paths2)
# Plot Mean Absolute Deviation of Bids from Values vs Round
plt.plot(rounds, ave_mad_values, marker='o', linestyle='--', color='blue', label='SPSB')
plt.plot(rounds2, ac, marker='.', linestyle='-', color='red', label='AC')
# plt.plot(rounds2, acb, marker='.', linestyle='--', color='green', label='AC-B')

# Plot Mean Absolute Deviation of Bids from Values vs Round
# plt.plot(rounds, mad_values, marker='o', linestyle='-', color='blue')
plt.xlabel('Round')
plt.ylabel('Mean Absolute Deviation')
plt.title('Mean Absolute Deviation of Bids from Values vs Round')
# plt.ylim([0,15])
plt.grid(True)
plt.legend(loc='upper right')
plt.show()

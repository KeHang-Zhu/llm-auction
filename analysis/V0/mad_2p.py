import json
import numpy as np
import matplotlib.pyplot as plt

# Load the JSON file
# file_path = '/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_21-40-46.json'
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_21-44-00.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_21-46-50.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_21-51-26.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-22_21-53-37.json"

# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-23_19-53-29.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-23_19-56-40.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-23_19-59-12.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-23_20-01-41.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-23_20-04-53.json"
# file_path = "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/seal_ascend_second_common_open/result_10_2024-05-27_12-41-29.json"
# with open(file_path, 'r') as file:
#     data = json.load(file)

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
            bidder_index = ord(bid['agent'].split()[-1]) - ord('A')
            bids[bidder_index] = int(bid['bid'])

        winner_bidder = round_data['history']['winner']['winner']

        if winner_bidder == 'NA':
            mad = np.mean(np.abs(bids - values))
        else:
            winner_index = ord(winner_bidder.split()[-1]) - ord('A')

            # Remove the winner's bid and corresponding value
            values = np.delete(values, winner_index)
            bids = np.delete(bids, winner_index)

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
        print(mad_values)
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

file_paths = [
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-31-47.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-33-21.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-34-48.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-36-14.json",
    "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-37-37.json"]
# file_paths0 = [
# "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V0/seal_ascend_second_common_open/result_10_2024-05-27_13-33-21.json"
# ]
# file_paths0 =
# file_paths1 = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_20-29-50.json"]

# file_paths = [
#     # 
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_20-37-01.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_21-07-42.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_21-09-11.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_21-10-40.json",
#     "/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_21-12-07.json"
#     ]

# file_paths4=["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V1/seal_ascend_second_common_open/result_10_2024-05-27_20-47-43.json"]
rounds, ave_mad_values= calculate_average_mad(file_paths)

# Plot Mean Absolute Deviation of Bids from Values vs Round
plt.plot(rounds, ave_mad_values, marker='o', linestyle='--', color='blue', label='reasoning, T =0.5 ')

# Plot Mean Absolute Deviation of Bids from Values vs Round
# plt.plot(rounds, mad_values, marker='o', linestyle='-', color='blue')
plt.xlabel('Round')
plt.ylabel('Mean Absolute Deviation')
plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.grid(True)
plt.legend(loc='upper right')
plt.show()

import json
import csv
import os

def parse_json_to_csv(json_file_paths, csv_file_path):
    # Prepare the CSV data
    csv_data = []
    headers = ["round", "bidder", "value", "bid", "winner", "AC", "Blind"]

    for json_file_path in json_file_paths:
        # Read the JSON file
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        # Get the filename without the path
        filename = os.path.basename(json_file_path)

        for round_key, round_data in data.items():
            round_number = round_data["round"]
            values = round_data["value"]
            history = round_data["history"]
            winner = history["winner"]["winner"]

            # Create a mapping of bidders to their values
            bidder_value_map = {f"Bidder {i}": value for i, value in enumerate(values)}

            for bid_info in history["bidding history"]:
                bidder = bid_info["agent"]
                bid = bid_info["bid"]
                value = bidder_value_map[bidder]
                is_winner = bidder == winner

                csv_data.append([round_number, bidder, value, bid, is_winner, False, True])

    # Write to CSV file
    with open(csv_file_path, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(csv_data)

    print(f"CSV file '{csv_file_path}' has been created successfully.")

# Usage
# json_file_paths = [
#     "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_open/result_10_2024-05-22_19-19-57.json"
# ]
# json_file_paths = ["/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_blind/result_10_2024-05-22_22-10-31.json",
# "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_blind/result_10_2024-05-22_22-28-27.json",
# "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_blind/result_10_2024-05-22_22-51-42.json",
# "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_blind/result_10_2024-05-22_23-34-41.json",
# "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/clock_ascend_second_private_blind/result_10_2024-05-22_23-56-20.json"]

json_file_paths = [ "/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/result_10_2024-05-23_19-53-29.json",
"/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/result_10_2024-05-23_19-56-40.json",
"/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/result_10_2024-05-23_19-59-12.json",
"/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/result_10_2024-05-23_20-01-41.json",
"/Users/wonderland/Desktop/auction/llm-auction/results/OSP/seal_ascend_second_private_open/result_10_2024-05-23_20-04-53.json"]


csv_file_path = "OPS_all.csv"

parse_json_to_csv(json_file_paths, csv_file_path)
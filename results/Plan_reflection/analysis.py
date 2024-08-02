file_paths1 = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-980826.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982049.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982140.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982255.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-982367.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__first_private_close/result_15_2024-06-20_20-59-24-983239.json"]

file_paths2 = ["/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_17-54-38.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_17-57-54.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_18-09-34.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_18-20-59.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_18-32-06.json",
"/Users/wonderland/Desktop/auction/llm-auction/experiment_logs/V6/seal__second_private_close/result_15_2024-06-20_18-43-30.json"]


## make a CSV: 
# take the round number, player name, bid, value, plan
# overbid = True if bid > value, otherwise False
# underbid = True if bid < value, otherwise False
# first = True if in path_file1, False if in path_file2

import pandas as pd
import json

# Load JSON data from the file
def parse_data(file_path, df):
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Create a DataFrame to store the required data

    # Function to check if bid > value
    def is_overbid(bid, value):
        return bid > value

    # Function to check if bid < value
    def is_underbid(bid, value):
        return bid < value

    # List to collect new rows
    new_rows = []

    # Process each round in the JSON data
    for round_key, round_data in data.items():
        round_number = round_data['round']
        values = round_data['value']
        history = round_data['history']['bidding history']
        plans = round_data['plan']
        
        # Iterate over each player in the round
        for i, player_data in enumerate(history):
            player_name = player_data['agent']
            bid = float(player_data['bid'])
            value = float(values[i])
            plan = plans[i]
            overbid = is_overbid(bid, value)
            underbid = is_underbid(bid, value)
            first = file_path in file_paths1  # Check if the file is in the first set
            
            # Create a dictionary for the new row
            new_row = {
                'Round': round_number,
                'Player Name': player_name,
                'Bid': bid,
                'Value': value,
                'Plan': plan,
                'Overbid': overbid,
                'Underbid': underbid,
                'First': first
            }
            new_rows.append(new_row)
    
    # Append new rows to the DataFrame using pd.concat
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    return df



df = pd.DataFrame(columns=['Round', 'Player Name', 'Bid', 'Value', 'Plan', 'Overbid', 'Underbid', 'First'])


# Process each file path
for file_path in file_paths1 + file_paths2:
    df = parse_data(file_path, df)

# Save the DataFrame to a CSV file
csv_output_path = "fp_sp_auction_data.csv"
df.to_csv(csv_output_path, index=False)


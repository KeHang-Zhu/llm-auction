import csv
from collections import defaultdict

def process_csv(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['remaining_bidders']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        round_data = defaultdict(list)
        for row in reader:
            try:
                price = int(row['price'])
                round_data[price].append(row)
            except ValueError:
                print(f"Skipping row with invalid price: {row}")

        for price, rows in sorted(round_data.items()):
            bidders_this_round = set()
            filtered_rows = []

            for row in rows:
                bidder = int(row['bidder'].split()[-1])
                value = int(row['value'])
                answer = int(row['answer'])
                bidders_this_round.add(bidder)

                if answer == 1 and value > price + 1:
                    filtered_rows.append(row)

            remaining_bidders = len(bidders_this_round)

            for row in filtered_rows:
                row['remaining_bidders'] = remaining_bidders
                writer.writerow(row)

        print(f"Filtered data has been written to {output_file}")

# Usage
input_file = 'combined_output_AC_B.csv'  # Replace with your input file name
output_file = 'filtered_output_AC_B.csv'
process_csv(input_file, output_file)
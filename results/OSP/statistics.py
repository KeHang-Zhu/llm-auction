import csv
from collections import defaultdict

def analyze_auctions(filename):
    data = defaultdict(list)
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['AC'] == 'True', row['Blind'] == 'True')
            data[key].append(row)

    results = {}
    for (is_clock, is_blind), rows in data.items():
        if is_clock and not is_blind:
            format_name = "Standard Clock"
        elif is_clock and is_blind:
            format_name = "Blind Clock"
        elif not is_clock and is_blind:
            format_name = "Sealed-bid"
        else:
            continue  # Skip other combinations

        if is_clock:
                total_bids = sum(1 for row in rows if row['winner'] == 'False')
        else:
            total_bids = len(rows)
        truthful_bids = 0
        total_deviation = 0

        for row in rows:
            value = float(row['value'])
            bid = float(row['bid'])
            is_winner = row['winner'] == 'True'

            if is_clock:
                if not is_winner:
                    if abs(bid - value) <= 1:
                        truthful_bids += 1
                    total_deviation += abs(bid - value)
            else:
                if bid == value:
                    truthful_bids += 1
                total_deviation += abs(bid - value)

        percent_truthful = (truthful_bids / total_bids) * 100
        percent_not_truthful = 100 - percent_truthful
        avg_deviation = total_deviation / total_bids

        results[format_name] = {
            "% Truthful": f"{percent_truthful:.2f}%",
            "% Not Truthful": f"{percent_not_truthful:.2f}%",
            "Average Deviation": f"{avg_deviation:.2f}"
        }

    return results

def print_results(results):
    print("| Auction Format      | % Truthful | % Not Truthful | Average Deviation |")
    print("|---------------------|------------|-----------------|-------------------|")
    for format_name, stats in results.items():
        print(f"| {format_name:<19} | {stats['% Truthful']:>10} | {stats['% Not Truthful']:>15} | {stats['Average Deviation']:>17} |")

if __name__ == "__main__":
    filename = "OPS_all.csv"  # Update this with the actual filename if different
    results = analyze_auctions(filename)
    print_results(results)
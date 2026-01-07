"""
Export experiment results to CSV format.
Combines configuration parameters from YAML and detailed results from JSON.
"""

import json
import csv
import os
from pathlib import Path
import yaml


def flatten_results_to_csv(config_path: str, result_json_path: str, output_csv_path: str):
    """
    Convert experiment results to flat CSV format.

    Args:
        config_path: Path to the YAML configuration file
        result_json_path: Path to the result JSON file
        output_csv_path: Path for output CSV file
    """
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load results
    with open(result_json_path, 'r') as f:
        results = json.load(f)

    # Extract config parameters
    exp_name = config['experiment']['name']
    exp_version = config['experiment'].get('version', 'N/A')
    model = config['llm']['model']
    temperature = config['llm'].get('temperature', 'N/A')
    service_name = config['llm'].get('service_name', 'openai')
    num_agents = config['auction']['number_agents']
    num_rounds = config['auction']['rounds']
    seal_clock = config['rule']['seal_clock']
    price_order = config['rule']['price_order']
    private_value = config['rule']['private_value']
    increment = config['value']['increment']
    seed_base = config['value'].get('seed_base', 'N/A')
    special_name = config['rule'].get('special_name', 'N/A')

    # Extract timestamp from result file path
    timestamp = Path(result_json_path).parent.parent.name.replace('run_', '')
    repetition_id = Path(result_json_path).stem.split('_')[-1]

    # Prepare rows
    rows = []

    # Process each round
    for round_key in sorted(results.keys()):
        round_data = results[round_key]
        round_num = round_data['round']
        values = round_data['value']
        bidding_history = round_data['history']['bidding history']
        winner_info = round_data['history']['winner']
        winner_name = winner_info['winner']
        final_price = winner_info['price']
        profits = round_data['profit']
        plans = round_data['plan']

        # Process each player in this round
        # Player name order is fixed: Andy, Betty, Charles (maps to values array indices)
        player_name_to_idx = {
            'Bidder Andy': 0,
            'Bidder Betty': 1,
            'Bidder Charles': 2
        }

        for idx, bid_entry in enumerate(bidding_history):
            player_name = bid_entry['agent']
            player_bid = bid_entry['bid']

            # Get correct index based on player name (not bidding history order)
            player_idx = player_name_to_idx.get(player_name, idx)
            player_value = values[player_idx]
            player_profit = profits[player_idx]
            player_plan = plans[player_idx]
            is_winner = (player_name == winner_name)

            row = {
                # Round-specific data (priority - at front)
                'round': round_num,
                'player_name': player_name,
                'player_value': player_value,
                'bid': player_bid,
                'is_winner': is_winner,
                'final_price': final_price,
                'profit': player_profit,

                # Configuration parameters (middle)
                'experiment_name': exp_name,
                'version': exp_version,
                'model': model,
                'service_name': service_name,
                'temperature': temperature,
                'number_agents': num_agents,
                'total_rounds': num_rounds,
                'seal_clock': seal_clock,
                'price_order': price_order,
                'private_value': private_value,
                'increment': increment,
                'seed_base': seed_base,
                'special_name': special_name,
                'timestamp': timestamp,
                'repetition_id': repetition_id,

                # Strategic plan (last)
                'plan': player_plan
            }
            rows.append(row)

    # Write to CSV
    if rows:
        fieldnames = list(rows[0].keys())

        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists(output_csv_path)

        with open(output_csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)

        return len(rows)
    return 0


def export_experiment_results(run_dir: str, config_path: str, output_dir: str = "results", silent: bool = False):
    """
    Export all result files from an experiment run to CSV.

    Args:
        run_dir: Path to the experiment run directory
        config_path: Path to the configuration YAML file
        output_dir: Directory to save CSV files (default: "results")
        silent: If True, suppress print statements (for integration with main.py)

    Returns:
        Path to generated CSV file, or None if failed
    """
    def log(msg):
        if not silent:
            print(msg)

    run_dir_path = Path(run_dir)
    raw_data_dir = run_dir_path / "raw_data"

    if not raw_data_dir.exists():
        log(f"No raw_data directory found in {run_dir}")
        return None

    # Find all result JSON files
    result_files = list(raw_data_dir.glob("result_*.json"))

    if not result_files:
        log(f"No result files found in {raw_data_dir}")
        return None

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output CSV filename from config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    exp_name = config['experiment']['name']
    output_csv = os.path.join(output_dir, f"{exp_name}_results.csv")

    # Delete existing CSV file to avoid appending to old data
    if os.path.exists(output_csv):
        os.remove(output_csv)
        log(f"Removed existing CSV: {output_csv}")

    # Process each result file
    total_rows = 0
    for result_file in sorted(result_files):
        rows_added = flatten_results_to_csv(
            config_path=config_path,
            result_json_path=str(result_file),
            output_csv_path=output_csv
        )
        total_rows += rows_added
        log(f"Processed {result_file.name}: {rows_added} rows")

    log(f"\nTotal: {total_rows} rows exported to {output_csv}")
    return output_csv


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python export_results.py <run_dir> <config_path> [output_dir]")
        sys.exit(1)

    run_dir = sys.argv[1]
    config_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "results"

    export_experiment_results(run_dir, config_path, output_dir)

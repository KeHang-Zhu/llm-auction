#!/usr/bin/env python3
"""
Summarize all experiment results from experiment_logs into a single CSV file.
Reads all results/*.csv files from each experiment and combines them.
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import glob

def find_all_result_csvs(experiment_logs_dir="experiment_logs"):
    """Find all result CSV files in experiment_logs directory."""
    result_files = []

    # Iterate through each model directory
    for model_dir in Path(experiment_logs_dir).iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name

        # Iterate through each experiment directory
        for exp_dir in model_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            exp_name = exp_dir.name

            # Find all run directories
            for run_dir in exp_dir.glob("run_*/"):
                results_dir = run_dir / "results"
                if not results_dir.exists():
                    continue

                # Find all CSV files in results directory
                for csv_file in results_dir.glob("*.csv"):
                    result_files.append({
                        'model': model_name,
                        'experiment': exp_name,
                        'run_dir': str(run_dir),
                        'csv_path': str(csv_file)
                    })

    return result_files

def load_and_combine_results(result_files):
    """Load all CSV files and combine them into a single DataFrame."""
    all_dfs = []

    for file_info in result_files:
        try:
            df = pd.read_csv(file_info['csv_path'])

            # Add metadata columns if they don't exist
            if 'model' not in df.columns:
                df['model'] = file_info['model']
            if 'experiment' not in df.columns:
                df['experiment'] = file_info['experiment']

            all_dfs.append(df)
            print(f"✓ Loaded {file_info['model']}/{file_info['experiment']}: {len(df)} rows")

        except Exception as e:
            print(f"✗ Error loading {file_info['csv_path']}: {e}")
            continue

    if not all_dfs:
        print("No data to combine!")
        return None

    # Combine all DataFrames
    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df

def generate_summary_stats(combined_df):
    """Generate summary statistics from combined results."""
    summary = combined_df.groupby(['model', 'experiment']).agg({
        'round': 'count',  # Total number of observations
        'is_winner': 'sum',  # Total wins
        'profit': ['mean', 'std', 'min', 'max'],
        'bid': ['mean', 'std'],
        'player_value': ['mean', 'min', 'max']
    }).reset_index()

    summary.columns = ['_'.join(col).strip('_') for col in summary.columns.values]
    summary = summary.rename(columns={
        'round_count': 'total_observations',
        'is_winner_sum': 'total_wins'
    })

    return summary

def main():
    print("=" * 60)
    print("Experiment Results Summarization")
    print("=" * 60)
    print()

    # Find all result CSV files
    print("Scanning experiment_logs directory...")
    result_files = find_all_result_csvs()
    print(f"Found {len(result_files)} result CSV files\n")

    if not result_files:
        print("No result files found!")
        return

    # Load and combine all results
    print("Loading and combining results...")
    combined_df = load_and_combine_results(result_files)

    if combined_df is None:
        print("Failed to combine results!")
        return

    print(f"\nTotal rows in combined dataset: {len(combined_df)}")
    print(f"Columns: {list(combined_df.columns)}")

    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)

    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_file = f"results/all_experiments_combined_{timestamp}.csv"
    combined_df.to_csv(combined_file, index=False)
    print(f"\n✓ Saved combined results to: {combined_file}")

    # Generate and save summary statistics
    print("\nGenerating summary statistics...")
    summary_df = generate_summary_stats(combined_df)
    summary_file = f"results/experiments_summary_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"✓ Saved summary statistics to: {summary_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("Summary by Model and Experiment:")
    print("=" * 60)
    print(summary_df.to_string(index=False))

    # Model-level summary
    print("\n" + "=" * 60)
    print("Summary by Model:")
    print("=" * 60)
    model_summary = combined_df.groupby('model').agg({
        'round': 'count',
        'profit': ['mean', 'std'],
        'is_winner': lambda x: f"{x.sum()}/{len(x)} ({x.mean()*100:.1f}%)"
    }).reset_index()
    model_summary.columns = ['Model', 'Total Observations', 'Avg Profit', 'Std Profit', 'Win Rate']
    print(model_summary.to_string(index=False))

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()

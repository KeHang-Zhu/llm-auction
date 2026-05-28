#!/usr/bin/env python3
"""
Merge results.csv files from multiple runs of an experiment.

Usage:
    python3 merge_results.py --experiment ascending_clock_apv
    python3 merge_results.py --experiment ascending_clock_apv_closed
    python3 merge_results.py --all  # Merge all experiments
"""

import argparse
import pandas as pd
from pathlib import Path
import sys


def merge_experiment_results(experiment_dir: Path, output_filename: str = None):
    """
    Merge all results CSV files from different runs of an experiment.

    Args:
        experiment_dir: Path to experiment directory (e.g., experiment_logs/V10/ascending_clock_apv)
        output_filename: Optional custom output filename

    Returns:
        Path to merged CSV file, or None if no results found
    """
    # Find all results CSV files
    result_files = list(experiment_dir.glob("run_*/results/*.csv"))

    if not result_files:
        print(f"⊘ No results found in {experiment_dir}")
        return None

    print(f"\n{'='*80}")
    print(f"Merging results for: {experiment_dir.name}")
    print(f"{'='*80}")
    print(f"Found {len(result_files)} run(s):")

    # Read all CSV files
    dfs = []
    for i, csv_file in enumerate(sorted(result_files)):
        run_dir = csv_file.parent.parent.name
        print(f"  {i+1}. {run_dir} - {csv_file.stat().st_size / 1024:.1f} KB")

        # Read CSV
        df = pd.read_csv(csv_file)

        # Add run_id column to identify which run each row came from
        df['run_id'] = run_dir

        dfs.append(df)

    # Concatenate all dataframes
    merged_df = pd.concat(dfs, ignore_index=True)

    # Sort by repetition_id, round, player_name for easier reading
    if 'repetition_id' in merged_df.columns:
        merged_df = merged_df.sort_values(['repetition_id', 'round', 'player_name'])

    # Generate output filename
    if output_filename is None:
        output_filename = f"{experiment_dir.name}_merged_results.csv"

    output_path = experiment_dir / output_filename

    # Save merged CSV
    merged_df.to_csv(output_path, index=False)

    print(f"\n✓ Merged {len(merged_df)} rows from {len(result_files)} runs")
    print(f"  Output: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")

    # Print summary statistics
    if 'repetition_id' in merged_df.columns:
        unique_reps = merged_df['repetition_id'].nunique()
        print(f"  Unique repetitions: {unique_reps}")

    if 'round' in merged_df.columns:
        unique_rounds = merged_df['round'].nunique()
        print(f"  Unique rounds: {unique_rounds}")

    return output_path


def merge_all_experiments(base_dir: Path = None):
    """
    Merge results for all experiments in the base directory.

    Args:
        base_dir: Base directory containing experiments (default: experiment_logs/V10)
    """
    if base_dir is None:
        base_dir = Path("experiment_logs/V10")

    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        return

    # Find all experiment directories
    experiment_dirs = [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

    print(f"\n{'='*80}")
    print(f"MERGING ALL EXPERIMENTS IN: {base_dir}")
    print(f"{'='*80}")
    print(f"Found {len(experiment_dirs)} experiment(s)")

    merged_count = 0
    for exp_dir in sorted(experiment_dirs):
        result = merge_experiment_results(exp_dir)
        if result:
            merged_count += 1

    print(f"\n{'='*80}")
    print(f"SUMMARY: Successfully merged {merged_count}/{len(experiment_dirs)} experiments")
    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(
        description='Merge results CSV files from multiple experiment runs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge specific experiment
  python3 merge_results.py --experiment ascending_clock_apv

  # Merge all experiments in experiment_logs/V10/
  python3 merge_results.py --all

  # Merge with custom output filename
  python3 merge_results.py --experiment ascending_clock_apv --output combined.csv

  # Merge from custom base directory
  python3 merge_results.py --all --base-dir robustness_logs/V10
        """
    )

    parser.add_argument(
        '--experiment',
        type=str,
        help='Experiment name to merge (e.g., ascending_clock_apv)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Merge results for all experiments'
    )

    parser.add_argument(
        '--base-dir',
        type=str,
        default='experiment_logs/V10',
        help='Base directory containing experiments (default: experiment_logs/V10)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Custom output filename (default: {experiment_name}_merged_results.csv)'
    )

    args = parser.parse_args()

    # Check that at least one option is specified
    if not args.experiment and not args.all:
        parser.error("Must specify either --experiment or --all")

    base_dir = Path(args.base_dir)

    if args.all:
        # Merge all experiments
        merge_all_experiments(base_dir)
    else:
        # Merge specific experiment
        experiment_dir = base_dir / args.experiment
        if not experiment_dir.exists():
            print(f"Error: Experiment directory not found: {experiment_dir}")
            return 1

        result = merge_experiment_results(experiment_dir, args.output)
        if result is None:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

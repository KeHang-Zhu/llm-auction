#!/usr/bin/env python3
"""
Check consistency between raw JSON data and exported CSV results.

Verifies that player values are correctly mapped to player names in CSV files.
"""

import json
import pandas as pd
from pathlib import Path
import sys
from collections import defaultdict


def load_json_data(json_file: Path) -> dict:
    """Load raw JSON result file."""
    with open(json_file, 'r') as f:
        return json.load(f)


def check_single_result(csv_file: Path, json_dir: Path) -> dict:
    """
    Check consistency for a single result file.

    Args:
        csv_file: Path to results CSV
        json_dir: Path to raw_data directory containing JSON files

    Returns:
        Dictionary with check results
    """
    issues = []
    checked_count = 0

    # Load CSV
    df = pd.read_csv(csv_file)

    # Get unique repetition IDs from CSV
    if 'repetition_id' not in df.columns:
        return {
            'csv_file': str(csv_file),
            'status': 'error',
            'message': 'No repetition_id column found',
            'issues': [],
            'checked_count': 0
        }

    unique_reps = df['repetition_id'].unique()

    # For each repetition, check consistency
    for rep_id in unique_reps:
        # Get CSV data for this repetition
        rep_df = df[df['repetition_id'] == rep_id].copy()

        if rep_df.empty:
            continue

        # Get round number (should be same for all rows in a repetition)
        round_num = rep_df['round'].iloc[0]

        # Try to find corresponding JSON file
        # JSON files are named like result_1_2026-01-06_22-55-37-169631.json
        # repetition_id is the timestamp part like "22-55-37-169631"
        json_pattern = f"result_{round_num}_*{rep_id}.json"
        json_files = list(json_dir.glob(json_pattern))

        if not json_files:
            # Try alternative pattern
            json_pattern = f"result_*.json"
            json_files = list(json_dir.glob(json_pattern))
            # Filter by checking if rep_id is in filename
            json_files = [f for f in json_files if rep_id in f.name]

        if not json_files:
            continue  # Skip if no matching JSON found

        # Use the first matching JSON file
        json_file = json_files[0]

        try:
            # Load JSON data
            json_data = load_json_data(json_file)

            # Get the round data
            round_key = f"round_{round_num}"
            if round_key not in json_data:
                continue

            round_data = json_data[round_key]

            # Extract values and history
            values = round_data.get('value', [])
            history = round_data.get('history', {})
            bidding_history = history.get('bidding history', [])

            # Agent name order is fixed: Andy, Betty, Charles
            agent_names = ['Bidder Andy', 'Bidder Betty', 'Bidder Charles']

            # Create mapping: agent_name -> expected_value
            expected_values = {}
            for i, agent_name in enumerate(agent_names):
                if i < len(values):
                    expected_values[agent_name] = values[i]

            # Check each row in CSV
            for _, row in rep_df.iterrows():
                player_name = row['player_name']
                csv_value = row['player_value']

                if player_name in expected_values:
                    json_value = expected_values[player_name]

                    if csv_value != json_value:
                        issues.append({
                            'repetition_id': rep_id,
                            'round': round_num,
                            'player_name': player_name,
                            'csv_value': csv_value,
                            'json_value': json_value,
                            'json_file': json_file.name
                        })

            checked_count += 1

        except Exception as e:
            issues.append({
                'repetition_id': rep_id,
                'error': f"Error processing: {str(e)}",
                'json_file': json_file.name if json_files else 'not found'
            })

    return {
        'csv_file': str(csv_file),
        'status': 'ok' if not issues else 'inconsistent',
        'issues': issues,
        'checked_count': checked_count
    }


def check_all_experiments(base_dir: Path = None):
    """
    Check all experiments in the base directory.

    Args:
        base_dir: Base directory containing experiments
    """
    if base_dir is None:
        base_dir = Path("experiment_logs/V10")

    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        return

    print(f"\n{'='*80}")
    print(f"CHECKING VALUE CONSISTENCY IN: {base_dir}")
    print(f"{'='*80}\n")

    all_results = []
    total_issues = 0

    # Find all experiment directories
    experiment_dirs = sorted([d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

    for exp_dir in experiment_dirs:
        print(f"\n📁 {exp_dir.name}")
        print(f"{'─'*80}")

        # Find all run directories
        run_dirs = sorted(exp_dir.glob("run_*"))

        if not run_dirs:
            print(f"  ⊘ No run directories found")
            continue

        for run_dir in run_dirs:
            # Find results CSV
            csv_files = list((run_dir / "results").glob("*.csv"))
            if not csv_files:
                print(f"  ⊘ {run_dir.name}: No CSV found")
                continue

            csv_file = csv_files[0]

            # Find raw_data directory
            raw_data_dir = run_dir / "raw_data"
            if not raw_data_dir.exists():
                print(f"  ⊘ {run_dir.name}: No raw_data directory")
                continue

            # Check consistency
            result = check_single_result(csv_file, raw_data_dir)
            all_results.append(result)

            # Print result
            if result['status'] == 'ok':
                print(f"  ✓ {run_dir.name}: {result['checked_count']} repetitions checked - OK")
            elif result['status'] == 'inconsistent':
                print(f"  ✗ {run_dir.name}: {len(result['issues'])} ISSUES FOUND (checked {result['checked_count']} reps)")
                total_issues += len(result['issues'])
            else:
                print(f"  ⊘ {run_dir.name}: {result.get('message', 'Error')}")

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")

    total_checks = sum(r['checked_count'] for r in all_results)
    inconsistent_results = [r for r in all_results if r['status'] == 'inconsistent']

    print(f"Total repetitions checked: {total_checks}")
    print(f"Total issues found: {total_issues}")

    if inconsistent_results:
        print(f"\n{'='*80}")
        print(f"DETAILED ISSUES")
        print(f"{'='*80}")

        for result in inconsistent_results:
            if result['issues']:
                print(f"\n📄 {result['csv_file']}")
                print(f"{'─'*80}")

                for issue in result['issues']:
                    if 'error' in issue:
                        print(f"  ✗ Error: {issue['error']}")
                    else:
                        print(f"  ✗ Repetition {issue['repetition_id']}, Round {issue['round']}")
                        print(f"    Player: {issue['player_name']}")
                        print(f"    CSV value: {issue['csv_value']}")
                        print(f"    JSON value: {issue['json_value']}")
                        print(f"    JSON file: {issue['json_file']}")
    else:
        print(f"\n✅ All checks passed! No inconsistencies found.")

    return len(inconsistent_results) == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Check value consistency between CSV and JSON files'
    )
    parser.add_argument(
        '--base-dir',
        type=str,
        default='experiment_logs/V10',
        help='Base directory to check (default: experiment_logs/V10)'
    )
    parser.add_argument(
        '--experiment',
        type=str,
        help='Check only specific experiment'
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir)

    if args.experiment:
        # Check specific experiment
        exp_dir = base_dir / args.experiment
        if not exp_dir.exists():
            print(f"Error: Experiment not found: {exp_dir}")
            return 1

        # Temporarily modify base_dir to only include this experiment
        success = check_all_experiments(base_dir)
    else:
        # Check all experiments
        success = check_all_experiments(base_dir)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Generate missing results CSV files for experiments that have raw_data but no results CSV.
"""

import os
import sys
from pathlib import Path
import subprocess

# Import the export function
sys.path.insert(0, 'src')
from export_results import export_experiment_results


def find_experiments_missing_results(experiment_logs_dir="experiment_logs"):
    """Find all experiments that have raw_data but no results CSV."""
    missing_results = []

    for model_dir in Path(experiment_logs_dir).iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name

        for exp_dir in model_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            exp_name = exp_dir.name

            # Find all run directories
            for run_dir in exp_dir.glob("run_*/"):
                raw_data_dir = run_dir / "raw_data"
                results_dir = run_dir / "results"
                config_file = run_dir / "config.yaml"

                # Check if raw_data exists and has files
                if not raw_data_dir.exists():
                    continue

                raw_files = list(raw_data_dir.glob("result_*.json"))
                if not raw_files:
                    continue

                # Check if results directory is empty or has no CSV
                csv_files = list(results_dir.glob("*.csv")) if results_dir.exists() else []

                if not csv_files:
                    missing_results.append({
                        'model': model_name,
                        'experiment': exp_name,
                        'run_dir': str(run_dir),
                        'config_file': str(config_file),
                        'results_dir': str(results_dir),
                        'raw_file_count': len(raw_files)
                    })

    return missing_results


def generate_results_csv(missing_info):
    """Generate results CSV for a single experiment."""
    run_dir = missing_info['run_dir']
    config_file = missing_info['config_file']
    results_dir = missing_info['results_dir']

    print(f"\n{'='*60}")
    print(f"Processing: {missing_info['model']}/{missing_info['experiment']}")
    print(f"Run directory: {run_dir}")
    print(f"Raw files: {missing_info['raw_file_count']}")
    print(f"{'='*60}")

    # Check if config file exists
    if not os.path.exists(config_file):
        print(f"✗ Config file not found: {config_file}")
        return False

    # Create results directory if it doesn't exist
    os.makedirs(results_dir, exist_ok=True)

    try:
        # Export results
        csv_path = export_experiment_results(
            run_dir=run_dir,
            config_path=config_file,
            output_dir=results_dir,
            silent=False
        )

        if csv_path:
            print(f"✓ Successfully generated: {csv_path}")
            return True
        else:
            print(f"✗ Failed to generate results CSV")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("Generate Missing Results CSV Files")
    print("="*60)
    print()

    # Find experiments missing results
    print("Scanning experiment_logs directory...")
    missing = find_experiments_missing_results()

    if not missing:
        print("✓ All experiments have results CSV files!")
        return

    print(f"\nFound {len(missing)} experiments missing results CSV:\n")
    for info in missing:
        print(f"  • {info['model']}/{info['experiment']}: {info['raw_file_count']} raw files")

    print("\n" + "="*60)
    print("Generating missing results CSV files...")
    print("="*60)

    success_count = 0
    fail_count = 0

    for info in missing:
        if generate_results_csv(info):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    print(f"✓ Successfully generated: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print(f"Total: {len(missing)}")
    print("="*60)


if __name__ == "__main__":
    main()

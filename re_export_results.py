#!/usr/bin/env python3
"""
Re-export results for experiments with incorrect CSV data.

This script re-exports CSV files using the fixed export_results.py.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from export_results import export_experiment_results


def re_export_experiments(experiments: list, base_dir: Path = None):
    """
    Re-export CSV files for specified experiments.

    Args:
        experiments: List of experiment names to re-export
        base_dir: Base directory containing experiments
    """
    if base_dir is None:
        base_dir = Path("experiment_logs/V10")

    print(f"\n{'='*80}")
    print(f"RE-EXPORTING RESULTS")
    print(f"{'='*80}\n")

    total_exported = 0
    total_failed = 0

    for exp_name in experiments:
        exp_dir = base_dir / exp_name

        if not exp_dir.exists():
            print(f"⊘ {exp_name}: Directory not found")
            continue

        print(f"\n📁 {exp_name}")
        print(f"{'─'*80}")

        # Find all run directories
        run_dirs = sorted(exp_dir.glob("run_*"))

        if not run_dirs:
            print(f"  ⊘ No run directories found")
            continue

        for run_dir in run_dirs:
            run_name = run_dir.name

            try:
                # Re-export using export_experiment_results
                csv_path = export_experiment_results(
                    run_dir=str(run_dir),
                    config_path=str(run_dir / "config.yaml"),
                    output_dir=str(run_dir / "results"),
                    silent=True
                )

                if csv_path:
                    print(f"  ✓ {run_name}: Exported to {Path(csv_path).name}")
                    total_exported += 1
                else:
                    print(f"  ✗ {run_name}: Export failed (no result files)")
                    total_failed += 1

            except Exception as e:
                print(f"  ✗ {run_name}: Error - {str(e)}")
                total_failed += 1

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Successfully exported: {total_exported}")
    print(f"Failed: {total_failed}")
    print(f"{'='*80}\n")

    return total_failed == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Re-export experiment results with fixed export logic'
    )
    parser.add_argument(
        '--experiments',
        nargs='+',
        default=['ascending_clock_apv', 'ascending_clock_apv_closed'],
        help='Experiments to re-export (default: clock auctions)'
    )
    parser.add_argument(
        '--base-dir',
        type=str,
        default='experiment_logs/V10',
        help='Base directory (default: experiment_logs/V10)'
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir)

    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        return 1

    success = re_export_experiments(args.experiments, base_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

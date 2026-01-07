#!/usr/bin/env python3
"""
Script to batch update repetitions in YAML config files.

Rules:
- Clock auctions (seal_clock: "clock"): repetitions = 50
- Sealed bid auctions (seal_clock: "seal"): repetitions = 100
- Special case: Files with "15rounds" in name: repetitions = 10
"""

import yaml
from pathlib import Path
import sys


def update_repetitions(yaml_path: Path) -> bool:
    """
    Update repetitions in a YAML config file.

    Args:
        yaml_path: Path to YAML file

    Returns:
        True if updated, False otherwise
    """
    try:
        # Read YAML file
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        # Determine the new repetition value
        if '15rounds' in yaml_path.name:
            new_reps = 10
            reason = "15rounds file"
        elif config['rule']['seal_clock'] == 'clock':
            new_reps = 50
            reason = "clock auction"
        elif config['rule']['seal_clock'] == 'seal':
            new_reps = 100
            reason = "sealed bid auction"
        else:
            print(f"  ⊘ Unknown seal_clock type: {config['rule']['seal_clock']}")
            return False

        # Get current repetitions
        current_reps = config['execution']['repetitions']

        # Update if different
        if current_reps != new_reps:
            config['execution']['repetitions'] = new_reps

            # Write back to file
            with open(yaml_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            print(f"  ✓ {yaml_path.name}: {current_reps} → {new_reps} ({reason})")
            return True
        else:
            print(f"  ○ {yaml_path.name}: already {new_reps} ({reason})")
            return False

    except Exception as e:
        print(f"  ✗ Error processing {yaml_path.name}: {e}")
        return False


def main():
    """Main function to update all config files."""
    # Define directories
    base_dir = Path(__file__).parent
    experiment_dir = base_dir / "configs" / "experiments"
    robustness_dir = base_dir / "configs" / "robustness"

    print("=" * 80)
    print("UPDATING REPETITIONS IN CONFIG FILES")
    print("=" * 80)
    print("\nRules:")
    print("  - Clock auctions: repetitions = 50")
    print("  - Sealed bid auctions: repetitions = 100")
    print("  - Files with '15rounds': repetitions = 10")
    print("=" * 80)

    # Process experiments directory
    print(f"\n📁 Processing: {experiment_dir}")
    print("-" * 80)
    experiment_files = sorted(experiment_dir.glob("*.yaml"))
    exp_updated = 0
    for yaml_file in experiment_files:
        if update_repetitions(yaml_file):
            exp_updated += 1

    print(f"\n  Summary: {exp_updated}/{len(experiment_files)} files updated")

    # Process robustness directory
    print(f"\n📁 Processing: {robustness_dir}")
    print("-" * 80)
    robustness_files = sorted(robustness_dir.glob("*.yaml"))
    rob_updated = 0
    for yaml_file in robustness_files:
        if update_repetitions(yaml_file):
            rob_updated += 1

    print(f"\n  Summary: {rob_updated}/{len(robustness_files)} files updated")

    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    total_files = len(experiment_files) + len(robustness_files)
    total_updated = exp_updated + rob_updated
    print(f"  Total files processed: {total_files}")
    print(f"  Files updated: {total_updated}")
    print(f"  Files unchanged: {total_files - total_updated}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())

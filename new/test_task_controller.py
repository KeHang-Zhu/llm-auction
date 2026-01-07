"""
Test script for Task Controller

Quick test to verify the task controller functionality.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from task_controller import TaskController, parse_config_list_file


def test_basic_functionality():
    """Test basic task controller functionality."""
    print("=" * 80)
    print("TESTING TASK CONTROLLER")
    print("=" * 80)

    # Test 1: Parse config list file
    print("\n1. Testing config list parsing...")
    try:
        list_file = Path(__file__).parent / "example_experiments.txt"
        if list_file.exists():
            configs = parse_config_list_file(str(list_file))
            print(f"   ✓ Parsed {len(configs)} configs from example file")
        else:
            print(f"   ⊘ Example file not found: {list_file}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Validate configs
    print("\n2. Testing config validation...")
    try:
        # Use a small set of test configs
        test_configs = [
            "configs/experiments/01_01_spsb_ipv.yaml",
            "configs/robustness/01_01_spsb_ipv_gpt5mini.yaml",
            "nonexistent_config.yaml"
        ]

        controller = TaskController(
            config_paths=test_configs,
            max_workers=2,
            check_existing=True,
            force_rerun=False
        )

        valid_configs = controller.validate_configs()
        print(f"   ✓ Validated {len(valid_configs)}/{len(test_configs)} configs")
        print(f"   ✓ Skipped {len(controller.results)} invalid configs")

    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Check experiment status
    print("\n3. Testing experiment status checking...")
    try:
        test_config = "configs/experiments/01_01_spsb_ipv.yaml"
        if Path(test_config).exists():
            controller = TaskController(
                config_paths=[test_config],
                max_workers=1
            )
            status = controller.check_experiment_status(test_config)
            if status:
                print(f"   ✓ Found existing experiment")
                results = status.get('results_summary', {})
                print(f"     Completed: {results.get('completed_runs', 0)}/{results.get('total_runs', 0)}")
            else:
                print(f"   ⊘ No existing experiment found")
        else:
            print(f"   ⊘ Test config not found: {test_config}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nTo run a real batch experiment, use:")
    print('  python new/task_controller.py --configs "configs/robustness/01_01_*.yaml"')
    print("\nFor more examples, see: new/README_task_controller.md")


if __name__ == "__main__":
    test_basic_functionality()

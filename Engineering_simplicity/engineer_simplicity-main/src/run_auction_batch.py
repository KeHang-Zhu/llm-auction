"""
Batch runner for Auction experiments.
Loads YAML configs and runs multiple experiment configurations.

Usage:
    python3 src/run_auction_batch.py configs_auction/interventions_claude/axis1_contingent_baseline.yaml
    python3 src/run_auction_batch.py configs_auction/interventions_claude/*.yaml  # Run all configs in folder
"""

from edsl import Cache
import os
import yaml
import sys
import pandas as pd
import concurrent.futures

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from util_plan import Auction_plan, Rule_plan


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def run_single_experiment(i, config, cache):
    """
    Run a single auction experiment instance.

    Args:
        i: Experiment index
        config: Configuration dictionary
        cache: EDSL Cache instance
    """
    # Extract config values
    number_agents = config['auction']['number_agents']
    rounds = config['auction']['rounds']

    seal_clock = config['rule']['seal_clock']
    ascend_descend = config['rule'].get('ascend_descend', 'ascend')
    price_order = config['rule']['price_order']
    private_value = config['rule']['private_value']
    open_blind = config['rule']['open_blind']
    closing = config['rule'].get('closing', False)
    reserve_price = config['rule'].get('reserve_price', 0)
    special_name = config['rule'].get('special_name', '')

    common_range = config['value']['common_range']
    private_range = config['value']['private_range']
    increment = config['value']['increment']
    seed_base = config['value']['seed_base']

    model = config['llm']['model']
    temperature = config['llm']['temperature']
    service_name = config['llm'].get('service_name', None)

    templates_dir = config['prompt'].get('rule_template_dir', 'rule_template/auctions/')
    output_dir = config['execution']['output_dir']

    # Create rule
    rule = Rule_plan(
        seal_clock=seal_clock,
        price_order=price_order,
        private_value=private_value,
        open_blind=open_blind,
        rounds=rounds,
        turns=20,
        common_range=common_range,
        private_range=private_range,
        increment=increment,
        number_agents=number_agents,
        special_name=special_name,
        closing=closing,
        reserve_price=reserve_price,
        templates_dir=templates_dir
    )

    # Create auction
    timestring = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S-%f")

    auction = Auction_plan(
        number_agents=number_agents,
        rule=rule,
        output_dir=output_dir,
        timestring=timestring,
        cache=cache,
        model=model,
        temperature=temperature,
        service_name=service_name
    )

    # Run experiment
    auction.draw_value(seed=seed_base + i)
    auction.run_repeated()

    # Save cache
    cache.write_jsonl(os.path.join(output_dir, f"raw_output__{timestring}.jsonl"))

    print(f"\n{'='*70}")
    print(f"Experiment {i+1} completed: {config['experiment']['name']}")
    print(f"{'='*70}")


def run_config(config_path):
    """
    Run all experiments for a single config file.

    Args:
        config_path: Path to YAML configuration file
    """
    print(f"\n{'='*70}")
    print(f"Loading configuration: {config_path}")
    print(f"{'='*70}")

    config = load_config(config_path)

    # Print experiment info
    print(f"\nExperiment: {config['experiment']['name']}")
    print(f"Description: {config['experiment']['description']}")
    print(f"Rule: {config['rule']['seal_clock']} / {config['rule']['price_order']} / {config['rule']['private_value']}")
    print(f"Special Template: {config['rule'].get('special_name', 'N/A')}")
    print(f"Repetitions: {config['execution']['repetitions']}")
    print(f"Model: {config['llm']['model']}")
    print(f"Output: {config['execution']['output_dir']}")

    # Create output directory
    os.makedirs(config['execution']['output_dir'], exist_ok=True)

    # Create cache
    cache = Cache()

    # Get execution parameters
    repetitions = config['execution']['repetitions']
    parallel = config['execution']['parallel']
    max_workers = config['execution']['max_workers']

    if parallel:
        print(f"\nRunning {repetitions} experiments in parallel (max_workers={max_workers})...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_single_experiment, i, config, cache)
                for i in range(repetitions)
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in experiment: {e}")
                    import traceback
                    traceback.print_exc()
    else:
        print(f"\nRunning {repetitions} experiments sequentially...")
        for i in range(repetitions):
            try:
                run_single_experiment(i, config, cache)
            except Exception as e:
                print(f"Error in experiment {i}: {e}")
                import traceback
                traceback.print_exc()

    print(f"\n{'='*70}")
    print(f"All experiments completed for: {config['experiment']['name']}")
    print(f"Results saved to: {config['execution']['output_dir']}")
    print(f"{'='*70}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 src/run_auction_batch.py <config_file1.yaml> [config_file2.yaml] ...")
        print("\nExample:")
        print("  python3 src/run_auction_batch.py configs_auction/interventions_claude/axis1_contingent_baseline.yaml")
        print("  python3 src/run_auction_batch.py configs_auction/interventions_gpt4o/*.yaml")
        print("\nAvailable intervention directories:")
        import glob
        dirs = sorted(glob.glob("configs_auction/interventions_*/"))
        for d in dirs:
            configs = glob.glob(f"{d}*.yaml")
            print(f"  - {d} ({len(configs)} configs)")
        sys.exit(1)

    # Get config file paths from command line
    config_paths = sys.argv[1:]

    print(f"\n{'#'*70}")
    print(f"# AUCTION BATCH RUNNER")
    print(f"# Running {len(config_paths)} configuration(s)")
    print(f"{'#'*70}")

    # Run each config
    for config_path in config_paths:
        if not os.path.exists(config_path):
            print(f"\nError: Config file not found: {config_path}")
            continue

        try:
            run_config(config_path)
        except Exception as e:
            print(f"\nError running config {config_path}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'#'*70}")
    print(f"# BATCH COMPLETE")
    print(f"{'#'*70}")

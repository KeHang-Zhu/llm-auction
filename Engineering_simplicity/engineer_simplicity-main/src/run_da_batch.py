"""
Batch runner for DA experiments.
Loads YAML configs and runs multiple experiment configurations.

Usage:
    python3 src/run_da_batch.py configs_da/da_direct_baseline_gpt4o.yaml
    python3 src/run_da_batch.py configs_da/*.yaml  # Run all configs
"""

from edsl import Cache
import os
import yaml
import sys
import concurrent.futures
from util_da import Rule_DA, DA_plan


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def run_single_experiment(i, config, cache):
    """
    Run a single DA experiment instance.

    Args:
        i: Experiment index
        config: Configuration dictionary
        cache: EDSL Cache instance
    """
    # Extract config values
    mechanism_type = config['mechanism']['mechanism_type']
    intervention_type = config['mechanism']['intervention_type']
    special_name = config['mechanism']['special_name']

    number_students = config['da']['number_students']
    number_schools = config['da']['number_schools']

    common_range = config['value']['common_range']
    private_range = config['value']['private_range']
    seed_base = config['value']['seed_base']

    model = config['llm']['model']
    temperature = config['llm']['temperature']
    service_name = config['llm'].get('service_name', None)

    templates_dir = config['prompt']['templates_dir']
    output_dir = config['execution']['output_dir']

    global_ranking_strategy = config['global_ranking']['strategy']

    # Create rule
    rule = Rule_DA(
        mechanism_type=mechanism_type,
        intervention_type=intervention_type,
        special_name=special_name,
        templates_dir=templates_dir,
        common_range=common_range,
        private_range=private_range,
        global_ranking_strategy=global_ranking_strategy
    )

    # Create DA plan (saves to base folder, not run_ subfolder)
    da = DA_plan(
        number_students=number_students,
        number_schools=number_schools,
        rule=rule,
        output_dir=output_dir,
        cache=cache,
        model=model,
        temperature=temperature,
        service_name=service_name,
        config_dict=config,  # Save config to folder (only once)
        experiment_index=i + 1  # For result numbering: result_1, result_2, etc.
    )

    # Run experiment
    da.draw_values(seed=seed_base + i)
    da.build_students()
    da.run()
    da.data_to_json()

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
    print(f"Mechanism: {config['mechanism']['mechanism_type']}")
    print(f"Template: {config['mechanism']['special_name']}")
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
        print("Usage: python3 src/run_da_batch.py <config_file1.yaml> [config_file2.yaml] ...")
        print("\nExample:")
        print("  python3 src/run_da_batch.py configs_da/da_direct_baseline_gpt4o.yaml")
        print("  python3 src/run_da_batch.py configs_da/da_axis3_secondorder_gpt4o.yaml")
        print("\nAvailable configs:")
        import glob
        configs = sorted(glob.glob("configs_da/*.yaml"))
        for config in configs:
            print(f"  - {config}")
        sys.exit(1)

    # Get config file paths from command line
    config_paths = sys.argv[1:]

    print(f"\n{'#'*70}")
    print(f"# DA BATCH RUNNER")
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

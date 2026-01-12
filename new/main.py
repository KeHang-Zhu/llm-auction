"""
Unified experiment orchestrator for LLM auction experiments.

This module provides a command-line interface to run auction experiments
using YAML configuration files. It handles:
- Configuration loading and validation
- Experiment metadata management
- Auction execution (serial or parallel)
- Data and results storage

Usage:
    python new/main.py --config configs/experiments/01_spsb_ipv.yaml
    python new/main.py --config configs/experiments/10_ebay_reserve_0.yaml --parallel
"""

import sys
import argparse
import logging
from pathlib import Path
import concurrent.futures
from typing import Optional, Dict, Any
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edsl import Cache
from experiment.config import ExperimentConfig
from experiment.metadata import MetadataManager
from export_results import export_experiment_results

# Import auction classes
from util_plan import Auction_plan, Rule_plan
from util_ebay import Auction_ebay

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExperimentOrchestrator:
    """
    Orchestrates auction experiments based on YAML configuration.

    Handles the complete workflow:
    1. Load configuration
    2. Set up experiment directories and metadata
    3. Create appropriate auction objects
    4. Run experiments (serial or parallel)
    5. Save results and metadata
    """

    def __init__(self, config_path: str):
        """
        Initialize orchestrator with configuration file.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config = ExperimentConfig.from_yaml(config_path)
        self.metadata_mgr = None
        self.cache = Cache()

        logger.info(f"Loaded configuration: {self.config.experiment_name}")
        logger.info(f"  Version: {self.config.version}")
        logger.info(f"  Mechanism: {self.config.mechanism_type} / {self.config.payment_rule}")
        logger.info(f"  Value model: {self.config.value_model}")
        logger.info(f"  Strategy: {self.config.strategy_type}")

    def setup_experiment(self):
        """
        Set up experiment directories and metadata management.

        Creates:
        - Run directory with timestamp
        - Configuration snapshot
        - Prompt file copies
        """
        logger.info("Setting up experiment directories...")

        # Create metadata manager
        self.metadata_mgr = MetadataManager(
            base_output_dir=self.config.output_dir,
            experiment_name=self.config.experiment_name
        )

        # Create run directory
        self.metadata_mgr.create_run_directory()

        # Save config snapshot
        self.metadata_mgr.save_config_snapshot(self.config.to_dict())

        # Copy prompt files
        prompt_dir = self.config.get('prompt.prompt_dir', 'Prompt/')
        rule_template_dir = self.config.get('prompt.rule_template_dir', 'rule_template/V10/')
        include_payment_example = self.config.get('prompt.include_payment_example', False)
        payment_examples_path = self.config.get('prompt.payment_examples_path')

        self.metadata_mgr.copy_prompt_files(
            prompt_dir=prompt_dir,
            rule_template_dir=rule_template_dir,
            special_name=self.config.special_rule_template,
            include_payment_example=include_payment_example,
            payment_examples_path=payment_examples_path
        )

        logger.info(f"Run directory: {self.metadata_mgr.run_dir}")

    def create_rule(self) -> Rule_plan:
        """
        Create Rule object from configuration.

        Returns:
            Rule_plan object configured according to YAML
        """
        rule_config = self.config.get_section('rule')
        value_config = self.config.get_section('value')
        auction_config = self.config.get_section('auction')
        prompt_config = self.config.get_section('prompt')

        # Handle eBay special parameters
        turns = rule_config.get('turns', 20)
        start_price = rule_config.get('start_price', 0)
        include_payment_example = prompt_config.get('include_payment_example', False)
        payment_example_key = prompt_config.get('payment_example_key')
        payment_examples_path = prompt_config.get('payment_examples_path')

        rule = Rule_plan(
            seal_clock=rule_config['seal_clock'],
            ascend_descend=rule_config.get('ascend_descend', 'ascend'),
            price_order=rule_config['price_order'],
            private_value=rule_config['private_value'],
            open_blind=rule_config['open_blind'],
            rounds=auction_config['rounds'],
            turns=turns,
            common_range=value_config['common_range'],
            private_range=value_config['private_range'],
            increment=value_config['increment'],
            number_agents=auction_config['number_agents'],
            special_name=rule_config.get('special_name', ''),
            start_price=start_price,
            closing=rule_config['closing'],
            reserve_price=rule_config['reserve_price'],
            include_payment_example=include_payment_example,
            payment_example_key=payment_example_key,
            payment_examples_path=payment_examples_path
        )

        return rule

    def create_auction(self, rule: Rule_plan, run_id: int,
                      run_cache: Optional[Cache] = None) -> Any:
        """
        Create appropriate auction object based on strategy type.

        Args:
            rule: Rule_plan object
            run_id: Run identifier (for timestamp)
            run_cache: Optional cache object (if None, uses self.cache)

        Returns:
            Auction object (Auction_plan or Auction_ebay)
        """
        cache = run_cache if run_cache is not None else self.cache

        # Generate timestamp
        timestring = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S-%f")

        # Get output paths
        output_paths = self.metadata_mgr.get_output_paths()
        output_dir = str(output_paths['raw_data'])

        # Select auction class based on strategy type
        strategy_type = self.config.strategy_type
        model = self.config.model_name
        temperature = self.config.temperature
        service_name = getattr(self.config, 'service_name', None)
        num_agents = self.config.num_agents

        if strategy_type == 'ebay':
            # eBay auction
            auction = Auction_ebay(
                number_agents=num_agents,
                rule=rule,
                output_dir=output_dir,
                timestring=timestring,
                cache=cache,
                model=model,
                temperature=temperature
            )
            logger.debug(f"Created Auction_ebay (run {run_id})")

        elif strategy_type == 'plan_reflection':
            # Plan-reflection auction (default)
            auction = Auction_plan(
                number_agents=num_agents,
                rule=rule,
                output_dir=output_dir,
                timestring=timestring,
                cache=cache,
                model=model,
                temperature=temperature,
                service_name=service_name
            )
            logger.debug(f"Created Auction_plan (run {run_id})")

        else:
            # Fallback to plan_reflection for other types
            logger.warning(f"Strategy type '{strategy_type}' not fully implemented, using plan_reflection")
            auction = Auction_plan(
                number_agents=num_agents,
                rule=rule,
                output_dir=output_dir,
                timestring=timestring,
                cache=cache,
                model=model,
                temperature=temperature,
                service_name=service_name
            )

        return auction

    def run_single_experiment(self, run_id: int, run_cache: Optional[Cache] = None) -> Dict[str, Any]:
        """
        Run a single experiment iteration.

        Args:
            run_id: Iteration number (0 to repetitions-1)
            run_cache: Optional separate cache for parallel execution

        Returns:
            Dictionary with run results and metadata
        """
        logger.info(f"Starting experiment run {run_id + 1}/{self.config.repetitions}")

        # Create rule
        rule = self.create_rule()

        # Create auction
        auction = self.create_auction(rule, run_id, run_cache)

        # Draw values with seed
        seed = self.config.seed_base + run_id
        auction.draw_value(seed=seed)
        logger.debug(f"Drew values with seed {seed}")

        # Run auction
        auction.run_repeated()
        logger.info(f"Completed experiment run {run_id + 1}")

        # Get results path
        output_paths = self.metadata_mgr.get_output_paths()

        # Save cache
        cache_to_use = run_cache if run_cache is not None else self.cache
        cache_file = output_paths['raw_data'] / f"raw_output__run{run_id}.jsonl"
        cache_to_use.write_jsonl(str(cache_file))
        logger.debug(f"Saved cache to {cache_file}")

        return {
            'run_id': run_id,
            'seed': seed,
            'cache_file': str(cache_file),
            'status': 'completed'
        }

    def run_experiments_serial(self) -> list[Dict[str, Any]]:
        """
        Run all experiments serially (one after another).

        Returns:
            List of result dictionaries for each run
        """
        logger.info(f"Running {self.config.repetitions} experiments serially...")

        results = []
        for i in range(self.config.repetitions):
            try:
                result = self.run_single_experiment(i)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in run {i}: {e}", exc_info=True)
                results.append({
                    'run_id': i,
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def run_experiments_parallel(self) -> list[Dict[str, Any]]:
        """
        Run experiments in parallel using ThreadPoolExecutor.

        Returns:
            List of result dictionaries for each run
        """
        max_workers = self.config.max_workers
        logger.info(f"Running {self.config.repetitions} experiments in parallel (max_workers={max_workers})...")

        results = []

        # Create separate cache for each worker to avoid conflicts
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            futures = []
            for i in range(self.config.repetitions):
                # Each worker gets its own cache
                worker_cache = Cache()
                future = executor.submit(self.run_single_experiment, i, worker_cache)
                futures.append((i, future))

            # Collect results as they complete
            for run_id, future in futures:
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"✓ Run {run_id + 1} completed")
                except Exception as e:
                    logger.error(f"✗ Run {run_id + 1} failed: {e}")
                    results.append({
                        'run_id': run_id,
                        'status': 'failed',
                        'error': str(e)
                    })

        return results

    def collect_results_summary(self, run_results: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect summary statistics from all runs.

        Args:
            run_results: List of result dictionaries from each run

        Returns:
            Summary dictionary
        """
        completed = sum(1 for r in run_results if r['status'] == 'completed')
        failed = sum(1 for r in run_results if r['status'] == 'failed')

        summary = {
            'total_runs': len(run_results),
            'completed_runs': completed,
            'failed_runs': failed,
            'total_rounds': self.config.num_rounds * completed,
            'expected_llm_calls': self.config.num_rounds * self.config.num_agents * completed,
            'cache_files': [r['cache_file'] for r in run_results if r['status'] == 'completed'],
            'seeds_used': [r['seed'] for r in run_results if r['status'] == 'completed']
        }

        # Add failed runs info if any
        if failed > 0:
            summary['failed_run_ids'] = [r['run_id'] for r in run_results if r['status'] == 'failed']
            summary['errors'] = [r.get('error', 'Unknown error') for r in run_results if r['status'] == 'failed']

        return summary

    def finalize_experiment(self, run_results: list[Dict[str, Any]]):
        """
        Finalize experiment by generating summary and updating index.

        Args:
            run_results: List of result dictionaries from each run
        """
        logger.info("Finalizing experiment...")

        # Collect results summary
        results_summary = self.collect_results_summary(run_results)

        # Execution info
        execution_info = {
            'completed_repetitions': results_summary['completed_runs'],
            'failed_repetitions': results_summary['failed_runs'],
            'parallel_execution': self.config.parallel,
            'max_workers': self.config.max_workers if self.config.parallel else 1
        }

        # Finalize metadata
        summary = self.metadata_mgr.finalize(
            results_summary=results_summary,
            execution_info=execution_info
        )

        logger.info("Experiment finalized!")
        logger.info(f"  Duration: {summary['execution']['duration_seconds']:.2f}s")
        logger.info(f"  Completed: {results_summary['completed_runs']}/{results_summary['total_runs']} runs")

        if results_summary['failed_runs'] > 0:
            logger.warning(f"  Failed: {results_summary['failed_runs']} runs")

        # Auto-export results to CSV
        logger.info("Exporting results to CSV...")
        try:
            # Save CSV in the run directory under results/
            csv_output_dir = str(self.metadata_mgr.run_dir / "results")

            csv_path = export_experiment_results(
                run_dir=str(self.metadata_mgr.run_dir),
                config_path=self.config_path,
                output_dir=csv_output_dir,
                silent=True
            )
            if csv_path:
                logger.info(f"  CSV exported: {csv_path}")
            else:
                logger.warning("  CSV export failed (no result files found)")
        except Exception as e:
            logger.error(f"  CSV export error: {e}", exc_info=True)

    def run(self):
        """
        Run the complete experiment workflow.

        1. Setup experiment directories
        2. Run experiments (serial or parallel)
        3. Finalize and save metadata
        """
        logger.info("=" * 70)
        logger.info(f"Starting Experiment: {self.config.experiment_name}")
        logger.info("=" * 70)

        # Setup
        self.setup_experiment()

        # Run experiments
        if self.config.parallel:
            run_results = self.run_experiments_parallel()
        else:
            run_results = self.run_experiments_serial()

        # Finalize
        self.finalize_experiment(run_results)

        logger.info("=" * 70)
        logger.info(f"Experiment Complete!")
        logger.info(f"Results saved to: {self.metadata_mgr.run_dir}")
        logger.info("=" * 70)


def main():
    """
    Main entry point for command-line interface.
    """
    parser = argparse.ArgumentParser(
        description='Run LLM auction experiments from YAML configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run SPSB IPV experiment
  python new/main.py --config configs/experiments/01_spsb_ipv.yaml

  # Run eBay auction with parallel execution
  python new/main.py --config configs/experiments/10_ebay_reserve_0.yaml --parallel

  # Run intervention study
  python new/main.py --config configs/experiments/18_intervention_menu.yaml
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to YAML configuration file'
    )

    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Override config to enable parallel execution'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        help='Override config max_workers for parallel execution'
    )

    parser.add_argument(
        '--repetitions',
        type=int,
        help='Override config repetitions'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check config file exists
    if not Path(args.config).exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1

    try:
        # Create orchestrator
        orchestrator = ExperimentOrchestrator(args.config)

        # Override config if command-line args provided
        if args.parallel:
            orchestrator.config._config['execution']['parallel'] = True
            logger.info("Overriding config: parallel=True")

        if args.max_workers:
            orchestrator.config._config['execution']['max_workers'] = args.max_workers
            logger.info(f"Overriding config: max_workers={args.max_workers}")

        if args.repetitions:
            orchestrator.config._config['execution']['repetitions'] = args.repetitions
            logger.info(f"Overriding config: repetitions={args.repetitions}")

        # Run experiment
        orchestrator.run()

        return 0

    except Exception as e:
        logger.error(f"Experiment failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

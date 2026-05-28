"""
Task Controller for Batch Experiment Execution

This module provides a controller to run multiple YAML experiment configurations
in parallel, track their success/failure status, and generate comprehensive reports.

Features:
- Execute multiple experiments from a list of YAML configs
- Parallel execution across experiments
- Monitor and validate experiment completion
- Generate detailed success/failure reports

Usage:
    python new/task_controller.py --configs configs/robustness/*.yaml
    python new/task_controller.py --config-list experiments.txt --max-workers 4
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import concurrent.futures

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from experiment.config import ExperimentConfig

# Import ExperimentOrchestrator from new/main.py
try:
    from main import ExperimentOrchestrator
except ImportError:
    # Try importing from new directory
    from new.main import ExperimentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a single experiment task."""
    config_path: str
    experiment_name: str
    status: str  # 'success', 'failed', 'skipped'
    output_dir: Optional[str] = None
    run_dir: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    completed_repetitions: int = 0
    failed_repetitions: int = 0
    total_repetitions: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BatchReport:
    """Summary report for a batch of experiments."""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    skipped_tasks: int
    start_time: str
    end_time: str
    total_duration_seconds: float
    task_results: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def print_summary(self):
        """Print human-readable summary."""
        print("\n" + "=" * 80)
        print("BATCH EXECUTION REPORT")
        print("=" * 80)
        print(f"Total Tasks:      {self.total_tasks}")
        print(f"✓ Successful:     {self.successful_tasks}")
        print(f"✗ Failed:         {self.failed_tasks}")
        print(f"⊘ Skipped:        {self.skipped_tasks}")
        print(f"Duration:         {self.total_duration_seconds:.2f}s ({self.total_duration_seconds/60:.2f}m)")
        print("=" * 80)

        if self.successful_tasks > 0:
            print("\n✓ SUCCESSFUL TASKS:")
            for result in self.task_results:
                if result['status'] == 'success':
                    print(f"  - {result['experiment_name']}")
                    print(f"    Config: {result['config_path']}")
                    print(f"    Output: {result['run_dir']}")
                    print(f"    Repetitions: {result['completed_repetitions']}/{result['total_repetitions']}")
                    print(f"    Duration: {result['duration_seconds']:.2f}s")

        if self.failed_tasks > 0:
            print("\n✗ FAILED TASKS:")
            for result in self.task_results:
                if result['status'] == 'failed':
                    print(f"  - {result['experiment_name']}")
                    print(f"    Config: {result['config_path']}")
                    print(f"    Error: {result['error_message']}")

        if self.skipped_tasks > 0:
            print("\n⊘ SKIPPED TASKS:")
            for result in self.task_results:
                if result['status'] == 'skipped':
                    print(f"  - {result['experiment_name']}")
                    print(f"    Config: {result['config_path']}")
                    print(f"    Reason: {result['error_message']}")

        print("\n" + "=" * 80)


class TaskController:
    """
    Controller for running batch experiments.

    Manages execution of multiple experiment configurations, monitors their
    completion status, and generates comprehensive reports.
    """

    def __init__(self,
                 config_paths: List[str],
                 max_workers: int = 4,
                 repetitions_override: Optional[int] = None,
                 check_existing: bool = True,
                 force_rerun: bool = False):
        """
        Initialize task controller.

        Args:
            config_paths: List of YAML config file paths
            max_workers: Maximum parallel workers for batch execution
            repetitions_override: Override repetitions for all experiments
            check_existing: Check if experiments already completed successfully
            force_rerun: Force rerun even if experiments exist
        """
        self.config_paths = config_paths
        self.max_workers = max_workers
        self.repetitions_override = repetitions_override
        self.check_existing = check_existing and not force_rerun
        self.force_rerun = force_rerun

        self.results: List[TaskResult] = []
        self.start_time = None
        self.end_time = None

        logger.info(f"Initialized TaskController with {len(config_paths)} tasks")
        logger.info(f"  Max workers: {max_workers}")
        logger.info(f"  Check existing: {self.check_existing}")
        logger.info(f"  Force rerun: {force_rerun}")

    def validate_configs(self) -> List[str]:
        """
        Validate that all config files exist and are readable.

        Returns:
            List of valid config paths
        """
        valid_configs = []

        for config_path in self.config_paths:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Config file not found: {config_path}")
                self.results.append(TaskResult(
                    config_path=config_path,
                    experiment_name="unknown",
                    status="skipped",
                    error_message="Config file not found"
                ))
            elif not path.is_file():
                logger.warning(f"Not a file: {config_path}")
                self.results.append(TaskResult(
                    config_path=config_path,
                    experiment_name="unknown",
                    status="skipped",
                    error_message="Not a file"
                ))
            else:
                try:
                    # Try to load config to validate
                    ExperimentConfig.from_yaml(config_path)
                    valid_configs.append(config_path)
                except Exception as e:
                    logger.error(f"Invalid config {config_path}: {e}")
                    self.results.append(TaskResult(
                        config_path=config_path,
                        experiment_name="unknown",
                        status="skipped",
                        error_message=f"Invalid config: {str(e)}"
                    ))

        logger.info(f"Validated {len(valid_configs)}/{len(self.config_paths)} configs")
        return valid_configs

    def check_experiment_status(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Check if an experiment has already been completed successfully.

        Args:
            config_path: Path to experiment config

        Returns:
            Experiment summary if completed, None otherwise
        """
        try:
            config = ExperimentConfig.from_yaml(config_path)
            output_dir = Path(config.output_dir)
            experiment_name = config.experiment_name

            # Look for successful runs in the output directory
            if not output_dir.exists():
                return None

            # Find the most recent run directory
            run_dirs = sorted(output_dir.glob("run_*"), key=lambda x: x.name, reverse=True)

            for run_dir in run_dirs:
                summary_file = run_dir / "experiment_summary.json"
                if summary_file.exists():
                    with open(summary_file, 'r') as f:
                        summary = json.load(f)

                    # Check if experiment completed successfully
                    results = summary.get('results_summary', {})
                    completed = results.get('completed_runs', 0)
                    failed = results.get('failed_runs', 0)
                    total = results.get('total_runs', 0)

                    # Check if we need the same number of repetitions
                    expected_reps = self.repetitions_override or config.repetitions

                    if completed == total == expected_reps and failed == 0:
                        logger.info(f"✓ Found completed experiment: {experiment_name}")
                        logger.info(f"  Run: {run_dir}")
                        return summary

            return None

        except Exception as e:
            logger.debug(f"Error checking experiment status for {config_path}: {e}")
            return None

    def run_single_task(self, config_path: str) -> TaskResult:
        """
        Run a single experiment task.

        Args:
            config_path: Path to YAML config

        Returns:
            TaskResult with execution details
        """
        start_time = datetime.now()

        try:
            # Load config to get experiment name
            config = ExperimentConfig.from_yaml(config_path)
            experiment_name = config.experiment_name

            # Check if already completed
            if self.check_existing:
                existing_summary = self.check_experiment_status(config_path)
                if existing_summary:
                    results = existing_summary.get('results_summary', {})
                    execution = existing_summary.get('execution', {})

                    return TaskResult(
                        config_path=config_path,
                        experiment_name=experiment_name,
                        status="skipped",
                        output_dir=str(Path(config.output_dir)),
                        run_dir=existing_summary.get('run_id'),
                        start_time=execution.get('start_time'),
                        end_time=execution.get('end_time'),
                        duration_seconds=execution.get('duration_seconds'),
                        completed_repetitions=results.get('completed_runs', 0),
                        failed_repetitions=results.get('failed_runs', 0),
                        total_repetitions=results.get('total_runs', 0),
                        error_message="Already completed (skipped)"
                    )

            logger.info(f"Starting experiment: {experiment_name}")
            logger.info(f"  Config: {config_path}")

            # Create orchestrator
            orchestrator = ExperimentOrchestrator(config_path)

            # Override repetitions if specified
            if self.repetitions_override:
                orchestrator.config._config['execution']['repetitions'] = self.repetitions_override
                logger.info(f"  Overriding repetitions: {self.repetitions_override}")

            # Run experiment
            orchestrator.run()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Get results from the orchestrator
            output_dir = str(orchestrator.metadata_mgr.run_dir.parent)
            run_dir = str(orchestrator.metadata_mgr.run_dir)

            # Load summary to get accurate counts
            summary_file = orchestrator.metadata_mgr.run_dir / "experiment_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                results = summary.get('results_summary', {})
                completed_reps = results.get('completed_runs', 0)
                failed_reps = results.get('failed_runs', 0)
                total_reps = results.get('total_runs', 0)
            else:
                completed_reps = 0
                failed_reps = 0
                total_reps = orchestrator.config.repetitions

            # Determine status
            if failed_reps == 0 and completed_reps == total_reps:
                status = "success"
            elif completed_reps > 0:
                status = "partial"
            else:
                status = "failed"

            return TaskResult(
                config_path=config_path,
                experiment_name=experiment_name,
                status=status,
                output_dir=output_dir,
                run_dir=run_dir,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                completed_repetitions=completed_reps,
                failed_repetitions=failed_reps,
                total_repetitions=total_reps,
                error_message=None if status == "success" else f"{failed_reps} repetitions failed"
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Task failed: {config_path}")
            logger.error(f"  Error: {str(e)}", exc_info=True)

            # Try to get experiment name
            try:
                config = ExperimentConfig.from_yaml(config_path)
                experiment_name = config.experiment_name
            except:
                experiment_name = Path(config_path).stem

            return TaskResult(
                config_path=config_path,
                experiment_name=experiment_name,
                status="failed",
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                error_message=str(e)
            )

    def run_batch(self) -> BatchReport:
        """
        Run all experiments in batch mode.

        Returns:
            BatchReport with summary statistics
        """
        self.start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("STARTING BATCH EXECUTION")
        logger.info("=" * 80)

        # Validate configs
        valid_configs = self.validate_configs()

        if not valid_configs:
            logger.error("No valid configs to run!")
            self.end_time = datetime.now()
            return self._generate_report()

        # Run experiments in parallel
        logger.info(f"Running {len(valid_configs)} experiments with max_workers={self.max_workers}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_config = {
                executor.submit(self.run_single_task, config_path): config_path
                for config_path in valid_configs
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_config):
                config_path = future_to_config[future]
                try:
                    result = future.result()
                    self.results.append(result)

                    if result.status == "success":
                        logger.info(f"✓ Task completed: {result.experiment_name}")
                    elif result.status == "skipped":
                        logger.info(f"⊘ Task skipped: {result.experiment_name}")
                    else:
                        logger.error(f"✗ Task failed: {result.experiment_name}")

                except Exception as e:
                    logger.error(f"Unexpected error for {config_path}: {e}")
                    self.results.append(TaskResult(
                        config_path=config_path,
                        experiment_name=Path(config_path).stem,
                        status="failed",
                        error_message=f"Unexpected error: {str(e)}"
                    ))

        self.end_time = datetime.now()

        # Generate and return report
        return self._generate_report()

    def _generate_report(self) -> BatchReport:
        """
        Generate batch execution report.

        Returns:
            BatchReport with summary statistics
        """
        total_duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0

        # Count statuses (treat 'partial' as 'failed')
        successful = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status in ["failed", "partial"])
        skipped = sum(1 for r in self.results if r.status == "skipped")

        report = BatchReport(
            total_tasks=len(self.results),
            successful_tasks=successful,
            failed_tasks=failed,
            skipped_tasks=skipped,
            start_time=self.start_time.isoformat() if self.start_time else "",
            end_time=self.end_time.isoformat() if self.end_time else "",
            total_duration_seconds=total_duration,
            task_results=[r.to_dict() for r in self.results]
        )

        return report

    def save_report(self, output_path: str):
        """
        Save batch report to JSON file.

        Args:
            output_path: Path to save report
        """
        report = self._generate_report()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Report saved to: {output_path}")


def parse_config_list_file(file_path: str) -> List[str]:
    """
    Parse a text file containing list of config paths (one per line).

    Args:
        file_path: Path to text file

    Returns:
        List of config paths
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Filter out empty lines and comments
    configs = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith('#')
    ]

    return configs


def main():
    """Main entry point for command-line interface."""
    parser = argparse.ArgumentParser(
        description='Batch experiment task controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run multiple experiments from glob pattern
  python new/task_controller.py --configs "configs/robustness/01_*.yaml"

  # Run from config list file
  python new/task_controller.py --config-list experiments.txt --max-workers 4

  # Force rerun all experiments
  python new/task_controller.py --configs "configs/experiments/*.yaml" --force-rerun

  # Override repetitions for all experiments
  python new/task_controller.py --configs "configs/robustness/*.yaml" --repetitions 10
        """
    )

    # Config specification (mutually exclusive)
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument(
        '--configs',
        nargs='+',
        help='List of YAML config paths (supports wildcards)'
    )
    config_group.add_argument(
        '--config-list',
        type=str,
        help='Path to text file with list of config paths (one per line)'
    )

    # Execution options
    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='Maximum parallel workers for batch execution (default: 4)'
    )

    parser.add_argument(
        '--repetitions',
        type=int,
        help='Override repetitions for all experiments'
    )

    parser.add_argument(
        '--force-rerun',
        action='store_true',
        help='Force rerun even if experiments already completed'
    )

    parser.add_argument(
        '--no-check-existing',
        action='store_true',
        help='Do not check for existing completed experiments'
    )

    # Output options
    parser.add_argument(
        '--report-output',
        type=str,
        default='batch_report.json',
        help='Path to save batch report JSON (default: batch_report.json)'
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

    # Parse config paths
    if args.configs:
        # Expand wildcards in config paths
        from glob import glob
        config_paths = []
        for pattern in args.configs:
            expanded = glob(pattern)
            if expanded:
                config_paths.extend(expanded)
            else:
                # Not a pattern, use as-is
                config_paths.append(pattern)
    else:
        # Load from file
        config_paths = parse_config_list_file(args.config_list)

    if not config_paths:
        logger.error("No config files specified!")
        return 1

    logger.info(f"Found {len(config_paths)} config files to process")

    try:
        # Create controller
        controller = TaskController(
            config_paths=config_paths,
            max_workers=args.max_workers,
            repetitions_override=args.repetitions,
            check_existing=not args.no_check_existing,
            force_rerun=args.force_rerun
        )

        # Run batch
        report = controller.run_batch()

        # Print summary
        report.print_summary()

        # Save report
        controller.save_report(args.report_output)

        # Exit with appropriate code
        if report.failed_tasks > 0:
            logger.warning(f"Batch completed with {report.failed_tasks} failures")
            return 1
        else:
            logger.info("Batch completed successfully!")
            return 0

    except Exception as e:
        logger.error(f"Batch execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

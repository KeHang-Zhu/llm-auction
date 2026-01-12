"""
Metadata management for LLM auction experiments.

This module handles:
- Creating experiment run directories
- Saving configuration snapshots
- Copying prompt files used in experiments
- Recording git commit information
- Generating experiment summary JSON
- Maintaining experiment index
"""

import json
import yaml
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class MetadataManager:
    """
    Manages experiment metadata and output directory structure.

    Creates organized directory structures for experiment runs,
    saves configuration snapshots, and maintains experiment metadata.
    """

    def __init__(self, base_output_dir: str, experiment_name: str):
        """
        Initialize metadata manager.

        Args:
            base_output_dir: Base directory for experiment outputs
            experiment_name: Name of the experiment
        """
        self.base_output_dir = Path(base_output_dir)
        self.experiment_name = experiment_name
        self.run_dir = None
        self.run_id = None
        self.start_time = None
        self.end_time = None

    def create_run_directory(self) -> Path:
        """
        Create directory for this experiment run.

        Creates structure:
        experiment_logs/{experiment_name}/run_{timestamp}/

        Returns:
            Path to the created run directory
        """
        # Generate run ID with timestamp (microsecond precision)
        timestamp = datetime.now()
        self.start_time = timestamp
        self.run_id = timestamp.strftime("%Y-%m-%d_%H-%M-%S-%f")

        # Create run directory
        self.run_dir = self.base_output_dir / f"run_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.run_dir / "prompts").mkdir(exist_ok=True)
        (self.run_dir / "raw_data").mkdir(exist_ok=True)
        (self.run_dir / "results").mkdir(exist_ok=True)

        logger.info(f"Created run directory: {self.run_dir}")

        return self.run_dir

    def save_config_snapshot(self, config_dict: Dict[str, Any]) -> Path:
        """
        Save configuration snapshot to run directory.

        Args:
            config_dict: Configuration dictionary to save

        Returns:
            Path to saved config file
        """
        if self.run_dir is None:
            raise RuntimeError("Run directory not created. Call create_run_directory() first.")

        config_file = self.run_dir / "config.yaml"

        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved config snapshot: {config_file}")

        return config_file

    def copy_prompt_files(self, prompt_dir: str, rule_template_dir: str,
                         special_name: Optional[str] = None,
                         include_payment_example: bool = False,
                         payment_examples_path: Optional[str] = None) -> List[str]:
        """
        Copy prompt files used in experiment to run directory.

        Args:
            prompt_dir: Directory containing prompt files
            rule_template_dir: Directory containing rule templates
            special_name: Special rule template filename (optional)

        Returns:
            List of copied file paths (relative to run_dir)
        """
        if self.run_dir is None:
            raise RuntimeError("Run directory not created. Call create_run_directory() first.")

        prompts_dest = self.run_dir / "prompts"
        copied_files = []

        # Copy main prompt files (ONLY actively used files)
        prompt_dir = Path(prompt_dir)
        prompt_files = [
            'instruction.txt',
            'persona.txt',
            'unified_sealed_bid.txt',
            'unified_clock.txt'
        ]

        for filename in prompt_files:
            src = prompt_dir / filename
            if src.exists():
                dest = prompts_dest / filename
                shutil.copy2(src, dest)
                copied_files.append(f"prompts/{filename}")
                logger.debug(f"Copied prompt file: {filename}")

        # Copy rule template
        rule_template_dir = Path(rule_template_dir)
        (prompts_dest / "rule_template").mkdir(exist_ok=True)

        if special_name:
            src = rule_template_dir / special_name
            if src.exists():
                dest = prompts_dest / "rule_template" / special_name
                shutil.copy2(src, dest)
                copied_files.append(f"prompts/rule_template/{special_name}")
                logger.info(f"Copied rule template: {special_name}")
            else:
                logger.warning(f"Rule template not found: {src}")

        # Copy payment examples (optional)
        if include_payment_example:
            examples_path = Path(payment_examples_path) if payment_examples_path else (prompt_dir / "payment_examples.yaml")
            if examples_path.exists():
                dest = prompts_dest / "payment_examples.yaml"
                shutil.copy2(examples_path, dest)
                copied_files.append("prompts/payment_examples.yaml")
                logger.debug("Copied payment examples file")
            else:
                logger.warning(f"Payment examples file not found: {examples_path}")

        return copied_files

    def record_git_commit(self) -> Optional[str]:
        """
        Get current git commit hash.

        Returns:
            Git commit hash (short), or None if not a git repo
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = result.stdout.strip()
            logger.info(f"Git commit: {commit_hash}")
            return commit_hash
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not retrieve git commit hash")
            return None

    def generate_experiment_summary(self,
                                    config_dict: Dict[str, Any],
                                    prompt_files: List[str],
                                    results_summary: Optional[Dict[str, Any]] = None,
                                    execution_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate experiment summary metadata.

        Args:
            config_dict: Configuration dictionary
            prompt_files: List of prompt files used
            results_summary: Optional summary of results
            execution_info: Optional execution information

        Returns:
            Experiment summary dictionary
        """
        if self.run_dir is None:
            raise RuntimeError("Run directory not created. Call create_run_directory() first.")

        # Record end time if not already set
        if self.end_time is None:
            self.end_time = datetime.now()

        # Calculate duration
        duration = (self.end_time - self.start_time).total_seconds()

        # Get git commit
        git_commit = self.record_git_commit()

        # Build summary
        summary = {
            "experiment_name": self.experiment_name,
            "run_id": self.run_id,
            "version": config_dict.get('experiment', {}).get('version', 'unknown'),
            "timestamp": self.run_id,
            "git_commit": git_commit,
            "config_snapshot": config_dict,
            "prompt_files_used": prompt_files,
            "execution": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": duration,
                "repetitions": config_dict.get('execution', {}).get('repetitions', 0),
                "parallel": config_dict.get('execution', {}).get('parallel', False)
            },
            "output_files": {
                "config": "config.yaml",
                "prompts": "prompts/",
                "raw_data": "raw_data/",
                "results": "results/"
            }
        }

        # Add execution info if provided
        if execution_info:
            summary["execution"].update(execution_info)

        # Add results summary if provided
        if results_summary:
            summary["results_summary"] = results_summary

        # Save summary to file
        summary_file = self.run_dir / "experiment_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Generated experiment summary: {summary_file}")

        return summary

    def update_experiments_index(self, summary: Dict[str, Any]) -> Path:
        """
        Update experiment index file with this run's metadata.

        Args:
            summary: Experiment summary dictionary

        Returns:
            Path to experiments index file
        """
        index_file = self.base_output_dir / "experiments_index.json"

        # Load existing index or create new one
        if index_file.exists():
            with open(index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {"experiments": []}

        # Create index entry
        entry = {
            "name": self.experiment_name,
            "run_id": self.run_id,
            "timestamp": summary['execution']['start_time'],
            "duration": summary['execution']['duration_seconds'],
            "status": "completed",
            "output_dir": str(self.run_dir.relative_to(self.base_output_dir.parent))
        }

        # Add config hash for tracking
        config_str = json.dumps(summary['config_snapshot'], sort_keys=True)
        import hashlib
        entry["config_hash"] = hashlib.md5(config_str.encode()).hexdigest()[:8]

        # Append to index
        index["experiments"].append(entry)

        # Save updated index
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        logger.info(f"Updated experiments index: {index_file}")

        return index_file

    def save_execution_log(self, log_entries: List[str]):
        """
        Save execution log to run directory.

        Args:
            log_entries: List of log message strings
        """
        if self.run_dir is None:
            raise RuntimeError("Run directory not created. Call create_run_directory() first.")

        log_file = self.run_dir / "experiment.log"

        with open(log_file, 'w') as f:
            f.write('\n'.join(log_entries))

        logger.info(f"Saved execution log: {log_file}")

    def get_output_paths(self) -> Dict[str, Path]:
        """
        Get paths to output directories and files.

        Returns:
            Dictionary mapping output types to their paths
        """
        if self.run_dir is None:
            raise RuntimeError("Run directory not created. Call create_run_directory() first.")

        return {
            "run_dir": self.run_dir,
            "config": self.run_dir / "config.yaml",
            "prompts": self.run_dir / "prompts",
            "raw_data": self.run_dir / "raw_data",
            "results": self.run_dir / "results",
            "summary": self.run_dir / "experiment_summary.json",
            "log": self.run_dir / "experiment.log"
        }

    def finalize(self, results_summary: Optional[Dict[str, Any]] = None,
                execution_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Finalize experiment metadata.

        Generates summary, updates index, and returns summary dictionary.

        Args:
            results_summary: Optional results summary
            execution_info: Optional execution information

        Returns:
            Complete experiment summary
        """
        # Record end time
        self.end_time = datetime.now()

        # Load config from saved snapshot
        config_file = self.run_dir / "config.yaml"
        with open(config_file, 'r') as f:
            config_dict = yaml.safe_load(f)

        # Get prompt files from prompts directory
        prompts_dir = self.run_dir / "prompts"
        prompt_files = [
            str(p.relative_to(self.run_dir))
            for p in prompts_dir.rglob("*.txt")
        ]

        # Generate summary
        summary = self.generate_experiment_summary(
            config_dict=config_dict,
            prompt_files=prompt_files,
            results_summary=results_summary,
            execution_info=execution_info
        )

        # Update index
        self.update_experiments_index(summary)

        logger.info(f"Finalized experiment metadata for {self.experiment_name}")

        return summary


def create_experiment_run(config_dict: Dict[str, Any],
                         base_output_dir: Optional[str] = None) -> MetadataManager:
    """
    Create a new experiment run with metadata management.

    Convenience function that creates MetadataManager, sets up directories,
    and saves configuration snapshot.

    Args:
        config_dict: Configuration dictionary
        base_output_dir: Optional base output directory (from config if not provided)

    Returns:
        MetadataManager instance ready for use
    """
    # Get experiment name and output dir from config
    experiment_name = config_dict.get('experiment', {}).get('name', 'unnamed_experiment')

    if base_output_dir is None:
        base_output_dir = config_dict.get('execution', {}).get('output_dir', 'experiment_logs')

    # Create metadata manager
    metadata_mgr = MetadataManager(base_output_dir, experiment_name)

    # Create run directory
    metadata_mgr.create_run_directory()

    # Save config snapshot
    metadata_mgr.save_config_snapshot(config_dict)

    # Copy prompt files
    prompt_config = config_dict.get('prompt', {})
    rule_config = config_dict.get('rule', {})

    prompt_files = metadata_mgr.copy_prompt_files(
        prompt_dir=prompt_config.get('prompt_dir', 'Prompt/'),
        rule_template_dir=prompt_config.get('rule_template_dir', 'rule_template/V10/'),
        special_name=rule_config.get('special_name'),
        include_payment_example=prompt_config.get('include_payment_example', False),
        payment_examples_path=prompt_config.get('payment_examples_path')
    )

    logger.info(f"Experiment run created: {metadata_mgr.run_dir}")

    return metadata_mgr

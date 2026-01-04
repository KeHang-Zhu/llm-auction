"""
Configuration loading and validation for LLM auction experiments.

This module provides functionality to load YAML configuration files
and validate their structure for auction experiments.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ExperimentConfig:
    """
    Experiment configuration container.

    Loads and validates YAML configuration files for auction experiments.
    Provides easy access to all configuration parameters.
    """

    # Required top-level sections
    REQUIRED_SECTIONS = ['experiment', 'auction', 'rule', 'value', 'llm', 'prompt', 'execution']

    # Required parameters in each section
    REQUIRED_PARAMS = {
        'experiment': ['name', 'version', 'description'],
        'auction': ['number_agents', 'rounds'],
        'rule': ['seal_clock', 'price_order', 'private_value', 'open_blind', 'closing', 'reserve_price'],
        'value': ['common_range', 'private_range', 'increment', 'seed_base'],
        'llm': ['model', 'temperature'],
        'prompt': ['strategy_type', 'prompt_dir', 'rule_template_dir'],
        'execution': ['repetitions', 'parallel', 'max_workers', 'output_dir']
    }

    def __init__(self, config_dict: Dict[str, Any], config_path: Optional[str] = None):
        """
        Initialize configuration from dictionary.

        Args:
            config_dict: Configuration dictionary loaded from YAML
            config_path: Optional path to the config file (for reference)
        """
        self.config_path = config_path
        self._config = config_dict
        self._validate()

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'ExperimentConfig':
        """
        Load configuration from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            ExperimentConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigurationError: If config is invalid
        """
        yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        logger.info(f"Loading configuration from {yaml_path}")

        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        return cls(config_dict, str(yaml_path))

    def _validate(self):
        """
        Validate configuration structure and parameters.

        Raises:
            ConfigurationError: If validation fails
        """
        # Check required sections
        for section in self.REQUIRED_SECTIONS:
            if section not in self._config:
                raise ConfigurationError(f"Missing required section: {section}")

        # Check required parameters in each section
        for section, params in self.REQUIRED_PARAMS.items():
            for param in params:
                if param not in self._config[section]:
                    raise ConfigurationError(
                        f"Missing required parameter '{param}' in section '{section}'"
                    )

        # Validate specific parameter values
        self._validate_auction_params()
        self._validate_rule_params()
        self._validate_value_params()
        self._validate_llm_params()
        self._validate_prompt_params()
        self._validate_execution_params()

        logger.info("Configuration validation successful")

    def _validate_auction_params(self):
        """Validate auction parameters."""
        num_agents = self._config['auction']['number_agents']
        if not isinstance(num_agents, int) or num_agents < 2:
            raise ConfigurationError("number_agents must be an integer >= 2")

        rounds = self._config['auction']['rounds']
        if not isinstance(rounds, int) or rounds < 1:
            raise ConfigurationError("rounds must be an integer >= 1")

    def _validate_rule_params(self):
        """Validate rule parameters."""
        rule = self._config['rule']

        # Validate seal_clock
        if rule['seal_clock'] not in ['seal', 'clock']:
            raise ConfigurationError("seal_clock must be 'seal' or 'clock'")

        # Validate price_order
        if rule['price_order'] not in ['first', 'second', 'third', 'allpay']:
            raise ConfigurationError("price_order must be 'first', 'second', 'third', or 'allpay'")

        # Validate private_value
        if rule['private_value'] not in ['private', 'affiliated', 'common']:
            raise ConfigurationError("private_value must be 'private', 'affiliated', or 'common'")

        # Validate open_blind
        if rule['open_blind'] not in ['open', 'blind']:
            raise ConfigurationError("open_blind must be 'open' or 'blind'")

        # Validate closing
        if not isinstance(rule['closing'], bool):
            raise ConfigurationError("closing must be a boolean")

        # Validate reserve_price
        if not isinstance(rule['reserve_price'], (int, float)) or rule['reserve_price'] < 0:
            raise ConfigurationError("reserve_price must be a non-negative number")

    def _validate_value_params(self):
        """Validate value generation parameters."""
        value = self._config['value']

        # Validate common_range
        if not isinstance(value['common_range'], list) or len(value['common_range']) != 2:
            raise ConfigurationError("common_range must be a list of [min, max]")
        if value['common_range'][0] >= value['common_range'][1]:
            raise ConfigurationError("common_range min must be less than max")

        # Validate private_range
        if not isinstance(value['private_range'], (int, float)) or value['private_range'] <= 0:
            raise ConfigurationError("private_range must be a positive number")

        # Validate increment
        if not isinstance(value['increment'], (int, float)) or value['increment'] <= 0:
            raise ConfigurationError("increment must be a positive number")

        # Validate seed_base
        if not isinstance(value['seed_base'], int):
            raise ConfigurationError("seed_base must be an integer")

    def _validate_llm_params(self):
        """Validate LLM parameters."""
        llm = self._config['llm']

        # Validate model
        valid_models = ['gpt-4o', 'gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo']
        if llm['model'] not in valid_models:
            logger.warning(f"Model '{llm['model']}' not in known models: {valid_models}")

        # Validate temperature
        if not isinstance(llm['temperature'], (int, float)) or not 0 <= llm['temperature'] <= 2:
            raise ConfigurationError("temperature must be a number between 0 and 2")

    def _validate_prompt_params(self):
        """Validate prompt parameters."""
        prompt = self._config['prompt']

        # Validate strategy_type
        valid_strategies = ['plan_reflection', 'direct', 'ebay', 'json']
        if prompt['strategy_type'] not in valid_strategies:
            raise ConfigurationError(f"strategy_type must be one of {valid_strategies}")

        # Check if directories exist (warning only)
        if not Path(prompt['prompt_dir']).exists():
            logger.warning(f"Prompt directory not found: {prompt['prompt_dir']}")

        if not Path(prompt['rule_template_dir']).exists():
            logger.warning(f"Rule template directory not found: {prompt['rule_template_dir']}")

    def _validate_execution_params(self):
        """Validate execution parameters."""
        execution = self._config['execution']

        # Validate repetitions
        if not isinstance(execution['repetitions'], int) or execution['repetitions'] < 1:
            raise ConfigurationError("repetitions must be an integer >= 1")

        # Validate parallel
        if not isinstance(execution['parallel'], bool):
            raise ConfigurationError("parallel must be a boolean")

        # Validate max_workers
        if not isinstance(execution['max_workers'], int) or execution['max_workers'] < 1:
            raise ConfigurationError("max_workers must be an integer >= 1")

        # output_dir is allowed to be any string

    # Convenient property accessors

    @property
    def experiment_name(self) -> str:
        """Get experiment name."""
        return self._config['experiment']['name']

    @property
    def version(self) -> str:
        """Get experiment version."""
        return self._config['experiment']['version']

    @property
    def description(self) -> str:
        """Get experiment description."""
        return self._config['experiment']['description']

    @property
    def num_agents(self) -> int:
        """Get number of agents."""
        return self._config['auction']['number_agents']

    @property
    def num_rounds(self) -> int:
        """Get number of rounds."""
        return self._config['auction']['rounds']

    @property
    def mechanism_type(self) -> str:
        """Get mechanism type (seal/clock)."""
        return self._config['rule']['seal_clock']

    @property
    def payment_rule(self) -> str:
        """Get payment rule (first/second/third/allpay)."""
        return self._config['rule']['price_order']

    @property
    def value_model(self) -> str:
        """Get value model (private/affiliated/common)."""
        return self._config['rule']['private_value']

    @property
    def information_type(self) -> str:
        """Get information type (open/blind)."""
        return self._config['rule']['open_blind']

    @property
    def has_soft_closing(self) -> bool:
        """Check if soft closing rule is enabled."""
        return self._config['rule']['closing']

    @property
    def reserve_price(self) -> float:
        """Get reserve price."""
        return self._config['rule']['reserve_price']

    @property
    def special_rule_template(self) -> Optional[str]:
        """Get special rule template name if specified."""
        return self._config['rule'].get('special_name')

    @property
    def seed_base(self) -> int:
        """Get base random seed."""
        return self._config['value']['seed_base']

    @property
    def repetitions(self) -> int:
        """Get number of experiment repetitions."""
        return self._config['execution']['repetitions']

    @property
    def parallel(self) -> bool:
        """Check if parallel execution is enabled."""
        return self._config['execution']['parallel']

    @property
    def max_workers(self) -> int:
        """Get maximum number of parallel workers."""
        return self._config['execution']['max_workers']

    @property
    def output_dir(self) -> str:
        """Get output directory path."""
        return self._config['execution']['output_dir']

    @property
    def model_name(self) -> str:
        """Get LLM model name."""
        return self._config['llm']['model']

    @property
    def temperature(self) -> float:
        """Get LLM temperature."""
        return self._config['llm']['temperature']

    @property
    def service_name(self) -> Optional[str]:
        """Get LLM service name (optional, for models like Gemini)."""
        return self._config['llm'].get('service_name', None)

    @property
    def strategy_type(self) -> str:
        """Get prompt strategy type."""
        return self._config['prompt']['strategy_type']

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Section name (e.g., 'auction', 'rule')

        Returns:
            Dictionary containing section configuration
        """
        return self._config.get(section, {})

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key path.

        Args:
            key: Dot-separated key path (e.g., 'auction.number_agents')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"ExperimentConfig(name='{self.experiment_name}', version='{self.version}')"


def load_config(config_path: str) -> ExperimentConfig:
    """
    Load experiment configuration from YAML file.

    Convenience function that wraps ExperimentConfig.from_yaml().

    Args:
        config_path: Path to YAML configuration file

    Returns:
        ExperimentConfig instance
    """
    return ExperimentConfig.from_yaml(config_path)


def validate_all_configs(config_dir: str = "configs/experiments") -> Dict[str, bool]:
    """
    Validate all configuration files in a directory.

    Args:
        config_dir: Directory containing YAML config files

    Returns:
        Dictionary mapping filenames to validation success (True/False)
    """
    config_dir = Path(config_dir)
    results = {}

    for config_file in sorted(config_dir.glob("*.yaml")):
        try:
            ExperimentConfig.from_yaml(str(config_file))
            results[config_file.name] = True
            logger.info(f"✓ {config_file.name}")
        except Exception as e:
            results[config_file.name] = False
            logger.error(f"✗ {config_file.name}: {e}")

    return results

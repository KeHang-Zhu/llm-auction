# LLM Auction Experiment Configuration Files

## Directory Structure

- `experiments/`: sealed-bid, common-value, eBay-style, and description-intervention examples.
- `clock/`: open and closed ascending-clock configurations by model and temperature.
- `robustness/`: alternative-model and temperature configurations.
- `interventions/`, `intervention_claude/`, `intervention_gpt5/`: additional historical intervention designs.
- `template.yaml`: starting point for a new configuration.

## Quick Start

Run from the repository root after installing `requirements.txt` and configuring the relevant provider credentials:

```bash
python scripts/main.py --config configs/experiments/01_01_spsb_ipv.yaml
python scripts/main.py --config configs/clock/01_06_ascending_clock_apv.yaml
```

Optional command-line overrides are `--parallel`, `--max-workers`, `--repetitions`, and `--verbose`. Other settings are read from YAML. New runs can incur API charges.

## Configuration File Structure

| Section | Important fields |
| --- | --- |
| `experiment` | `name`, `version`, `description` |
| `auction` | `number_agents`, `rounds` |
| `rule` | `seal_clock`, `ascend_descend`, `price_order`, `private_value`, `open_blind`, `closing`, `reserve_price`, `special_name`, `turns` |
| `value` | `common_range`, `private_range`, `increment`, `seed_base` |
| `llm` | `model`, `temperature` |
| `prompt` | `strategy_type`, `prompt_dir`, `rule_template_dir`, `include_payment_example` |
| `execution` | `repetitions`, `parallel`, `max_workers`, `output_dir` |

Ascending clocks use `ascend_descend: ascend`. The closed-clock examples use `open_blind: blind`. The exact model and seed must be read from the configuration; a filename is not a reliable model identifier. In particular, the historical `claude_sonnet` filenames correspond to Claude 3.5 Haiku in the published baseline data.

## Output Structure

An orchestrated experiment writes a timestamped run directory containing the configuration snapshot, prompt snapshots, raw result files, exported results, and experiment metadata. The precise output directory is set in the YAML file.

## Reproducing the Current Paper

New API runs are not required. Install `requirements-analysis.txt` and run:

```bash
python scripts/reproduce_paper.py --check
```

See [the data map](../data_map.md) for the exact recorded datasets. The current four-model framing comparison includes archived protocols in `experiment_logs/paper_interventions/protocols.json`, and the eBay analysis uses the released `ebay_proxy` and `ebay_closing_rule` trajectories. Historical configuration examples with similar names are not interchangeable with these recorded cells.

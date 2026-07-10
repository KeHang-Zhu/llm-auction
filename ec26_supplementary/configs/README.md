# LLM Auction Experiment Configuration Files

This directory contains all YAML configuration files for LLM auction experiments.

## 📁 Directory Structure

```
configs/
├── template.yaml           # Configuration template (copy this to create new experiments)
├── README.md              # This file
└── experiments/           # All experiment configurations (23 files)
    ├── 01-09: Standard Auctions
    ├── 10-17: eBay & Amazon Variations
    └── 18-23: Intervention Studies
```

## 🚀 Quick Start

### 1. Run Existing Configuration

```bash
# Example: Run SPSB IPV experiment
python main.py --config configs/experiments/01_spsb_ipv.yaml
```

### 2. Create New Experiment Configuration

```bash
# Copy template
cp configs/template.yaml configs/experiments/my_experiment.yaml

# Edit configuration file
vim configs/experiments/my_experiment.yaml

# Run experiment
python main.py --config configs/experiments/my_experiment.yaml
```

## 📋 Configuration File Structure

Each YAML configuration file contains:

### Experiment Metadata (experiment)
- `name`: Experiment name
- `version`: Version number (currently V10)
- `description`: Experiment description

### Auction Configuration (auction)
- `number_agents`: Number of participants (default 3)
- `rounds`: Number of auction rounds (default 15, eBay: 1)

### Rule Configuration (rule)
- `seal_clock`: Auction type (`"seal"` / `"clock"`)
- `ascend_descend`: Direction (`"ascend"` / `"descend"`) - no use for seal, place holder
- `price_order`: Payment rule (`"first"` / `"second"` / `"third"` / `"allpay"`)
- `private_value`: Value model (`"private"` / `"affiliated"` / `"common"`)
- `open_blind`: Information visibility (`"open"` / `"blind"`)
- `closing`: Soft closing rule (Amazon: true, eBay: false)
- `reserve_price`: Reserve price
- `special_name`: Special rule template filename

### Value Generation Configuration (value)
- `common_range`: Common value range [min, max]
- `private_range`: Private value range
- `increment`: Bid increment
- `seed_base`: Base random seed (private: 1299, affiliated: 1399)

### LLM Configuration (llm)
- `model`: Model name (`"gpt-4o"` for most, `"gpt-4"` for eBay)
- `temperature`: Temperature parameter (0.0 - 1.0)

### Prompt Configuration (prompt)
- `strategy_type`: Prompt strategy (`"plan_reflection"` / `"direct"` / `"ebay"` / `"json"`)
- `prompt_dir`: Prompt file directory
- `rule_template_dir`: Rule template directory

### Execution Configuration (execution)
- `repetitions`: Number of experiment repetitions
- `parallel`: Whether to execute in parallel
- `max_workers`: Number of parallel threads
- `output_dir`: Output directory

## 🔬 Experiment Types

### Standard Auctions (01-09)

| # | Name | Type | Value Model | Description |
|---|------|------|-------------|-------------|
| 01 | SPSB IPV | Sealed-Second | Private | Standard Second-Price Sealed Bid |
| 02 | SPSB APV | Sealed-Second | Affiliated | Affiliated Private Values |
| 03 | FPSB IPV | Sealed-First | Private | First-Price Sealed Bid |
| 04 | Third Price IPV | Sealed-Third | Private | Third-Price Sealed Bid |
| 05 | All-Pay IPV | Sealed-AllPay | Private | All-Pay Auction |
| 06 | Ascending Clock APV | Clock-Ascend | Affiliated | Ascending Clock Auction |
| 07 | Sealed Feedback APV | Sealed-Second | Affiliated | Sealed Bid with Feedback |
| 08 | Common Value First | Sealed-First | Common | Winner's Curse (First Price) |
| 09 | Common Value Second | Sealed-Second | Common | Winner's Curse (Second Price) |

### eBay Variations (10-13)

| # | Name | Reserve Price | Closing | Description |
|---|------|---------------|---------|-------------|
| 10 | eBay Reserve 0 | 0 | false | No reserve price |
| 11 | eBay Reserve 40 | 40 | false | Hidden reserve price 40 |
| 12 | eBay Reserve 50 | 50 | false | Hidden reserve price 50 |
| 13 | eBay Reserve 60 | 60 | false | Hidden reserve price 60 |

**Note**: eBay auctions use `model: "gpt-4"`, `strategy_type: "ebay"`, and `rounds: 1` with `turns: 10` time periods.

### Amazon Variations (14-17)

| # | Name | Reserve Price | Closing | Description |
|---|------|---------------|---------|-------------|
| 14 | Amazon Reserve 0 | 0 | true | No reserve price |
| 15 | Amazon Reserve 40 | 40 | true | Reserve price 40 |
| 16 | Amazon Reserve 50 | 50 | true | Reserve price 50 |
| 17 | Amazon Reserve 60 | 60 | true | Reserve price 60 |

**Note**: Amazon auctions use `model: "gpt-4o"`, `strategy_type: "plan_reflection"`, soft closing (`closing: true`), and `rounds: 15`.

### Intervention Studies (18-23)

| # | Name | Intervention Type | Description |
|---|------|-------------------|-------------|
| 18 | Menu Description | Framing | Menu-based auction description |
| 19 | Proxy Breitmoser | Framing | Clock auction described as proxy bidding |
| 20 | Nash Deviation | Strategy | Testing Nash equilibrium deviation |
| 21 | Wrong Strategy | Strategy | Incorrect strategy suggestions |
| 22 | Dominant Strategy | Strategy | Revealing dominant strategy (truth-telling) |
| 23 | Risk Neutrality | Behavioral | Suggesting risk-neutral behavior |

## 📊 Output Structure

Each experiment run creates:

```
experiment_logs/V10/{experiment_name}/
└── run_YYYY-MM-DD_HH-MM-SS/
    ├── config.yaml                 # Configuration snapshot
    ├── prompts/                    # Prompt files used
    ├── raw_data/                   # LLM cache (JSONL)
    ├── results/                    # Result JSON files
    ├── experiment_summary.json     # Experiment metadata
    └── experiment.log              # Execution log
```

## 🔧 Advanced Usage

### Batch Run Experiments

```bash
# Run all standard auctions
for i in {01..09}; do
    python main.py --config configs/experiments/${i}_*.yaml
done

# Run all eBay variations
for i in {10..13}; do
    python main.py --config configs/experiments/${i}_*.yaml
done

# Run all Amazon variations
for i in {14..17}; do
    python main.py --config configs/experiments/${i}_*.yaml
done

# Run all interventions
for i in {18..23}; do
    python main.py --config configs/experiments/${i}_*.yaml
done
```

### Parallel Execution

Set in configuration file:
```yaml
execution:
  parallel: true
  max_workers: 4
```

### Custom Random Seed

```yaml
value:
  seed_base: 2024  # Use custom seed
```

## 📝 Important Notes

1. **Seed Selection**:
   - Private value experiments: `seed_base: 1299`
   - Affiliated value experiments: `seed_base: 1399`

2. **Model Selection**:
   - Standard experiments: `gpt-4o`
   - eBay experiments: `gpt-4` (for consistency)

3. **Closing Rules**:
   - Amazon: `closing: true` (has soft closing)
   - eBay: `closing: false` (no soft closing)

4. **Rule Templates**:
   - Ensure `special_name` files exist in `rule_template/V10/` directory
   - If not specified, system auto-selects based on other parameters

5. **Placeholder Parameters**:
   - `ascend_descend`: Only used for clock auctions, marked as "no use for seal, place holder" in sealed auctions

## 🆘 Troubleshooting

### Validate YAML Format

```bash
# Validate single file
python3 -c "import yaml; yaml.safe_load(open('configs/experiments/01_spsb_ipv.yaml'))"

# Validate all files
python3 -c "
import yaml, os
for f in sorted(os.listdir('configs/experiments')):
    if f.endswith('.yaml'):
        yaml.safe_load(open(f'configs/experiments/{f}'))
        print(f'✓ {f}')
"
```

### Check Rule Templates

```bash
# List available rule templates
ls rule_template/V10/
```

### Verify Output Directory

```bash
# Check write permissions
mkdir -p experiment_logs/V10/test && rmdir experiment_logs/V10/test
```

## 📚 References

- Implementation Plan: See project root plan file
- Prompt Files: `Prompt/` directory
- Rule Templates: `rule_template/V10/` directory
- Analysis Scripts: `results/Plan_reflection/` directory

---

**Version**: V10
**Created**: 2026-01-02
**Last Updated**: 2026-01-02
**Total Configurations**: 23 experiments + 1 template

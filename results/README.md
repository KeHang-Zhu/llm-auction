# Experiment Results CSV Export

This directory is a placeholder for documentation. CSV files are saved within each experiment run directory.

## Directory Structure

CSV files are saved **within each experiment run directory**:

```
experiment_logs/V10/spsb_ipv/
└── run_2026-01-04_00-29-54-383247/
    ├── config.yaml
    ├── prompts/
    ├── raw_data/
    │   ├── raw_output__run0.jsonl
    │   └── result_5_*.json
    ├── experiment_summary.json
    └── results/                           # CSV files saved here
        └── spsb_ipv_results.csv

robustness_logs/V10/spsb_ipv_gemini/
└── run_2026-01-04_01-15-30-123456/
    ├── config.yaml
    ├── prompts/
    ├── raw_data/
    └── results/                           # CSV files saved here
        └── spsb_ipv_gemini_results.csv
```

## Automatic Export

CSV files are **automatically generated** when experiments complete. You don't need to run any manual export commands.

When you run:
```bash
python new/main.py --config configs/experiments/01_01_spsb_ipv.yaml
```

The CSV will be automatically created at:
```
experiment_logs/V10/spsb_ipv/run_<timestamp>/results/spsb_ipv_results.csv
```

For robustness experiments:
```bash
python new/main.py --config configs/robustness/01_01_spsb_ipv_gemini.yaml
```

The CSV will be saved at:
```
robustness_logs/V10/spsb_ipv_gemini/run_<timestamp>/results/spsb_ipv_gemini_results.csv
```

## CSV Format

Each row represents one player's action in one round. The CSV columns are ordered as follows:

### 1. Round-Specific Data (Columns 1-7) - Primary Data
- `round`: Round number (0-indexed)
- `player_name`: Player identifier (e.g., "Bidder Andy")
- `player_value`: Player's private value for this round
- `bid`: Player's submitted bid
- `is_winner`: True if this player won the round
- `final_price`: Final price paid by winner
- `profit`: Player's profit for this round (value - price if won, 0 otherwise)

### 2. Configuration Parameters (Columns 8-22) - Experiment Settings
- `experiment_name`: Name of the experiment
- `version`: Experiment version (e.g., V10)
- `model`: LLM model used (e.g., gpt-4o, gemini-1.5-flash, claude-3-sonnet)
- `service_name`: LLM service provider (openai, google, anthropic)
- `temperature`: Model temperature setting
- `number_agents`: Number of bidders
- `total_rounds`: Total number of auction rounds
- `seal_clock`: Auction mechanism (seal or clock)
- `price_order`: Payment rule (first, second, third, allpay)
- `private_value`: Value model (private, affiliated, common)
- `increment`: Bid increment
- `seed_base`: Random seed base
- `special_name`: Rule template file name
- `timestamp`: Experiment run timestamp
- `repetition_id`: Unique ID for this repetition

### 3. Strategic Plan (Column 23) - Last Column
- `plan`: Player's strategic plan/reasoning (LLM-generated text)

## Example Row

```csv
round,player_name,player_value,bid,is_winner,final_price,profit,experiment_name,version,model,service_name,temperature,...,plan
0,Bidder Andy,41,28.0,False,30.0,0,spsb_ipv,V10,gpt-4o,openai,0.5,...,"My value is $41. To maximize profit, bid slightly above two-thirds of my value..."
```

Note: "..." represents the remaining configuration columns (number_agents through repetition_id).

## Multiple Runs

Each experiment run creates its own CSV file in its own run directory. To compare multiple runs, you'll need to load and merge the CSVs from different run directories.

## Data Analysis

You can load the CSV in Python for analysis:

```python
import pandas as pd
from pathlib import Path

# Load a specific run's results
run_dir = "experiment_logs/V10/spsb_ipv/run_2026-01-04_00-29-54-383247"
df = pd.read_csv(f"{run_dir}/results/spsb_ipv_results.csv")

# Example: Calculate average profit by player
avg_profit = df.groupby('player_name')['profit'].mean()

# Load and compare multiple runs
run_dirs = [
    "experiment_logs/V10/spsb_ipv/run_2026-01-03_00-31-32-572980",
    "experiment_logs/V10/spsb_ipv/run_2026-01-04_00-29-54-383247"
]

dfs = []
for run_dir in run_dirs:
    csv_path = Path(run_dir) / "results" / "spsb_ipv_results.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        dfs.append(df)

combined_df = pd.concat(dfs, ignore_index=True)

# Compare different models
gemini_df = pd.read_csv("robustness_logs/V10/spsb_ipv_gemini/run_<timestamp>/results/spsb_ipv_gemini_results.csv")
claude_df = pd.read_csv("robustness_logs/V10/spsb_ipv_claude_sonnet/run_<timestamp>/results/spsb_ipv_claude_sonnet_results.csv")
```

## Collecting All CSVs

If you want to merge all experiment results into a single file, you can use:

```bash
# Find all CSV files in experiment_logs
find experiment_logs -name "*.csv" -type f

# Merge all CSVs (after removing headers from all but the first)
find experiment_logs -name "*.csv" -exec cat {} + > all_experiments.csv
```

Or in Python:

```python
import pandas as pd
from pathlib import Path

# Recursively find all CSV files
csv_files = Path("experiment_logs").rglob("results/*.csv")

# Load and concatenate
dfs = [pd.read_csv(f) for f in csv_files]
combined = pd.concat(dfs, ignore_index=True)

# Save to a single file
combined.to_csv("all_experiments_combined.csv", index=False)
```

## Manual Export (if needed)

If you need to re-export results manually:

```bash
python3 src/export_results.py <run_dir> <config_path> <output_dir>

# Example
python3 src/export_results.py \
  experiment_logs/V10/spsb_ipv/run_2026-01-03_00-31-32-572980 \
  configs/experiments/01_01_spsb_ipv.yaml \
  experiment_logs/V10/spsb_ipv/run_2026-01-03_00-31-32-572980/results
```

## Notes

- CSV files use UTF-8 encoding
- Plan text may contain quotes and commas (properly escaped)
- Each run directory is self-contained with config, prompts, raw data, and CSV results
- Timestamp in run directory name ensures unique directories for each experiment run

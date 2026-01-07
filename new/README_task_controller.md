# Task Controller Usage Guide

## Overview

The Task Controller (`task_controller.py`) is a batch execution tool that allows you to run multiple auction experiments in parallel, track their success/failure status, and generate comprehensive reports.

## Features

- ✅ **Batch Execution**: Run multiple YAML experiment configurations
- ⚡ **Parallel Processing**: Execute experiments concurrently with configurable workers
- 🔍 **Smart Checking**: Automatically detect already-completed experiments
- 📊 **Comprehensive Reporting**: Detailed success/failure reports with timing information
- 🔄 **Flexible Configuration**: Override repetitions and other settings globally

## Quick Start

### 1. Run experiments from glob pattern

```bash
# Run all robustness experiments
python new/task_controller.py --configs "configs/robustness/01_*.yaml" --max-workers 4

# Run all GPT-4o experiments
python new/task_controller.py --configs "configs/robustness/*_gpt4o_*.yaml"
```

### 2. Run experiments from a list file

Create a text file with experiment paths (one per line):

```bash
# experiments.txt
configs/experiments/01_01_spsb_ipv.yaml
configs/experiments/01_02_spsb_apv.yaml
configs/robustness/01_01_spsb_ipv_claude_sonnet.yaml
```

Then run:

```bash
python new/task_controller.py --config-list experiments.txt --max-workers 4
```

### 3. Run with custom settings

```bash
# Override repetitions for all experiments
python new/task_controller.py --configs "configs/robustness/*.yaml" --repetitions 10

# Force rerun even if experiments exist
python new/task_controller.py --configs "configs/experiments/*.yaml" --force-rerun

# Disable checking for existing experiments
python new/task_controller.py --configs "configs/*.yaml" --no-check-existing
```

## Command-Line Options

### Required (choose one):

- `--configs [PATHS...]`: List of YAML config paths (supports wildcards like `*.yaml`)
- `--config-list FILE`: Path to text file with list of config paths

### Execution Options:

- `--max-workers N`: Maximum parallel workers (default: 4)
- `--repetitions N`: Override repetitions for all experiments
- `--force-rerun`: Force rerun even if experiments completed
- `--no-check-existing`: Don't check for existing completed experiments

### Output Options:

- `--report-output FILE`: Path to save batch report JSON (default: `batch_report.json`)
- `--verbose`: Enable verbose logging

## How It Works

### 1. Validation Phase

The controller validates all config files before execution:
- Checks if files exist
- Validates YAML syntax
- Verifies config structure

### 2. Execution Phase

For each experiment:
- **Check existing**: If `--force-rerun` not set, checks if experiment already completed successfully
- **Run experiment**: Executes using the main orchestrator
- **Track status**: Records success/failure, timing, and repetition counts

Experiments run in parallel with `max_workers` concurrent tasks.

### 3. Reporting Phase

Generates a comprehensive report including:
- Total/successful/failed task counts
- Execution duration for each task
- Output directories and run IDs
- Error messages for failed tasks

## Understanding the Report

### Console Output

```
================================================================================
BATCH EXECUTION REPORT
================================================================================
Total Tasks:      10
✓ Successful:     8
✗ Failed:         2
⊘ Skipped:        0
Duration:         3245.67s (54.09m)
================================================================================

✓ SUCCESSFUL TASKS:
  - spsb_ipv_gpt4o
    Config: configs/robustness/01_01_spsb_ipv_gpt4o.yaml
    Output: experiment_logs/V10/spsb_ipv_gpt4o/run_2026-01-04_15-30-00-123456
    Repetitions: 5/5
    Duration: 324.56s

✗ FAILED TASKS:
  - spsb_apv_llama
    Config: configs/robustness/01_02_spsb_apv_llama.yaml
    Error: Model API timeout after 3 retries
```

### JSON Report

The JSON report (`batch_report.json`) contains detailed information:

```json
{
  "total_tasks": 10,
  "successful_tasks": 8,
  "failed_tasks": 2,
  "skipped_tasks": 0,
  "start_time": "2026-01-04T15:00:00.000000",
  "end_time": "2026-01-04T16:00:00.000000",
  "total_duration_seconds": 3600.0,
  "task_results": [
    {
      "config_path": "configs/robustness/01_01_spsb_ipv_gpt4o.yaml",
      "experiment_name": "spsb_ipv_gpt4o",
      "status": "success",
      "output_dir": "experiment_logs/V10/spsb_ipv_gpt4o",
      "run_dir": "experiment_logs/V10/spsb_ipv_gpt4o/run_2026-01-04_15-30-00-123456",
      "start_time": "2026-01-04T15:00:00.000000",
      "end_time": "2026-01-04T15:05:24.560000",
      "duration_seconds": 324.56,
      "completed_repetitions": 5,
      "failed_repetitions": 0,
      "total_repetitions": 5,
      "error_message": null
    }
  ]
}
```

## Status Types

- **success**: All repetitions completed successfully
- **failed**: Experiment failed to run or some repetitions failed
- **skipped**: Experiment already completed (when `check_existing=True`)
- **partial**: Some but not all repetitions completed (treated as failed)

## Smart Completion Detection

The controller checks if experiments are already completed by:

1. Looking in the `output_dir` specified in the config
2. Finding the most recent `run_*` directory
3. Reading `experiment_summary.json`
4. Comparing completed repetitions with expected repetitions
5. Skipping if already successfully completed

To disable this behavior, use `--no-check-existing` or `--force-rerun`.

## Common Use Cases

### 1. Run all robustness checks for a specific auction

```bash
python new/task_controller.py --configs "configs/robustness/01_01_spsb_ipv_*.yaml" --max-workers 6
```

### 2. Run experiments with different models in parallel

```bash
python new/task_controller.py --configs \
  configs/robustness/01_01_spsb_ipv_gpt4o.yaml \
  configs/robustness/01_01_spsb_ipv_claude_sonnet.yaml \
  configs/robustness/01_01_spsb_ipv_gemini.yaml \
  configs/robustness/01_01_spsb_ipv_llama.yaml \
  --max-workers 4
```

### 3. Rerun failed experiments only

First, check the report to identify failed experiments:
```bash
cat batch_report.json | jq '.task_results[] | select(.status=="failed") | .config_path'
```

Then create a file with just those configs and rerun:
```bash
python new/task_controller.py --config-list failed_experiments.txt --force-rerun
```

### 4. Run a quick test with reduced repetitions

```bash
python new/task_controller.py \
  --configs "configs/experiments/01_*.yaml" \
  --repetitions 1 \
  --max-workers 8
```

## Tips

1. **Start small**: Test with 1-2 experiments first before running large batches
2. **Monitor resources**: Each worker uses API quota and memory
3. **Check logs**: Use `--verbose` to debug issues
4. **Save reports**: Reports are automatically saved to `batch_report.json`
5. **Interrupted runs**: The controller will skip already-completed experiments on restart

## Troubleshooting

### All tasks are being skipped

- Use `--force-rerun` to override completion detection
- Check that your output directories don't have old completed runs

### Tasks failing with API errors

- Reduce `--max-workers` to avoid rate limiting
- Check API credentials and quotas

### Out of memory errors

- Reduce `--max-workers`
- Each experiment loads models and data into memory

## Integration with Main Orchestrator

The task controller uses the same `ExperimentOrchestrator` from `main.py`, so:
- All config options work the same way
- Output structure is identical
- Can use `export_results.py` on the generated data

## Example Workflow

```bash
# 1. Run all GPT-4o robustness experiments
python new/task_controller.py \
  --configs "configs/robustness/*_gpt4o_*.yaml" \
  --max-workers 4 \
  --report-output reports/gpt4o_batch.json

# 2. Check the report
cat reports/gpt4o_batch.json | jq '.successful_tasks'

# 3. Export all results to CSV
for run_dir in experiment_logs/V10/*/run_*; do
  python export_results.py --run-dir "$run_dir"
done
```

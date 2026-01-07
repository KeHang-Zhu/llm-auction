#!/bin/bash
# Demonstration script for Task Controller usage

echo "=============================================================================="
echo "TASK CONTROLLER DEMONSTRATION"
echo "=============================================================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

echo "1. Show help information"
echo "------------------------------------------------------------------------------"
python3 new/task_controller.py --help
echo ""

echo ""
echo "2. Example: Run specific YAML configs"
echo "------------------------------------------------------------------------------"
echo "Command:"
echo '  python3 new/task_controller.py --configs \\'
echo '    configs/robustness/01_01_spsb_ipv_gpt5mini.yaml \\'
echo '    configs/robustness/01_01_spsb_ipv_llama.yaml \\'
echo '    --max-workers 2'
echo ""
echo "This will run 2 experiments in parallel with 2 workers."
echo ""

echo ""
echo "3. Example: Run all configs matching a pattern"
echo "------------------------------------------------------------------------------"
echo "Command:"
echo '  python3 new/task_controller.py --configs "configs/robustness/01_01_*.yaml" --max-workers 4'
echo ""
echo "This will run all SPSB IPV robustness experiments."
echo ""

echo ""
echo "4. Example: Run from a config list file"
echo "------------------------------------------------------------------------------"
echo "Command:"
echo '  python3 new/task_controller.py --config-list new/example_experiments.txt --max-workers 4'
echo ""
echo "This will run experiments listed in the text file."
echo ""

echo ""
echo "5. Example: Override repetitions for all experiments"
echo "------------------------------------------------------------------------------"
echo "Command:"
echo '  python3 new/task_controller.py --configs "configs/experiments/*.yaml" --repetitions 10'
echo ""
echo "This will run all experiments with 10 repetitions each (overriding config)."
echo ""

echo ""
echo "6. Example: Force rerun completed experiments"
echo "------------------------------------------------------------------------------"
echo "Command:"
echo '  python3 new/task_controller.py --configs "configs/*.yaml" --force-rerun'
echo ""
echo "This will rerun experiments even if they already completed successfully."
echo ""

echo ""
echo "=============================================================================="
echo "KEY FEATURES"
echo "=============================================================================="
echo ""
echo "✅ Parallel Execution: Run multiple experiments concurrently"
echo "✅ Smart Checking: Skip already-completed experiments"
echo "✅ Progress Tracking: Monitor success/failure of each task"
echo "✅ Detailed Reports: JSON reports with all execution details"
echo "✅ Flexible Config: Override settings globally or per-experiment"
echo ""

echo ""
echo "=============================================================================="
echo "OUTPUT FILES"
echo "=============================================================================="
echo ""
echo "Each experiment creates:"
echo "  - experiment_logs/V10/{experiment_name}/run_{timestamp}/"
echo "    ├── config.yaml                  # Config snapshot"
echo "    ├── experiment_summary.json      # Execution summary"
echo "    ├── raw_data/                    # Raw LLM outputs"
echo "    ├── results/                     # CSV results"
echo "    └── prompts/                     # Prompt files used"
echo ""
echo "Batch execution creates:"
echo "  - batch_report.json                # Overall batch report"
echo ""

echo ""
echo "=============================================================================="
echo "For more details, see: new/README_task_controller.md"
echo "=============================================================================="

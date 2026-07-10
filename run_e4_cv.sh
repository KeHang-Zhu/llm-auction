#!/bin/zsh
export OPEN_ROUTER_API_KEY=$(grep -oE 'OPENROUTER_API_KEY=\S+' /Users/avshah/coarse-reviews/.env | cut -d= -f2)
for c in configs/robustness_gemma/01_08_common_value_first_gemma27b.yaml configs/robustness_gemma/01_09_common_value_second_gemma27b.yaml; do
  .venv/bin/python Engineering_simplicity/engineer_simplicity-main/new/topup_runs.py --config "$c" --retries 2 --sleep 8
done
echo "=== E4 CV CELLS DONE (clock cells intentionally skipped: per-tick mode too slow; survey-vs-tick harmonization left to native-key run) ==="

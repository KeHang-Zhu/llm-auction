#!/bin/zsh
export OPEN_ROUTER_API_KEY=$(grep -oE 'OPENROUTER_API_KEY=\S+' /Users/avshah/coarse-reviews/.env | cut -d= -f2)
PY=.venv/bin/python
for c in configs/robustness_gemma/*.yaml; do
  echo "=== E4 cell: $c ==="
  $PY Engineering_simplicity/engineer_simplicity-main/new/topup_runs.py --config "$c" --retries 3
done
echo "=== E4 GEMMA BATTERY DONE ==="

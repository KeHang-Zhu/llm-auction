#!/bin/zsh
export OPEN_ROUTER_API_KEY=$(grep -oE 'OPENROUTER_API_KEY=\S+' /Users/avshah/coarse-reviews/.env | cut -d= -f2)
for c in configs_auction/pilot_gullibility/*.yaml; do
  ../../.venv/bin/python new/topup_runs.py --config "$c" --retries 2 --sleep 8
done
echo "=== GULLIBILITY PILOT DONE ==="

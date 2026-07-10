#!/bin/zsh
export OPEN_ROUTER_API_KEY=$(grep -oE 'OPENROUTER_API_KEY=\S+' /Users/avshah/coarse-reviews/.env | cut -d= -f2)
PY=../../.venv/bin/python
echo "=== PHASE 1: gpt5mini auction cells (2 parallel) ==="
ls configs_auction/frontier/gpt5mini/*.yaml | xargs -P 2 -I{} $PY new/topup_runs.py --config {} --retries 3
echo "=== PHASE 2: gemma E2 clock top-up ==="
$PY new/topup_runs.py --config configs_auction/ac_ipv/ascending_clock_ipv_closed_gemma.yaml --retries 3
echo "=== PHASE 3: gpt-4o E2 clock top-up ==="
$PY new/topup_runs.py --config configs_auction/ac_ipv/ascending_clock_ipv_closed_gpt4o.yaml --retries 3
echo "=== PHASE 4: gpt5mini DA battery ==="
$PY src/run_da_batch.py configs_da/frontier/gpt5mini/*.yaml
echo "=== ALL TOPUP PHASES DONE ==="
curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPEN_ROUTER_API_KEY"

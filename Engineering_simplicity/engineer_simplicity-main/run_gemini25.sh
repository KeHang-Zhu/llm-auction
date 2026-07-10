#!/bin/zsh
# Waits for run_topups.sh to finish, then runs the gemini-2.5-flash batteries if credit allows.
export OPEN_ROUTER_API_KEY=$(grep -oE 'OPENROUTER_API_KEY=\S+' /Users/avshah/coarse-reviews/.env | cut -d= -f2)
PY=../../.venv/bin/python
while pgrep -f "run_topups.sh" > /dev/null; do sleep 60; done
USED=$(curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPEN_ROUTER_API_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d['total_credits']-d['total_usage'])")
echo "credit remaining: $USED"
if (( $(echo "$USED < 10" | bc -l) )); then echo "INSUFFICIENT CREDIT — skipping gemini25flash battery"; exit 0; fi
echo "=== gemini25flash auction battery ==="
for c in configs_auction/frontier/gemini25flash/*.yaml; do
  $PY new/topup_runs.py --config "$c" --retries 3
done
echo "=== gemini25flash DA battery ==="
$PY src/run_da_batch.py configs_da/frontier/gemini25flash/*.yaml
echo "=== GEMINI25FLASH DONE ==="
curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPEN_ROUTER_API_KEY"

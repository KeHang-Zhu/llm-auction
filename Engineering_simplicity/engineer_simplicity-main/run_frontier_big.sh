#!/bin/zsh
# Runs after run_gemini25.sh: claude-sonnet-5 battery, then gpt-5 battery, each gated on credit.
export OPEN_ROUTER_API_KEY=$(grep -oE 'OPENROUTER_API_KEY=\S+' /Users/avshah/coarse-reviews/.env | cut -d= -f2)
PY=../../.venv/bin/python
credit() { curl -s https://openrouter.ai/api/v1/credits -H "Authorization: Bearer $OPEN_ROUTER_API_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d['total_credits']-d['total_usage'])"; }
while pgrep -f "run_gemini25.sh|run_topups.sh|run_e4_gemma.sh" > /dev/null; do sleep 90; done
for M in claude_sonnet5 gpt5; do
  C=$(credit); echo "=== credit before $M: $C ==="
  if (( $(echo "$C < 32" | bc -l) )); then echo "SKIPPING $M battery (credit $C < 32)"; continue; fi
  echo "=== $M auction battery ==="
  for c in configs_auction/frontier/$M/*.yaml; do $PY new/topup_runs.py --config "$c" --retries 2 --sleep 8; done
  echo "=== $M DA battery ==="
  $PY src/run_da_batch.py configs_da/frontier/$M/*.yaml
done
echo "=== BIG FRONTIER BATTERIES DONE ==="; credit

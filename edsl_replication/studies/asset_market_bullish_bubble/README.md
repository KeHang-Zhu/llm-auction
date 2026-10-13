# Bullish news and bubble behavior market

This is a separate follow-up condition to `asset_market_midpoint_news`. It
keeps the same 30-period EDSL call market and payoff rules, while changing the
behavioral instructions and the private update.

All twelve traders receive a behavioral persona: four momentum buyers, four
bubble riders, and four active profit-taking sellers. Their opening instructions
provide concrete order anchors to support two-sided trade. After period 15,
two traders in each behavioral group receive a private bullish analyst forecast:
expected resale prices could reach $20 by period 25 because institutional demand
is unusually strong. The message is explicitly a forecast; dividends and the
actual $14 terminal redemption do not change. The six update recipients are
selected reproducibly and balanced across behavioral groups.

This design is intended to make trading and speculative price movement more
likely. It remains an exploratory mixed-treatment session: a shared tape permits
spillovers across traders, and one market cannot establish a treatment effect.

Prepare the serialized specification without model calls:

```bash
python3 edsl_replication/studies/asset_market_bullish_bubble/experiment.py \
  --output edsl_replication/studies/asset_market_bullish_bubble/pilot_01 \
  --prepare-only
```

For local EDSL execution with the configured provider, omit `--prepare-only`.
The run writes the workflow, state, job, and response artifacts beneath
`pilot_01/`.

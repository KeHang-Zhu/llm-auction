# Early bearish-news asset market

This follow-up keeps the bullish bubble pilot's 30-period call market, payoff
rules, trader personas, and stratified six-person information assignment. It
changes the private message to a downside forecast and delivers it before the
first orders, so treated traders see it before any opening price movement.
The forecast says prices could fall toward $10 by period 10 because expected
resale demand has weakened. Dividends and the $14 terminal redemption are
explicitly unchanged.

Prepare a serializable specification without model calls:

```bash
python3 edsl_replication/studies/asset_market_bearish_early/experiment.py \
  --output edsl_replication/studies/asset_market_bearish_early/pilot_01 \
  --prepare-only
```

Run locally with the configured provider by omitting `--prepare-only`. The
pilot writes its workflow, shared-state, job, and response artifacts beneath
`pilot_01/`. The first six scripted workflow items publish private updates;
period 1 orders wait until all six updates are recorded.

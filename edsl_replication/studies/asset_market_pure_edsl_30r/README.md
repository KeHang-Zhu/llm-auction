# 30-round pure EDSL call-market replication

This directory ports the 12-trader, 30-round baseline market to an EDSL
`Machine` without using EDSL's `call_market` factory or registering custom
runtime algorithms. The clearing, admission, trade transfers, interest,
dividends, cash constraints, inventory constraints, and terminal redemption
are represented by serializable state-machine expressions.

## Rules carried over

- 12 traders, 30 rounds, $100 initial cash and 4 shares per trader.
- One sealed order per trader per round: buy, sell, or hold, with a requested
  integer quantity and a cent-denominated limit.
- Buy quantity is capped by affordability and total shares; sell quantity by
  inventory. Borrowing and short selling are prevented.
- Orders rank by limit price; tied prices use the original seeded per-round
  priority order. The market fills the maximal crossing quantity and uses the
  marginal bid/ask midpoint rounded half-up to cents.
- All traders receive the same per-round dividend, either $0.40 or $1.00 with
  equal probability; cash receives 5% interest rounded half-up to cents.
- After the final period's interest and dividend, remaining shares redeem at
  $14.00 each.

The seeded dividend and tie-priority paths are generated at authoring time with
the same Python `random.Random(f"{seed}:dividend:{period}")` and
`random.Random(f"{seed}:priority:{period}")` rules as the native market, then
stored as constants in the serialized Machine. Execution uses those constants;
there are no runtime market callbacks. The expression language is still
interpreted by EDSL's standard runtime.

The experiment configures a 10,000,000-step per-operation ceiling because the
machine retains growing order and trader histories. The default 1,000,000-step
ceiling was exhausted by a late-round transition.

The original model response specified price in dollars. This replication asks
for integer cents instead so the machine can preserve exact monetary values
without a Python conversion step. The economic price precision remains cents.

## Build and inspect

```sh
python3 edsl_replication/studies/asset_market_pure_edsl_30r/experiment.py \
  --output edsl_replication/studies/asset_market_pure_edsl_30r/pilot_02 \
  --prepare-only
```

The resulting `specification.json` includes the JSON-serializable Machine and
workflow. The machine builder calls `Machine.validate()` and declares
`algorithms=()`.

The standalone report is `paper.pdf`. It includes the state-machine definition,
workflow execution sequence, syntax-highlighted excerpts from the actual
Python source, and visual summaries of the saved pilot. Rebuild it from this
directory with:

```sh
pdflatex -interaction=nonstopmode -halt-on-error paper.tex
pdflatex -interaction=nonstopmode -halt-on-error paper.tex
```

Run the deterministic full-horizon mechanics smoke without model calls:

```sh
python3 edsl_replication/studies/asset_market_pure_edsl_30r/smoke_run.py
```

Run the focused transition conformance suite from the repository root:

```sh
PYTHONPATH=edsl_replication/studies/asset_market_pure_edsl_30r \
  python3 -m unittest -v test_machine_conformance
```

The suite checks command preconditions, order caps and invalid orders,
no-crossing and multi-unit clearing, seeded tie priority, midpoint and
half-cent interest rounding, trade settlement, period advancement, and final
redemption. Expected fills and balances are calculated in ordinary Python as
independent reference values.

## Run the model market

```sh
python3 edsl_replication/studies/asset_market_pure_edsl_30r/experiment.py \
  --output edsl_replication/studies/asset_market_pure_edsl_30r/pilot_02
```

This runs 360 trader decisions (12 traders × 30 rounds) using EDSL's configured
provider credentials. A different seed and output directory define another
independent market.

## Pilot result

The completed `pilot_02` run used `gpt-4o` through EDSL's `openai` service with
seed `153101`. It completed all 360 trader decisions and settled all 30 rounds.
The serialized machine declares no custom algorithms. The backend recorded 360
state reads and 420 writes (360 order submissions, 30 clearings, and 30
settlements).

Trading was sparse: 8 units crossed in 5 rounds, with no trades in the other 25.
The traded rounds were 10–14; prices rose from $15.00 to $15.14. The 213 buy,
89 sell, and 58 hold decisions were not enough to sustain matching after round
14. At a 5% cash rate, the discounted expected dividends and $14 terminal
redemption imply a $14 fundamental price: the expected $0.70 dividend is
exactly 5% of $14. The five observed prices were therefore 7.1%–8.1% above
that benchmark, but applied to only eight matched units. All 48 shares were
redeemed at the end. Final trader cash ranged from $661.18 to $690.67,
including interest, dividends, trade proceeds, and redemption.

`analyze_run.py` regenerates `results_summary.json`, `round_summary.csv`, and
`trader_summary.csv` from the persisted workflow and shared-state databases.
Forecast errors in the summary are conditional on a transaction being observed
at the forecast target period, so their sample sizes are smaller than the 360
forecasts. This single seeded run demonstrates end-to-end execution; comparison
with the paper requires repeated markets and the paper's outcome statistics.

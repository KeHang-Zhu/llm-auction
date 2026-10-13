# Short population-scale capability pilot

This pilot checks whether the shared-state call market can construct, execute,
and settle markets with larger trader populations. It holds the model, prompt,
per-trader endowment, strategy balance, EDSL machine, and random seed constant
while varying the trader count. The short horizon is five periods so the pilot
can demonstrate execution scale without paying for full 30-period markets.

| Traders | Strategy counts (buyer / seller / flexible) | Planned decisions | Status |
| ---: | ---: | ---: | --- |
| 12 | 4 / 4 / 4 | 60 | Complete: 60 decisions, 5 rounds settled, 9 units traded in 2 rounds; 58 sec; 78,170 prompt / 11,342 completion tokens |
| 24 | 8 / 8 / 8 | 120 | Complete: 120 decisions, 5 rounds settled, 4 units traded in 1 round; 102 sec; 155,002 prompt / 22,378 completion tokens |
| 48 | 16 / 16 / 16 | 240 | Complete: 240 decisions, 5 rounds settled, 16 units traded in 2 rounds; 209 sec; 311,970 prompt / 45,525 completion tokens |

All cells completed every planned decision and settled all five rounds. They
used GPT-4o through the OpenAI service and seed `153101`. The 12-, 24-, and
48-trader markets completed in 58, 102, and 209 seconds, respectively. Across
those runs, transaction volume was 9, 4, and 16 units. Token counts are recorded
from provider responses; no monetary cost estimate is included. These runs
demonstrate successful execution at each tested population size. Outcomes are
from one seeded market per size.

The machine-readable comparison is in [`scale_summary.csv`](scale_summary.csv).
Each run directory includes its serialized experiment, model-call log,
completion record, and `results_summary.json`. SQLite state databases are
retained locally but ignored by Git.

Run each market from the repository root with:

```sh
python3 edsl_replication/studies/asset_market_pure_edsl_30r/experiment.py \
  --traders 24 --periods 5 --seed 153101 \
  --output edsl_replication/studies/asset_market_pure_edsl_30r/scaling/five_periods/agents_24
```

The market supports integer multi-unit orders, with buys limited by cash and
sells by inventory. This population-size pilot exercises that existing action
space; it does not independently estimate the effect of changing requested
quantities. Full workflow records are kept in each run directory. Generate a
compact summary for a completed run with:

```sh
python3 edsl_replication/studies/asset_market_pure_edsl_30r/analyze_run.py \
  --run-dir edsl_replication/studies/asset_market_pure_edsl_30r/scaling/five_periods/agents_24
```

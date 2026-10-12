# Two-round live-decision call-market pilot

This pilot connects live trader interviews to the declarative call-market
Machine. Four traders submit one sealed buy, sell, or hold order in each of two
rounds. The EDSL Machine admits affordable buys and inventory-backed sells,
selects the highest eligible bid and lowest eligible ask, executes one midpoint
trade when they cross, records the round, and carries cash and shares forward.

The workflow uses `Workflow.repeat` with a two-round bound. Its compiled repeat
block, per-round steps, stop condition, surveys, participant routing, shared
state operations, and execution plan are all JSON data in
`specification.json`. `WorkflowExperiment.run` advances the workflow and opens
the next round after the prior round settles; there is no Python loop over
market rounds in the runner. The Python authoring function supplies the repeated
step template, which `Workflow.repeat` materializes into the bounded portable
workflow definition.

The repeat stop condition is the Machine's own `complete_when` predicate via
`market.is_complete()`. After settlement, the coordinator reads the scoped
Machine state and evaluates that predicate; round one leaves the Machine open,
so the second round proceeds, while the final settlement marks it complete.

## Prepare and run

Build the portable experiment specification without making model calls:

```sh
PYTHONPATH=edsl_replication/studies/multi_round_call_market_live \
  python3 edsl_replication/studies/multi_round_call_market_live/experiment.py \
  --output edsl_replication/studies/multi_round_call_market_live/pilot_01 \
  --prepare-only
```

Run the four traders with EDSL's configured provider credentials:

```sh
PYTHONPATH=edsl_replication/studies/multi_round_call_market_live \
  python3 edsl_replication/studies/multi_round_call_market_live/experiment.py \
  --output edsl_replication/studies/multi_round_call_market_live/pilot_01
```

To exercise the Machine-state stop condition without making another set of
model calls, replay the decisions from `pilot_01` into a fresh state scope:

```sh
PYTHONPATH=edsl_replication/studies/multi_round_call_market_live \
  python3 edsl_replication/studies/multi_round_call_market_live/experiment.py \
  --output edsl_replication/studies/multi_round_call_market_live/pilot_02 \
  --replay-from edsl_replication/studies/multi_round_call_market_live/pilot_01
```

The replay reads the eight saved trader submissions from `pilot_01` and reuses
them in a fresh run; it makes no model calls. Exchange clearing and settlement
are scripted workflow actions that invoke only the Machine's declarative
commands. The resulting workflow and state databases preserve the decisions,
order eligibility, tape, and account changes for review.

## Pilot result

The original `pilot_01` run used eight `gpt-4o` trader interviews. Both rounds cleared
one share at 1,238 cents. Trader B bought from D in round one; trader A bought
from C in round two. Round-two responses reflected carried state: B held after
spending most of its cash in round one, while D held after selling its only
share. The final accounts held 8,000 cents and four shares in total, matching
the initial totals. `pilot_02` replays those same trader decisions and confirms
the Machine completion predicate advances the repeat after round one and stops
after round two. Each run's `results_summary.json` contains its round tape, all
submitted decisions, and ending accounts.

This demonstrates model interviews interleaved with a bounded repeated
workflow, including state visibility across rounds and direct state-based loop
termination. `Workflow.repeat` evaluates the Machine's declared completion
predicate against the live scoped state after each iteration settles. The
condition reads the predicate; it does not invoke the Machine's
close/finalization transition. `pilot_02/results_summary.json` records the
replayed run's tape, decisions, ending accounts, and the Machine-based stop
condition.

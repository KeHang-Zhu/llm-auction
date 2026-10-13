# Why express an experiment as an EDSL state machine?

## Summary

An EDSL state machine makes an experiment's changing state and the rules for
changing it explicit. In the 30-round asset-market pilot, trader choices came
from model interviews, while order admission, matching, prices, transfers,
interest, dividends, and redemption were defined as Machine commands. The
result was a market mechanism that could be inspected, validated, serialized,
and executed through the shared-state workflow without custom market callback
algorithms.

The main benefit is not that a state machine removes Python or makes model
behavior deterministic. Python still authors the Machine and EDSL's runtime
still interprets its expression language. Rather, the market's authoritative
transition rules are represented as data in the EDSL, instead of being hidden
inside an opaque function that mutates state.

## What the approach means

A Machine has typed state fields, named commands, command inputs and
preconditions, expression-based effects, a view of state for participants, and
optional runtime algorithms. A command defines a legal transition from one
state to the next. In the asset market, the core commands were:

1. `submit_order` checks the period, trader, order format, available cash, and
   share inventory before recording one order per trader.
2. `clear_orders` requires all 12 orders, ranks unit bids and asks, finds the
   largest crossing quantity, and records the uniform price and fills.
3. `settle` applies trades and income, records history, resets the order book,
   and advances the period. In the final period it also redeems remaining
   shares.

The workflow orchestrates interviews and command calls. Each trader reads a
personalized view of their account together with the public tape and submits an
order. Once all interviews finish, a scripted exchange step invokes the
Machine's clearing command, followed by settlement. The exchange response is a
trigger for a defined transition; the model does not calculate the matching
allocation.

## Concrete benefits

### 1. The mechanism is inspectable

The state schema, command preconditions, and state effects are visible in the
Machine definition. For example, the `clear_orders` precondition requires the
current period, exactly 12 submitted orders, and no pending clearing. Those
conditions document when clearing is legal as executable rules. The matching
expressions show how bids, asks, ties, and the midpoint price are handled.

This is useful when the experiment must be reviewed, compared with a paper, or
modified later. A reviewer can inspect what the machine actually enforces,
rather than infer the mechanism from prose or from a long callback's control
flow.

### 2. The transition rules travel as serializable data

The Machine can be represented as JSON, including its typed fields, command
structure, expressions, and constants. That representation can be saved with
the experiment, inspected by tooling, compared across versions, and loaded by a
compatible EDSL runtime. In this market, the seeded dividend and tie-priority
schedules were materialized as Machine constants, so the run used the schedule
stored with its definition.

Serialization makes the experiment definition easier to preserve and inspect.
It does not make the JSON self-executing: an EDSL runtime that understands the
expression language and its operations is still required. The model's choices
and external provider behavior are also outside the Machine JSON.

### 3. Preconditions make phase order explicit

The market permits one order per trader per period, clearing only after all
traders submit, and settlement only after a clearing exists. These rules are
checked at the transition boundary. This narrows the set of states the
mechanism accepts and makes sequencing requirements part of the implementation
rather than a convention that every caller must remember.

That pattern is broadly useful for experiments with rounds, treatments,
auctions, asset transfers, or interventions: encode the conditions for a
transition where the transition is defined.

### 4. Workflow and economic mechanism are separated

The workflow decides who acts and when. The Machine defines the permitted
state changes and the consequences of those actions. In this experiment,
traders generate orders through model interviews, while deterministic EDSL
expressions handle the exchange. The same market mechanism can therefore be
invoked by a different workflow or participant mix without rewriting the
clearing and settlement rules.

This separation also clarifies where uncertainty enters. The trader's answer
can vary with the model, prompt, or provider; given a submitted order and the
stored state and constants, the matching and accounting rules are specified by
the Machine.

### 5. Shared state supports an auditable run history

Participants can read a controlled view of the same evolving market. The view
can reveal public information, such as the tape, while returning only the
current trader's private account. Writes pass through named commands. The
workflow and shared-state stores then retain the submitted decisions and
transition events.

In the completed pilot, 360 trader interviews generated 360 state reads and
360 order writes. The 30 rounds added 30 clearing writes and 30 settlement
writes, for 420 state writes total. The saved state and workflow databases
support analysis of decisions, fills, balances, and completion without relying
only on a final market summary.

### 6. Standard operations can be composed without custom callbacks

The pilot implemented order admission, unit expansion, sorting, crossing
quantity, marginal-price calculation, fills, cash and share transfers,
interest, dividends, and redemption using built-in expression operations. Its
Machine declared an empty `algorithms` list. This keeps the authoritative
mechanism in the serializable definition and avoids depending on custom Python
market algorithms during execution.

This is especially useful when portability, inspectability, or machine-readable
experiment definitions matter. A callback can still be appropriate where the
mechanism needs an operation the expression language does not provide, or
where a custom implementation is materially clearer. The pure approach is
valuable when the needed rules can be expressed clearly with the available
operations.

## Evidence from the 30-round pilot

The implementation completed 360 trader decisions and all 30 rounds. The
machine ended at period 31 with no pending orders, zero remaining shares, and
all 48 shares redeemed. The run also exercised the intended phase sequence:
one order from each of 12 traders, one clearing, and one settlement per round.

This demonstrates that the representation can carry a complete market
lifecycle, not only a small auction example. It is evidence about the
implementation and execution path. It is not evidence that model traders
replicate the economic results of the paper: this was one seeded market, with
only eight units traded in five periods. Repeated markets and comparison to the
paper's market-level statistics are still needed for that claim.

## Costs and boundaries

- **The Machine is still interpreted.** The JSON is a definition; it needs a
  compatible EDSL runtime to execute expressions.
- **Authoring still uses Python.** Python builds the expression tree and, in
  this market, materializes seeded schedules. The benefit is that transition
  logic is expressed in the DSL, not that the whole application ceases to use
  Python.
- **DSL expressions can be harder to write and read.** Nested expression
  builders can be less direct than ordinary Python for complex algorithms.
  Helpers, focused expressions, and validation are important to keep a large
  Machine maintainable.
- **Evaluation consumes resources.** The market preserves growing order and
  trader histories for auditability. A late-round operation exceeded the
  default one-million-step limit, so this workflow uses a ten-million-step
  per-operation limit. Clearing and settlement together averaged about 3.3
  seconds per round in the pilot; a batch of 12 model interviews took about
  38--40 seconds. In this run, model inference was the larger time cost.
- **Deterministic mechanics do not make the market run deterministic.** Given
  the same state, orders, and constants, the defined mechanics apply the same
  rules. Model responses can differ across calls, and external inference is
  not made reproducible merely by serializing the Machine.

## When to use this approach

Use a Machine when state transitions are central to the experiment and should
be reviewable, serializable, and guarded by explicit preconditions. It fits
especially well when multiple participants or workflow steps interact with
shared state and when later analysis needs a durable record of how state
changed.

Use a simpler implementation when the process has little shared state, few
meaningful transition constraints, or when a required operation cannot be
expressed clearly in the DSL. The value of the Machine comes from making the
experiment's state and rules easier to inspect and govern; it is not a goal in
itself to encode every computation in a DSL.

## Related files

- [`machine_definition.py`](machine_definition.py): the 30-period market Machine.
- [`experiment.py`](experiment.py): agents, shared-state setup, and workflow.
- [`paper.pdf`](paper.pdf): detailed mathematical and empirical writeup.
- [`pilot_02/results_summary.json`](pilot_02/results_summary.json): completed pilot summary.

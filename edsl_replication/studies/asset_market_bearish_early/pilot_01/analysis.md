# Pilot 01: early bearish news and bubble behavior

## Design

This 30-period EDSL call market has 12 traders, each starting with $100 and four
shares. Cash earns 5% interest, dividends are $0.40 or $1.00 with equal
probability, and remaining shares are redeemed for $14 after period 30. The
behavioral composition matches the bullish bubble pilot: four momentum buyers,
four bubble riders, and four profit-taking sellers. Each style has concrete
opening price instructions.

Six traders, two from each style, receive a private bearish analyst forecast
before period 1. It says weakened resale demand could bring prices toward $10 by
period 10, while explicitly stating the $14 redemption and dividend rules are
unchanged. Recipients: trader-00, trader-01, trader-05, trader-07, trader-08,
and trader-10. The message is a forecast, not a payoff rule.

## Results

- All 30 periods settled: 360 trader decisions, 30 settlements, six private
  update writes, and 396 completed workflow items.
- 51 shares traded across 22 periods. There were transactions in periods 1–4,
  6–10, 14–25, and 29. Prices rose from $15.25 in period 1 to $26.50 in period
  29; the highest observed price was $26.50. The price was $20 by period 10,
  despite the treated traders' downside update forecasting a possible decline
  toward $10 by then.
- Traders submitted 171 buy orders, 99 sell orders, and 90 holds over 360
  decisions. Momentum buyers submitted 116 buys; bubble riders submitted 40
  buys and 76 sells; profit takers submitted 86 holds, 19 sells, and 15 buys.
- The mean current-price forecast for update recipients was $14.50 in period 1
  versus $15.00 for traders without news. The groups had converged by period 10
  ($19.67 versus $19.75) and remained close in period 25 ($25.83 versus $26.00).
- All traders ended with zero shares after redemption. Ending cash ranged from
  $538.65 to $799.35.

The bearish report did not prevent an opening run-up. The first-period rationales
show treated momentum traders followed their early-buying instructions despite
the report; treated bubble riders explicitly said they would ride speculative
demand; and treated profit takers used the report to justify early selling. The
market then rose for most of the session. This is useful evidence that the
behavioral prompts can dominate a private downside signal in this one session.
It is not a causal estimate: all traders observed one shared tape, there was
only one market, and 4 of 12 traders had bubble-rider instructions.

Compared descriptively with the separate bullish-news pilot, this session had
51 traded shares rather than 22 and a $26.50 peak rather than $18.00. Because
these are separate single markets, the difference cannot be attributed to news
sign or timing. The pilot makes a strong case for repeated seeded markets with
news sign and delivery time varied independently.

Plots: [`market_outcomes.png`](market_outcomes.png) and
[`forecast_paths.png`](forecast_paths.png). The shading is one within-group
standard deviation, not a confidence interval. The generated machine diagram
is [`market_machine.png`](market_machine.png).

## Shared-state execution

The implementation extends EDSL's `call_market` machine with a private update
map, a `publish_update` command, and a `your_update` view selected by the current
trader name. Six scripted exchange steps populate the map before any order step.
Period 1 orders depend on those steps, so recipients see the update in their
first decision and other traders receive the empty-view message. The full
workflow and state event history are preserved in this directory. See
[`experiment.py`](../experiment.py) for the source.

## Limits

This is one session with a mixed treatment and strong behavior prompts. Shared
prices create cross-trader spillovers. The forecast statement does not alter
realized payoffs, but LLM agents can misread forecasts or prioritize assigned
behavioral instructions. Repeated independent markets and factorial treatment
assignment are needed to identify whether bearish news reduces price bubbles.

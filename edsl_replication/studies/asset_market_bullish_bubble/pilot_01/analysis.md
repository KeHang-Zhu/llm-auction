# Pilot 01: bullish news and bubble behavior

## Design

This 30-period market has 12 traders, each beginning with $100 cash and four
shares. The standard EDSL call-market rules remain in place: 5% cash interest,
$0.40 or $1.00 dividends with equal probability, uniform-price settlement, and
$14 terminal redemption. Four traders receive momentum-buying instructions,
four receive bubble-riding instructions, and four receive profit-taking seller
instructions. Their prompts include concrete opening order anchors to encourage
early two-sided trade.

After period 15 settles, two traders in each behavior group receive a private
positive analyst update: an institutional research desk forecasts resale
prices could reach $20 by period 25 on unusually strong buying demand. It is a
forecast, not a guaranteed payoff; the dividend and actual redemption rules do
not change. This assignment is balanced across behavior and reproducible from
seed 141027. The recipients are trader-00, trader-01, trader-04, trader-05,
trader-09, and trader-11.

## Results

- All 30 periods settled; 360 trader decisions, 30 settlements, and six private
  update deliveries completed (396 workflow items).
- 22 shares traded in seven periods: periods 1–4 and 27–29. No trade occurred
  in the 23 periods from 5 through 26.
- Transaction prices in periods 1–4 were $15.25, $16.63, $17.25, and $17.90.
  The highest price was $18.00 in period 27; prices in periods 28 and 29 were
  $17.75. These prices exceeded the $14 terminal redemption amount, but this
  one-session pattern is not enough to establish a bubble.
- Traders submitted 181 buy orders and 39 sell orders across 360 decisions.
  Momentum traders submitted 78 buys; bubble riders submitted 103 buys; profit
  takers submitted 15 sells. The behavior prompts produced substantially more
  active order choices than the generic-prompt pilot.
- After news delivery, the mean current-price forecast for treated traders was
  $17.77 in period 15, $17.93 in period 16, and $18.17 in period 25. The
  no-news means were $17.77, $17.77, and $17.90. These are descriptive means
  from six traders per group in one shared market.
- All traders ended with zero shares after redemption. Ending cash ranged from
  $642.76 to $717.52, reflecting interest, dividends, and trade gains/losses.

The prompts generated early speculative trading and prices above redemption,
but turnover stopped after period 4 and resumed only near the end. The bullish
update coincided with a modest treated-control forecast gap after period 15;
it did not produce an immediate transaction-price change because no trades
occurred in periods 16–26. The pilot supports a stronger behavioral design than
the generic version, but it does not identify the causal effect of the news.

The price/volume path and forecast paths are in
[`market_outcomes.png`](market_outcomes.png) and
[`forecast_paths.png`](forecast_paths.png). Shading is one within-group standard
deviation, not a confidence interval.

## Shared-state execution

The native `call_market` machine was extended with a `private_updates` map, a
`publish_update` command, and a `your_update` view projected by the current
trader name. The map is hidden from the participant view; only each trader's
own message is returned. Six scripted exchange workflow items publish updates
after period 15 settlement and before period 16 orders. The complete generated
machine diagram is [`market_machine.png`](market_machine.png); source is in
[`experiment.py`](../experiment.py).

## Limits

There is one market session and one shared public tape. Traders can affect one
another through prices and observed trading, so participants are not
independent treatment units. No trades occurred for 23 consecutive periods,
which limits conclusions about the news treatment. Repeated independent market
sessions are needed to assess how reliable the early price rise and late
trading are.

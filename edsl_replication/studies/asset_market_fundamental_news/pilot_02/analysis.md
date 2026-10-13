# Payoff-relevant news market: pilot 02

## Experimental design

Each condition is one independent 30-period call market with 12 traders. The
initial redemption is $14. Four traders in each market follow each of three
fixed trading styles: value buyer, value seller, and flexible value trader.
Prompts and initial endowments are identical across arms. Cash earns 5% and
shares pay common $0.40 or $1.00 dividends with equal probability.

After period 5 settles and before period 6 orders, the positive arm announces a
binding change in terminal redemption from $14 to $20; the negative arm changes
it from $14 to $8. The control receives no payoff update and remains at $14.
Each condition uses the same replicate seed, so the dividend sequence is paired
across arms. News applies to the entire market to avoid within-market treatment
spillover between traders.

## Pilot results

| Measure | Positive | Negative | Control |
|---|---:|---:|---:|
| Period 5 mean current-price forecast | $14.22 | $14.32 | $14.23 |
| Period 6 mean current-price forecast | $19.41 | $8.83 | $14.23 |
| Period 5 mean 10-period forecast | $15.32 | $15.08 | $14.89 |
| Period 6 mean 10-period forecast | $21.54 | $9.97 | $14.89 |
| Buy orders (30 periods) | 219 | 195 | 149 |
| Sell orders (30 periods) | 92 | 114 | 120 |
| Holds (30 periods) | 49 | 51 | 91 |
| Shares traded | 0 | 0 | 0 |
| Trading periods | 0 / 30 | 0 / 30 | 0 / 30 |
| Ending cash per trader | $703.21 | $655.21 | $679.21 |

The payoff information caused a large, immediate, correctly signed shift in
forecasts. From period 5 to 6, the positive arm's mean current-price forecast
rose by $5.19; the negative arm fell by $5.48; and the control was unchanged.
The submitted buy limits show the same immediate pattern at the trader level:
among the six traders in each arm who submitted buy orders in both periods,
the mean limit rose by $3.60 after positive news, fell by $5.28 after negative
news, and changed by $0.00 in control. The paired lines in the figure connect
each trader's own period-5 and period-6 buy limit; open symbols mark a buyer
who appeared in only one of those periods.
The average period-6 best bid and best ask were $19.00 and $21.00 in the
positive arm, $9.50 and $10.00 in the negative arm, and $13.90 and $15.00 in
control. Thus news changed stated beliefs and submitted order prices, while
every best bid still remained below the best ask.

There were no transactions in any arm. The session therefore shows that the
binding payoff news mattered for beliefs and quotes, but it does not show a
transaction-price response. The lack of fills is a market-design limitation,
not evidence that the news had no effect. A follow-up should preserve the
payoff-changing update while making buyer and seller quotes more likely to
overlap—for example, by using value-based quote instructions with a smaller,
pre-specified bid/ask spread. That adjustment should be identical in every
condition.

These are three single-market pilots, not independent evidence of an average
treatment effect. The 12 traders in a market share a price path and are not 12
independent experimental units. A larger study should use many independently
seeded markets per arm and calculate power at the market level.

## Visualizations

[`forecast_paths.png`](forecast_paths.png) shows the forecast response; dotted
steps show the terminal redemption value. [`order_frontiers.png`](order_frontiers.png)
plots the highest submitted buy limit and lowest submitted sell limit for each
period. The shaded area marks periods in which the quotes did not cross.
[`bids_before_after.png`](bids_before_after.png) directly compares each trader's
buy limit before and after the announcement, with the no-news market as a
control.

## Shared-state machine and transition sequence

The market definition is `FundamentalNewsCallMarket`, an EDSL shared-state
machine constructed from the machine returned by EDSL's `call_market` factory.
It copies that machine's state fields, commands, view, completion rule, close
effects, and native algorithms into a new machine of the same EDSL machine
type, then extends the definition. This is not Python subclassing. Native
settlement is configured with zero terminal redemption so it cannot apply a
stale payoff. The extended machine adds a live `terminal_redemption_cents`
field, an announcement field, an auditable event sequence, and a
`redemption_applied` guard.

1. Periods 1–5 use the initial $14 terminal redemption.
2. Period-5 settlement advances the current period to 6.
3. In positive and negative arms, a scripted exchange command changes the
   redemption field and appends the public announcement to `fundamental_events`.
   This happens before period-6 trader decisions. In control, no news command
   executes.
4. Each trader reads the same updated redemption from the public view. Their
   order is written with `submit`; the native `settle` command matches orders
   and processes dividends and interest.
5. Period-30 settlement records `redeemed_shares` but pays zero redemption.
   The following `apply_terminal_redemption` command maps over all accounts,
   adds `redeemed_shares × terminal_redemption_cents` to cash, and sets the
   one-time guard. The workflow waits for this transition before completion.

The details are in [`experiment.py`](../experiment.py); the machine diagram is
[`fundamental_news_machine.png`](fundamental_news_machine.png). All three
corrected arms completed: 392 workflow items for each news arm and 391 for the
no-news control. The final state confirms the arm's intended redemption was
applied. The earlier positive run is archived under `../pilot_01/` and excluded:
its period guard caused the announcement to be a no-op.

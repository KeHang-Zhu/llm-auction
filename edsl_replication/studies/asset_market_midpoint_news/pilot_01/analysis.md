# Pilot 01: midpoint private analyst update

## Design and implementation

This 30-period shared call market has 12 traders, each starting with $100 cash
and four shares. Each period traders submit sealed limit orders, then the
exchange settles the call market and updates the public tape. Six traders were
selected reproducibly (`seed=141026`) to receive a private analyst estimate
after period 15 settled and before period 16 began. The estimate revised the
analyst's terminal-value estimate from $14 to $16 per share; the market's actual
redemption remained $14. The six recipients were trader-00, trader-01,
trader-02, trader-05, trader-06, and trader-07.

The state machine is the native EDSL `call_market` machine with one additional
map, `private_updates`, one `publish_update` command, and a `your_update` view
that selects `private_updates[current.name]`. The update map is not exposed as a
whole in the trader view. The complete EDSL-generated diagram is
[`market_machine.png`](market_machine.png). Source and launch instructions are
in [`experiment.py`](../experiment.py) and the study README.

## Observed results

- All 30 periods settled; all 396 workflow items completed (360 trader
  decisions, 30 settlements, and six update deliveries).
- There were **zero transactions in all 30 periods**. Every tape row has null
  transaction price and zero volume.
- All 12 traders finished with four shares redeemed and $646.34 cash each.
- At period 16, one of six informed traders submitted a buy order; the other
  treated traders held. No control trader submitted a buy or sell order. The
  buy orders did not cross any offers, so there was no trade.
- The treated group’s mean current-price forecast was $10.85 in period 15 and
  $11.02 in period 16. The control group's means were $13.28 and $13.33. These
  are descriptive values from one market, not a treatment-effect estimate.
- The treated trader who began buying continued to submit a buy order in later
  rounds, but no trader offered shares. In period 30, all traders held through
  the terminal redemption.

This pilot demonstrates private delivery and persistence of an update in the
shared-state workflow. It does not show that private news moves market prices:
there was no price formation at all. The weak participation and the wide spread
in traders' forecasts are the main substantive result. A follow-up should give
traders distinct trading roles or stronger order-choice instructions, and run
multiple independently seeded markets before comparing treatment groups.

The time path of both groups' forecasts is shown in
[`forecast_paths.png`](forecast_paths.png). Shading is one within-group standard
deviation, not a confidence interval.

## Response recovery

Four initial final-period responses contained `null` for forecasts at horizons
that extended beyond the final period. EDSL correctly rejected those answers
against the required numerical decision schema. The run retained the valid
responses and state events. To complete the final settlement, the recovery
utility filled only those out-of-horizon fields with the known $14 terminal
redemption amount. It preserved the raw model responses in `model-calls.jsonl`
and recorded each imputed field in `recovery.json`. These forecast fields did
not determine final-period orders. No additional model calls were needed for
the recovery. The prompt now explicitly instructs traders to use terminal
redemption for forecast horizons beyond period 30.

## Limits

There is one market session, six treated traders within that session, and a
single private positive estimate. The six control traders share the public
tape with treated traders, so price-mediated spillovers are possible in a
market with transactions. Because this market had no transactions, this pilot
cannot estimate direct or spillover effects. The update is explicitly an
analyst estimate rather than a change in the market's actual payoff rule.

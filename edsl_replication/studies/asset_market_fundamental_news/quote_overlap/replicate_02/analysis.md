# Narrow-spread quote pilot: replicate 02

## Design

This paired pilot used one 12-trader market per arm and 30 trading periods. The
positive and negative arms announced binding terminal redemption changes from
$14 to $20 and $8, respectively, after period 5. The control stayed at $14.
All arms used the same `narrow_spread` quote rule, which places a value-based
buy limit $1.25 above the trader's current-price forecast or a sell limit $1.25
below it. The arms used the same seed.

## Observed price response

| Arm | Period 5 price | Period 6 price | Change | Periods with trades | Units traded |
| --- | ---: | ---: | ---: | ---: | ---: |
| Positive news ($20 payoff) | $14.40 | $20.25 | +$5.85 | 8 | 16 |
| Negative news ($8 payoff) | No trade | $8.35 | First post-news trade | 7 | 21 |
| Control ($14 payoff) | $14.40 | $14.48 | +$0.08 | 16 | 16 |

The negative market had no period-5 transaction, so its first post-news print
was $8.35 in period 6. Mean current-price forecasts moved in the corresponding
directions from period 5 to 6: +$5.26 in positive, -$3.54 in negative, and
+$0.08 in control. All three arms traded, making this a successful
price-observation pilot after the original patient-quote arms produced no
trades.

The positive print was slightly above its $20 terminal payoff, and the
negative print was slightly above its $8 payoff. These outcomes show a
directional short-run price response; they do not establish accurate price
discovery or welfare gains.

## Interpretation and limitations

The pilot changes how limits are submitted, and it has only one independent
market per arm. Traders interact within a shared market, so 12 traders are not
12 independent treatment replications. The volume and price differences are
descriptive. The quote rule can itself affect transaction prices, although it
is held constant across these three arms. Follow-up work should repeat markets
with multiple paired seeds and analyze market-level period-5-to-6 price changes
and post-news price paths. The original patient-quote study and this
narrow-spread pilot should not be pooled as one treatment.

## Files

- `summary.json`: arm summaries and transaction tapes.
- `forecast_paths.png`: mean forecast paths against terminal redemption.
- `order_frontiers.png`: best submitted buy and sell limits by period.
- `bids_before_after.png`: within-trader buy-limit changes for buyers observed
  both before and after news.
- `fundamental_news_machine.png`: state-machine diagram.

The full workflow state, model-call records, inference batches, and job files
are retained in each arm directory for audit and reproduction.

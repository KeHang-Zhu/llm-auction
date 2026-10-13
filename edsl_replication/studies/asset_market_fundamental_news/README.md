# Payoff-relevant news in a multiround asset market

This study asks whether traders respond when news changes the asset's actual
terminal payoff. It uses a purpose-built `FundamentalNewsCallMarket` shared-state
machine rather than the existing static-redemption market. Redemption is a
state field, the period-5 announcement updates that field for the entire market,
and final redemption uses the value currently stored in state.

## Arms

Each arm is an independent 30-period market with 12 traders and the same
endowments, dividend schedule, trading styles, and machine. Four traders use a
value-buyer style, four a value-seller style, and four a flexible value-based
style. After period 5 settlement and before period 6 orders:

- **Positive:** a binding official update changes redemption from $14 to $20.
- **Negative:** a binding official update changes redemption from $14 to $8.
- **Control:** no payoff update; redemption remains $14.

The treatment is assigned to the whole market because traders share prices and
their decisions spill over to one another. The first five periods provide a
common pre-news path; periods 6–30 measure response after the payoff change.
Dividends and all other market rules remain constant.

## Prepare and run

Prepare each arm without model calls:

```bash
python3 edsl_replication/studies/asset_market_fundamental_news/experiment.py \
  --arm positive --replicate 1 \
  --output edsl_replication/studies/asset_market_fundamental_news/pilot_02/positive \
  --prepare-only
```

Replace `positive` with `negative` or `control`. To run locally with EDSL's
configured provider, omit `--prepare-only`. Use a new `--replicate` and output
directory for every independent market. Seeds are paired by replicate across
arms (`153100 + replicate`).

The corrected specifications and pilot outputs are stored in
`pilot_02/{positive,negative,control}`. Each arm has one completed 30-period
pilot. The first positive run is preserved in
`pilot_01/positive/` as a diagnostic only: a period guard made the news command
a no-op, so its prices and beliefs do not represent the positive-news condition.

The payoff updates shifted period-6 forecasts in the expected directions, but
none of the three pilots had crossing orders or trades. See the standalone
[`pilot_02/paper.pdf`](pilot_02/paper.pdf), detailed
[`pilot_02/analysis.md`](pilot_02/analysis.md), and
[`pilot_02/fundamental_news_machine.png`](pilot_02/fundamental_news_machine.png).

## Reading the evidence

The main outcomes are the change in traders' price forecasts from periods 5 to
6, the transaction-price path relative to the updated redemption amount, order
limits and sides, and trading volume. Markets are the independent units; the 12
traders within one shared market are not 12 independent replications. Pilot
sessions can reveal workflow or prompt problems but are not enough to establish
an effect. A larger number of independent markets per arm should be chosen from
a power analysis using pilot-level variation.

## Follow-up: narrow-spread price discovery

The original pilot forecasts moved after news, but the quotes did not cross:
at period 6 the best bid/ask were $19/$21 after positive news, $9.50/$10 after
negative news, and $13.90/$15 in control. The narrow_spread quote policy is
designed to produce observable transaction prices while leaving treatment
assignment and payoff rules unchanged. Buyers use their current-price forecast
plus $1.25 as their maximum buy limit; sellers use their forecast minus $1.25
as their minimum sell limit. Flexible traders use the same rule for either
side. The fixed offset applies in every arm, so any news response is compared
against the same quote policy in control.

Run one paired replicate (the same dividend and priority seed is used for all
three arms):

    for arm in positive negative control; do
      python3 edsl_replication/studies/asset_market_fundamental_news/experiment.py \
        --arm "$arm" --replicate 2 --quote-policy narrow_spread \
        --output "edsl_replication/studies/asset_market_fundamental_news/quote_overlap/replicate_02/$arm"
    done

Use another replicate number for each independent market set. Summarize a
completed set with:

    python3 edsl_replication/studies/asset_market_fundamental_news/summarize_pilots.py \
      --root edsl_replication/studies/asset_market_fundamental_news/quote_overlap/replicate_02

Compare the period-5-to-6 transaction price (and the first post-news trade if
there is no period-6 trade), trade volume, and allocation across the three
arms. Keep forecasts and submitted quotes as manipulation checks. The prior
pilot motivates the quote policy but is not pooled with this treatment; this
first follow-up is still a pilot, not a replicated treatment effect.

The completed run is documented in
[`quote_overlap/replicate_02/analysis.md`](quote_overlap/replicate_02/analysis.md),
with per-period transaction prices and volume in its `summary.json`. The
positive market's price rose from $14.40 in period 5 to $20.25 in period 6;
the negative market's first post-news trade was $8.35 in period 6 (no period-5
trade); and control moved from $14.40 to $14.48. Each treatment direction
appeared in one market, so these results demonstrate that the design can
produce observable prices but do not estimate a reliable treatment effect.

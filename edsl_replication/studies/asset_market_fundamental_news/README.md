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

# Midpoint private news asset market

## Design

This is an exploratory 30-period call market based on EDSL's typed asset-market
example. Twelve traders begin with the same cash and share endowment and trade
against a shared public tape. After period 15 settles, six traders selected by a
reproducible seed receive a private analyst update before period 16. The other
six receive no update. The update revises an analyst's estimate of terminal
redemption value from $14 to $16 per share; it is explicitly an estimate, while
the exchange still redeems every share for $14. The update is private and is
stored in the shared-state machine under the recipient's trader name.

The first run is a pilot of one market session. Traders' orders affect the
public tape, so the treatment can spill over to untreated traders through
prices. Interpret the pilot descriptively; it is not a clean estimate of a
direct information effect. No model calls are made by the preparation command.

## Run

From the repository root, prepare a serializable workflow and state-machine
specification:

```bash
python3 edsl_replication/studies/asset_market_midpoint_news/experiment.py \
  --output edsl_replication/studies/asset_market_midpoint_news/pilot_01 \
  --prepare-only
```

To execute, use the locally configured EDSL provider credentials:

```bash
python3 edsl_replication/studies/asset_market_midpoint_news/experiment.py \
  --output edsl_replication/studies/asset_market_midpoint_news/pilot_01
```

The run artifacts, including the serialized experiment, completion record, and
SQLite shared state, are written beneath the chosen output directory.

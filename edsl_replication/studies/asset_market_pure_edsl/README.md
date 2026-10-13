# Pure EDSL call-market prototype

This folder is a separate prototype for expressing call-market clearing as an
EDSL `Machine` without the native `call_market` factory or experiment-specific
runtime algorithms. `machine_definition.py` authors the machine from `Machine`,
`Command`, state fields, and serializable EDSL expressions. Its
`algorithms` declaration is empty.

## Market currently represented

- Four named traders, five periods, and two shares per trader at the start.
- Each trader submits one buy, sell, or hold order per period.
- A buy or sell order represents one share; cash and inventory bounds are
  checked when the order is submitted.
- The EDSL expression tree sorts bids and asks by price and then seat, scans
  price-priority pairs with `iterate`, chooses a marginal midpoint in cents,
  and updates both traders' accounts using `map_items`.
- No crossing orders means zero volume and no cash/share transfer.
- The market repeats until the configured final period.

This is deliberately a narrow clearing prototype. It leaves out dividends,
interest, terminal redemption, random tie-breaking, and quantity orders. Those
can be added after checking how readable and maintainable the DSL expressions
remain. Python is used to author/combine expression objects and initialize the
machine; the submitted machine contains no Python callbacks or custom
algorithm registrations. The EDSL runtime still interprets its standard
operators.

## Build a diagram

From the repository root:

```sh
python3 edsl_replication/studies/asset_market_pure_edsl/machine_definition.py \
  --diagram edsl_replication/studies/asset_market_pure_edsl/call_market_machine.png
```

The builder calls `Machine.validate()` before returning the machine.

## Run one illustrative clearing

```sh
python3 edsl_replication/studies/asset_market_pure_edsl/run_smoke.py
```

The example submits a $10 buy limit and a $9 ask. It should clear one share at
$9.50 and transfer cash and inventory through the machine's expression-defined
settlement. The standard EDSL interpreter runs this without registering market
callbacks.

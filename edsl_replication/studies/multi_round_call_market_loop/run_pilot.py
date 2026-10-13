"""Run the entire multi-round pilot with one generic Machine close call."""

from __future__ import annotations

import json

from edsl.sharedstate import Runtime

from machine_definition import build_machine


def main():
    machine = build_machine()
    runtime = Runtime()
    initial_state = runtime.initial_state(machine)
    result = runtime.close_result(machine, initial_state)
    if result.event["status"] != "applied":
        raise RuntimeError(f"Machine close did not apply: {result.event}")

    market = result.state["market"]
    report = {
        "rounds": len(market["tape"]),
        "crossing_rounds": sum(row["crossed"] for row in market["tape"]),
        "volumes": [row["volume"] for row in market["tape"]],
        "transaction_prices_cents": [row["price_cents"] for row in market["tape"]],
        "accounts": market["accounts"],
        "total_cash_cents": sum(
            account["cash_cents"] for account in market["accounts"].values()
        ),
        "total_shares": sum(
            account["shares"] for account in market["accounts"].values()
        ),
        "finished": market["finished"],
        "python_round_driver_calls": 0,
        "machine_close_calls": 1,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

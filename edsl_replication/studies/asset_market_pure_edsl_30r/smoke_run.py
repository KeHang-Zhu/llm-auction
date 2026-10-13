"""Run a deterministic full-horizon order path through the pure EDSL Machine."""

from __future__ import annotations

from edsl.sharedstate import ExecutionLimits, Runtime

from machine_definition import PERIODS, TRADERS, build_machine


def main():
    runtime = Runtime(limits=ExecutionLimits(max_steps=10_000_000))
    machine = build_machine(seed=153101)
    state = runtime.initial_state(machine)

    for period in range(1, PERIODS + 1):
        for seat, trader in enumerate(TRADERS):
            if seat < 4:
                decision = {"side": "buy", "price_cents": 1500, "quantity": 1}
            elif seat < 8:
                decision = {"side": "sell", "price_cents": 1400, "quantity": 1}
            else:
                decision = {"side": "hold", "price_cents": 0, "quantity": 0}
            state = runtime.execute(
                machine,
                state,
                "submit_order",
                {"trader": trader, "period": period, "decision": decision},
            ).state
        state = runtime.execute(
            machine, state, "clear_orders", {"period": period}
        ).state
        state = runtime.execute(machine, state, "settle", {"period": period}).state
        print(f"completed period {period}/{PERIODS}", flush=True)

    accounts = state["accounts"]
    summary = {
        "periods": len(state["tape"]),
        "orders": len(state["order_log"]),
        "trades": sum(row["volume"] for row in state["tape"]),
        "finished": state["finished"],
        "remaining_shares": sum(row["shares"] for row in accounts.values()),
        "redeemed_shares": sum(row["redeemed_shares"] for row in accounts.values()),
        "total_cash_cents": sum(row["cash_cents"] for row in accounts.values()),
        "final_period": state["period"],
    }
    print(summary)
    assert summary["periods"] == PERIODS
    assert summary["orders"] == len(TRADERS) * PERIODS
    assert summary["finished"] is True
    assert summary["remaining_shares"] == 0
    assert summary["redeemed_shares"] == len(TRADERS) * 4


if __name__ == "__main__":
    main()

"""Run one illustrative period through the standard EDSL DSL interpreter."""

from edsl.sharedstate import Runtime

from machine_definition import build_machine


def main():
    machine = build_machine()
    runtime = Runtime()
    state = runtime.initial_state(machine)
    orders = (
        ("trader-00", "buy", 1_000),
        ("trader-01", "sell", 900),
        ("trader-02", "hold", 0),
        ("trader-03", "hold", 0),
    )
    for trader, side, limit_cents in orders:
        state = runtime.execute(
            machine,
            state,
            "submit_order",
            {
                "trader": trader,
                "period": 1,
                "side": side,
                "limit_cents": limit_cents,
            },
        ).state
    state = runtime.execute(machine, state, "settle", {"period": 1}).state
    print("Registered market algorithms:", machine.algorithms)
    print("Period 1:", state["tape"][-1])
    print("Buyer account:", state["accounts"]["trader-00"])
    print("Seller account:", state["accounts"]["trader-01"])


if __name__ == "__main__":
    main()

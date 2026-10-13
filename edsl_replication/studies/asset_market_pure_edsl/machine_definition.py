"""A small repeated call market expressed without custom algorithms.

All clearing and balance changes are EDSL expressions attached to Machine
commands. This is an authoring module; it does not register Python runtime
algorithms.
"""

from edsl.sharedstate import (
    Command,
    Machine,
    StateType,
    arg,
    assign,
    choose,
    constant,
    current,
    expr,
    field,
    filter_items,
    iterate,
    let,
    local,
    map_items,
    record,
    reduce,
    round_ratio,
    state_field,
    take,
    put,
)


TRADERS = ("trader-00", "trader-01", "trader-02", "trader-03")
PERIODS = 5
INITIAL_CASH_CENTS = 10_000
INITIAL_SHARES = 2


def _sorted_orders(side: str, descending_price: bool):
    return reduce(
        "sort_records",
        filter_items(
            field("orders").values(),
            item="order",
            predicate=local("order").get("side") == side,
        ),
        fields=("limit_cents", "seat"),
        descending=(descending_price, False),
    )


def _scan_state(bids, asks):
    """Count crossing one-share orders in price priority using EDSL iterate."""
    return iterate(
        record(index=0, volume=0),
        state="scan",
        until=(
            (local("scan").get("index") >= bids.length())
            | (local("scan").get("index") >= asks.length())
            | (
                bids.at(local("scan").get("index")).get("limit_cents")
                < asks.at(local("scan").get("index")).get("limit_cents")
            )
        ),
        step=record(
            index=local("scan").get("index") + 1,
            volume=local("scan").get("volume") + 1,
        ),
        max_steps=constant("trader_count"),
    )


def _with_clearance(body):
    """Bind ranked sides and clearing result inside an expression tree."""
    return let(
        "ranked_bids",
        _sorted_orders("buy", True),
        let(
            "ranked_asks",
            _sorted_orders("sell", False),
            let(
                "scan_result",
                _scan_state(local("ranked_bids"), local("ranked_asks")),
                body,
            ),
        ),
    )


def _clearance_record():
    volume = local("scan_result").get("volume")
    price = choose(
        volume > 0,
        round_ratio(
            local("ranked_bids").at(volume - 1).get("limit_cents")
            + local("ranked_asks").at(volume - 1).get("limit_cents"),
            2,
            rounding="half_up",
        ),
        0,
    )
    return record(
        volume=volume,
        price_cents=price,
        matched_bids=take(local("ranked_bids"), volume),
        matched_asks=take(local("ranked_asks"), volume),
    )


def _accounts_after_clear():
    return _with_clearance(
        map_items(
            field("accounts"),
            key="trader",
            value="account",
            key_expr=local("trader"),
            value_expr=let(
                "order",
                field("orders").get(local("trader")),
                let(
                    "clearing",
                    _clearance_record(),
                    local("account")
                    .with_item(
                        "cash_cents",
                        local("account").get("cash_cents")
                        + choose(
                            local("clearing").get("matched_bids").contains(local("order")),
                            expr("subtract", 0, local("clearing").get("price_cents")),
                            choose(
                                local("clearing").get("matched_asks").contains(local("order")),
                                local("clearing").get("price_cents"),
                                0,
                            ),
                        ),
                    )
                    .with_item(
                        "shares",
                        local("account").get("shares")
                        + choose(
                            local("clearing").get("matched_bids").contains(local("order")),
                            1,
                            choose(
                                local("clearing").get("matched_asks").contains(local("order")),
                                0 - 1,
                                0,
                            ),
                        ),
                    ),
                ),
            ),
        )
    )


def _tape_after_clear():
    return _with_clearance(
        field("tape").appended(
            let(
                "clearing",
                _clearance_record(),
                record(
                    period=field("period"),
                    volume=local("clearing").get("volume"),
                    price_cents=choose(
                        local("clearing").get("volume") > 0,
                        local("clearing").get("price_cents"),
                        None,
                    ),
                    best_bid_cents=choose(
                        local("ranked_bids").length() > 0,
                        local("ranked_bids").first().get("limit_cents"),
                        None,
                    ),
                    best_ask_cents=choose(
                        local("ranked_asks").length() > 0,
                        local("ranked_asks").first().get("limit_cents"),
                        None,
                    ),
                ),
            )
        )
    )


def build_machine() -> Machine:
    traders = list(TRADERS)
    seats = {trader: seat for seat, trader in enumerate(TRADERS)}
    machine = Machine(
        name="PureEDSLCallMarket",
        constants={
            "traders": traders,
            "trader_count": len(traders),
            "periods": PERIODS,
        },
        fields={
            "accounts": state_field(
                StateType.map(),
                {
                    trader: {
                        "seat": seats[trader],
                        "cash_cents": INITIAL_CASH_CENTS,
                        "shares": INITIAL_SHARES,
                    }
                    for trader in TRADERS
                },
            ),
            "orders": state_field(StateType.map(), {}),
            "tape": state_field(StateType.sequence(), []),
            "period": state_field(StateType.integer(minimum=1), 1),
            "last_price_cents": state_field(
                StateType.optional(StateType.integer(minimum=0)), None
            ),
            "finished": state_field(StateType.boolean(), False),
        },
        commands={
            "submit_order": Command(
                inputs={
                    "trader": StateType.text(),
                    "period": StateType.integer(minimum=1),
                    "side": StateType.choice(("buy", "sell", "hold")),
                    "limit_cents": StateType.integer(minimum=0),
                },
                require=(
                    (~field("finished"))
                    & (arg("period") == field("period"))
                    & field("accounts").contains(arg("trader"))
                    & (~field("orders").contains(arg("trader")))
                    & choose(
                        arg("side") == "hold",
                        arg("limit_cents") == 0,
                        choose(
                            arg("side") == "buy",
                            (arg("limit_cents") > 0)
                            & (
                                field("accounts").get(arg("trader")).get("cash_cents")
                                >= arg("limit_cents")
                            ),
                            (arg("limit_cents") > 0)
                            & (field("accounts").get(arg("trader")).get("shares") > 0),
                        ),
                    )
                ),
                effects=(
                    put(
                        "orders",
                        arg("trader"),
                        record(
                            trader=arg("trader"),
                            seat=field("accounts").get(arg("trader")).get("seat"),
                            side=arg("side"),
                            limit_cents=arg("limit_cents"),
                        ),
                        once=True,
                    ),
                ),
            ),
            "settle": Command(
                inputs={"period": StateType.integer(minimum=1)},
                require=(
                    (~field("finished"))
                    & (arg("period") == field("period"))
                    & (field("orders").length() == constant("trader_count"))
                ),
                effects=(
                    assign("accounts", _accounts_after_clear()),
                    assign("tape", _tape_after_clear()),
                    assign("last_price_cents", choose(
                        _with_clearance(
                            local("scan_result").get("volume") > 0
                        ),
                        _with_clearance(
                            round_ratio(
                                local("ranked_bids").at(
                                    local("scan_result").get("volume") - 1
                                ).get("limit_cents")
                                + local("ranked_asks").at(
                                    local("scan_result").get("volume") - 1
                                ).get("limit_cents"),
                                2,
                                rounding="half_up",
                            )
                        ),
                        field("last_price_cents"),
                    )),
                    assign("orders", {}),
                    assign("finished", field("period") == constant("periods")),
                    assign("period", field("period") + 1),
                ),
            ),
        },
        view={
            "period": field("period"),
            "tape": field("tape"),
            "your_account": field("accounts").get(current("name")),
            "finished": field("finished"),
        },
        algorithms=(),
    )
    machine.validate()
    return machine


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagram", help="write the Machine diagram to this PNG")
    args = parser.parse_args()
    market = build_machine()
    if args.diagram:
        market.show_diagram(args.diagram, renderer="pydot", detail=True)
    print(f"Built {market.name}; registered custom algorithms: {market.algorithms}")

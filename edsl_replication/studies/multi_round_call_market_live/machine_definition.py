"""Two-round call market with EDSL-native order admission and settlement."""

from __future__ import annotations

from edsl.sharedstate import (
    Command,
    Machine,
    StateType,
    arg,
    assign,
    choose,
    constant,
    current,
    field,
    filter_items,
    let,
    local,
    map_items,
    put,
    record,
    reduce,
    round_ratio,
    state_field,
)


TRADERS = ("trader-A", "trader-B", "trader-C", "trader-D")
ROUNDS = 2
INITIAL_CASH_CENTS = 2_000
INITIAL_SHARES = 1


def _best_orders(side: str):
    """Rank eligible one-unit orders, with a sentinel for an empty side."""
    orders = filter_items(
        field("orders").values(),
        item="order",
        predicate=(local("order").get("side") == side)
        & local("order").get("eligible"),
    )
    sentinel_price = 0 if side == "buy" else 100_000_000
    sentinel = record(
        trader=None,
        seat=999,
        side=side,
        price_cents=sentinel_price,
        eligible=False,
    )
    return reduce(
        "sort_records",
        orders.appended(sentinel),
        fields=("price_cents", "seat"),
        descending=(side == "buy", False),
    )


def _clearing_record():
    raw_bids = filter_items(
        field("orders").values(),
        item="order",
        predicate=(local("order").get("side") == "buy")
        & local("order").get("eligible"),
    )
    raw_asks = filter_items(
        field("orders").values(),
        item="order",
        predicate=(local("order").get("side") == "sell")
        & local("order").get("eligible"),
    )
    bid = local("ranked_bids").first()
    ask = local("ranked_asks").first()
    crossed = (local("raw_bids").length() > 0) & (
        local("raw_asks").length() > 0
    ) & (bid.get("price_cents") >= ask.get("price_cents"))
    price = round_ratio(
        bid.get("price_cents") + ask.get("price_cents"),
        2,
        rounding="half_up",
    )
    return let(
        "raw_bids",
        raw_bids,
        let(
            "raw_asks",
            raw_asks,
            let(
                "ranked_bids",
                _best_orders("buy"),
                let(
                    "ranked_asks",
                    _best_orders("sell"),
                    let(
                        "crossed",
                        crossed,
                        let(
                            "price_cents",
                            price,
                            record(
                                round=field("round"),
                                orders=field("orders").values(),
                                best_bid=bid,
                                best_ask=ask,
                                crossed=local("crossed"),
                                volume=choose(local("crossed"), 1, 0),
                                price_cents=choose(
                                    local("crossed"), local("price_cents"), None
                                ),
                                buyer=choose(
                                    local("crossed"), bid.get("trader"), None
                                ),
                                seller=choose(
                                    local("crossed"), ask.get("trader"), None
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _settled_accounts():
    clearing = field("clearing")
    buyer = clearing.get("buyer")
    seller = clearing.get("seller")
    price = clearing.get("price_cents", 0)
    return map_items(
        field("accounts"),
        key="trader",
        value="account",
        key_expr=local("trader"),
        value_expr=local("account")
        .with_item(
            "cash_cents",
            local("account").get("cash_cents")
            + choose(
                (clearing.get("volume") > 0) & (local("trader") == seller),
                price,
                0,
            )
            - choose(
                (clearing.get("volume") > 0) & (local("trader") == buyer),
                price,
                0,
            ),
        )
        .with_item(
            "shares",
            local("account").get("shares")
            + choose(
                (clearing.get("volume") > 0) & (local("trader") == buyer),
                1,
                0,
            )
            - choose(
                (clearing.get("volume") > 0) & (local("trader") == seller),
                1,
                0,
            ),
        )
        .with_item(
            "history",
            local("account").get("history").appended(
                record(
                    round=clearing.get("round"),
                    side=field("orders").get(local("trader")).get("side"),
                    limit_cents=field("orders")
                    .get(local("trader"))
                    .get("price_cents"),
                    eligible=field("orders").get(local("trader")).get("eligible"),
                    fill=choose(
                        (clearing.get("volume") > 0)
                        & (local("trader") == buyer),
                        1,
                        choose(
                            (clearing.get("volume") > 0)
                            & (local("trader") == seller),
                            -1,
                            0,
                        ),
                    ),
                    transaction_price_cents=clearing.get("price_cents"),
                )
            ),
        ),
    )


def build_machine() -> Machine:
    seats = {trader: seat for seat, trader in enumerate(TRADERS)}
    initial_accounts = {
        trader: {
            "seat": seats[trader],
            "cash_cents": INITIAL_CASH_CENTS,
            "shares": INITIAL_SHARES,
            "history": [],
        }
        for trader in TRADERS
    }
    machine = Machine(
        name="LiveDecisionMultiRoundCallMarket",
        constants={
            "rounds": ROUNDS,
            "traders": list(TRADERS),
            "trader_count": len(TRADERS),
            "initial_accounts": initial_accounts,
        },
        fields={
            "accounts": state_field(StateType.map(), initial_accounts),
            "orders": state_field(StateType.map(), {}),
            "clearing": state_field(
                StateType.optional(StateType.map()), None
            ),
            "tape": state_field(StateType.sequence(), []),
            # EDSL arithmetic widens integer addition to number.
            "round": state_field(StateType.number(minimum=1), 1),
            "last_price_cents": state_field(
                StateType.integer(minimum=0), 1_200
            ),
            "finished": state_field(StateType.boolean(), False),
        },
        commands={
            "submit_order": Command(
                inputs={
                    "trader": StateType.text(),
                    "decision": StateType.map(),
                },
                require=(
                    (~field("finished"))
                    & field("accounts").contains(arg("trader"))
                    & (~field("orders").contains(arg("trader")))
                    & (
                        (
                            (arg("decision").get("side") == "hold")
                            & (arg("decision").get("price_cents") == 0)
                        )
                        | (
                            (
                                (arg("decision").get("side") == "buy")
                                | (arg("decision").get("side") == "sell")
                            )
                            & (arg("decision").get("price_cents") > 0)
                            & (arg("decision").get("price_cents") <= 100_000_000)
                        )
                    )
                ),
                effects=(
                    put(
                        "orders",
                        arg("trader"),
                        let(
                            "trader",
                            arg("trader"),
                            let(
                                "side",
                                arg("decision").get("side"),
                                let(
                                    "price_cents",
                                    arg("decision").get("price_cents"),
                                    record(
                                        trader=local("trader"),
                                        seat=field("accounts")
                                        .get(local("trader"))
                                        .get("seat"),
                                        round=field("round"),
                                        side=local("side"),
                                        price_cents=local("price_cents"),
                                        eligible=choose(
                                            local("side") == "buy",
                                            field("accounts")
                                            .get(local("trader"))
                                            .get("cash_cents")
                                            >= local("price_cents"),
                                            choose(
                                                local("side") == "sell",
                                                field("accounts")
                                                .get(local("trader"))
                                                .get("shares")
                                                >= 1,
                                                True,
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        once=True,
                    ),
                ),
            ),
            "clear_orders": Command(
                inputs={},
                require=(
                    (~field("finished"))
                    & (field("orders").length() == constant("trader_count"))
                    & (field("clearing") == None)
                ),
                effects=(assign("clearing", _clearing_record()),),
            ),
            "settle_round": Command(
                inputs={},
                require=(
                    (~field("finished"))
                    & (field("clearing") != None)
                ),
                effects=(
                    assign("accounts", _settled_accounts()),
                    assign("tape", field("tape").appended(field("clearing"))),
                    assign(
                        "last_price_cents",
                        choose(
                            field("clearing").get("volume") > 0,
                            field("clearing").get("price_cents"),
                            field("last_price_cents"),
                        ),
                    ),
                    assign("orders", {}),
                    assign("clearing", None),
                    assign("finished", field("round") == constant("rounds")),
                    assign("round", field("round") + 1),
                ),
            ),
        },
        view={
            "round": field("round"),
            "rounds": constant("rounds"),
            "tape": field("tape"),
            "last_price_cents": field("last_price_cents"),
            "your_account": field("accounts").get(current("name")),
            "finished": field("finished"),
        },
        complete_when=field("finished"),
        algorithms=(),
    )
    machine.validate()
    return machine

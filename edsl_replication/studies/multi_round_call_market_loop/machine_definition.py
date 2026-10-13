"""A compact multi-round call market driven by an EDSL Machine loop.

The three-round order path is an explicit constant so this pilot isolates the
runner question: can one generic Machine close execute round selection,
matching, settlement, and state carryover without a Python round driver?
"""

from __future__ import annotations

from edsl.sharedstate import (
    Machine,
    StateType,
    assign,
    choose,
    constant,
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
)


TRADERS = ("trader-A", "trader-B", "trader-C", "trader-D")
INITIAL_CASH_CENTS = 2_000
INITIAL_SHARES = 1


def _market_type():
    return StateType.record(
        {
            # The expression type checker treats integer addition as number;
            # using number here keeps the loop accumulator invariant explicit.
            "round": StateType.number(minimum=1),
            "accounts": StateType.map(),
            "tape": StateType.sequence(),
            "finished": StateType.boolean(),
        }
    )


def _initial_market():
    return {
        "round": 1,
        "accounts": {
            trader: {"cash_cents": INITIAL_CASH_CENTS, "shares": INITIAL_SHARES}
            for trader in TRADERS
        },
        "tape": [],
        "finished": False,
    }


def _best_orders(side: str):
    return reduce(
        "sort_records",
        filter_items(
            local("orders"),
            item="order",
            predicate=local("order").get("side") == side,
        ),
        fields=("price_cents", "seat"),
        descending=(side == "buy", False),
    )


def _round_step():
    market = local("market")
    round_number = market.get("round")
    round_orders = constant("order_schedule").at(round_number - 1)
    bids = _best_orders("buy")
    asks = _best_orders("sell")
    best_bid = bids.first()
    best_ask = asks.first()
    crossed = best_bid.get("price_cents") >= best_ask.get("price_cents")
    price_cents = round_ratio(
        best_bid.get("price_cents") + best_ask.get("price_cents"),
        2,
        rounding="half_up",
    )
    buyer = best_bid.get("trader")
    seller = best_ask.get("trader")

    accounts_after = map_items(
        market.get("accounts"),
        key="trader",
        value="account",
        key_expr=local("trader"),
        value_expr=local("account")
        .with_item(
            "cash_cents",
            local("account").get("cash_cents")
            + choose(
                crossed & (local("trader") == seller), price_cents, 0
            )
            - choose(
                crossed & (local("trader") == buyer), price_cents, 0
            ),
        )
        .with_item(
            "shares",
            local("account").get("shares")
            + choose(crossed & (local("trader") == buyer), 1, 0)
            - choose(crossed & (local("trader") == seller), 1, 0),
        ),
    )
    round_record = record(
        round=round_number,
        orders=round_orders,
        best_bid=best_bid,
        best_ask=best_ask,
        crossed=crossed,
        volume=choose(crossed, 1, 0),
        price_cents=choose(crossed, price_cents, None),
        buyer=choose(crossed, buyer, None),
        seller=choose(crossed, seller, None),
        accounts_after=accounts_after,
    )
    next_market = record(
        round=round_number + 1,
        accounts=accounts_after,
        tape=market.get("tape").appended(round_record),
        finished=round_number == constant("round_count"),
    )
    return let(
        "orders",
        round_orders,
        let(
            "bids",
            bids,
            let(
                "asks",
                asks,
                let(
                    "best_bid",
                    best_bid,
                    let(
                        "best_ask",
                        best_ask,
                        let(
                            "crossed",
                            crossed,
                            let("price_cents", price_cents, next_market),
                        ),
                    ),
                ),
            ),
        ),
    )


def _market_loop():
    state = local("market")
    loop = iterate(
        constant("initial_market"),
        state="market",
        state_type=_market_type(),
        until=state.get("round") > constant("round_count"),
        step=_round_step(),
        max_steps=constant("round_count"),
    )
    return loop.with_item("finished", True)


def build_machine() -> Machine:
    """Build a Machine whose close effects autonomously run three rounds."""
    order_schedule = [
        [
            {"trader": "trader-A", "seat": 0, "side": "buy", "price_cents": 1_100},
            {"trader": "trader-B", "seat": 1, "side": "sell", "price_cents": 1_000},
        ],
        [
            {"trader": "trader-C", "seat": 2, "side": "buy", "price_cents": 900},
            {"trader": "trader-D", "seat": 3, "side": "sell", "price_cents": 1_200},
        ],
        [
            {"trader": "trader-B", "seat": 1, "side": "buy", "price_cents": 1_300},
            {"trader": "trader-A", "seat": 0, "side": "sell", "price_cents": 1_200},
        ],
    ]
    initial = _initial_market()
    machine = Machine(
        name="MultiRoundCallMarketLoopPilot",
        constants={
            "traders": list(TRADERS),
            "round_count": len(order_schedule),
            "order_schedule": order_schedule,
            "initial_market": initial,
        },
        fields={"market": state_field(_market_type(), initial)},
        commands={},
        view={
            "round": field("market").get("round"),
            "tape": field("market").get("tape"),
            "accounts": field("market").get("accounts"),
            "finished": field("market").get("finished"),
        },
        close_effects=(
            # The runner calls close once; the round loop stays in this
            # serialized EDSL expression rather than a Python driver.
            assign("market", _market_loop()),
        ),
        complete_when=field("market").get("finished"),
        algorithms=(),
    )
    machine.validate()
    return machine

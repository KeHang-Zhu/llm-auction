"""Full 30-period call market authored as a callback-free EDSL Machine.

Python builds the serializable expression tree and precomputes the exogenous
random schedules. All order admission, clearing, transfers, income, and final
redemption are Machine command expressions; ``algorithms`` is empty.
"""

from __future__ import annotations

import random

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
    fold,
    expr,
    iterate,
    let,
    local,
    map_items,
    map_sequence,
    put,
    record,
    reduce,
    round_ratio,
    state_field,
    take,
)


TRADERS = tuple(f"trader-{seat:02d}" for seat in range(12))
PERIODS = 30
INITIAL_CASH_CENTS = 10_000
INITIAL_SHARES = 4
INITIAL_REFERENCE_CENTS = 1_400
REDEMPTION_CENTS = 1_400
INTEREST_NUMERATOR = 5
INTEREST_DENOMINATOR = 100
DIVIDEND_VALUES_CENTS = (40, 100)


def _minimum(left, right):
    return choose(left <= right, left, right)


def _priority_schedule(seed: int, traders=TRADERS, periods: int = PERIODS):
    schedule = []
    for period in range(1, periods + 1):
        priority_order = list(traders)
        random.Random(f"{seed}:priority:{period}").shuffle(priority_order)
        schedule.append({trader: rank for rank, trader in enumerate(priority_order)})
    return schedule


def _dividend_schedule(seed: int, periods: int = PERIODS):
    return [
        random.Random(f"{seed}:dividend:{period}").choice(DIVIDEND_VALUES_CENTS)
        for period in range(1, periods + 1)
    ]


def _admitted_order():
    decision = local("decision")
    side = decision.get("side")
    price = decision.get("price_cents")
    quantity = decision.get("quantity")
    valid = choose(
        side == "hold",
        (price == 0) & (quantity == 0),
        ((side == "buy") | (side == "sell"))
        & (price > 0)
        & (quantity > 0),
    )
    account = field("accounts").get(local("trader"))
    affordable = round_ratio(
        account.get("cash_cents"), price, rounding="floor"
    )
    buy_quantity = _minimum(
        quantity,
        _minimum(affordable, constant("maximum_buy_quantity")),
    )
    sell_quantity = _minimum(quantity, account.get("shares"))
    accepted_quantity = choose(
        valid,
        choose(side == "buy", buy_quantity, choose(side == "sell", sell_quantity, 0)),
        0,
    )
    return record(
        trader=local("trader"),
        seat=account.get("seat"),
        priority=constant("priority_schedule")
        .at(field("period") - 1)
        .get(local("trader")),
        period=field("period"),
        decision=decision,
        side=side,
        limit_cents=choose(valid, price, 0),
        accepted_quantity=accepted_quantity,
        rejection=choose(valid, None, "invalid order"),
    )


def _expanded_units(side: str):
    ordered = reduce(
        "sort_records",
        filter_items(
            field("orders").values(),
            item="order",
            predicate=(local("order").get("side") == side)
            & (local("order").get("accepted_quantity") > 0),
        ),
        fields=("limit_cents", "priority"),
        descending=(side == "buy", False),
    )
    return fold(
        ordered,
        [],
        item="order",
        accumulator="units",
        body=let(
            "expanded",
            iterate(
                record(index=0, result=local("units")),
                state="unit_cursor",
                until=(
                    local("unit_cursor").get("index")
                    >= local("order").get("accepted_quantity")
                ),
                step=record(
                    index=local("unit_cursor").get("index") + 1,
                    result=local("unit_cursor").get("result").appended(
                        record(
                            trader=local("order").get("trader"),
                            seat=local("order").get("seat"),
                            priority=local("order").get("priority"),
                            limit_cents=local("order").get("limit_cents"),
                            unit_index=local("unit_cursor").get("index"),
                        )
                    ),
                ),
                max_steps=constant("maximum_buy_quantity"),
            ),
            local("expanded").get("result"),
        ),
    )


def _ranked_units(side: str):
    return reduce(
        "sort_records",
        _expanded_units(side),
        fields=("limit_cents", "priority", "unit_index"),
        descending=(side == "buy", False, False),
    )


def _volume_scan():
    bids, asks = local("ranked_bids"), local("ranked_asks")
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
        max_steps=constant("total_shares"),
    )


def _with_clearing(body):
    volume = local("scan_result").get("volume")
    marginal_bid = local("ranked_bids").at(volume - 1).get("limit_cents")
    marginal_ask = local("ranked_asks").at(volume - 1).get("limit_cents")
    price = choose(
        volume > 0,
        round_ratio(marginal_bid + marginal_ask, 2, rounding="half_up"),
        0,
    )
    return let(
        "ranked_bids",
        _ranked_units("buy"),
        let(
            "ranked_asks",
            _ranked_units("sell"),
            let(
                "scan_result",
                _volume_scan(),
                let(
                    "volume",
                    volume,
                    let(
                        "price_cents",
                        price,
                        let(
                            "matched_bids",
                            take(local("ranked_bids"), volume),
                            let(
                                "matched_asks",
                                take(local("ranked_asks"), volume),
                                let(
                                    "buy_fills",
                                    reduce(
                                        "count_by",
                                        map_sequence(
                                            local("matched_bids"),
                                            item="unit",
                                            value_expr=local("unit").get("trader"),
                                        ),
                                    ),
                                    let(
                                        "sell_fills",
                                        reduce(
                                            "count_by",
                                            map_sequence(
                                                local("matched_asks"),
                                                item="unit",
                                                value_expr=local("unit").get("trader"),
                                            ),
                                        ),
                                        body,
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _clearing_record():
    return _with_clearing(
        record(
            volume=local("volume"),
            price_cents=local("price_cents"),
            matched_bids=local("matched_bids"),
            matched_asks=local("matched_asks"),
            buy_fills=local("buy_fills"),
            sell_fills=local("sell_fills"),
        )
    )


def _updated_accounts():
    def updated_account():
        buy_fill = field("clearing").get("buy_fills").get(local("trader"), 0)
        sell_fill = field("clearing").get("sell_fills").get(local("trader"), 0)
        traded_cash = local("account").get("cash_cents") + (
            sell_fill - buy_fill
        ) * field("clearing").get("price_cents")
        traded_shares = (
            local("account").get("shares") + buy_fill - sell_fill
        )
        interest = round_ratio(
            traded_cash * constant("interest_numerator"),
            constant("interest_denominator"),
            rounding="half_up",
        )
        dividend = constant("dividend_schedule").at(field("period") - 1)
        final_period = field("period") == constant("periods")
        income_cash = traded_cash + interest + dividend * traded_shares
        redemption = choose(
            final_period,
            traded_shares * constant("redemption_cents"),
            0,
        )
        order = field("orders").get(local("trader"))
        signed_fill = choose(
            order.get("side") == "buy",
            buy_fill,
            choose(
                order.get("side") == "sell",
                expr("subtract", 0, sell_fill),
                0,
            ),
        )
        history_row = record(
            period=field("period"),
            decision=order.get("decision"),
            side=order.get("side"),
            limit_cents=order.get("limit_cents"),
            accepted_quantity=order.get("accepted_quantity"),
            rejection=order.get("rejection"),
            fill=signed_fill,
            transaction_price=choose(
                field("clearing").get("volume") > 0,
                field("clearing").get("price_cents") / 100,
                None,
            ),
            interest=interest / 100,
            interest_cents=interest,
            dividend_per_share=dividend / 100,
            cash_after_income_cents=income_cash,
            redemption_cents=redemption,
        )
        return (
            local("account")
            .with_item("cash_cents", income_cash + redemption)
            .with_item(
                "shares",
                choose(final_period, 0, traded_shares),
            )
            .with_item(
                "redeemed_shares",
                choose(final_period, traded_shares, local("account").get("redeemed_shares")),
            )
            .with_item(
                "history",
                local("account").get("history").appended(history_row),
            )
        )

    return map_items(
        field("accounts"),
        key="trader",
        value="account",
        key_expr=local("trader"),
        value_expr=updated_account(),
    )


def _order_log_after_clear():
    ordered = reduce(
        "sort_records",
        field("orders").values(),
        fields=("seat",),
        descending=(False,),
    )
    rows = map_sequence(
        ordered,
        item="order",
        value_expr=let(
            "buy_fill",
            field("clearing").get("buy_fills").get(local("order").get("trader"), 0),
            let(
                "sell_fill",
                field("clearing").get("sell_fills").get(local("order").get("trader"), 0),
                local("order")
                .with_item(
                    "fill",
                    choose(
                        local("order").get("side") == "buy",
                        local("buy_fill"),
                        choose(
                            local("order").get("side") == "sell",
                            expr("subtract", 0, local("sell_fill")),
                            0,
                        ),
                    ),
                )
                .with_item(
                    "transaction_price",
                    choose(
                        field("clearing").get("volume") > 0,
                        field("clearing").get("price_cents") / 100,
                        None,
                    ),
                ),
            ),
        ),
    )
    return fold(
        rows,
        field("order_log"),
        item="row",
        accumulator="log",
        body=local("log").appended(local("row")),
    )


def _tape_after_clear():
    accounts_after = _updated_accounts()
    return let(
        "accounts_after",
        accounts_after,
        let(
            "recent_accounts",
            map_sequence(
                local("accounts_after").values(),
                item="account",
                value_expr=local("account").get("history").at(-1),
            ),
            let(
                "interest_total",
                reduce(
                    "sum",
                    map_sequence(
                        local("recent_accounts"),
                        item="row",
                        value_expr=local("row").get("interest_cents"),
                    ),
                ),
                let(
                    "cash_total_pre_redemption",
                    reduce(
                        "sum",
                        map_sequence(
                            local("recent_accounts"),
                            item="row",
                            value_expr=local("row").get("cash_after_income_cents"),
                        ),
                    ),
                    field("tape").appended(
                        record(
                            period=field("period"),
                            price=choose(
                                field("clearing").get("volume") > 0,
                                field("clearing").get("price_cents") / 100,
                                None,
                            ),
                            reference_price=choose(
                                field("clearing").get("volume") > 0,
                                field("clearing").get("price_cents") / 100,
                                field("last_price_cents") / 100,
                            ),
                            volume=field("clearing").get("volume"),
                            dividend=constant("dividend_schedule").at(
                                field("period") - 1
                            )
                            / 100,
                            total_interest=local("interest_total") / 100,
                            total_cash=local("cash_total_pre_redemption") / 100,
                            total_shares=constant("total_shares"),
                        )
                    ),
                ),
            ),
        ),
    )


def build_machine(
    seed: int = 153101, traders=TRADERS, periods: int = PERIODS
) -> Machine:
    traders = tuple(traders)
    if not traders:
        raise ValueError("at least one trader is required")
    if periods < 1:
        raise ValueError("periods must be at least 1")
    seats = {trader: seat for seat, trader in enumerate(traders)}
    constants = {
        "seed": seed,
        "periods": periods,
        "traders": list(traders),
        "trader_count": len(traders),
        "total_shares": len(traders) * INITIAL_SHARES,
        "maximum_buy_quantity": len(traders) * INITIAL_SHARES,
        "initial_reference_cents": INITIAL_REFERENCE_CENTS,
        "redemption_cents": REDEMPTION_CENTS,
        "interest_numerator": INTEREST_NUMERATOR,
        "interest_denominator": INTEREST_DENOMINATOR,
        "dividend_schedule": _dividend_schedule(seed, periods),
        "priority_schedule": _priority_schedule(seed, traders, periods),
    }
    machine = Machine(
        name="PureEDSLCallMarket30Round",
        constants=constants,
        fields={
            "accounts": state_field(
                StateType.map(),
                {
                    trader: {
                        "seat": seats[trader],
                        "cash_cents": INITIAL_CASH_CENTS,
                        "shares": INITIAL_SHARES,
                        "history": [],
                        "redeemed_shares": None,
                    }
                    for trader in traders
                },
            ),
            "orders": state_field(StateType.map(), {}),
            "clearing": state_field(StateType.optional(StateType.map()), None),
            "order_log": state_field(StateType.sequence(), []),
            "tape": state_field(StateType.sequence(), []),
            "period": state_field(StateType.integer(minimum=1), 1),
            "last_price_cents": state_field(
                StateType.integer(minimum=0), INITIAL_REFERENCE_CENTS
            ),
            "finished": state_field(StateType.boolean(), False),
        },
        commands={
            "submit_order": Command(
                inputs={
                    "trader": StateType.text(),
                    "period": StateType.integer(minimum=1),
                    "decision": StateType.map(),
                },
                require=(
                    (~field("finished"))
                    & (arg("period") == field("period"))
                    & field("accounts").contains(arg("trader"))
                    & (~field("orders").contains(arg("trader")))
                ),
                effects=(
                    put(
                        "orders",
                        arg("trader"),
                        let("trader", arg("trader"), let("decision", arg("decision"), _admitted_order())),
                        once=True,
                    ),
                ),
            ),
            "clear_orders": Command(
                inputs={"period": StateType.integer(minimum=1)},
                require=(
                    (~field("finished"))
                    & (arg("period") == field("period"))
                    & (field("orders").length() == constant("trader_count"))
                    & (field("clearing") == None)
                ),
                effects=(assign("clearing", _clearing_record()),),
            ),
            "settle": Command(
                inputs={"period": StateType.integer(minimum=1)},
                require=(
                    (~field("finished"))
                    & (arg("period") == field("period"))
                    & (field("clearing") != None)
                ),
                effects=(
                    assign("accounts", _updated_accounts()),
                    assign("order_log", _order_log_after_clear()),
                    assign("tape", _tape_after_clear()),
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
                    assign("finished", field("period") == constant("periods")),
                    assign("period", field("period") + 1),
                ),
            ),
        },
        view={
            "period": field("period"),
            "tape": field("tape"),
            "clearing_pending": field("clearing"),
            "last_price": field("last_price_cents") / 100,
            "your_account": field("accounts").get(current("name")),
            "finished": field("finished"),
        },
        complete_when=field("finished"),
        algorithms=(),
    )
    machine.validate()
    return machine

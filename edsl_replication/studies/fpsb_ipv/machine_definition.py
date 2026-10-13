def build_sealed_machine(config: dict[str, Any]) -> Machine:
    """Build a sealed-bid mechanism with config-specific constants and settlement."""
    auction, rule = config["auction"], config["rule"]
    count = auction["number_agents"]
    order = rule["price_order"]
    rank_index = {"first": 0, "second": 1, "third": 2, "allpay": 0}[order]
    ranked = reduce(
        "sort_records", field("bids").values(), fields=("amount", "seat"),
        descending=(True, False),
    )
    winner = ranked.first()
    winner_id = winner.get("bidder")
    settlement_bid = choose(
        ranked.length() > rank_index, ranked.at(rank_index).get("amount"), 0
    )
    value_field = "common_value" if rule["private_value"] == "common" else "value"
    payments = map_items(
        field("bids"), key="bidder", value="bid", key_expr=local("bidder"),
        value_expr=choose(
            constant("all_pay"), local("bid").get("amount"),
            choose(local("bidder") == winner_id, settlement_bid, 0),
        ),
    )
    utilities = map_items(
        field("bids"), key="bidder", value="bid", key_expr=local("bidder"),
        value_expr=local("bid").get(value_field) - payments.get(local("bidder")),
    )
    machine = Machine(
        name=f"{config['experiment']['name']}_sealed",
        constants={"bidder_count": count, "rank_index": rank_index,
                   "all_pay": order == "allpay", "price_order": order,
                   "value_type": rule["private_value"]},
        fields={
            "bids": state_field(StateType.map(), {}),
            "winner": state_field(StateType.optional(StateType.text()), None),
            "winning_bid": state_field(StateType.optional(StateType.number()), None),
            "price": state_field(StateType.optional(StateType.number()), None),
            "payments": state_field(StateType.map(), {}),
            "utilities": state_field(StateType.map(), {}),
        },
        commands={"submit_bid": Command(
            inputs={"bidder": StateType.text(), "seat": StateType.integer(minimum=0),
                    "value": StateType.number(), "common_value": StateType.number(),
                    "amount": StateType.number(minimum=0)},
            effects=(put("bids", arg("bidder"), record(
                bidder=arg("bidder"), seat=arg("seat"), value=arg("value"),
                common_value=arg("common_value"), amount=arg("amount"),
            )),),
        )},
        view={
            "bidder_count": constant("bidder_count"),
            "bid_count": field("bids").length(),
            "bids": choose(current("closed"), field("bids"), {}),
            "winner": choose(current("closed"), field("winner"), None),
            "winning_bid": choose(current("closed"), field("winning_bid"), None),
            "price": choose(current("closed"), field("price"), None),
            "payments": choose(current("closed"), field("payments"), {}),
            "utilities": choose(current("closed"), field("utilities"), {}),
        },
        complete_when=field("bids").length() == constant("bidder_count"),
        close_effects=(assign("winner", winner_id),
                       assign("winning_bid", winner.get("amount")),
                       assign("price", settlement_bid),
                       assign("payments", payments), assign("utilities", utilities)),
    )
    return machine

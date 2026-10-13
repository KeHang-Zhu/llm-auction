def build_proxy_machine(config: dict[str, Any]) -> Machine:
    """Build an eBay/Amazon proxy-bid machine with serial public price updates."""
    auction, rule, value_cfg = config["auction"], config["rule"], config["value"]
    count, turns = auction["number_agents"], rule["turns"]
    names = [f"Bidder {n}" for n in NAMES[:count]]
    initial_bids = {name: 0 for name in names}
    # A candidate maximum map includes the current agent's submitted maximum.
    valid_amount = choose(
        arg("amount") < field("max_bids").get(arg("bidder")),
        field("max_bids").get(arg("bidder")), arg("amount"),
    )
    updated_bids = map_items(
        field("max_bids"), key="bidder", value="amount",
        key_expr=local("bidder"),
        value_expr=choose(local("bidder") == arg("bidder"), valid_amount, local("amount")),
    )
    ranked = reduce(
        "sort_records",
        map_items(updated_bids, key="bidder", value="amount",
                  key_expr=local("bidder"),
                  value_expr=record(bidder=local("bidder"), amount=local("amount"))).values(),
        fields=("amount", "bidder"), descending=(True, False),
    )
    top = ranked.first()
    second = choose(ranked.length() > 1, ranked.at(1).get("amount"), 0)
    current_price = choose(
        second > 0,
        choose(top.get("amount") < second + constant("increment"),
               top.get("amount"), second + constant("increment")),
        constant("start_price"),
    )
    sale = current_price >= constant("reserve_price")
    winner = choose(sale, top.get("bidder"), None)
    final_ranked = reduce(
        "sort_records",
        map_items(field("max_bids"), key="bidder", value="amount",
                  key_expr=local("bidder"),
                  value_expr=record(bidder=local("bidder"), amount=local("amount"))).values(),
        fields=("amount", "bidder"), descending=(True, False),
    )
    final_sale = field("current_price") >= constant("reserve_price")
    final_winner = choose(final_sale, final_ranked.first().get("bidder"), None)
    payments = map_items(
        field("max_bids"), key="bidder", value="amount",
        key_expr=local("bidder"),
        value_expr=choose(local("bidder") == final_winner, field("current_price"), 0),
    )
    utilities = map_items(
        field("max_bids"), key="bidder", value="amount",
        key_expr=local("bidder"),
        value_expr=choose(
            local("bidder") == final_winner,
            field("values").get(local("bidder")) - field("current_price"), 0,
        ),
    )
    # amounts may only be raised; EDSL serial order makes each update visible
    # to the next bidder in a round.
    return Machine(
        name=f"{config['experiment']['name']}_proxy",
        constants={"bidder_count": count, "turns": turns,
                   "increment": value_cfg["increment"],
                   "reserve_price": rule["reserve_price"],
                   "start_price": rule.get("start_price", 0),
                   "soft_close": bool(rule.get("closing", False))},
        fields={
            "max_bids": state_field(StateType.map(), initial_bids),
            "values": state_field(StateType.map(), {}),
            "actions": state_field(StateType.map(), {}),
            "period": state_field(StateType.integer(minimum=0), 0),
            "current_price": state_field(StateType.number(minimum=0), rule.get("start_price", 0)),
            "winner": state_field(StateType.optional(StateType.text()), None),
            "price": state_field(StateType.optional(StateType.number()), None),
            "payments": state_field(StateType.map(), {}),
            "utilities": state_field(StateType.map(), {}),
        },
        commands={"update_bid": Command(
            inputs={"bidder": StateType.text(), "event_id": StateType.text(),
                    "amount": StateType.number(minimum=0),
                    "value": StateType.number(), "seat": StateType.integer(minimum=0),
                    "period": StateType.integer(minimum=0)},
            effects=(
                assign("max_bids", updated_bids),
                put("values", arg("bidder"), arg("value")),
                put("actions", arg("event_id"), record(
                    bidder=arg("bidder"), amount=valid_amount, period=arg("period"),
                    seat=arg("seat"))),
                assign("current_price", current_price),
                assign("period", arg("period")),
            ),
        )},
        view={
            "bidder_count": constant("bidder_count"),
            "turns": constant("turns"),
            "current_price": field("current_price"),
            "your_max_bid": field("max_bids").get(current("agent.bidder_id", default=""), 0),
            "your_value": field("values").get(current("agent.bidder_id", default=""), 0),
            "action_count": field("actions").length(),
            "winner": choose(current("closed"), field("winner"), None),
            "price": choose(current("closed"), field("price"), None),
            "payments": choose(current("closed"), field("payments"), {}),
            "utilities": choose(current("closed"), field("utilities"), {}),
        },
        complete_when=field("actions").length() >= constant("bidder_count") * constant("turns"),
        close_effects=(assign("winner", final_winner),
                       assign("price", choose(final_sale, field("current_price"), None)),
                       assign("payments", payments), assign("utilities", utilities)),
    )

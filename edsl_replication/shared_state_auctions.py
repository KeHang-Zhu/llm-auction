"""Shared-state EDSL runners for the archived llm-auction conditions.

Each condition receives its own machine definition and scope map. Sealed-bid
conditions settle through one atomic close; proxy-bidding conditions use a
separate sequential machine with a public price view between turns.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

import yaml
from edsl import Agent, AgentList, InterviewSchedule, Model, QuestionFreeText, QuestionNumerical, Survey
from edsl.prompts import Prompt
from edsl.runner import Runner
from edsl.sharedstate import (
    Command, Machine, SharedState, SharedStateMap, StateType, arg, assign,
    choose, constant, current, field, local, map_items, put, record, reduce,
    state_field,
)

ROOT = Path(__file__).resolve().parents[1]
NAMES = ["Andy", "Betty", "Charles", "David", "Ethel", "Florian", "Gray"]


def study_slug(config_path: Path) -> str:
    """Return the unique per-YAML folder name without its numeric section prefix."""
    return re.sub(r"^\d+_\d+_", "", config_path.stem)


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


def draw_values(config: dict[str, Any], seed: int) -> tuple[list[int], int]:
    """Reproduce Auction_plan.draw_value's seeded sequence for one auction."""
    rule, value = config["rule"], config["value"]
    rng = random.Random(seed)
    kind = rule["private_value"]
    common = 0 if kind == "private" else rng.randint(*value["common_range"])
    if kind == "common":
        vals = [common + rng.randint(-value["private_range"], value["private_range"])
                for _ in range(config["auction"]["number_agents"])]
    else:
        vals = [common + rng.randint(0, value["private_range"])
                for _ in range(config["auction"]["number_agents"])]
    return vals, common


def make_prompts(config: dict[str, Any], name: str, other_names: str,
                 value: int, repetition: int) -> tuple[str, str]:
    rule, value_cfg = config["rule"], config["value"]
    prompts = config["prompt"]
    prompt_dir = ROOT / prompts.get("prompt_dir", "Prompt/")
    templates = ROOT / prompts.get("rule_template_dir", "rule_template/V10/")
    instruction = Prompt.from_txt(str(prompt_dir / "instruction.txt")).render(
        {"name": name, "other_agent_names": other_names})
    persona = Prompt.from_txt(str(prompt_dir / "persona.txt")).render({})
    explanation = Prompt.from_txt(str(templates / rule["special_name"])).render({
        "item_description": "256GB IPhone 16 pro", "item_condition": "used",
        "start_price": rule.get("start_price", 0), "num_rounds": config["auction"]["rounds"],
        "bid_increment": value_cfg["increment"], "private": value_cfg["private_range"],
        "increment": value_cfg["increment"], "num_bidders": config["auction"]["number_agents"] - 1,
        "n": config["auction"]["rounds"], "common_low": value_cfg["common_range"][0],
        "common_high": value_cfg["common_range"][1],
    })
    unified = Prompt.from_txt(str(prompt_dir / "unified_sealed_bid.txt")).render({
        "history_section": "", "current_round": 1,
        "total_rounds": config["auction"]["rounds"], "current_value": value,
        "transcript": "",
    })
    context = f"{instruction}{persona}\n{explanation}\n{unified}"
    marker = "Your response must use these EXACT tags below:"
    if marker in context:
        context = context.split(marker, 1)[0].rstrip()
    return (context + "\n\nState your bidding plan in no more than 100 words. Do not include a bid.",
            context + "\n\nBased on your plan below, submit your bid as a number only.")


def build_sealed_run(config: dict[str, Any], repetitions: int):
    count = config["auction"]["number_agents"]
    values_cfg = config["value"]
    machine = build_sealed_machine(config)
    state_id = f"llm-auction-{config['experiment']['name']}-{random.randrange(1 << 62):x}"
    states = SharedStateMap(SharedState(auction=machine), state_id=state_id)
    scoped = states.by(current.agent.auction_id).auction
    plan = QuestionFreeText(question_name="plan", question_text="{{ agent.prompt_plan }}")
    bid = QuestionNumerical(question_name="bid_response", question_text=(
        "{{ agent.prompt_bid }}\n\nYour plan was: {{ plan.answer }}"), min_value=0)
    survey = Survey([scoped.read(), plan, bid, scoped.submit_bid(
        bidder=current.agent.bidder_id, seat=current.agent.seat,
        value=current.agent.value, common_value=current.agent.common_value,
        amount=bid.answer)])
    agents = AgentList()
    for repetition in range(repetitions):
        seed = values_cfg["seed_base"] + repetition
        values, common = draw_values(config, seed)
        aid = f"auction-{repetition:04d}"
        for seat, value in enumerate(values):
            name = f"Bidder {NAMES[seat]}"
            others = ", ".join(f"Bidder {n}" for i, n in enumerate(NAMES[:count]) if i != seat)
            prompt_plan, prompt_bid = make_prompts(config, name, others, value, repetition)
            agents.append(Agent(name=name, traits={
                "auction_id": aid, "bidder_id": name, "seat": seat, "turn": seat,
                "value": value, "common_value": common, "seed": seed,
                "prompt_plan": str(prompt_plan), "prompt_bid": str(prompt_bid),
            }))
    schedule = InterviewSchedule.rounds(
        count=1, group_by="auction_id", within_round="concurrent",
        state_visibility="snapshot", finalize_when=scoped.is_complete())
    llm = config["llm"]
    model = Model(llm["model"], service_name=llm.get("service_name", "openai"),
                  temperature=llm["temperature"])
    return survey, agents, model, schedule, states


def build_proxy_run(config: dict[str, Any], repetitions: int):
    count, turns = config["auction"]["number_agents"], config["rule"]["turns"]
    machine = build_proxy_machine(config)
    state_id = f"llm-auction-{config['experiment']['name']}-{random.randrange(1 << 62):x}"
    states = SharedStateMap(SharedState(auction=machine), state_id=state_id)
    scoped = states.by(current.agent.auction_id).auction
    bid = QuestionNumerical(
        question_name="bid_response",
        question_text=("{{ agent.prompt_bid }}\n\n"
                       "Public current price: ${{ shared_state.auction.current_price }}. "
                       "Your current maximum: ${{ shared_state.auction.your_max_bid }}. "
                       "Enter only the maximum you want to maintain or submit. "
                       "A lower amount is treated as holding your current maximum."), min_value=0)
    survey = Survey([scoped.read(), bid, scoped.update_bid(
        bidder=current.agent.bidder_id, event_id=current.agent.event_id,
        amount=bid.answer, value=current.agent.value, seat=current.agent.seat,
        period=current.agent.period)])
    agents = AgentList()
    for repetition in range(repetitions):
        seed = config["value"]["seed_base"] + repetition
        values, common = draw_values(config, seed)
        auction_id = f"auction-{repetition:04d}"
        for period in range(turns):
            # Stable random within-day order mirrors the legacy random order once
            # per auction; serial live execution preserves proxy price updates.
            ordering = list(range(count))
            random.Random(seed * 1000 + period).shuffle(ordering)
            turn_positions = {seat: pos for pos, seat in enumerate(ordering)}
            for seat, value in enumerate(values):
                name = f"Bidder {NAMES[seat]}"
                others = ", ".join(f"Bidder {n}" for i, n in enumerate(NAMES[:count]) if i != seat)
                explanation = Prompt.from_txt(str(ROOT / config["prompt"]["rule_template_dir"] /
                                                   config["rule"]["special_name"])).render({
                    "item_description": "256GB IPhone 16 pro", "item_condition": "used",
                    "start_price": config["rule"].get("start_price", 0),
                    "num_rounds": turns, "bid_increment": config["value"]["increment"],
                    "private": config["value"]["private_range"],
                    "increment": config["value"]["increment"], "num_bidders": count - 1,
                    "n": turns, "common_low": config["value"]["common_range"][0],
                    "common_high": config["value"]["common_range"][1],
                })
                ask = Prompt.from_txt(str(ROOT / config["prompt"]["prompt_dir"] / "ebay_asking.txt")).render({
                    "name": name, "total_periods": turns, "current_period": period,
                    "private_value": value, "current_price": "(see live price below)",
                    "transcript": "", "previous_bid": "Your current maximum is shown below",
                    "last_bid_amount": "(see your current maximum below)",
                    "ordering": "Bidders act in the displayed random order.",
                })
                ask = str(ask).split("Your response must use these EXACT tags below.", 1)[0].strip()
                agents.append(Agent(name=name, traits={
                    "auction_id": auction_id, "bidder_id": name, "seat": seat,
                    "turn_order": period * count + turn_positions[seat],
                    "period": period, "event_id": f"{auction_id}-p{period}-s{seat}",
                    "value": value, "common_value": common, "seed": seed,
                    "prompt_bid": f"{explanation}\n{ask}",
                }))
    schedule = InterviewSchedule.rounds(
        count=1, group_by="auction_id", within_round="serial",
        order_by="turn_order", state_visibility="live",
        finalize_when=scoped.is_complete())
    llm = config["llm"]
    model = Model(llm["model"], service_name=llm.get("service_name", "openai"),
                  temperature=llm["temperature"])
    return survey, agents, model, schedule, states


def run_config(config_path: Path, repetitions: int | None = None,
               output: Path | None = None) -> Path:
    config = yaml.safe_load(config_path.read_text())
    n = repetitions if repetitions is not None else config["execution"]["repetitions"]
    if config["rule"]["seal_clock"] != "seal":
        raise NotImplementedError("Clock auctions are not in the archived 27 YAML conditions")
    if config["prompt"].get("strategy_type") == "ebay":
        survey, agents, model, schedule, states = build_proxy_run(config, n)
    else:
        survey, agents, model, schedule, states = build_sealed_run(config, n)
    results = Runner(interview_schedule=schedule).submit(
        survey.by(agents).by(model), cache=False).results()
    dest = output or (ROOT / "edsl_replication" / "studies" /
                      study_slug(config_path) / "raw_results.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"config": config,
                                "run_metadata": {"repetitions": n},
                                "state_map": states.to_dict(),
                                "results": results.to_dict()}, indent=2, default=str) + "\n")
    print(f"Saved {len(agents)} bidder interviews to {dest}")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run_config(args.config, args.repetitions, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

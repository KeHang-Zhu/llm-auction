"""First EDSL shared-state port of the archived three-bidder SPSB-IPV cell.

Run with the feature/shared-state-v0 EDSL checkout installed:

    python -m edsl_replication.spsb_ipv_shared_state \
        --config configs/experiments/01_01_spsb_ipv.yaml --repetitions 2 \
        

EDSL runs locally and uses the provider credentials configured in the
environment. This is a new model run, not a replay of the archived responses.
It preserves the archived value draw and auction instructions. EDSL asks for
the plan and numeric bid as separate questions so the bid can be written as a
typed value; that differs from the legacy single-response PLAN/ACTION prompt.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import yaml

from edsl import (
    Agent,
    AgentList,
    InterviewSchedule,
    Model,
    QuestionFreeText,
    QuestionNumerical,
    Survey,
)
from edsl.prompts import Prompt
from edsl.runner import Runner
from edsl.sharedstate import (
    Command,
    Machine,
    SharedState,
    SharedStateMap,
    StateType,
    arg,
    choose,
    constant,
    current,
    field,
    local,
    map_items,
    put,
    record,
    reduce,
    assign,
    state_field,
)


ROOT = Path(__file__).resolve().parents[1]


def build_machine(*, bidder_count: int) -> Machine:
    """Define a sealed, single-unit auction with second-price settlement."""
    ranked = reduce(
        "sort_records",
        field("bids").values(),
        fields=("amount", "seat"),
        descending=(True, False),
    )
    winner = ranked.first()
    winner_id = winner.get("bidder")
    second_bid = choose(ranked.length() > 1, ranked.at(1).get("amount"), 0)
    utilities = map_items(
        field("bids"),
        key="bidder",
        value="bid",
        key_expr=local("bidder"),
        value_expr=(
            choose(local("bidder") == winner_id, local("bid").get("value"), 0)
            - choose(local("bidder") == winner_id, second_bid, 0)
        ),
    )
    return Machine(
        name="SPSB_IPV",
        constants={"bidder_count": bidder_count},
        fields={
            "bids": state_field(StateType.map(), {}),
            "winner": state_field(StateType.optional(StateType.text()), None),
            "winning_bid": state_field(StateType.optional(StateType.number()), None),
            "price": state_field(StateType.optional(StateType.number()), None),
            "utilities": state_field(StateType.map(), {}),
        },
        commands={
            "submit_bid": Command(
                inputs={
                    "bidder": StateType.text(),
                    "seat": StateType.integer(minimum=0),
                    "private_value": StateType.number(minimum=0),
                    "amount": StateType.number(minimum=0),
                },
                effects=(
                    put(
                        "bids",
                        arg("bidder"),
                        record(
                            bidder=arg("bidder"),
                            seat=arg("seat"),
                            value=arg("private_value"),
                            amount=arg("amount"),
                        ),
                    ),
                ),
            ),
        },
        view={
            "bidder_count": constant("bidder_count"),
            "bid_count": field("bids").length(),
            # The view intentionally withholds bids and outcomes until close.
            "bids": choose(
                current("closed"),
                map_items(
                    field("bids"),
                    key="bidder",
                    value="bid",
                    key_expr=local("bidder"),
                    value_expr=local("bid").get("amount"),
                ),
                {},
            ),
            "winner": choose(current("closed"), field("winner"), None),
            "winning_bid": choose(current("closed"), field("winning_bid"), None),
            "price": choose(current("closed"), field("price"), None),
            "utilities": choose(current("closed"), field("utilities"), {}),
        },
        complete_when=field("bids").length() == constant("bidder_count"),
        close_effects=(
            assign("winner", winner_id),
            assign("winning_bid", winner.get("amount")),
            assign("price", second_bid),
            assign("utilities", utilities),
        ),
    )


def _prompts(
    rule: dict[str, Any], bidder_name: str, other_names: str, value: int
) -> tuple[str, str]:
    prompt_dir = ROOT / rule.get("prompt_dir", "Prompt/")
    templates_dir = ROOT / rule.get("rule_template_dir", "rule_template/V10/")
    instruction = str(
        Prompt.from_txt(str(prompt_dir / "instruction.txt")).render(
            {"name": bidder_name, "other_agent_names": other_names}
        )
    )
    persona = str(Prompt.from_txt(str(prompt_dir / "persona.txt")).render({}))
    explanation = str(
        Prompt.from_txt(
            str(templates_dir / rule.get("special_name", "private_second_price.txt"))
        ).render(
            {
                "item_description": "256GB IPhone 16 pro",
                "item_condition": "used",
                "start_price": 0,
                "num_rounds": rule["rounds"],
                "bid_increment": rule["increment"],
                "private": rule["private_range"],
                "increment": rule["increment"],
                "num_bidders": rule["number_agents"] - 1,
                "n": rule["rounds"],
                "common_low": rule["common_range"][0],
                "common_high": rule["common_range"][1],
            }
        )
    )
    unified = str(
        Prompt.from_txt(str(prompt_dir / "unified_sealed_bid.txt")).render(
            {
                "history_section": "",
                "current_round": 1,
                "total_rounds": rule["rounds"],
                "current_value": value,
                "transcript": "",
            }
        )
    )
    context = f"{instruction}{persona}\n{explanation}\n{unified}"
    marker = "Your response must use these EXACT tags below:"
    if marker in context:
        context = context.split(marker, 1)[0].rstrip()
    plan_prompt = (
        context
        + "\n\nState your bidding plan in no more than 100 words. Do not include a bid."
    )
    bid_prompt = context
    bid_prompt += "\n\nBased on your plan below, submit your bid as a number only."
    return plan_prompt, bid_prompt


def draw_private_values(seed: int, bidder_count: int, private_range: int) -> list[int]:
    """Match Auction_plan.draw_value's private-value RNG sequence."""
    rng = random.Random(seed)
    return [rng.randint(0, private_range) for _ in range(bidder_count)]


def build_run(config: dict[str, Any], repetitions: int):
    auction = config["auction"]
    rule = config["rule"]
    value_config = config["value"]
    llm = config["llm"]
    bidder_count = auction["number_agents"]
    if auction["rounds"] != 1 or rule["price_order"] != "second" or rule["private_value"] != "private":
        raise ValueError("This first port currently supports one-round SPSB-IPV only")

    machine = build_machine(bidder_count=bidder_count)
    state_id = f"llm-auction-spsb-ipv-{random.randrange(1 << 62):x}"
    states = SharedStateMap(SharedState(auction=machine), state_id=state_id)
    scoped = states.by(current.agent.auction_id).auction
    plan = QuestionFreeText(
        question_name="plan",
        question_text="{{ agent.prompt_plan }}",
    )
    bid = QuestionNumerical(
        question_name="bid_response",
        question_text=(
            "{{ agent.prompt_bid }}\n\nYour plan was: {{ plan.answer }}"
        ),
        min_value=0,
    )
    survey = Survey(
        [
            scoped.read(),
            plan,
            bid,
            scoped.submit_bid(
                bidder=current.agent.bidder_id,
                seat=current.agent.seat,
                private_value=current.agent.value,
                amount=bid.answer,
            ),
        ]
    )

    names = ["Andy", "Betty", "Charles", "David", "Ethel", "Florian", "Gray"]
    agents = AgentList()
    for repetition in range(repetitions):
        seed = value_config["seed_base"] + repetition
        values = draw_private_values(seed, bidder_count, value_config["private_range"])
        auction_id = f"auction-{repetition:04d}"
        for seat, value in enumerate(values):
            name = f"Bidder {names[seat]}"
            others = ", ".join(
                f"Bidder {n}"
                for i, n in enumerate(names[:bidder_count])
                if i != seat
            )
            prompt_rule = {
                "prompt_dir": config["prompt"]["prompt_dir"],
                "rule_template_dir": config["prompt"]["rule_template_dir"],
                "special_name": rule["special_name"],
                "rounds": auction["rounds"],
                "increment": value_config["increment"],
                "private_range": value_config["private_range"],
                "number_agents": bidder_count,
                "common_range": value_config["common_range"],
            }
            prompt_plan, prompt_bid = _prompts(prompt_rule, name, others, value)
            agents.append(
                Agent(
                    name=name,
                    traits={
                        "auction_id": auction_id,
                        "bidder_id": name,
                        "seat": seat,
                        "turn": seat,
                        "value": value,
                        "seed": seed,
                        "prompt_plan": prompt_plan,
                        "prompt_bid": prompt_bid,
                    },
                )
            )

    schedule = InterviewSchedule.rounds(
        count=1,
        group_by="auction_id",
        within_round="concurrent",
        state_visibility="snapshot",
        finalize_when=scoped.is_complete(),
    )
    # The active profile's local model catalogue may be stale or partial. The
    # SPSB-IPV YAML identifies GPT-4o, so pin its provider explicitly and use
    # the OPENAI_API_KEY loaded by EDSL from the project .env.
    model = Model(
        llm["model"],
        service_name=llm.get("service_name", "openai"),
        temperature=llm["temperature"],
    )
    return survey, agents, model, schedule, states


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiments/01_01_spsb_ipv.yaml")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    config = yaml.safe_load(args.config.read_text())
    repetitions = args.repetitions or config["execution"]["repetitions"]
    survey, agents, model, schedule, states = build_run(config, repetitions)

    results = Runner(interview_schedule=schedule).submit(
        survey.by(agents).by(model), cache=False
    ).results()
    output = args.output or (
        ROOT / "edsl_replication" / "runs" / f"spsb_ipv_{states.state_id}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "config": config,
        "state_map": states.to_dict(),
        "results": results.to_dict(),
    }
    output.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"Saved {len(agents)} bidder interviews to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

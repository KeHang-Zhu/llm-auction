"""Prepare or run a two-round call market with live trader decisions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from edsl import Agent, QuestionDict, QuestionFreeText, Survey
from edsl.sharedstate import SharedState, SharedStateMap, current
from edsl.workflows import (
    ExecutionPlan,
    Workflow,
    WorkflowExperiment,
    llm,
    role,
    scripted,
)

from machine_definition import ROUNDS, TRADERS, build_machine


def _decision_question():
    return QuestionDict(
        question_name="decision",
        question_text=(
            f"Round {{{{ workflow.repeat.round }}}} of {ROUNDS}. Submit one sealed order for one "
            "share: buy, sell, or hold. A buy limit is the most you will pay; a "
            "sell limit is the least you will accept. Use integer cents. For hold, "
            "enter price_cents=0. You may buy only if your cash covers your limit, "
            "and may sell only shares you own. The exchange selects the highest "
            "eligible bid and lowest eligible ask; if they cross, one share trades "
            "at their midpoint rounded to cents. Orders expire after this round.\n\n"
            "The asset's reference value is $13.00. The public tape and your current "
            "cash, inventory, and prior orders are shown below. Use your assigned "
            "trading style, the account, and the tape to choose an action.\n\n"
            "YOUR ACCOUNT\n{{ shared_state.market.your_account }}\n\n"
            "PUBLIC TAPE\n{{ shared_state.market.tape }}\n\n"
            "Return side as buy, sell, or hold; price_cents as an integer; and a "
            "brief rationale."
        ),
        answer_keys=["side", "price_cents", "rationale"],
        value_types=["str", "int", "str"],
        include_comment=False,
    )


def build_experiment(*, model="gpt-4o", service="openai", temperature=0.2):
    strategies = {
        "trader-A": (
            "value_buyer",
            "Look for opportunities to buy below $13.00. Consider a one-share "
            "bid near $12.50 when affordable. Reassess using the tape and your "
            "inventory in the next round; do not buy beyond available cash.",
        ),
        "trader-B": (
            "value_buyer",
            "Look for opportunities to buy below $13.00. Consider a one-share "
            "bid near $12.75 when affordable. Reassess using the tape and your "
            "inventory in the next round; do not buy beyond available cash.",
        ),
        "trader-C": (
            "value_seller",
            "Look for opportunities to sell above $12.00. Consider a one-share "
            "ask near $12.25 when you own a share. Reassess using the tape and "
            "your inventory in the next round; never sell more than you own.",
        ),
        "trader-D": (
            "value_seller",
            "Look for opportunities to sell above $12.00. Consider a one-share "
            "ask near $12.00 when you own a share. Reassess using the tape and "
            "your inventory in the next round; never sell more than you own.",
        ),
    }
    agents = [
        Agent(
            name=name,
            traits={"role": "trader", "strategy": strategies[name][0]},
            instruction=(
                "You are an experimental asset-market trader. Maximize your final "
                "cash and inventory value. Follow the market rules in the question.\n\n"
                + strategies[name][1]
            ),
        )
        for name in TRADERS
    ]
    agents.append(Agent(name="exchange", traits={"role": "exchange"}))

    states = SharedStateMap(
        SharedState(market=build_machine()),
        state_id="live-two-round-call-market",
    )
    market = states.by("session").market
    workflow = Workflow(
        "Two-round live-decision call market",
        metadata={
            "rounds": ROUNDS,
            "traders": len(TRADERS),
            "machine": "LiveDecisionMultiRoundCallMarket",
            "model": model,
            "service": service,
            "temperature": temperature,
            "repeat_control": "Machine.is_complete(), bounded at two rounds",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    execution = ExecutionPlan().bind(
        role("trader"),
        llm(model=model, service=service, parameters={"temperature": temperature}),
    ).bind(
        role("exchange"),
        scripted(answers={"settled": "settled"}),
    )

    def build_round(iteration):
        iteration.input("round", market.read(), path=("round",))
        decision = _decision_question()
        orders = iteration.step(
            "orders",
            Survey([decision]),
            assigned_to=role("trader"),
            visible_to=role("exchange"),
            reads=(market.read(),),
            writes=(
                market.submit_order(
                    trader=current.agent.name,
                    decision=decision.answer,
                ),
            ),
            metadata={"phase": "sealed orders"},
        )
        settled = QuestionFreeText(
            question_name="settled",
            question_text=(
                "Confirm that EDSL cleared and settled round "
                "{{ workflow.repeat.round }}."
            ),
        )
        settle = iteration.step(
            "exchange",
            Survey([settled]),
            assigned_to=role("exchange"),
            after=orders,
            reads=(market.read(),),
            writes=(
                market.clear_orders(),
                market.settle_round(),
            ),
            metadata={"phase": "clear and settle"},
        )
        iteration.stop_when(market.is_complete())

    workflow.repeat(
        "market_rounds",
        max_iterations=ROUNDS,
        min_iterations=1,
        build=build_round,
    )

    return WorkflowExperiment(
        workflow.compile(),
        [states],
        agents,
        execution,
        metadata={
            "rounds": ROUNDS,
            "same_market_scope_across_rounds": True,
            "python_round_driver": False,
            "machine_json_bytes": len(build_machine().to_json()),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--service", default="openai")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--specification",
        type=Path,
        help="run a saved portable workflow JSON specification directly",
    )
    parser.add_argument(
        "--replay-from",
        type=Path,
        help="reuse trader answers from a completed pilot without model calls",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    spec_path = args.output / "specification.json"
    if args.resume:
        experiment = WorkflowExperiment.load(args.output / "experiment.json")
    elif args.specification:
        experiment = WorkflowExperiment.load(args.specification)
    elif spec_path.exists() and not args.replay_from:
        experiment = WorkflowExperiment.load(spec_path)
    else:
        experiment = build_experiment(
            model=args.model, service=args.service, temperature=args.temperature
        )

    if args.prepare_only:
        experiment.save(spec_path)
        print(json.dumps({"status": "prepared", "specification": str(spec_path)}))
        return

    from dotenv import load_dotenv

    load_dotenv()
    replay = None
    if args.replay_from:
        import sqlite3

        with sqlite3.connect(args.replay_from / "workflow.sqlite") as connection:
            rows = connection.execute(
                """
                SELECT i.step_name, i.participant_id, s.answers
                FROM workflow_items AS i
                JOIN workflow_submissions AS s ON s.work_item_id = i.id
                ORDER BY i.created_at
                """
            ).fetchall()
        replay = []
        for step_name, participant, encoded_answers in rows:
            if step_name.startswith("orders-"):
                answers = json.loads(encoded_answers)
            elif step_name.startswith("exchange-"):
                answers = {"settled": "settled"}
            else:
                continue
            replay.append(
                {"step": step_name, "participant": participant, "answers": answers}
            )
    result = experiment.run(
        args.output, resume=args.resume, responses=replay
    )
    (args.output / "completion.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

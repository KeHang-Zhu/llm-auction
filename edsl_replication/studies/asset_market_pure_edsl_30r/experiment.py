"""Replicate the 30-period 12-trader market using a callback-free EDSL Machine."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from edsl import Agent, QuestionDict, QuestionFreeText, Survey
from edsl.sharedstate import ExecutionLimits, Runtime, SharedState, SharedStateMap, current
from edsl.workflows import ExecutionPlan, Workflow, WorkflowExperiment, llm, role, scripted

from machine_definition import PERIODS, TRADERS, build_machine


SYSTEM = (
    "You are a participant in a multi-period experimental asset market. Try to "
    "maximize your final cash wealth. Use your account, public price history, "
    "dividend rules, and terminal redemption value when deciding what to do."
)

# Long histories are deliberately retained in this machine for auditability.
# The default interpreter budget is too small for one late-round transition,
# so this experiment raises only the per-operation step ceiling.
MACHINE_RUNTIME = Runtime(limits=ExecutionLimits(max_steps=10_000_000))

STYLE = {
    "value_buyer": (
        "You tend to buy when the transaction price is below your estimate of the "
        "asset's payoff value. Compare the price with dividends and terminal "
        "redemption. Consider buying one or two shares when you see a meaningful "
        "discount; do not buy simply because prices are rising."
    ),
    "value_seller": (
        "You tend to sell when the transaction price is above your estimate of the "
        "asset's payoff value. Compare the price with dividends and terminal "
        "redemption. Consider offering one share when you see a meaningful premium; "
        "do not sell simply because prices are falling."
    ),
    "flexible_value": (
        "You trade flexibly based on estimated payoff value. Compare transaction "
        "prices with dividends and terminal redemption; buy below value, sell above "
        "value, and hold when the price seems fair. Avoid extrapolating a short "
        "price trend without payoff-based evidence."
    ),
}


def question_text(period: int) -> str:
    return (
        f"Period {period} of {PERIODS}; {PERIODS - period + 1} periods remain.\n\n"
        "MARKET RULES\n"
        "There are 12 traders. Each began with $100 cash and 4 shares. Submit one "
        "sealed limit order: buy, sell, or hold. A buy limit is the most you will "
        "pay per share; a sell limit is the least you will accept. Orders are for "
        "integer quantities. The exchange matches crossing orders by price; ties "
        "are resolved using a seeded random priority. All filled units receive the "
        "same uniform clearing price: the midpoint of the marginal matched bid "
        "and ask, rounded to cents. Unfilled orders expire. You cannot borrow cash "
        "or sell shares you do not own. Buy quantity is limited by cash divided by "
        "your limit; sell quantity is limited by your inventory. Cash earns 5% "
        "interest each round, rounded to cents. Each share pays a common dividend "
        "of $0.40 or $1.00, equally likely, each round. After round 30 income, each "
        "remaining share is redeemed for $14.00; you keep all cash.\n\n"
        "YOUR ACCOUNT\n"
        "Cash: ${{ shared_state.market.your_account.cash_cents / 100 }}; "
        "shares: {{ shared_state.market.your_account.shares }}.\n"
        "Your prior orders and fills: {{ shared_state.market.your_account.history }}\n\n"
        "PUBLIC MARKET TAPE\n{{ shared_state.market.tape }}\n\n"
        "Forecast the transaction price now and 2, 5, and 10 periods ahead, then "
        "choose a buy, sell, or hold order. Enter all forecasts in dollars. Enter "
        "the order limit as integer cents (for example, $14.25 is 1425). For hold, "
        "use price_cents=0 and quantity=0. Do not return null for a forecast. "
        "Return forecast_0, forecast_2, forecast_5, forecast_10, side, "
        "price_cents, quantity, and a brief rationale."
    )


def _decision_question(period: int):
    return QuestionDict(
        question_name="decision",
        question_text=question_text(period),
        answer_keys=[
            "forecast_0",
            "forecast_2",
            "forecast_5",
            "forecast_10",
            "side",
            "price_cents",
            "quantity",
            "rationale",
        ],
        value_types=["float", "float", "float", "float", "str", "int", "int", "str"],
        include_comment=False,
    )


def build(*, seed: int = 153101, model: str = "gpt-4o", service: str = "openai"):
    strategies = ["value_buyer"] * 4 + ["value_seller"] * 4 + ["flexible_value"] * 4
    agents = [
        Agent(
            name=name,
            traits={"role": "trader", "strategy": strategies[seat], "seat": seat},
            instruction=SYSTEM + "\n\nTRADING STYLE\n" + STYLE[strategies[seat]],
        )
        for seat, name in enumerate(TRADERS)
    ]
    agents.append(Agent(name="exchange", traits={"role": "exchange"}))

    states = SharedStateMap(
        SharedState(market=build_machine(seed)),
        state_id=f"pure-edsl-call-market-seed-{seed}",
    )
    market = states.by("session").market
    workflow = Workflow(
        "30-period pure EDSL call market",
        metadata={
            "seed": seed,
            "periods": PERIODS,
            "traders": len(TRADERS),
            "machine": "PureEDSLCallMarket30Round",
            "custom_market_algorithms": [],
            "strategy_composition": {key: 4 for key in STYLE},
            "price_input": "integer cents",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    plan = ExecutionPlan().bind(
        role("trader"),
        llm(model=model, service=service, parameters={"temperature": 0.2}),
    ).bind(
        role("exchange"),
        scripted(answers={"clear": "matched", "settlement": "settled"}),
    )

    previous = None
    for period in range(1, PERIODS + 1):
        decision = _decision_question(period)
        orders = workflow.step(
            f"orders-{period}",
            Survey([decision]),
            assigned_to=role("trader"),
            after=previous,
            visible_to=role("exchange"),
            reads=(market.read(),),
            writes=(
                market.submit_order(
                    trader=current.agent.name,
                    period=period,
                    decision=decision.answer,
                ),
            ),
            metadata={"period": period, "phase": "sealed orders"},
        )
        cleared = workflow.step(
            f"clear-{period}",
            Survey(
                [
                    QuestionFreeText(
                        question_name="clear",
                        question_text="Compute the crossing allocation from the machine's EDSL expressions.",
                    )
                ]
            ),
            assigned_to=role("exchange"),
            after=orders,
            writes=(market.clear_orders(period=period),),
            metadata={"period": period, "phase": "machine price priority and matching"},
        )
        settled = workflow.step(
            f"settle-{period}",
            Survey(
                [
                    QuestionFreeText(
                        question_name="settlement",
                        question_text="Apply the EDSL clearing result, account transfers, income, and final redemption.",
                    )
                ]
            ),
            assigned_to=role("exchange"),
            after=cleared,
            writes=(market.settle(period=period),),
            metadata={"period": period, "phase": "machine settlement"},
        )
        previous = settled

    return WorkflowExperiment(
        workflow.compile(),
        [states],
        agents,
        plan,
        metadata={
            "seed": seed,
            "economic_horizon": PERIODS,
            "strategy_by_trader": {
                agent.name: agent.traits.get("strategy")
                for agent in agents
                if agent.traits["role"] == "trader"
            },
            "machine_json_bytes": len(build_machine(seed).to_json()),
            "custom_market_algorithms": [],
        },
        runtime=MACHINE_RUNTIME,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=153101)
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--service", default="openai")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    specification = args.output / "specification.json"
    if args.resume:
        experiment = WorkflowExperiment.load(
            args.output / "experiment.json", runtime=MACHINE_RUNTIME
        )
    elif specification.exists():
        experiment = WorkflowExperiment.load(specification, runtime=MACHINE_RUNTIME)
    else:
        experiment = build(seed=args.seed, model=args.model, service=args.service)
    if args.prepare_only:
        experiment.save(specification)
        print(json.dumps({"status": "prepared", "path": str(specification)}))
        return
    from dotenv import load_dotenv

    load_dotenv()
    result = experiment.run(args.output, resume=args.resume)
    (args.output / "completion.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

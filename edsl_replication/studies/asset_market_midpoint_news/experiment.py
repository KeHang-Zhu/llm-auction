"""Midpoint private-news treatment for EDSL's typed call-market workflow."""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from edsl import Agent, QuestionFreeText, Survey
from edsl.sharedstate import (
    CallMarketRules,
    CashInterest,
    Command,
    DecisionSchema,
    DiscreteDistribution,
    Endowment,
    Redemption,
    ShareDividend,
    SharedState,
    SharedStateMap,
    StateType,
    arg,
    call_market,
    current,
    field,
    put,
    state_field,
)
from edsl.workflows import (
    ExecutionPlan,
    Workflow,
    WorkflowExperiment,
    llm,
    role,
    scripted,
)
from edsl.workflows.definition import ParticipantSelector


SEED = 141026
PERIODS = 30
MIDPOINT = 15
TRADERS = tuple(f"trader-{seat:02d}" for seat in range(12))
UPDATE = (
    "PRIVATE ANALYST UPDATE (received after period 15): An outside analyst has "
    "revised its estimate of terminal redemption value from $14.00 to $16.00 "
    "per share. This is an estimate, not a guaranteed payoff. The exchange's "
    "actual terminal redemption rule remains $14.00 per share. Do not disclose "
    "this private message to other traders unless you choose to do so."
)

RULES = CallMarketRules(
    periods=PERIODS,
    endowment=Endowment(cash_cents=10_000, shares=4),
    redemption=Redemption(value_cents=1_400),
    income=(
        CashInterest(rate=0.05),
        ShareDividend(
            distribution=DiscreteDistribution(
                values_cents=(40, 100), probabilities=(0.5, 0.5)
            )
        ),
    ),
)

SYSTEM = (
    "You are a participant in a multi-period experimental asset market. "
    "Try to maximize your final cash wealth. Use your own account, the public "
    "price history, and any private information shown to you. Your private "
    "information is not automatically visible to other traders."
)


def build_market():
    machine = call_market(TRADERS, rules=RULES, seed=SEED)
    # The private map is deliberately omitted from the public view. Each trader
    # sees only the entry selected by current("name").
    machine.fields["private_updates"] = state_field(StateType.map(), {})
    machine.commands["publish_update"] = Command(
        inputs={"recipient": StateType.text(), "message": StateType.text()},
        effects=(put("private_updates", arg("recipient"), arg("message")),),
    )
    machine.view["your_update"] = field("private_updates").get(current("name"))
    machine.validate()
    return machine


def build_agents():
    shuffled = list(TRADERS)
    random.Random(SEED).shuffle(shuffled)
    recipients = set(shuffled[: len(TRADERS) // 2])
    agents = [
        Agent(
            name=name,
            traits={
                "role": "trader",
                "treatment": "news" if name in recipients else "control",
                "seat": i,
            },
            instruction=SYSTEM,
        )
        for i, name in enumerate(TRADERS)
    ]
    agents.append(Agent(name="exchange", traits={"role": "exchange"}))
    return agents, tuple(name for name in TRADERS if name in recipients)


def question_text(period: int) -> str:
    return (
        f"Period {period} of {PERIODS}; {PERIODS - period + 1} periods remain.\n\n"
        "MARKET RULES\n"
        + RULES.instructions(len(TRADERS))
        + "YOUR PRIVATE UPDATE\n"
        "{{ shared_state.market.your_update or 'No private analyst update has been issued to you.' }}\n\n"
        "YOUR ACCOUNT\n"
        "Cash: ${{ shared_state.market.your_account.cash_cents / 100 }}; "
        "shares: {{ shared_state.market.your_account.shares }}.\n"
        "Your prior orders and fills: {{ shared_state.market.your_account.history }}\n\n"
        "PUBLIC MARKET TAPE\n{{ shared_state.market.tape }}\n\n"
        "Forecast the transaction price now and 2, 5, and 10 periods ahead, then "
        "choose a buy, sell, or hold order with a limit price and integer quantity. "
        "For any forecast horizon that extends beyond period 30, enter the known "
        "terminal redemption value, $14.00. Do not return null for a forecast. "
        "All prices and forecasts are in dollars. For hold, use price=0 and quantity=0. "
        "Return forecast_0, forecast_2, forecast_5, forecast_10, side, price, "
        "quantity, and a brief rationale."
    )


def build(*, model="gpt-4o", service="openai"):
    agents, recipients = build_agents()
    states = SharedStateMap(
        SharedState(market=build_market()), state_id="midpoint-private-news-market"
    )
    market = states.by("session").market
    workflow = Workflow(
        "30-period asset market with midpoint private news",
        metadata={
            "economic_horizon": PERIODS,
            "treatment": "six seeded traders receive a private terminal-value estimate after period 15",
            "recipient_names": list(recipients),
        },
    )
    plan = ExecutionPlan().bind(
        role("trader"),
        llm(model=model, service=service, parameters={"temperature": 0.5}),
    ).bind(role("exchange"), scripted(answers={"settlement": "clear", "publish": "recorded"}))

    previous = None
    for period in range(1, PERIODS + 1):
        decision = DecisionSchema().question(
            question_name="decision", question_text=question_text(period)
        )
        orders = workflow.step(
            f"orders-{period}",
            Survey([decision]),
            assigned_to=role("trader"),
            after=previous,
            visible_to=role("exchange"),
            reads=(market.read(),),
            writes=(market.submit(trader=current.agent.name, period=period, decision=decision.answer),),
            metadata={"period": period, "phase": "sealed orders"},
        )
        settled = workflow.step(
            f"settle-{period}",
            Survey([QuestionFreeText(question_name="settlement", question_text="Run deterministic market settlement.")]),
            assigned_to=role("exchange"),
            after=orders,
            writes=(market.settle(period=period),),
            metadata={"period": period, "phase": "settlement"},
        )
        previous = settled
        if period == MIDPOINT:
            for recipient in recipients:
                published = workflow.step(
                    f"publish-private-update-{recipient}",
                    Survey([QuestionFreeText(question_name="publish", question_text="Record this private information update.")]),
                    assigned_to=role("exchange"),
                    after=previous,
                    writes=(market.publish_update(recipient=recipient, message=UPDATE),),
                    metadata={"period": MIDPOINT, "phase": "private information update", "recipient": recipient},
                )
                previous = published

    return WorkflowExperiment(
        workflow.compile(),
        [states],
        agents,
        plan,
        metadata={
            "seed": SEED,
            "economic_horizon": PERIODS,
            "treatment_recipients": list(recipients),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--service", default="openai")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    specification = args.output / "specification.json"
    if args.resume:
        experiment = WorkflowExperiment.load(args.output / "experiment.json")
    elif specification.exists():
        experiment = WorkflowExperiment.load(specification)
    else:
        experiment = build(model=args.model, service=args.service)
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

"""Payoff-relevant news treatment in a multiround EDSL asset market."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from edsl import Agent, QuestionFreeText, Survey
from edsl.sharedstate import (
    CallMarketRules, CashInterest, Command, DecisionSchema, DiscreteDistribution,
    Endowment, Redemption, ShareDividend, SharedState, SharedStateMap, StateType,
    arg, call_market, current, field, local, map_items, record, append, assign,
    require, state_field,
)
from edsl.workflows import ExecutionPlan, Workflow, WorkflowExperiment, llm, role, scripted


SEED_BASE = 153100
PERIODS = 30
NEWS_PERIOD = 5
TRADERS = tuple(f"trader-{seat:02d}" for seat in range(12))
ARMS = {
    "positive": {
        "redemption_cents": 2_000,
        "message": (
            "OFFICIAL PAYOFF UPDATE: The exchange authority has revised the asset's "
            "terminal redemption from $14.00 to $20.00 per share, effective at the "
            "end of period 30. This is a binding change to the payoff rule, not an "
            "analyst forecast. Dividends and all other market rules are unchanged."
        ),
    },
    "negative": {
        "redemption_cents": 800,
        "message": (
            "OFFICIAL PAYOFF UPDATE: The exchange authority has revised the asset's "
            "terminal redemption from $14.00 to $8.00 per share, effective at the "
            "end of period 30. This is a binding change to the payoff rule, not an "
            "analyst forecast. Dividends and all other market rules are unchanged."
        ),
    },
    "control": {
        "redemption_cents": 1_400,
        "message": None,
    },
}

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
    "You are a participant in a multi-period experimental asset market. Try to "
    "maximize your final cash wealth. Use your account, public price history, "
    "dividend rules, and the currently announced terminal redemption value. "
    "The redemption value shown in the market state is authoritative. Do not "
    "assume an analyst forecast changes the payoff rule."
)

STYLE = {
    "value_buyer": (
        "You tend to buy when the transaction price is below your estimate of the "
        "asset's payoff value. Compare the price with dividends and the currently "
        "announced terminal redemption. Consider buying one or two shares when "
        "you see a meaningful discount; do not buy simply because prices are rising."
    ),
    "value_seller": (
        "You tend to sell when the transaction price is above your estimate of the "
        "asset's payoff value. Compare the price with dividends and the currently "
        "announced terminal redemption. Consider offering one share when you see a "
        "meaningful premium; do not sell simply because prices are falling."
    ),
    "flexible_value": (
        "You trade flexibly based on estimated payoff value. Compare transaction "
        "prices with dividends and the currently announced terminal redemption; "
        "buy below value, sell above value, and hold when the price seems fair. "
        "Avoid extrapolating a short price trend without payoff-based evidence."
    ),
}

QUOTE_POLICIES = {
    "patient": {},
    "narrow_spread": {
        "value_buyer": (
            "QUOTE POLICY: Use your forecast_0 as the reference price. If you buy, "
            "submit a limit price exactly $1.25 above forecast_0. Treat that as "
            "your maximum acceptable price; if it exceeds what the asset is worth "
            "to you, hold instead."
        ),
        "value_seller": (
            "QUOTE POLICY: Use your forecast_0 as the reference price. If you sell, "
            "submit a limit price exactly $1.25 below forecast_0. Treat that as "
            "your minimum acceptable price; if it is below what the asset is worth "
            "to you, hold instead."
        ),
        "flexible_value": (
            "QUOTE POLICY: Use your forecast_0 as the reference price. If you buy, "
            "submit a limit price exactly $1.25 above forecast_0. If you sell, "
            "submit a limit price exactly $1.25 below forecast_0. These are your "
            "maximum buy and minimum sell prices; if the relevant limit is not "
            "acceptable given your payoff expectations, hold instead."
        ),
    },
}


def build_market(seed: int):
    # The native settlement algorithm is used for the call market with zero
    # redemption. The new machine stores the live redemption in state and applies
    # it as a separate, auditable final transition after period 30 settlement.
    machine_rules = RULES.model_copy(update={"redemption": Redemption(value_cents=0)})
    base = call_market(TRADERS, rules=machine_rules, seed=seed)
    machine = type(base)(
        name="FundamentalNewsCallMarket",
        constants=dict(base.constants),
        fields=dict(base.fields),
        commands=dict(base.commands),
        view=dict(base.view),
        complete_when=base.complete_when,
        close_effects=base.close_effects,
        algorithms=base.algorithms,
    )
    machine.fields["terminal_redemption_cents"] = state_field(
        StateType.integer(), RULES.redemption.value_cents
    )
    machine.fields["announcement"] = state_field(
        StateType.optional(StateType.text()), None
    )
    machine.fields["fundamental_events"] = state_field(StateType.sequence(), [])
    machine.fields["redemption_applied"] = state_field(StateType.boolean(), False)
    machine.commands["announce_payoff_change"] = Command(
        inputs={
            "value_cents": StateType.integer(),
            "message": StateType.text(),
            "period": StateType.integer(),
        },
        # Settlement advances the market's current period before the news step.
        require=field("period") == NEWS_PERIOD + 1,
        effects=(
            assign("terminal_redemption_cents", arg("value_cents")),
            assign("announcement", arg("message")),
            append(
                "fundamental_events",
                record(
                    period=arg("period"),
                    value_cents=arg("value_cents"),
                    message=arg("message"),
                ),
            ),
        ),
    )
    accounts_after_redemption = map_items(
        field("accounts"),
        key="trader",
        value="account",
        key_expr=local("trader"),
        value_expr=local("account").with_item(
            "cash_cents",
            local("account").get("cash_cents")
            + local("account").get("redeemed_shares")
            * field("terminal_redemption_cents"),
        ),
    )
    machine.commands["apply_terminal_redemption"] = Command(
        inputs={},
        require=field("finished") & ~field("redemption_applied"),
        effects=(
            assign("accounts", accounts_after_redemption),
            assign("redemption_applied", True),
        ),
    )
    machine.view["terminal_redemption_cents"] = field("terminal_redemption_cents")
    machine.view["announcement"] = field("announcement")
    machine.view["fundamental_events"] = field("fundamental_events")
    machine.validate()
    return machine


def question_text(period: int) -> str:
    return (
        f"Period {period} of {PERIODS}; {PERIODS - period + 1} periods remain.\n\n"
        "INITIAL MARKET RULES\n" + RULES.instructions(len(TRADERS))
        + "The initial terminal redemption is $14.00. The exchange authority may "
        "announce a binding change after period 5; any such change will appear "
        "below and replace the initial value.\n\n"
        "CURRENT TERMINAL REDEMPTION\n"
        "${{ shared_state.market.terminal_redemption_cents / 100 }} per share.\n\n"
        "OFFICIAL MARKET ANNOUNCEMENT\n"
        "{{ shared_state.market.announcement or 'No payoff update has been announced.' }}\n\n"
        "YOUR ACCOUNT\nCash: ${{ shared_state.market.your_account.cash_cents / 100 }}; "
        "shares: {{ shared_state.market.your_account.shares }}.\n"
        "Your prior orders and fills: {{ shared_state.market.your_account.history }}\n\n"
        "PUBLIC MARKET TAPE\n{{ shared_state.market.tape }}\n\n"
        "Forecast the transaction price now and 2, 5, and 10 periods ahead, then "
        "choose a buy, sell, or hold order with a limit price and integer quantity. "
        "For a horizon beyond period 30, enter the currently announced terminal "
        "redemption value. Do not return null for a forecast. All prices are in "
        "dollars. For hold, use price=0 and quantity=0. Return forecast_0, "
        "forecast_2, forecast_5, forecast_10, side, price, quantity, and a brief rationale."
    )


def build(
    *, arm: str, replicate: int = 1, model="gpt-4o", service="openai",
    quote_policy: str = "patient",
):
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {tuple(ARMS)}")
    if quote_policy not in QUOTE_POLICIES:
        raise ValueError(f"quote_policy must be one of {tuple(QUOTE_POLICIES)}")
    if replicate < 1:
        raise ValueError("replicate must be at least 1")
    seed = SEED_BASE + replicate
    styles = ["value_buyer"] * 4 + ["value_seller"] * 4 + ["flexible_value"] * 4
    agents = [
        Agent(
            name=name,
            traits={
                "role": "trader", "strategy": styles[i], "seat": i,
                "quote_policy": quote_policy,
            },
            instruction=(
                SYSTEM + "\n\nTRADING STYLE\n" + STYLE[styles[i]]
                + (
                    "\n\n" + QUOTE_POLICIES[quote_policy][styles[i]]
                    if quote_policy != "patient" else ""
                )
            ),
        )
        for i, name in enumerate(TRADERS)
    ]
    agents.append(Agent(name="exchange", traits={"role": "exchange"}))
    market_state = SharedStateMap(
        SharedState(market=build_market(seed)),
        state_id=f"fundamental-news-{quote_policy}-{arm}-replicate-{replicate}",
    )
    market = market_state.by("session").market
    workflow = Workflow(
        f"30-period payoff-news market: {arm}, {quote_policy}, replicate {replicate}",
        metadata={
            "arm": arm,
            "replicate": replicate,
            "quote_policy": quote_policy,
            "news_period": NEWS_PERIOD,
            "news_timing": "after period 5 settlement, before period 6 orders",
            "terminal_redemption_cents": ARMS[arm]["redemption_cents"],
            "behavior_composition": {style: 4 for style in STYLE},
        },
    )
    plan = ExecutionPlan().bind(
        role("trader"), llm(model=model, service=service, parameters={"temperature": 0.2})
    ).bind(
        role("exchange"),
        scripted(answers={"settlement": "clear", "announcement": "published", "redemption": "applied"}),
    )

    previous = None
    for period in range(1, PERIODS + 1):
        decision = DecisionSchema().question(
            question_name="decision", question_text=question_text(period)
        )
        orders = workflow.step(
            f"orders-{period}", Survey([decision]), assigned_to=role("trader"),
            after=previous, visible_to=role("exchange"), reads=(market.read(),),
            writes=(market.submit(
                trader=current.agent.name, period=period, decision=decision.answer
            ),),
            metadata={"period": period, "phase": "sealed orders"},
        )
        settled = workflow.step(
            f"settle-{period}",
            Survey([QuestionFreeText(question_name="settlement", question_text="Run deterministic market settlement.")]),
            assigned_to=role("exchange"), after=orders,
            writes=(market.settle(period=period),),
            metadata={"period": period, "phase": "settlement"},
        )
        previous = settled
        if period == NEWS_PERIOD and arm != "control":
            news = workflow.step(
                f"announce-{arm}-payoff-change",
                Survey([QuestionFreeText(question_name="announcement", question_text="Record the official payoff update.")]),
                assigned_to=role("exchange"), after=previous,
                writes=(market.announce_payoff_change(
                    value_cents=ARMS[arm]["redemption_cents"],
                    message=ARMS[arm]["message"], period=NEWS_PERIOD,
                ),),
                metadata={"period": NEWS_PERIOD, "phase": "binding payoff news", "arm": arm},
            )
            previous = news
        if period == PERIODS:
            redeemed = workflow.step(
                "apply-final-redemption",
                Survey([QuestionFreeText(question_name="redemption", question_text="Apply the current terminal redemption payoff." )]),
                assigned_to=role("exchange"), after=previous,
                writes=(market.apply_terminal_redemption(),),
                metadata={"period": PERIODS, "phase": "terminal redemption"},
            )
            previous = redeemed

    return WorkflowExperiment(
        workflow.compile(), [market_state], agents, plan,
        metadata={
            "seed": seed, "arm": arm, "replicate": replicate,
            "quote_policy": quote_policy,
            "news_period": NEWS_PERIOD,
            "terminal_redemption_cents": ARMS[arm]["redemption_cents"],
            "strategy_by_trader": {a.name: a.traits.get("strategy") for a in agents if a.traits["role"] == "trader"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--service", default="openai")
    parser.add_argument("--quote-policy", choices=QUOTE_POLICIES, default="patient")
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
        experiment = build(
            arm=args.arm, replicate=args.replicate,
            model=args.model, service=args.service,
            quote_policy=args.quote_policy,
        )
    if args.prepare_only:
        experiment.save(specification)
        print(json.dumps({"status": "prepared", "arm": args.arm, "path": str(specification)}))
        return
    from dotenv import load_dotenv
    load_dotenv()
    result = experiment.run(args.output, resume=args.resume)
    (args.output / "completion.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

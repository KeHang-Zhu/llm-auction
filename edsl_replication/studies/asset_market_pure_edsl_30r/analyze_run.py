"""Export compact market, trader, and shared-state summaries for a completed run."""

from __future__ import annotations

import csv
import argparse
import json
import sqlite3
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path


def main(run_dir: Path):
    run_dir = Path(run_dir)
    with (run_dir / "experiment.json").open() as handle:
        spec = json.load(handle)
    strategy = {
        agent["name"]: agent.get("traits", {}).get("strategy", "exchange")
        for agent in spec["agents"]
    }

    state_db = sqlite3.connect(run_dir / "state-0.sqlite")
    state_row = state_db.execute(
        "select payload from state_events where kind='write' order by sequence desc limit 1"
    ).fetchone()
    if not state_row:
        raise RuntimeError("no final shared-state write found")
    payload = json.loads(state_row[0])
    market = payload["state"]["market"]
    state_counts = dict(
        state_db.execute("select kind, count(*) from state_events group by kind")
    )
    state_db.close()

    workflow_db = sqlite3.connect(run_dir / "workflow.sqlite")
    responses = workflow_db.execute(
        """select i.step_name, i.participant_id, s.answers
           from workflow_submissions s join workflow_items i on i.id=s.work_item_id
           where i.step_name like 'orders-%' order by i.step_name, i.participant_id"""
    ).fetchall()
    workflow_status = dict(workflow_db.execute(
        "select status, count(*) from workflow_instances group by status"
    ).fetchall())
    created_at, completed_at = workflow_db.execute(
        "select created_at, completed_at from workflow_instances limit 1"
    ).fetchone()
    workflow_db.close()

    orders = market["order_log"]
    tape = market["tape"]
    accounts = market["accounts"]
    model_call_rows = [
        json.loads(line)
        for line in (run_dir / "model-calls.jsonl").read_text().splitlines()
        if line.strip()
    ]
    token_counts = Counter()
    for call in model_call_rows:
        usage = (
            call.get("result", {}).get("raw_model_response", {})
            .get("decision_raw_model_response", {}).get("usage", {})
        )
        token_counts["prompt"] += usage.get("prompt_tokens", 0)
        token_counts["completion"] += usage.get("completion_tokens", 0)
    side_counts = Counter(order["side"] for order in orders)
    action_by_strategy = defaultdict(Counter)
    for order in orders:
        action_by_strategy[strategy[order["trader"]]][order["side"]] += 1

    response_by_trader = defaultdict(list)
    forecast_errors = defaultdict(list)
    forecast_values = defaultdict(list)
    for step_name, trader, answers_json in responses:
        period = int(step_name.rsplit("-", 1)[1])
        decision = json.loads(answers_json)["decision"]
        response_by_trader[trader].append(decision)
        for horizon in (0, 2, 5, 10):
            forecast_values[horizon].append(float(decision[f"forecast_{horizon}"]))
            target_period = period + horizon
            if horizon == 0 and tape[period - 1]["price"] is not None:
                forecast_errors[horizon].append(
                    float(decision["forecast_0"]) - tape[period - 1]["price"]
                )
            elif horizon > 0 and target_period <= len(tape):
                target_price = tape[target_period - 1]["price"]
                if target_price is not None:
                    forecast_errors[horizon].append(
                        float(decision[f"forecast_{horizon}"]) - target_price
                    )

    round_path = run_dir / "round_summary.csv"
    with round_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(tape[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(tape)

    trader_path = run_dir / "trader_summary.csv"
    trader_rows = []
    for trader, account in sorted(accounts.items()):
        history = account["history"]
        signed_fills = [row["fill"] for row in history]
        trader_rows.append(
            {
                "trader": trader,
                "strategy": strategy[trader],
                "cash_dollars": account["cash_cents"] / 100,
                "shares_remaining": account["shares"],
                "shares_redeemed": account["redeemed_shares"],
                "buy_orders": sum(row["decision"]["side"] == "buy" for row in history),
                "sell_orders": sum(row["decision"]["side"] == "sell" for row in history),
                "hold_orders": sum(row["decision"]["side"] == "hold" for row in history),
                "accepted_units": sum(row["accepted_quantity"] for row in history),
                "buy_filled_units": sum(max(fill, 0) for fill in signed_fills),
                "sell_filled_units": sum(max(-fill, 0) for fill in signed_fills),
            }
        )
    with trader_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(trader_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(trader_rows)

    trade_rounds = [row for row in tape if row["volume"] > 0]
    traded_prices = [row["price"] for row in trade_rounds]
    final_cash = sum(account["cash_cents"] for account in accounts.values())
    summary = {
        "workflow_status": workflow_status,
        "model": spec["execution_plan"]["bindings"][0]["executor"]["options"]["model"],
        "service": spec["execution_plan"]["bindings"][0]["executor"]["options"]["service"],
        "seed": spec["metadata"]["seed"],
        "trader_count": len(accounts),
        "workflow_created_at": created_at,
        "workflow_completed_at": completed_at,
        "workflow_elapsed_seconds": (
            (datetime.fromisoformat(completed_at) - datetime.fromisoformat(created_at)).total_seconds()
            if completed_at else None
        ),
        "completed_trader_decisions": len(responses),
        "model_calls": len(model_call_rows),
        "prompt_tokens": token_counts["prompt"],
        "completion_tokens": token_counts["completion"],
        "periods_settled": len(tape),
        "state_events": state_counts,
        "machine_algorithms": spec["states"][0]["definition"]["machines"]["market"]["algorithms"],
        "order_actions": dict(side_counts),
        "actions_by_strategy": {k: dict(v) for k, v in action_by_strategy.items()},
        "trade_rounds": len(trade_rounds),
        "total_matched_units": sum(row["volume"] for row in tape),
        "mean_trade_price_dollars": sum(traded_prices) / len(traded_prices) if traded_prices else None,
        "median_trade_price_dollars": sorted(traded_prices)[len(traded_prices) // 2] if traded_prices else None,
        "last_trade_price_dollars": traded_prices[-1] if traded_prices else None,
        "no_trade_rounds": sum(row["volume"] == 0 for row in tape),
        "trade_periods": [
            {"period": row["period"], "price": row["price"], "volume": row["volume"]}
            for row in trade_rounds
        ],
        "mean_forecast_dollars": {
            str(h): sum(values) / len(values) for h, values in forecast_values.items()
        },
        "forecast_error_mae_dollars": {
            str(h): sum(abs(error) for error in errors) / len(errors)
            for h, errors in forecast_errors.items()
            if errors
        },
        "forecast_error_observations": {
            str(h): len(errors) for h, errors in forecast_errors.items()
        },
        "total_cash_dollars_after_redemption": final_cash / 100,
        "final_share_count": sum(account["shares"] for account in accounts.values()),
        "redeemed_shares": sum(account["redeemed_shares"] for account in accounts.values()),
        "trader_cash_range_dollars": [
            min(row["cash_dollars"] for row in trader_rows),
            max(row["cash_dollars"] for row in trader_rows),
        ],
        "terminal_state": {
            "finished": market["finished"],
            "period": market["period"],
            "last_price_cents": market["last_price_cents"],
            "orders_pending": len(market["orders"]),
        },
        "outputs": [round_path.name, trader_path.name],
    }
    summary_path = run_dir / "results_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir", type=Path,
        default=Path(__file__).parent / "pilot_02",
    )
    args = parser.parse_args()
    main(args.run_dir)

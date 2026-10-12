"""Export a compact summary from the persisted workflow and state event logs."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def analyze(output: Path):
    with sqlite3.connect(output / "state-0.sqlite") as connection:
        latest_payload = connection.execute(
            "SELECT payload FROM state_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    if latest_payload is None:
        raise RuntimeError("state log contains no events")
    final_event = json.loads(latest_payload[0])
    market = final_event["state"]["market"]

    with sqlite3.connect(output / "workflow.sqlite") as connection:
        rows = connection.execute(
            """
            SELECT i.step_name, i.participant_id, s.answers
            FROM workflow_items AS i
            JOIN workflow_submissions AS s ON s.work_item_id = i.id
            ORDER BY i.created_at
            """
        ).fetchall()
    submissions = [
        {
            "step": step,
            "participant": participant,
            "answers": json.loads(answers),
        }
        for step, participant, answers in rows
    ]

    trader_decisions = []
    exchange_settlement_acks = []
    for row in submissions:
        if row["step"].startswith("orders-"):
            answer = row["answers"]["decision"]
            trader_decisions.append(
                {
                    "round": int(row["step"].rsplit("-", 1)[1]),
                    "trader": row["participant"],
                    **answer,
                }
            )
        elif row["step"].startswith("exchange-"):
            exchange_settlement_acks.append(
                {
                    "round": int(row["step"].rsplit("-", 1)[1]),
                    "settled": row["answers"].get("settled"),
                }
            )

    tape = [
        {
            "round": event["round"],
            "best_bid": event["best_bid"]["price_cents"],
            "best_bidder": event["best_bid"]["trader"],
            "best_ask": event["best_ask"]["price_cents"],
            "best_asker": event["best_ask"]["trader"],
            "volume": event["volume"],
            "price_cents": event["price_cents"],
            "buyer": event["buyer"],
            "seller": event["seller"],
        }
        for event in market["tape"]
    ]
    accounts = {
        trader: {
            "cash_cents": account["cash_cents"],
            "shares": account["shares"],
        }
        for trader, account in market["accounts"].items()
    }
    summary = {
        "status": "completed",
        "round_count": len(tape),
        "trader_decision_count": len(trader_decisions),
        "exchange_settlement_acks": exchange_settlement_acks,
        "repeat_stop_condition": "Machine.is_complete()",
        "trades": sum(row["volume"] for row in tape),
        "tape": tape,
        "trader_decisions": trader_decisions,
        "ending_accounts": accounts,
        "ending_total_cash_cents": sum(
            account["cash_cents"] for account in accounts.values()
        ),
        "ending_total_shares": sum(
            account["shares"] for account in accounts.values()
        ),
        "machine_finished": market["finished"],
        "completed_work_items": len(submissions),
        "workflow_driver": "Workflow.repeat, max_iterations=2",
    }
    (output / "results_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "pilot_01",
    )
    args = parser.parse_args()
    print(json.dumps(analyze(args.output), indent=2))


if __name__ == "__main__":
    main()

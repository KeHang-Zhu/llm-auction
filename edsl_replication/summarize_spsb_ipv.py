"""Export bidder-level and auction-level summaries from one EDSL result JSON."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def summarize(source: Path, output_dir: Path) -> dict[str, Any]:
    payload = json.loads(source.read_text())
    results = payload["results"]
    result_rows = results["data"]
    bindings = results.get("shared_state", {}).get("bindings", [])
    if len(bindings) != 1:
        raise ValueError(f"expected one state binding, got {len(bindings)}")
    binding = bindings[0]
    exits = {
        snapshot["scope"]: snapshot["state"]["auction"]
        for snapshot in binding["exit_snapshots"]
    }

    rows_by_scope: dict[str, list[dict[str, Any]]] = {}
    failures = []
    for row in result_rows:
        traits = row["agent"]["traits"]
        answer = row.get("answer", {})
        if answer.get("bid_response") is None:
            failures.append(
                {
                    "auction_id": traits.get("auction_id"),
                    "bidder": traits.get("bidder_id"),
                    "answer": answer,
                }
            )
            continue
        rows_by_scope.setdefault(traits["auction_id"], []).append(
            {
                "repetition": int(traits["auction_id"].split("-")[-1]),
                "auction_id": traits["auction_id"],
                "seed": traits["seed"],
                "bidder": traits["bidder_id"],
                "seat": traits["seat"],
                "value": traits["value"],
                "plan": answer.get("plan"),
                "bid": float(answer["bid_response"]),
            }
        )

    bidder_rows = []
    auction_rows = []
    deviations = []
    prices = []
    winner_utilities = []
    efficient = 0
    on_grid = 0
    for scope, observed in sorted(rows_by_scope.items()):
        state = exits.get(scope)
        if state is None or state.get("winner") is None:
            failures.append({"auction_id": scope, "error": "missing closed state"})
            continue
        if len(observed) != 3:
            failures.append(
                {"auction_id": scope, "error": f"expected 3 bids, got {len(observed)}"}
            )
            continue
        winner = state["winner"]
        for observed_row in observed:
            delta = observed_row["bid"] - observed_row["value"]
            deviations.append(delta)
            on_grid += int(abs(observed_row["bid"] * 10 - round(observed_row["bid"] * 10)) < 1e-7)
            bidder_rows.append(
                observed_row
                | {
                    "bid_minus_value": delta,
                    "absolute_deviation": abs(delta),
                    "is_winner": observed_row["bidder"] == winner,
                    "profit": state["utilities"][observed_row["bidder"]],
                    "winner": winner,
                    "winning_bid": state["winning_bid"],
                    "price": state["price"],
                }
            )
        max_value = max(row["value"] for row in observed)
        winner_value = next(row["value"] for row in observed if row["bidder"] == winner)
        efficient += int(winner_value == max_value)
        prices.append(state["price"])
        winner_utilities.append(state["utilities"][winner])
        auction_rows.append(
            {
                "repetition": int(scope.split("-")[-1]),
                "auction_id": scope,
                "seed": observed[0]["seed"],
                "winner": winner,
                "winner_value": winner_value,
                "winning_bid": state["winning_bid"],
                "price": state["price"],
                "winner_profit": state["utilities"][winner],
                "allocatively_efficient": winner_value == max_value,
                "bidder_values": json.dumps(
                    {row["bidder"]: row["value"] for row in observed}, sort_keys=True
                ),
                "bids": json.dumps(
                    {row["bidder"]: row["bid"] for row in observed}, sort_keys=True
                ),
            }
        )

    if not bidder_rows:
        raise ValueError("no completed bidder observations found")
    all_values = [row["value"] for row in bidder_rows]
    all_bids = [row["bid"] for row in bidder_rows]
    summary = {
        "source_file": str(source),
        "model": result_rows[0].get("model", {}).get("model") if result_rows else None,
        "service": result_rows[0].get("model", {}).get("inference_service") if result_rows else None,
        "interviews": len(result_rows),
        "completed_bids": len(bidder_rows),
        "failed_observations": len(failures),
        "auctions_settled": len(auction_rows),
        "state_id": binding["state_id"],
        "event_count": len(binding["events"]),
        "read_events": sum(event["kind"] == "read" for event in binding["events"]),
        "write_events": sum(event["kind"] == "write" for event in binding["events"]),
        "close_events": sum(
            event["kind"] == "write" and event.get("command") == "$close"
            for event in binding["events"]
        ),
        "mean_value": statistics.mean(all_values),
        "mean_bid": statistics.mean(all_bids),
        "mean_bid_minus_value": statistics.mean(deviations),
        "median_bid_minus_value": statistics.median(deviations),
        "mean_absolute_deviation": statistics.mean(abs(value) for value in deviations),
        "smad_percent_normalizer_25": 100 * statistics.mean(abs(value) for value in deviations) / 25,
        "under_value": sum(value < -1e-9 for value in deviations),
        "equal_value": sum(abs(value) <= 1e-9 for value in deviations),
        "over_value": sum(value > 1e-9 for value in deviations),
        "bid_min": min(all_bids),
        "bid_max": max(all_bids),
        "bids_on_0_1_grid": on_grid,
        "mean_price": statistics.mean(prices),
        "median_price": statistics.median(prices),
        "mean_winner_utility": statistics.mean(winner_utilities),
        "allocatively_efficient_auctions": efficient,
        "winner_seat_counts": {
            name: sum(row["winner"] == name for row in auction_rows)
            for name in sorted({row["winner"] for row in auction_rows})
        },
        "protocol_note": (
            "Two-question plan/bid protocol; descriptive results are not directly "
            "comparable with the legacy one-response treatment."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        output_dir / "spsb_ipv_bidder_results.csv",
        bidder_rows,
        [
            "repetition", "auction_id", "seed", "bidder", "seat", "value", "plan",
            "bid", "bid_minus_value", "absolute_deviation", "is_winner", "profit",
            "winner", "winning_bid", "price",
        ],
    )
    _write_csv(
        output_dir / "spsb_ipv_auction_results.csv",
        auction_rows,
        [
            "repetition", "auction_id", "seed", "winner", "winner_value", "winning_bid",
            "price", "winner_profit", "allocatively_efficient", "bidder_values", "bids",
        ],
    )
    (output_dir / "spsb_ipv_summary.json").write_text(
        json.dumps(summary | {"failures": failures}, indent=2) + "\n"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    output_dir = args.output_dir or args.results.parent
    print(json.dumps(summarize(args.results, output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

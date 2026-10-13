#!/usr/bin/env python3
"""Audit existing Phase I evidence without model calls or third-party packages.

Run: python3 scripts/audit_phase1_evidence.py

Efficiency covers completed raw auctions in the five private-value baseline
formats and five main models. Each auction sells one object with zero reserve.
With seller opportunity cost taken as zero, realized total surplus is the
winner's value: bidder profit plus seller revenue. Optimal surplus is max(value).
We report both sum(realized)/sum(optimal) and mean(realized/optimal), as well as
the distinct statistic P(winner has a highest value), counting value ties as
efficient. These are descriptive statistics of saved completed runs, not a
guarantee about failed/missing runs or unseen auctions.

Read the recorded winner directly; do not reconstruct clock winners from exit
prices. The value-array order is Andy, Betty, Charles (util_plan.build_bidders).
Check profit accounting separately and retain discrepancies in the audit.
Common-value, eBay, framing, temperature, repeated-round, and duplicated V10
robustness data are excluded from efficiency. CSV model inventory also includes
the framing experiments, but its row counts are not independent observation
counts because exports can overlap.
"""

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMATS = (
    "fpsb_ipv", "spsb_ipv", "spsb_apv",
    "ascending_clock_apv", "ascending_clock_apv_closed",
)
MODELS = {
    "": "gpt-4o",
    "claude_sonnet": "claude-3-5-haiku-20241022",
    "gemini": "gemini-2.0-flash",
    "gpt5mini": "gpt-5-mini",
    "llama": "meta-llama/Meta-Llama-3-8B-Instruct",
}
NAMES = ("Bidder Andy", "Bidder Betty", "Bidder Charles")


def relative(path):
    return str(path.relative_to(ROOT))


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def inventory_models():
    counts, paths = Counter(), defaultdict(set)
    for base in ("experiment_logs", "robustness_logs"):
        for path in sorted((ROOT / base).rglob("*.csv")):
            if path.is_relative_to(ROOT / "robustness_logs" / "V10"):
                continue
            with path.open() as f:
                reader = csv.DictReader(f)
                if "model" not in (reader.fieldnames or []):
                    continue
                for row in reader:
                    model = row["model"].strip()
                    if model:
                        counts[model] += 1
                        paths[model].add(relative(path))
    return [{"model": m, "export_rows_including_overlaps": counts[m],
             "csv_files": len(paths[m]), "example_csv": min(paths[m])}
            for m in sorted(counts)]


def efficiency():
    detail, summary, issues = [], [], []
    for fmt in FORMATS:
        for suffix, model in MODELS.items():
            directory = (ROOT / "robustness_logs" / f"{fmt}_{suffix}" if suffix
                         else ROOT / "experiment_logs" / "V10" / fmt)
            cell = []
            for path in sorted(directory.glob("*/raw_data/*.json")):
                config = (path.parent.parent / "config.yaml").read_text()
                recorded_model = re.search(r"^  model: (.+)$", config, re.M)
                assert recorded_model and recorded_model[1].strip() == model, path
                assert re.search(r"^  number_agents: 3$", config, re.M), path
                assert re.search(r"^  rounds: 1$", config, re.M), path
                assert re.search(r"^  reserve_price: 0$", config, re.M), path
                assert re.search(r"^  private_value: (private|affiliated)$", config, re.M), path
                payload = path.read_bytes()
                for key, record in json.loads(payload).items():
                    if not key.startswith("round_"):
                        continue
                    values = record["value"]
                    assert len(values) == len(NAMES), path
                    assert all(math.isfinite(v) and v >= 0 for v in values), path
                    winner = record["history"]["winner"]
                    idx = NAMES.index(winner["winner"])
                    realized, optimal = values[idx], max(values)
                    assert optimal > 0, path
                    expected_profit = [0.0] * len(NAMES)
                    expected_profit[idx] = realized - winner["price"]
                    accounting_ok = len(record["profit"]) == len(NAMES) and all(
                        math.isclose(a, b, abs_tol=1e-7)
                        for a, b in zip(record["profit"], expected_profit))
                    if not accounting_ok:
                        issues.append({"raw_file": relative(path), "round": key,
                                       "recorded_profit": record["profit"],
                                       "expected_profit": expected_profit})
                    row = {
                        "format": fmt, "model": model, "raw_file": relative(path),
                        "sha256": hashlib.sha256(payload).hexdigest(), "round": key,
                        "winner": winner["winner"], "price": winner["price"],
                        "winner_value": realized, "max_value": optimal,
                        "efficiency_pct": 100 * realized / optimal,
                        "highest_value_winner": realized == optimal,
                        "profit_accounting_ok": accounting_ok,
                    }
                    detail.append(row)
                    cell.append(row)
            summary.append({
                "format": fmt, "model": model, "completed_auctions": len(cell),
                "aggregate_surplus_efficiency_pct": (
                    100 * sum(r["winner_value"] for r in cell)
                    / sum(r["max_value"] for r in cell) if cell else ""),
                "mean_auction_efficiency_pct": (
                    statistics.mean(r["efficiency_pct"] for r in cell) if cell else ""),
                "highest_value_winner_pct": (
                    100 * statistics.mean(r["highest_value_winner"] for r in cell)
                    if cell else ""),
                "profit_accounting_discrepancies": sum(
                    not r["profit_accounting_ok"] for r in cell),
                "thin_cell_under_30_auctions": len(cell) < 30,
            })
    return detail, summary, issues


def crosscheck_exports(detail):
    """Independently compare raw allocations with the existing bidder CSVs."""
    cells = defaultdict(list)
    for row in detail:
        cells[(row["format"], row["model"])].append(row)
    suffixes = {model: suffix for suffix, model in MODELS.items()}
    matched, unexported = 0, []
    for (fmt, model), rows in cells.items():
        suffix = suffixes[model]
        directory = (ROOT / "robustness_logs" / f"{fmt}_{suffix}" if suffix
                     else ROOT / "experiment_logs" / "V10" / fmt)
        files = sorted(directory.rglob("*_results.csv"))
        nonmerged = [p for p in files if "merged" not in p.name]
        groups = defaultdict(dict)
        for path in nonmerged or files:
            with path.open() as f:
                for row in csv.DictReader(f):
                    key = (row["timestamp"], row["repetition_id"], row["round"])
                    groups[key][row["player_name"]] = row
        exported = Counter()
        for players in groups.values():
            assert len(players) == 3, (fmt, model, players)
            winners = [r for r in players.values() if r["is_winner"].lower() == "true"]
            assert len(winners) == 1, (fmt, model, players)
            winner = winners[0]
            signature = (winner["player_name"], float(winner["player_value"]),
                         max(float(r["player_value"]) for r in players.values()),
                         round(float(winner["final_price"]), 8))
            exported[signature] += 1
        for row in rows:
            signature = (row["winner"], row["winner_value"], row["max_value"],
                         round(float(row["price"]), 8))
            if exported[signature]:
                exported[signature] -= 1
                matched += 1
            else:
                unexported.append(row["raw_file"])
        assert not +exported, (fmt, model, "CSV allocation absent from raw files", +exported)
    return {"matching_auction_allocations_and_prices": matched,
            "price_comparison_decimal_places": 8,
            "raw_auctions_without_matching_csv_export": unexported}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "results" / "phase1_evidence")
    args = parser.parse_args()
    models = inventory_models()
    detail, summary, issues = efficiency()
    crosscheck = crosscheck_exports(detail)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "recorded_models.csv", models)
    write_csv(args.output_dir / "allocative_efficiency_auctions.csv", detail)
    write_csv(args.output_dir / "allocative_efficiency_summary.csv", summary)
    manifest = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "recorded_models": len(models), "completed_auctions_audited": len(detail),
        "methodology": __doc__, "profit_accounting_discrepancies": issues,
        "independent_csv_crosscheck": crosscheck,
    }
    (args.output_dir / "audit.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Recorded models: {len(models)}; completed auctions audited: {len(detail)}")
    print(f"Profit accounting discrepancies: {len(issues)} (see audit.json)")
    print(f"CSV allocation cross-check matches: {crosscheck['matching_auction_allocations_and_prices']}")
    for row in summary:
        if row["model"] == "gpt-4o":
            print(f"{row['format']}: n={row['completed_auctions']}, "
                  f"surplus efficiency={row['aggregate_surplus_efficiency_pct']:.3f}%, "
                  f"highest-value winner={row['highest_value_winner_pct']:.3f}%")
    print(f"Outputs: {args.output_dir}")


if __name__ == "__main__":
    main()

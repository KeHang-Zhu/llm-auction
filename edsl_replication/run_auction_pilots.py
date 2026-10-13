"""Run a small local EDSL pilot for every archived auction condition."""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

import yaml

from edsl_replication.shared_state_auctions import ROOT, run_config, study_slug
from edsl_replication.write_auction_paper import write_study


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=2,
                        help="Auctions per condition (default: 2)")
    parser.add_argument("--only", action="append", default=[],
                        help="Run one condition slug or name; repeatable")
    parser.add_argument("--start-at", help="Start at this condition slug or name, inclusive")
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")

    configs = sorted((ROOT / "configs/experiments").glob("*.yaml"))
    status_path = ROOT / "edsl_replication" / "pilot_status.json"
    status: dict[str, dict[str, str]] = {}
    if status_path.exists():
        status.update(json.loads(status_path.read_text()))
    output_name = f"pilot_{args.repetitions:02d}_auctions"
    selected = 0
    started = args.start_at is None
    start_matched = started

    for config_path in configs:
        config = yaml.safe_load(config_path.read_text())
        slug, name = study_slug(config_path), config["experiment"]["name"]
        if not started:
            if args.start_at in (slug, name):
                started = True
                start_matched = True
            else:
                continue
        if args.only and slug not in args.only and name not in args.only:
            continue
        selected += 1
        pilot_dir = ROOT / "edsl_replication" / "studies" / slug / output_name
        raw_path = pilot_dir / "raw_results.json"
        paper_path = pilot_dir / "paper.pdf"
        try:
            if raw_path.exists():
                print(f"REUSING {slug}: {raw_path}", flush=True)
            else:
                status[slug] = {"status": "running", "repetitions": str(args.repetitions)}
                status_path.write_text(json.dumps(status, indent=2) + "\n")
                run_config(config_path, repetitions=args.repetitions, output=raw_path)
            # Rebuild derived files from the recorded pilot on resume as well.
            write_study(config_path, raw_results=raw_path, output_dir=pilot_dir)
            summary = json.loads((pilot_dir / "summary.json").read_text())
            if summary["completed_decisions"] == 0:
                raise RuntimeError(
                    "pilot has zero completed bidder decisions; see summary.json "
                    "and raw_results.json for recorded interview failures"
                )
            status[slug] = {
                "status": "complete", "repetitions": str(args.repetitions),
                "raw_results": str(raw_path), "paper": str(paper_path),
            }
            status_path.write_text(json.dumps(status, indent=2) + "\n")
            print(f"COMPLETE {slug}: {paper_path}", flush=True)
        except Exception as exc:
            status[slug] = {"status": "failed", "repetitions": str(args.repetitions),
                            "error": repr(exc), "traceback": traceback.format_exc()}
            status_path.write_text(json.dumps(status, indent=2) + "\n")
            print(f"FAILED {slug}: {exc}", flush=True)
            continue

    if not start_matched:
        print(f"Start condition not found: {args.start_at}")
        return 1
    if args.only and selected != len(args.only):
        print(f"Requested {len(args.only)} selector(s); matched {selected} config(s)")
        return 1
    completed = sum(row.get("status") == "complete" for row in status.values())
    failed = sum(row.get("status") == "failed" for row in status.values())
    partial = sum(row.get("status") == "partial_stopped" for row in status.values())
    print(f"PILOT PASS FINISHED: {selected} selected; {completed} complete, "
          f"{failed} failed, {partial} partial/stopped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

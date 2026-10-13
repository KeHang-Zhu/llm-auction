"""Run archived auction conditions locally and build one study folder per condition."""

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
    parser.add_argument("--start-at", help="Resume at this experiment name, inclusive")
    parser.add_argument("--only", action="append", default=[], help="Run one experiment name; repeatable")
    parser.add_argument("--repetitions", type=int,
                        help="Override archived repetitions for a small pilot run")
    args = parser.parse_args()
    configs = sorted((ROOT / "configs/experiments").glob("*.yaml"))
    status_file = ROOT / "edsl_replication" / "studies" / "run_status.json"
    status: dict[str, dict[str, str]] = {}
    if status_file.exists():
        status.update(json.loads(status_file.read_text()))
    started = args.start_at is None
    for config_path in configs:
        config = yaml.safe_load(config_path.read_text())
        name = config["experiment"]["name"]
        slug = study_slug(config_path)
        if args.only and slug not in args.only and name not in args.only:
            continue
        if not started:
            if slug == args.start_at or name == args.start_at:
                started = True
            else:
                continue
        study_dir = ROOT / "edsl_replication" / "studies" / slug
        old_spsb = ROOT / "edsl_replication/runs/spsb_ipv_gpt4o_100.json"
        try:
            raw_existing = study_dir / "raw_results.json"
            reusable = False
            if raw_existing.exists():
                previous = json.loads(raw_existing.read_text())
                old_config = previous.get("config", {})
                reusable = (
                    old_config.get("experiment", {}).get("name") == name
                    and old_config.get("auction", {}).get("number_agents")
                    == config["auction"]["number_agents"]
                )
            if reusable:
                raw = raw_existing
            elif name == "spsb_ipv" and old_spsb.exists():
                raw = old_spsb
            else:
                raw = run_config(config_path, repetitions=args.repetitions,
                                 output=study_dir / "raw_results.json")
            pdf = write_study(config_path, raw)
            status[slug] = {"status": "complete", "raw_results": str(raw), "pdf": str(pdf)}
            print(f"COMPLETE {slug}: {pdf}", flush=True)
        except Exception as exc:
            status[slug] = {"status": "failed", "error": repr(exc),
                            "traceback": traceback.format_exc()}
            status_file.parent.mkdir(parents=True, exist_ok=True)
            status_file.write_text(json.dumps(status, indent=2) + "\n")
            print(f"FAILED {slug}: {exc}", flush=True)
            break
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(status, indent=2) + "\n")
    return 0 if all(row["status"] == "complete" for row in status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

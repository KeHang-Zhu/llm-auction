#!/usr/bin/env python3
"""Top-up driver: run only the missing repetition ids of a config, with per-rep retries.

Why: partial cells fail transiently (empty provider responses under concurrency);
re-running a whole config duplicates already-completed seeds across run_* dirs, which
build_auction_cells.py would pool twice. This driver scans all existing
run_*/raw_data/raw_output__run{N}.jsonl under the config's output_dir, computes the
missing ids in range(repetitions), and runs exactly those (seed = seed_base + id is
deterministic, so the union across run dirs reconstructs the full K without duplicates).

Usage:
  python3 new/topup_runs.py --config <cfg.yaml> [--retries 3] [--sleep 20] [--dry-run]
"""

import argparse
import re
import sys
import time
from pathlib import Path

import importlib.util

_spec = importlib.util.spec_from_file_location("new_main", Path(__file__).parent / "main.py")
_new_main = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
_spec.loader.exec_module(_new_main)
ExperimentOrchestrator = _new_main.ExperimentOrchestrator


def existing_rep_ids(output_dir: Path):
    ids = set()
    for f in output_dir.glob("run_*/raw_data/raw_output__run*.jsonl"):
        m = re.search(r"raw_output__run(\d+)\.jsonl$", f.name)
        if m:
            ids.add(int(m.group(1)))
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=20.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    orch = ExperimentOrchestrator(args.config)
    out_dir = Path(orch.config.output_dir)
    K = orch.config.repetitions
    done = existing_rep_ids(out_dir)
    missing = [i for i in range(K) if i not in done]
    print(f"[topup] {args.config}: {len(done)}/{K} done, {len(missing)} missing: {missing}", flush=True)
    if args.dry_run or not missing:
        return

    orch.setup_experiment()  # creates run dir + metadata_mgr (required by run_single_experiment)

    results = []
    for rid in missing:
        ok = False
        for attempt in range(1, args.retries + 1):
            try:
                r = orch.run_single_experiment(rid)
                results.append(r)
                ok = True
                break
            except Exception as e:  # transient provider failures
                print(f"[topup] rep {rid} attempt {attempt} failed: {e}", flush=True)
                time.sleep(args.sleep * attempt)
        if not ok:
            results.append({"run_id": rid, "status": "failed", "error": "retries exhausted"})

    orch.finalize_experiment(results)
    n_ok = sum(1 for r in results if r.get("status") == "completed")
    print(f"[topup] DONE {n_ok}/{len(missing)} topped up; now {len(existing_rep_ids(out_dir))}/{K} total", flush=True)


if __name__ == "__main__":
    main()

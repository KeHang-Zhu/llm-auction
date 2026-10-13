"""Run a one-auction operational coverage sweep over the curated 50-model roster."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import signal
import sys
from contextlib import contextmanager
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SWEEP = Path(__file__).resolve().parent / "model_coverage_50"
BASE_CONFIG = ROOT / "configs/experiments/01_03_fpsb_ipv.yaml"
INPUT_TOKENS_PER_CALL = 2_000
OUTPUT_TOKENS_PER_CALL = 1_000
CALLS_PER_AUCTION = 6  # 3 bidders, each gets a plan question and a bid question.
# Load repository credentials before importing EDSL, whose model registry reads
# provider keys during initialization. GROK_API_KEY is accepted as the xAI key
# alias used by this project's .env; EDSL's service looks for XAI_API_KEY.
load_dotenv(ROOT / ".env", override=True)
if not os.environ.get("XAI_API_KEY") and os.environ.get("GROK_API_KEY"):
    os.environ["XAI_API_KEY"] = os.environ["GROK_API_KEY"]
sys.path.insert(0, str(ROOT))

from edsl_replication.shared_state_auctions import run_config


@contextmanager
def model_timeout(seconds: int):
    """Bound slow provider calls so one model cannot stall the full sweep."""
    if seconds <= 0:
        yield
        return
    previous = signal.getsignal(signal.SIGALRM)
    def alarm_handler(*_):
        raise TimeoutError(f"Model exceeded {seconds}s time limit")
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()


def model_cost(result_data: list[dict]) -> float:
    total = 0.0
    for row in result_data:
        response = row.get("raw_model_response") or {}
        total += sum(float(v) for k, v in response.items() if k.endswith("_cost"))
    return total


def run(roster_path: Path, max_spend: float, only_models: set[str] | None = None,
        retry_failed: bool = False, model_timeout_seconds: int = 240) -> int:
    SWEEP.mkdir(parents=True, exist_ok=True)
    runs_dir = SWEEP / "runs"
    runs_dir.mkdir(exist_ok=True)
    roster = list(csv.DictReader(roster_path.open(newline="")))
    names = [row["model"] for row in roster]
    if len(roster) != 50 or len(set(names)) != 50:
        raise ValueError(f"Expected 50 unique model IDs; found {len(roster)} rows and {len(set(names))} IDs")

    total_estimate = sum(
        CALLS_PER_AUCTION * (
            INPUT_TOKENS_PER_CALL * float(row["input_usd_per_1m"])
            + OUTPUT_TOKENS_PER_CALL * float(row["output_usd_per_1m"])
        ) / 1_000_000
        for row in roster
    )
    if total_estimate > max_spend:
        raise ValueError(f"Conservative token estimate ${total_estimate:.2f} exceeds cap ${max_spend:.2f}; no runs submitted")

    base = yaml.safe_load(BASE_CONFIG.read_text())
    summary_path = SWEEP / "summary.csv"
    # Resume from the prior attempt so successful models are not billed twice.
    rows_by_rank: dict[int, dict[str, object]] = {}
    if summary_path.exists():
        with summary_path.open(newline="") as f:
            for prior in csv.DictReader(f):
                rows_by_rank[int(prior["rank"])] = prior
    rows: list[dict[str, object]] = []
    actual_total = sum(
        float(row.get("actual_usd") or 0)
        for row in rows_by_rank.values()
    )

    for index, model_row in enumerate(roster, start=1):
        model_name, service = model_row["model"], model_row["service"]
        estimate = CALLS_PER_AUCTION * (
            INPUT_TOKENS_PER_CALL * float(model_row["input_usd_per_1m"])
            + OUTPUT_TOKENS_PER_CALL * float(model_row["output_usd_per_1m"])
        ) / 1_000_000
        prior = rows_by_rank.get(index)
        if only_models and model_name not in only_models:
            if prior:
                rows.append(prior)
            continue
        if prior and prior.get("status") == "complete":
            rows.append(prior)
            print(f"{index:02d}/50 {model_name}: already complete; preserving prior result", flush=True)
            continue
        if prior and prior.get("status") in {"partial_or_failed", "error"} and not retry_failed:
            rows.append(prior)
            print(f"{index:02d}/50 {model_name}: prior failure retained; use --retry-failed to rerun", flush=True)
            continue
        if service == "bedrock":
            row = prior or {
                "rank": index, "model": model_name, "service": service,
                "status": "pending_credentials", "valid_bidders": 0,
                "auction_id": "auction-0000", "estimate_usd": round(estimate, 6),
                "actual_usd": 0.0,
                "results_file": f"runs/{index:02d}-{slug(model_name)}.json",
                "error": "AWS Bedrock credentials not configured; run deferred.",
            }
            row["status"] = "pending_credentials"
            row["error"] = "AWS Bedrock credentials not configured; run deferred."
            rows.append(row)
            print(f"{index:02d}/50 {model_name}: pending AWS Bedrock credentials", flush=True)
            continue
        if actual_total + estimate > max_spend:
            print(f"STOP: remaining conservative estimate would exceed ${max_spend:.2f}", flush=True)
            break

        label = f"{index:02d}-{slug(model_name)}"
        config = json.loads(json.dumps(base))
        config["experiment"]["name"] = f"coverage50_{label}"
        config["llm"]["model"] = model_name
        config["llm"]["service_name"] = service
        config_path = SWEEP / f"{label}.yaml"
        output_path = runs_dir / f"{label}.json"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        row: dict[str, object] = prior or {
            "rank": index, "model": model_name, "service": service,
            "status": "error", "valid_bidders": 0, "auction_id": "auction-0000",
            "estimate_usd": round(estimate, 6), "actual_usd": 0.0,
            "results_file": str(output_path.relative_to(SWEEP)), "error": "",
        }
        prior_spend = float(row.get("actual_usd") or 0)
        row.update({
            "model": model_name, "service": service, "status": "error",
            "valid_bidders": 0, "estimate_usd": round(estimate, 6),
            "results_file": str(output_path.relative_to(SWEEP)), "error": "",
        })
        try:
            with model_timeout(model_timeout_seconds):
                run_config(config_path, repetitions=1, output=output_path)
            payload = json.loads(output_path.read_text())
            result_data = payload.get("results", {}).get("data", [])
            spend = model_cost(result_data)
            actual_total += spend
            valid = [
                item for item in result_data
                if isinstance(item.get("answer", {}).get("bid_response"), (int, float))
            ]
            row["valid_bidders"] = len(valid)
            row["actual_usd"] = round(prior_spend + spend, 6)
            row["status"] = "complete" if len(valid) == 3 else "partial_or_failed"
            if len(valid) != 3:
                row["error"] = "Fewer than three valid numeric bids; inspect raw result."
            print(f"{index:02d}/50 {model_name}: {row['status']} ({len(valid)}/3 bidders; ${spend:.4f}; total ${actual_total:.4f})", flush=True)
        except Exception as exc:
            row["actual_usd"] = round(prior_spend, 6)
            row["error"] = repr(exc)
            print(f"{index:02d}/50 {model_name}: ERROR {exc}", flush=True)
        rows.append(row)
        with summary_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    successful = sum(row["status"] == "complete" for row in rows)
    print(f"Finished {len(rows)} roster entries: {successful} complete; ${actual_total:.4f} observed model cost; estimated full sweep ${total_estimate:.2f}.", flush=True)
    pending = sum(row["status"] == "pending_credentials" for row in rows)
    return 0 if len(rows) == 50 and successful + pending == 50 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path, default=SWEEP / "models.csv")
    parser.add_argument("--max-spend", type=float, default=50.0)
    parser.add_argument("--only-model", action="append", default=[],
                        help="Run only this model ID; may be repeated.")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Retry models previously recorded as failed.")
    parser.add_argument("--model-timeout", type=int, default=240,
                        help="Maximum seconds allowed for one model (default: 240).")
    args = parser.parse_args()
    if args.max_spend <= 0:
        parser.error("--max-spend must be positive")
    return run(args.roster, args.max_spend, set(args.only_model) or None,
               args.retry_failed, args.model_timeout)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Inventory of every simulated auction behind the reported results.

For each experimental cell, reads the run summaries (experiment_summary.json)
to count attempted, completed and failed auctions and the error messages of
the failed ones, and takes the number of LLM decisions used in the analysis
from the analysis outputs.  Writes

    results/analysis/data_inventory.csv
    results/tables/data_inventory_lab.tex      (laboratory formats, N=3)
    results/tables/data_inventory_other.tex    (other experiments)
    results/tables/data_inventory_numbers.tex  (macros for the text)

Run:  python analysis/data_inventory.py
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "results" / "analysis"
TAB = ROOT / "results" / "tables"
V10, ROB, CLK = "experiment_logs/V10", "robustness_logs", "experiment_logs/clock_one_llm"
PAPER_INT = ROOT / "experiment_logs" / "paper_interventions"

FORMATS = [  # (key in logs, label, key in model_smad_results, key in temperature csv, kind)
    ("fpsb_ipv", "First-price IPV", "First-Price IPV", "FPSB IPV", "sealed"),
    ("spsb_ipv", "Second-price IPV", "Second-Price IPV", "SPSB IPV", "sealed"),
    ("spsb_apv", "Second-price APV", "Second-Price APV", "SP-APV", "sealed"),
    ("ascending_clock_apv", "Open clock APV", "Ascending Clock APV", "AC", "clock"),
    ("ascending_clock_apv_closed", "Closed clock APV", "AC-Closed (AC-B) APV", "AC-B", "clock"),
    ("common_value_first", "First-price CV", "First-Price CV", "FP-CV", "cv"),
    ("common_value_second", "Second-price CV", "Second-Price CV", "SP-CV", "cv"),
]
# (column label, model key in results, temperature, suffix in log dirs, replacement model in clocks)
COLUMNS = [
    ("GPT-4o, $T{=}0.1$", None, 0.1, "gpt4o_temp01", False),
    ("GPT-4o, $T{=}0.5$", "gpt4o", 0.5, "", False),
    ("GPT-4o, $T{=}1.0$", None, 1.0, "gpt4o_temp10", False),
    ("Claude 3.5 Haiku", "claude_sonnet", 0.5, "claude_sonnet", True),
    ("Gemini 2.0 Flash", "gemini", 0.5, "gemini", True),
    ("GPT-5-mini", "gpt5mini", 0.5, "gpt5mini", False),
    ("Llama-3-8B", "llama", 0.5, "llama", True),
]


def cell_dir(fmt: str, kind: str, suffix: str) -> Path:
    if kind == "clock":
        return ROOT / CLK / (f"{fmt}_{suffix}_one_llm" if suffix else f"{fmt}_one_llm")
    if not suffix:
        return ROOT / V10 / fmt
    return ROOT / ROB / f"{fmt}_{suffix}"


def classify(msg: str) -> str:
    m = msg.lower()
    if "timed out" in m:
        return "timeout"
    if "503" in m or "504" in m or "could not connect" in m:
        return "server"
    return "other"


def summarize(d: Path) -> dict:
    files = sorted(d.glob("run_*/experiment_summary.json"))
    if not files:
        raise FileNotFoundError(d)
    att = ok = fail = 0
    errs = collections.Counter()
    for f in files:
        s = json.load(open(f))
        r = s.get("results_summary", {})
        e = s.get("execution", {})
        a = r.get("total_runs", e.get("repetitions"))
        c = r.get("completed_runs", e.get("completed_repetitions"))
        att, ok = att + int(a), ok + int(c)
        fail += int(a) - int(c)
        msgs = r.get("errors") or []
        for m in msgs:
            errs[classify(str(m))] += 1
        # finalized cells: remaining runs stopped responding and were ended
        if int(a) - int(c) > len(msgs):
            errs["stalled"] += int(a) - int(c) - len(msgs)
    return {"attempted": att, "completed": ok, "failed": fail, **{f"err_{k}": v for k, v in errs.items()}}


def read_csv(p: Path) -> list[dict]:
    with open(p) as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    smad = {(r["auction"], r["model_key"]): r for r in read_csv(AN / "model_smad_results_one_llm.csv")}
    temp = {(float(r["temperature"]), r["format"]): r for r in read_csv(AN / "temperature_concordance_one_llm.csv")}
    rows = []
    for fmt, flab, skey, tkey, kind in FORMATS:
        for clab, mk, t, suf, repl in COLUMNS:
            s = summarize(cell_dir(fmt, kind, suf))
            used = int(float(smad[(skey, mk)]["n"])) if mk else int(float(temp[(t, tkey)]["n"]))
            rows.append({"block": "lab", "experiment": flab, "model": clab, "kind": kind,
                         "replacement": repl and kind == "clock", "used": used, **s})

    other = []
    for n in (4, 5, 6, 7):
        s = summarize(ROOT / V10 / f"common_value_first_{n}player")
        other.append({"block": "cv_n", "experiment": f"First-price CV, $N{{=}}{n}$", "model": "GPT-4o",
                      "unit": "auctions", "used": s["completed"], **s})
    for fmt, lab in (("fpsb_ipv_15_rounds", "First-price IPV"), ("spsb_ipv_15_round", "Second-price IPV")):
        s = summarize(ROOT / ROB / fmt)
        other.append({"block": "repeated", "experiment": f"{lab}, 15 rounds", "model": "GPT-4o",
                      "unit": "sessions", "used": s["completed"] * 15 * 3, **s})
    proto = json.load(open(PAPER_INT / "protocols.json"))
    base = read_csv(PAPER_INT / "baselines.csv")
    ints = {(r["model_display"], r["cell"]): int(float(r["n_bids"])) for r in read_csv(AN / "interventions_models.csv")}
    for mdir, mid, disp in (("gpt4o", "gpt-4o", "GPT-4o"), ("claude", "claude-3-5-haiku-20241022", "Claude 3.5 Haiku"),
                            ("gemini", "gemini-2.0-flash", "Gemini 2.0 Flash"), ("gemma", "google/gemma-3-27b-it", "Gemma-3-27B")):
        att = sum(proto[mdir][e]["execution"]["repetitions"] for e in ("axis1_contingent_baseline", "axis3_beliefs_baseline"))
        done = len({(r["experiment"], r["repetition_id"]) for r in base if r["model"] == mid})
        other.append({"block": "framing", "experiment": "SPSB IPV, standard description", "model": disp,
                      "unit": "auctions", "attempted": att, "completed": done, "failed": att - done, "used": ints[(disp, "baseline")]})
        for exp, cell, lab in (("intervention_menu", "menu", "SPSB IPV, menu description"),
                               ("intervention_proxy_breitmoser", "clock", "SPSB IPV, clock description")):
            att = proto[mdir][exp]["execution"]["repetitions"]
            done = len(list((PAPER_INT / mdir / exp).glob("result_*.json")))
            other.append({"block": "framing", "experiment": lab, "model": disp, "unit": "auctions",
                          "attempted": att, "completed": done, "failed": att - done, "used": ints[(disp, cell)]})
    for d, lab in (("ebay_proxy", "eBay-style, hard close"), ("ebay_closing_rule", "eBay-style, soft close")):
        n = len(list((ROOT / V10 / d).glob("result_*.csv")))
        other.append({"block": "ebay", "experiment": lab, "model": "GPT-4o", "unit": "auctions",
                      "attempted": n, "completed": n, "failed": 0, "used": n})

    allrows = rows + other
    keys = sorted({k for r in allrows for k in r})
    with open(AN / "data_inventory.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(allrows)

    # ---- laboratory table: completed / attempted, decisions used below
    hdr = " & ".join(["Format"] + [c[0] for c in COLUMNS])
    L = ["% Auto-generated by analysis/data_inventory.py -- do not edit by hand.",
         "\\begin{tabular}{@{}l" + "c" * len(COLUMNS) + "@{}}", "\\toprule", hdr + " \\\\", "\\midrule"]
    for fmt, flab, *_ in FORMATS:
        cells = [r for r in rows if r["experiment"] == flab]
        top = " & ".join(f"{r['completed']}/{r['attempted']}" + ("$^{r}$" if r["replacement"] else "") for r in cells)
        bot = " & ".join(f"{{\\scriptsize ({r['used']})}}" for r in cells)
        L += [f"{flab} & {top} \\\\", f" & {bot} \\\\"]
        if fmt in ("spsb_apv", "ascending_clock_apv_closed"):
            L.append("\\addlinespace")
    L += ["\\bottomrule", "\\end{tabular}"]
    (TAB / "data_inventory_lab.tex").write_text("\n".join(L) + "\n")

    # ---- other experiments
    O = ["% Auto-generated by analysis/data_inventory.py -- do not edit by hand.",
         "\\begin{tabular}{@{}llrrr@{}}", "\\toprule",
         "Experiment & Model & Attempted & Completed & Decisions used \\\\", "\\midrule"]
    prev = None
    for r in other:
        if prev and r["block"] != prev:
            O.append("\\addlinespace")
        prev = r["block"]
        unit = " sessions" if r["unit"] == "sessions" else ""
        a = "---" if r["attempted"] is None else f"{r['attempted']}{unit}"
        O.append(f"{r['experiment']} & {r['model']} & {a} & {r['completed']}{unit} & {r['used']} \\\\")
    O += ["\\bottomrule", "\\end{tabular}"]
    (TAB / "data_inventory_other.tex").write_text("\n".join(O) + "\n")

    # ---- numbers for the text (auctions; a failed 15-round session loses 15 auctions)
    logged = [r for r in allrows if r.get("attempted") is not None]
    mult = lambda r: 15 if r.get("unit") == "sessions" else 1
    att = sum(r["attempted"] * mult(r) for r in logged)
    fail = sum(r["failed"] * mult(r) for r in logged)
    with_log = [r for r in logged if r["block"] != "framing"]  # framing battery: no error log
    failed_runs = sum(r["failed"] for r in with_log)
    errs = collections.Counter()
    for r in with_log:
        for k in ("timeout", "server", "other", "stalled"):
            errs[k] += int(r.get(f"err_{k}", 0) or 0)
    assert sum(errs.values()) == failed_runs, (errs, failed_runs)
    M = ["% Auto-generated by analysis/data_inventory.py -- do not edit by hand.",
         f"\\newcommand{{\\InvAttempted}}{{{att:,}}}".replace(",", "{,}", 1) if att >= 1000 else f"\\newcommand{{\\InvAttempted}}{{{att}}}",
         f"\\newcommand{{\\InvFailed}}{{{fail}}}",
         f"\\newcommand{{\\InvFailedPct}}{{{100 * fail / att:.1f}}}",
         f"\\newcommand{{\\InvFailedRuns}}{{{failed_runs}}}",
         f"\\newcommand{{\\InvTimeout}}{{{errs['timeout']}}}",
         f"\\newcommand{{\\InvServer}}{{{errs['server'] + errs['other']}}}",
         f"\\newcommand{{\\InvStalled}}{{{errs['stalled']}}}"]
    (TAB / "data_inventory_numbers.tex").write_text("\n".join(M) + "\n")
    print(f"attempted {att}, failed {fail} ({100*fail/att:.1f}%), failed runs with log {failed_runs}: {dict(errs)}")
    print("wrote", TAB / "data_inventory_lab.tex", TAB / "data_inventory_other.tex")


if __name__ == "__main__":
    main()

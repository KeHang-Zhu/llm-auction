#!/usr/bin/env python3
"""Attempt / completion / censoring / usable counts for the one-LLM clock cells.

Answers the reviewers' question "How many clock auctions were attempted,
completed, and excluded?". Reads every run summary and result CSV under
CLOCK_ONE_LLM_DIR (default experiment_logs/clock_one_llm) through
analysis/clock_data.py.

Outputs
  results/analysis/clock_attrition_one_llm.csv
  results/tables/clock_attrition_one_llm.tex   (tabular-only fragment)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("CLOCK_DESIGN", "one_llm")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_data as cd  # noqa: E402

import pandas as pd  # noqa: E402

ROOT = cd.PROJECT_ROOT
FORMATS = [("ascending_clock_apv", "AC (open)"), ("ascending_clock_apv_closed", "AC-B (closed)")]
# (suffix, display label); labels name the model actually queried.
CELLS = [
    ("", "GPT-4o, $T=0.5$"),
    ("gpt4o_temp01", "GPT-4o, $T=0.1$"),
    ("gpt4o_temp10", "GPT-4o, $T=1.0$"),
    ("claude_sonnet", "Claude Haiku 5.5$^{r}$"),
    ("gemini", "Gemini 2.5 Flash$^{r}$"),
    ("gpt5mini", "GPT-5-mini"),
    ("llama", "Llama-3.1-8B$^{r}$"),
]
MIN_N = 30


def main() -> None:
    rows = []
    for fkey, flabel in FORMATS:
        for suffix, mlabel in CELLS:
            a = cd.one_llm_attrition(fkey, suffix)
            rows.append({"format": flabel, "model": mlabel, **a,
                         "failed": a["attempted"] - a["completed"]})
    df = pd.DataFrame(rows)
    out_csv = ROOT / "results" / "analysis" / "clock_attrition_one_llm.csv"
    df.to_csv(out_csv, index=False)

    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"Format & Model & Attempted & Failed & Completed & LLM won (censored) & Usable \\",
             r"\midrule"]
    for i, r in df.iterrows():
        if i and r["format"] != df.loc[i - 1, "format"]:
            lines.append(r"\midrule")
        usable = f"{r['usable']}" + (r"$^{\dagger}$" if r["usable"] < MIN_N else "")
        lines.append(f"{r['format']} & {r['model']} & {r['attempted']} & {r['failed']} & "
                     f"{r['completed']} & {r['censored']} & {usable} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    out_tex = ROOT / "results" / "tables" / "clock_attrition_one_llm.tex"
    out_tex.write_text("\n".join(lines) + "\n")
    print(df.to_string(index=False))
    short = df[df["usable"] < MIN_N]
    if len(short):
        print(f"\nCells below n={MIN_N}:\n{short[['format', 'model', 'usable']].to_string(index=False)}")
    print(f"\nSaved {out_csv.relative_to(ROOT)} and {out_tex.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

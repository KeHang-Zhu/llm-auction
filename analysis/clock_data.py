"""Shared loading of ascending-clock cells for the analysis scripts.

Two clock designs exist:

* ``legacy`` (default): three LLM bidders per auction, the data used in the
  September 2026 manuscript. Usable observations are non-winners, because the
  winner's exit price is censored by the end of the auction.
* ``one_llm``: one LLM bidder (Andy) against two programmed opponents that stay
  while the next price does not exceed their value (``configs/clock_one_llm/``).
  Each auction yields at most one LLM observation. The exporter writes
  ``is_llm``, ``llm_exit`` and ``llm_censored``. In the blind clock the LLM's
  exit is observed even after it wins; in the open clock a winning LLM is
  censored and dropped.

Select the design with the environment variable ``CLOCK_DESIGN`` (``legacy`` or
``one_llm``). ``CLOCK_ONE_LLM_DIR`` overrides the root of the one-LLM runs. In ``one_llm`` mode the analysis
scripts write their outputs with the suffix ``_one_llm`` so that the published
legacy outputs, which ``scripts/reproduce_paper.py --check`` verifies, are not
overwritten.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DESIGN = os.environ.get("CLOCK_DESIGN", "legacy").strip().lower()
if DESIGN not in {"legacy", "one_llm"}:
    raise ValueError(f"CLOCK_DESIGN must be 'legacy' or 'one_llm', not {DESIGN!r}")
ONE_LLM = DESIGN == "one_llm"

ONE_LLM_ROOT = Path(os.environ.get("CLOCK_ONE_LLM_DIR",
                                   PROJECT_ROOT / "experiment_logs" / "clock_one_llm"))
if not ONE_LLM_ROOT.is_absolute():
    ONE_LLM_ROOT = PROJECT_ROOT / ONE_LLM_ROOT

OUT_SUFFIX = "_one_llm" if ONE_LLM else ""


def out_name(filename: str) -> str:
    """'model_smad_results.csv' -> 'model_smad_results_one_llm.csv' in one_llm mode."""
    if not OUT_SUFFIX:
        return filename
    stem, dot, ext = filename.rpartition(".")
    return f"{stem}{OUT_SUFFIX}.{ext}" if dot else filename + OUT_SUFFIX


def one_llm_dir(format_key: str, suffix: str = "") -> Path:
    """Directory of a one-LLM cell. ``format_key`` is ``ascending_clock_apv`` or
    ``ascending_clock_apv_closed``; ``suffix`` is the model/temperature suffix
    used in robustness_logs (``""`` for GPT-4o at T=0.5, ``claude_sonnet``,
    ``gemini``, ``gpt5mini``, ``llama``, ``gpt4o_temp01``, ``gpt4o_temp10``)."""
    name = f"{format_key}_{suffix}_one_llm" if suffix else f"{format_key}_one_llm"
    return ONE_LLM_ROOT / name


def load_one_llm(format_key: str, suffix: str = "") -> pd.DataFrame | None:
    """All result CSVs of a one-LLM cell, de-duplicated; None if the cell has no data."""
    cell = one_llm_dir(format_key, suffix)
    files = sorted(cell.glob("run_*/results/*_results.csv"))
    files = [f for f in files if "merged" not in f.name]
    if not files:
        return None
    df = pd.concat([pd.read_csv(f).assign(source_csv=str(f.relative_to(PROJECT_ROOT)))
                    for f in files], ignore_index=True)
    key = [c for c in ("source_csv", "repetition_id", "round", "player_name") if c in df.columns]
    return df.drop_duplicates(subset=key).reset_index(drop=True)


def _as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def usable_clock_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows that carry an uncensored exit price, with ``bid`` set to that price.

    One-LLM data (``is_llm`` column present): the LLM row of each auction when
    ``llm_censored`` is False, using ``llm_exit``. Legacy data: non-winners.
    """
    if "is_llm" in df.columns and _as_bool(df["is_llm"]).any():
        d = df[_as_bool(df["is_llm"]) & ~_as_bool(df["llm_censored"])].copy()
        d["bid"] = pd.to_numeric(d["llm_exit"], errors="coerce")
        return d.dropna(subset=["bid"])
    return df[~_as_bool(df["is_winner"])].copy()


def one_llm_attrition(format_key: str, suffix: str = "") -> dict:
    """Attempted / completed / usable counts for a one-LLM cell, read from the
    run summaries and the result CSVs (for the attempt-and-exclusion table)."""
    import json

    cell = one_llm_dir(format_key, suffix)
    attempted = completed = 0
    for summ in cell.glob("run_*/experiment_summary.json"):
        s = json.loads(summ.read_text())
        rs = s.get("results_summary", s)
        attempted += int(rs.get("total_runs", 0) or 0)
        completed += int(rs.get("completed_runs", 0) or 0)
    df = load_one_llm(format_key, suffix)
    llm = df[_as_bool(df["is_llm"])] if df is not None else pd.DataFrame()
    usable = int((~_as_bool(llm["llm_censored"])).sum()) if len(llm) else 0
    return {"cell": str(cell.relative_to(PROJECT_ROOT)), "attempted": attempted,
            "completed": completed, "auctions_with_results": int(len(llm)),
            "censored": int(len(llm) - usable), "usable": usable}

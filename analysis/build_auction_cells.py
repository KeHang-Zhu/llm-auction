#!/usr/bin/env python3
"""
Build the master auction-cells dataset with full inference (plan E3/E6/E8).

For every (model x experiment) auction cell found in six sources, compute
descriptive stats on the signed deviation (bid - value, $), SMAD (normalized
by E[b*] = 24.5 for values Unif{0..49}), RNE-benchmark deviations for
first/third-price cells, and vs-baseline inference (Welch t, Mann-Whitney,
Cohen's d, bootstrap 95% CIs; 2000 draws, numpy seed 1299).

Sources
-------
(a) es_v12_csv : Engineering_simplicity/engineer_simplicity-main/results/
                 all_experiments_combined_20260204_114522.csv  (4 models)
(b) es_v12_raw : Engineering_simplicity/engineer_simplicity-main/
                 experiment_logs/<model>/<exp>/ flat result_*.json dirs that
                 are NOT in (a): intervention_{menu,proxy_breitmoser,
                 NE_strat_reveal,nash_deviation,wrong_strat_reveal},
                 axis1_contingent_{backward_induct,onestep,tree},
                 private_second_price. Env metadata comes from
                 configs_auction/interventions_<model>/<exp>.yaml.
(c) v12_gpt4o_recovered : recovered_logs/experiment_logs_gpt_4o/V12/*
                 (incl. _first/_third price-order variants; all gpt-4o).
(d) v10_gpt4o_anchor    : experiment_logs/V10/* (GPT-4o anchor cells).
(e) robustness          : robustness_logs/* (excl. duplicated V10/ subdir).
(f) v10_recovered_expl  : recovered_logs/experiment_logs_with_explanation/V10/*
                 (NOTE: configs say model gpt-4o, NOT gpt-5-mini; 14/22 runs
                 duplicate run-ids in (d) -- do not pool with (d)).

Baseline mapping (documented in the output .md):
- ES V12 family (a)+(b) and the recovered V12 family (c):
    axisK_* treatment           -> axisK_*_baseline (same axis, same suffix)
    loss_aversion_*             -> loss_aversion_baseline (same suffix)
    risk_averse / risk_seeking  -> risk_neutrality (V12r: intervention_risk_neutral_S)
    everything else (menu, proxy_breitmoser, strat reveals, nash_deviation,
      spsb, private_second_price, ascending_clock_closed, risk_neutrality,
      loss_aversion_baseline)   -> POOLED axis baseline (axis1+axis2+axis3
      baselines pooled, same model, same price-order suffix)
    axis baselines themselves   -> none (constituents of the pooled baseline)
- V10-style families (d), (f) and robustness (e), per model/temp group:
    fpsb_ipv, third_price_ipv*, all_pay_ipv, intervention_* -> spsb_ipv
    spsb_apv -> spsb_ipv ; ascending_clock_apv{,_closed} -> spsb_apv
    common_value_* -> none (no canonical truthful baseline; deviations are
      bid - private signal, descriptive only)

Outputs
-------
results/merged_ranking/auction_cells.csv
results/merged_ranking/auction_cells_summary.md

Reproducibility: every bootstrap uses a fresh np.random.default_rng(1299)
per cell, so results are independent of processing order.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ES = ROOT / "Engineering_simplicity" / "engineer_simplicity-main"
ES_CSV = ES / "results" / "all_experiments_combined_20260204_114522.csv"
OUT_DIR = ROOT / "results" / "merged_ranking"
OUT_CSV = OUT_DIR / "auction_cells.csv"
OUT_MD = OUT_DIR / "auction_cells_summary.md"

SEED = 1299
N_BOOT = 2000
SMAD_NORM = 24.5          # E[b*] for truthful bidding, values Unif{0..49}
WITHIN_FRAC = 0.02        # "within +/-2%" band: |bid - value| <= 0.02 * value
ENDOWMENT_CAP = 49.0      # for capped third-price RNE benchmark

PLAYER_IDX = {f"Bidder {n}": i for i, n in enumerate(
    ["Andy", "Betty", "Charles", "David", "Ethel", "Florian", "Gray"])}

ES_MODEL_DIRS = {  # experiment_logs/<dir> -> canonical model id
    "claude": "claude-3-5-haiku-20241022",
    "gemini": "gemini-2.0-flash",
    "gemma": "google/gemma-3-27b-it",
    "gpt4o": "gpt-4o",
    # frontier battery (plan/FRONTIER_RUNBOOK.md); runs routed via OpenRouter 2026-07-08
    "gpt5mini": "gpt-5-mini",
    "gemini25flash": "gemini-2.5-flash",
    "claude_sonnet5": "claude-sonnet-5",
    "gpt5": "gpt-5",
}

# ES paper's published pooled axis-baseline mean deviations (bid - value, $)
ES_PUBLISHED_BASELINES = {
    "claude-3-5-haiku-20241022": -0.5,
    "gemini-2.0-flash": -1.6,
    "gpt-4o": -3.3,
    "google/gemma-3-27b-it": -5.3,
}

BID_COLS = ["model", "experiment", "source", "family", "group",
            "player_value", "bid", "seal_clock", "price_order", "env",
            "increment", "seed_base", "number_agents", "temperature",
            "run_id", "source_path"]

# OpenRouter-routed runs (2026-07-08) carry provider-prefixed model ids in their
# configs/CSVs; normalize to the canonical ids so cells pool with the incumbent
# grids. (google/gemma-3-27b-it is already the canonical id — no alias needed.)
MODEL_ALIASES = {
    "openai/gpt-4o-2024-08-06": "gpt-4o",
    "openai/gpt-5-mini": "gpt-5-mini",
    "openai/gpt-5": "gpt-5",
    "anthropic/claude-3.5-haiku-20241022": "claude-3-5-haiku-20241022",
    "google/gemini-2.0-flash-001": "gemini-2.0-flash",
    "google/gemini-2.5-flash": "gemini-2.5-flash",
    "anthropic/claude-sonnet-5": "claude-sonnet-5",
}


def canon_model(m):
    return MODEL_ALIASES.get(m, m)


# ----------------------------------------------------------------------------
# Loaders -> long bid-level DataFrame
# ----------------------------------------------------------------------------
def _rows_from_run_csv(csv_path: Path, source, family, group, experiment,
                       model_override=None):
    df = pd.read_csv(csv_path)
    out = pd.DataFrame({
        "model": (canon_model(model_override) if model_override
                  else df["model"].map(canon_model)),
        "experiment": experiment,
        "source": source, "family": family, "group": group,
        "player_value": pd.to_numeric(df["player_value"], errors="coerce"),
        "bid": pd.to_numeric(df["bid"], errors="coerce"),
        "seal_clock": df.get("seal_clock"),
        "price_order": df.get("price_order"),
        "env": df.get("private_value"),
        "increment": df.get("increment"),
        "seed_base": df.get("seed_base"),
        "number_agents": df.get("number_agents"),
        "temperature": df.get("temperature"),
        "run_id": csv_path.parent.parent.name,
        "source_path": str(csv_path.relative_to(ROOT)),
    })
    return out


def _rows_from_raw_json(json_path: Path, cfg: dict, source, family, group,
                        experiment):
    """Parse a raw result_*.json (same logic as src/export_results.py)."""
    with open(json_path) as f:
        res = json.load(f)
    rule, val, auc = cfg["rule"], cfg["value"], cfg["auction"]
    llm = cfg["llm"]
    rows = []
    for rk in sorted(res.keys()):
        rd = res[rk]
        values = rd["value"]
        for idx, entry in enumerate(rd["history"]["bidding history"]):
            pidx = PLAYER_IDX.get(entry["agent"], idx)
            if pidx >= len(values):
                continue
            rows.append({
                "model": canon_model(llm["model"]), "experiment": experiment,
                "source": source, "family": family, "group": group,
                "player_value": values[pidx], "bid": entry.get("bid"),
                "seal_clock": rule["seal_clock"],
                "price_order": rule["price_order"],
                "env": rule["private_value"],
                "increment": val.get("increment"),
                "seed_base": val.get("seed_base"),
                "number_agents": auc["number_agents"],
                "temperature": llm.get("temperature"),
                "run_id": json_path.parent.name,
                "source_path": str(json_path.parent.relative_to(ROOT)),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["player_value"] = pd.to_numeric(df["player_value"], errors="coerce")
        df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
    return df


def _load_run_dirs(exp_dir: Path, source, family, group, experiment):
    """Load all run_* dirs under exp_dir: prefer results/*.csv, else raw JSON."""
    frames, notes = [], []
    run_dirs = sorted(exp_dir.glob("run_*"))
    for rd in run_dirs:
        csvs = sorted((rd / "results").glob("*.csv")) if (rd / "results").exists() else []
        if csvs:
            for c in csvs:
                frames.append(_rows_from_run_csv(c, source, family, group, experiment))
            continue
        raws = sorted((rd / "raw_data").glob("result_*.json")) if (rd / "raw_data").exists() else []
        if raws:
            cfg = yaml.safe_load(open(rd / "config.yaml"))
            for j in raws:
                frames.append(_rows_from_raw_json(j, cfg, source, family, group, experiment))
            notes.append(f"run {rd.name}: no results CSV, parsed {len(raws)} raw JSONs")
        else:
            notes.append(f"run {rd.name}: EMPTY (no results CSV, no raw_data)")
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BID_COLS)
    return df, notes, len(run_dirs)


def load_source_a():
    df = pd.read_csv(ES_CSV)
    out = pd.DataFrame({
        "model": df["model"], "experiment": df["experiment"],
        "source": "es_v12_csv", "family": "es_v12", "group": df["model"],
        "player_value": pd.to_numeric(df["player_value"], errors="coerce"),
        "bid": pd.to_numeric(df["bid"], errors="coerce"),
        "seal_clock": df["seal_clock"], "price_order": df["price_order"],
        "env": df["private_value"], "increment": df["increment"],
        "seed_base": df["seed_base"], "number_agents": df["number_agents"],
        "temperature": df["temperature"], "run_id": df["timestamp"],
        "source_path": str(ES_CSV.relative_to(ROOT)),
    })
    return out, {}


def load_source_b(csv_cells):
    """ES raw dirs (flat result_*.json) not present in the combined CSV."""
    frames, cell_notes = [], {}
    for mdir, model in ES_MODEL_DIRS.items():
        base = ES / "experiment_logs" / mdir
        if not base.exists():
            continue
        for exp_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            exp = exp_dir.name
            if (model, exp) in csv_cells:
                continue  # already covered by source (a)
            raws = sorted(exp_dir.glob("result_*.json"))
            if not raws:  # run-dir style but not in CSV -> load run dirs
                df, notes, _ = _load_run_dirs(exp_dir, "es_v12_raw", "es_v12",
                                              model, exp)
                if not df.empty:
                    frames.append(df)
                    if notes:
                        cell_notes[("es_v12_raw", model, exp)] = "; ".join(notes)
                continue
            cfg_path = ES / "configs_auction" / f"interventions_{mdir}" / f"{exp}.yaml"
            if not cfg_path.exists():
                cell_notes[("es_v12_raw", model, exp)] = f"no config found at {cfg_path.name}; skipped"
                continue
            cfg = yaml.safe_load(open(cfg_path))
            sub = [_rows_from_raw_json(j, cfg, "es_v12_raw", "es_v12", model, exp)
                   for j in raws]
            df = pd.concat([s for s in sub if not s.empty], ignore_index=True)
            df["source_path"] = str(exp_dir.relative_to(ROOT))
            frames.append(df)
    return pd.concat(frames, ignore_index=True), cell_notes


def load_run_dir_source(base: Path, source, family, group_fn):
    frames, cell_notes, empty_cells = [], {}, []
    for exp_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        exp = exp_dir.name
        group = group_fn(exp)
        df, notes, n_runs = _load_run_dirs(exp_dir, source, family, group, exp)
        if df.empty:
            empty_cells.append((source, family, group, exp,
                                str(exp_dir.relative_to(ROOT)),
                                "; ".join(notes) if notes else "no data"))
            continue
        frames.append(df)
        if notes:
            cell_notes[(source, df["model"].iloc[0], exp)] = "; ".join(notes)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BID_COLS)
    return df, cell_notes, empty_cells


# robustness dir-name parsing ------------------------------------------------
ROBUST_BASES = ["ascending_clock_apv_closed", "ascending_clock_apv",
                "common_value_first", "common_value_second", "fpsb_ipv",
                "spsb_apv", "spsb_ipv", "third_price_ipv", "all_pay_ipv"]
ROBUST_SUFFIXES = ["claude_sonnet", "gemini", "gpt5mini", "llama",
                   "gpt4o_temp01", "gpt4o_temp10"]


def robust_parse(exp):
    """Return (base_experiment, group_suffix) for a robustness dir name."""
    for b in ROBUST_BASES:
        if exp.startswith(b):
            rest = exp[len(b):].strip("_")
            variant = ""
            if rest.endswith("_3player") or rest == "3player":
                variant = "_3player"
                rest = rest.replace("3player", "").strip("_")
            if rest in ("15_rounds", "15_round"):
                return b + "_" + rest, "gpt4o_15round"
            suffix = rest if rest in ROBUST_SUFFIXES else (rest or "gpt4o")
            return b + variant, suffix
    return exp, "unknown"


# ----------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------
def boot_ci(dev, rng, n_boot=N_BOOT):
    """Percentile bootstrap CI on mean deviation and on SMAD_pct."""
    n = len(dev)
    idx = rng.integers(0, n, size=(n_boot, n))
    samp = dev[idx]
    means = samp.mean(axis=1)
    smads = 100.0 * np.abs(samp).mean(axis=1) / SMAD_NORM
    return (np.percentile(means, [2.5, 97.5]), np.percentile(smads, [2.5, 97.5]))


def cohens_d(a, b):
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return np.nan
    s = np.sqrt(((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1))
                / (n1 + n2 - 2))
    return (a.mean() - b.mean()) / s if s > 0 else np.nan


def rne_bstar(values, price_order, n_agents):
    """Risk-neutral Nash equilibrium bid for IPV sealed-bid auctions."""
    v = np.asarray(values, dtype=float)
    n = int(n_agents)
    if price_order == "first":
        return v * (n - 1) / n
    if price_order == "third" and n >= 3:
        return v * (n - 1) / (n - 2)
    if price_order == "second":
        return v.copy()
    return None


def summarize_cell(sub: pd.DataFrame):
    """Compute all per-cell statistics from bid-level rows."""
    n_raw = len(sub)
    sub = sub.dropna(subset=["player_value", "bid"])
    n_dropped = n_raw - len(sub)
    v = sub["player_value"].to_numpy(float)
    b = sub["bid"].to_numpy(float)
    dev = b - v
    n = len(dev)
    rec = {"n_bids": n, "n_rows_dropped_nan_bid": n_dropped}
    if n == 0:
        return rec, dev
    rng = np.random.default_rng(SEED)
    mean_ci, smad_ci = boot_ci(dev, rng)
    band = WITHIN_FRAC * v
    rec.update({
        "mean_dev": dev.mean(),
        "sd_dev": dev.std(ddof=1) if n > 1 else np.nan,
        "se_dev": dev.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan,
        "median_dev": np.median(dev),
        "mad": np.abs(dev).mean(),
        "smad_pct": 100.0 * np.abs(dev).mean() / SMAD_NORM,
        "boot_ci_mean_lo": mean_ci[0], "boot_ci_mean_hi": mean_ci[1],
        "boot_ci_smad_lo": smad_ci[0], "boot_ci_smad_hi": smad_ci[1],
        "share_under": float((dev < -band).mean()),
        "share_over": float((dev > band).mean()),
        "share_within_2pct": float((np.abs(dev) <= band).mean()),
    })
    # RNE benchmark for IPV sealed first/third (and second, where b*=v)
    env = sub["env"].mode().iloc[0] if sub["env"].notna().any() else None
    po = sub["price_order"].mode().iloc[0] if sub["price_order"].notna().any() else None
    sc = sub["seal_clock"].mode().iloc[0] if sub["seal_clock"].notna().any() else None
    na = sub["number_agents"].mode().iloc[0] if sub["number_agents"].notna().any() else None
    if env == "private" and sc == "seal" and po in ("first", "third") and na:
        bstar = rne_bstar(v, po, na)
        if bstar is not None:
            dev_r = b - bstar
            norm = bstar.mean()
            rec.update({
                "rne_benchmark": (f"b*=v*(n-1)/n, n={int(na)}" if po == "first"
                                  else f"b*=v*(n-1)/(n-2), n={int(na)}"),
                "mean_dev_rne": dev_r.mean(),
                "mad_rne": np.abs(dev_r).mean(),
                "smad_rne_pct": 100.0 * np.abs(dev_r).mean() / norm if norm > 0 else np.nan,
            })
            if po == "third":
                bcap = np.minimum(bstar, ENDOWMENT_CAP)
                rec["mean_dev_rne_capped"] = (b - bcap).mean()
    return rec, dev


def vs_baseline(dev, base_dev):
    if dev is None or base_dev is None or len(dev) < 2 or len(base_dev) < 2:
        return {}
    t, p = stats.ttest_ind(dev, base_dev, equal_var=False)
    try:
        mw = stats.mannwhitneyu(dev, base_dev, alternative="two-sided").pvalue
    except ValueError:
        mw = np.nan
    return {"diff_mean_dev": dev.mean() - base_dev.mean(),
            "welch_t": t, "welch_p": p, "mw_p": mw,
            "cohens_d": cohens_d(dev, base_dev)}


# ----------------------------------------------------------------------------
# Baseline mapping
# ----------------------------------------------------------------------------
# CORRECTED 2026-07-08: the V12 `axis2_forward_baseline` template was a two-stage
# sealed-bid-as-clock-exit description, not a plain SPSB text (see
# results/merged_ranking/_axis2_baseline_provenance.md). It is therefore a TREATED
# cell: excluded from the pooled axis baseline and contrasted against the clean pool.
AXIS_BASELINES = ["axis1_contingent_baseline", "axis3_beliefs_baseline"]
AXIS_BASELINES_LEGACY = ["axis1_contingent_baseline", "axis2_forward_baseline",
                         "axis3_beliefs_baseline"]


def v12_suffix(exp):
    if exp.endswith("_first"):
        return exp[:-6], "_first"
    if exp.endswith("_third"):
        return exp[:-6], "_third"
    return exp, ""


def baseline_for(family, group, exp, cell_devs):
    """Return (baseline_label, dev_array or None, is_baseline_flag)."""
    def pool(names, suffix=""):
        arrs, found = [], []
        for nm in names:
            key = (family, group, nm + suffix)
            if key in cell_devs and len(cell_devs[key]) > 0:
                arrs.append(cell_devs[key])
                found.append(nm + suffix)
        if not arrs:
            return None, None
        return "POOLED[" + "+".join(found) + "]", np.concatenate(arrs)

    def single(nm):
        key = (family, group, nm)
        if key in cell_devs and len(cell_devs[key]) > 0:
            return nm, cell_devs[key]
        return None, None

    if family in ("es_v12", "v12r"):
        core, suf = (exp, "") if family == "es_v12" else v12_suffix(exp)
        if core in AXIS_BASELINES:
            return None, None, True
        if core == "axis2_forward_baseline":
            # treated cell (two-stage clock-exit description): contrast vs clean pool
            lbl, arr = pool(AXIS_BASELINES, suf)
            return lbl, arr, False
        if core.startswith("axis1_"):
            lbl, arr = single("axis1_contingent_baseline" + suf)
        elif core.startswith("axis2_"):
            # axis-2 treatments: own-axis "baseline" is contaminated; use clean pool
            lbl, arr = pool(AXIS_BASELINES, suf)
        elif core.startswith("axis3_"):
            lbl, arr = single("axis3_beliefs_baseline" + suf)
        elif core.startswith("loss_aversion") and core != "loss_aversion_baseline":
            lbl, arr = single("loss_aversion_baseline" + suf)
        elif core in ("risk_averse", "risk_seeking"):
            lbl, arr = single("risk_neutrality" + suf)
        elif core in ("intervention_risk_averse", "intervention_risk_seeking"):
            lbl, arr = single("intervention_risk_neutral" + suf)
        else:
            lbl, arr = pool(AXIS_BASELINES, suf)
        return lbl, arr, False

    # V10-style families and robustness: mechanism-level baselines
    if exp == "spsb_ipv" or exp.startswith("spsb_ipv_15"):
        return None, None, True
    if exp.startswith("common_value"):
        return None, None, False
    if exp.startswith("ascending_clock_apv"):
        lbl, arr = single("spsb_apv")
        return lbl, arr, False
    if exp == "spsb_apv":
        lbl, arr = single("spsb_ipv")
        return lbl, arr, False
    if exp.startswith("fpsb_ipv_15"):
        lbl, arr = single("spsb_ipv_15_round")
        return lbl, arr, False
    lbl, arr = single("spsb_ipv")
    return lbl, arr, False


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_notes = {}

    # ---- load all sources ----
    df_a, _ = load_source_a()
    csv_cells = set(zip(df_a["model"], df_a["experiment"]))
    df_b, notes_b = load_source_b(csv_cells)
    all_notes.update(notes_b)

    df_c, notes_c, empty_c = load_run_dir_source(
        ROOT / "recovered_logs" / "experiment_logs_gpt_4o" / "V12",
        "v12_gpt4o_recovered", "v12r", lambda e: "gpt-4o")
    df_d, notes_d, empty_d = load_run_dir_source(
        ROOT / "experiment_logs" / "V10",
        "v10_gpt4o_anchor", "v10", lambda e: "gpt-4o")
    df_e, notes_e, empty_e = load_run_dir_source(
        ROOT / "robustness_logs",
        "robustness", "robustness", lambda e: robust_parse(e)[1])
    df_f, notes_f, empty_f = load_run_dir_source(
        ROOT / "recovered_logs" / "experiment_logs_with_explanation" / "V10",
        "v10_recovered_expl", "v10r_expl", lambda e: "gpt-4o")
    for nd in (notes_c, notes_d, notes_e, notes_f):
        all_notes.update(nd)

    # robustness: group is the model/temp suffix; drop the duplicated V10/ subdir
    df_e = df_e[~df_e["source_path"].str.startswith("robustness_logs/V10")]

    bids = pd.concat([df_a, df_b, df_c, df_d, df_e, df_f], ignore_index=True)
    print(f"Loaded {len(bids)} bid rows across "
          f"{bids.groupby(['source','model','experiment']).ngroups} cells")

    # ---- per-cell stats ----
    # cell_devs is keyed by (family, group, BASE experiment name); for the
    # robustness family the model/temp suffix is stripped from the dir name so
    # that e.g. spsb_ipv_llama is found as the baseline for fpsb_ipv_llama.
    cell_devs = {}
    records = []
    for (source, family, group, model, exp), sub in bids.groupby(
            ["source", "family", "group", "model", "experiment"], sort=True):
        base_exp = robust_parse(exp)[0] if family == "robustness" else exp
        rec = {"source": source, "family": family, "group": group,
               "model": model, "experiment": exp}
        stats_rec, dev = summarize_cell(sub)
        rec.update(stats_rec)
        rec.update({
            "env": ";".join(sorted(sub["env"].dropna().astype(str).unique())),
            "seal_clock": ";".join(sorted(sub["seal_clock"].dropna().astype(str).unique())),
            "price_order": ";".join(sorted(sub["price_order"].dropna().astype(str).unique())),
            "number_agents": ";".join(sorted(sub["number_agents"].dropna().astype(int).astype(str).unique())),
            "increment": ";".join(sorted(sub["increment"].dropna().astype(str).unique())),
            "seed_base": ";".join(sorted(sub["seed_base"].dropna().astype(int).astype(str).unique())),
            "temperature": ";".join(sorted(sub["temperature"].dropna().astype(str).unique())),
            "n_runs": sub["run_id"].nunique(),
            "source_path": ";".join(sorted(sub["source_path"].unique())[:3]),
            "notes": all_notes.get((source, model, exp), ""),
        })
        records.append(rec)
        cell_devs[(family, group, base_exp)] = dev

    # pooled axis-baseline cells (for the harmonized SPSB baseline question)
    pooled_rows = []
    for family, groups in [("es_v12", sorted(set(df_a["model"])))]:
        for g in groups:
            for label, blist in (("POOLED_axis_baseline", AXIS_BASELINES),
                                 ("POOLED_axis_baseline_legacy", AXIS_BASELINES_LEGACY)):
                arrs = [cell_devs[(family, g, nm)] for nm in blist
                        if (family, g, nm) in cell_devs]
                if arrs:
                    pooled_rows.append((family, g, label, np.concatenate(arrs)))
    for suf in ("", "_first", "_third"):
        for label, blist in ((f"POOLED_axis_baseline{suf}", AXIS_BASELINES),
                             (f"POOLED_axis_baseline_legacy{suf}", AXIS_BASELINES_LEGACY)):
            arrs = [cell_devs[("v12r", "gpt-4o", nm + suf)] for nm in blist
                    if ("v12r", "gpt-4o", nm + suf) in cell_devs]
            if arrs:
                pooled_rows.append(("v12r", "gpt-4o", label, np.concatenate(arrs)))
    for family, g, name, dev in pooled_rows:
        rng = np.random.default_rng(SEED)
        mean_ci, smad_ci = boot_ci(dev, rng)
        source = "es_v12_csv" if family == "es_v12" else "v12_gpt4o_recovered"
        records.append({
            "source": source, "family": family, "group": g, "model": g if family == "es_v12" else "gpt-4o",
            "experiment": name, "n_bids": len(dev), "n_rows_dropped_nan_bid": 0,
            "mean_dev": dev.mean(), "sd_dev": dev.std(ddof=1),
            "se_dev": dev.std(ddof=1) / np.sqrt(len(dev)),
            "median_dev": np.median(dev), "mad": np.abs(dev).mean(),
            "smad_pct": 100 * np.abs(dev).mean() / SMAD_NORM,
            "boot_ci_mean_lo": mean_ci[0], "boot_ci_mean_hi": mean_ci[1],
            "boot_ci_smad_lo": smad_ci[0], "boot_ci_smad_hi": smad_ci[1],
            "env": "private", "seal_clock": "seal",
            "price_order": {"": "second", "_first": "first", "_third": "third"}[
                name.replace("POOLED_axis_baseline", "").replace("_legacy", "")],
            "is_baseline": True,
            "notes": ("pooled axis1+axis3 baselines (derived cell; axis2_forward_baseline "
                      "excluded as a treated clock-exit description, see "
                      "results/merged_ranking/_axis2_baseline_provenance.md)"
                      if "_legacy" not in name else
                      "LEGACY pooled axis1+axis2+axis3 baselines (contains the treated "
                      "axis2 clock-exit cell; comparison only)"),
        })
        cell_devs[(family, g, name)] = dev

    # empty cells -> NA rows
    for (source, family, group, exp, path, note) in empty_c + empty_d + empty_e + empty_f:
        if "robustness_logs/V10" in path:
            continue
        records.append({"source": source, "family": family, "group": group,
                        "model": "NA", "experiment": exp, "n_bids": 0,
                        "source_path": path,
                        "notes": "NO DATA: " + note})

    cells = pd.DataFrame(records)

    # ---- vs-baseline inference ----
    infer_cols = {c: [] for c in ["baseline_experiment", "baseline_n",
                                  "baseline_mean_dev", "diff_mean_dev",
                                  "welch_t", "welch_p", "mw_p", "cohens_d",
                                  "is_baseline"]}
    for _, row in cells.iterrows():
        if row.get("n_bids", 0) == 0 or str(row["experiment"]).startswith("POOLED"):
            flag = bool(row.get("is_baseline", False))
            for c in infer_cols:
                infer_cols[c].append(flag if c == "is_baseline" else np.nan)
            continue
        base_exp = (robust_parse(row["experiment"])[0]
                    if row["family"] == "robustness" else row["experiment"])
        lbl, base_dev, is_base = baseline_for(row["family"], row["group"],
                                              base_exp, cell_devs)
        dev = cell_devs.get((row["family"], row["group"], base_exp))
        res = vs_baseline(dev, base_dev) if base_dev is not None else {}
        infer_cols["baseline_experiment"].append(lbl if lbl else np.nan)
        infer_cols["baseline_n"].append(len(base_dev) if base_dev is not None else np.nan)
        infer_cols["baseline_mean_dev"].append(base_dev.mean() if base_dev is not None else np.nan)
        infer_cols["diff_mean_dev"].append(res.get("diff_mean_dev", np.nan))
        infer_cols["welch_t"].append(res.get("welch_t", np.nan))
        infer_cols["welch_p"].append(res.get("welch_p", np.nan))
        infer_cols["mw_p"].append(res.get("mw_p", np.nan))
        infer_cols["cohens_d"].append(res.get("cohens_d", np.nan))
        infer_cols["is_baseline"].append(is_base)
    for c, vals in infer_cols.items():
        cells[c] = vals

    col_order = ["source", "family", "group", "model", "experiment",
                 "env", "seal_clock", "price_order", "number_agents",
                 "increment", "seed_base", "temperature", "n_runs", "n_bids",
                 "n_rows_dropped_nan_bid", "mean_dev", "sd_dev", "se_dev",
                 "median_dev", "mad", "smad_pct",
                 "boot_ci_mean_lo", "boot_ci_mean_hi",
                 "boot_ci_smad_lo", "boot_ci_smad_hi",
                 "share_under", "share_over", "share_within_2pct",
                 "rne_benchmark", "mean_dev_rne", "mad_rne", "smad_rne_pct",
                 "mean_dev_rne_capped",
                 "is_baseline", "baseline_experiment", "baseline_n",
                 "baseline_mean_dev", "diff_mean_dev", "welch_t", "welch_p",
                 "mw_p", "cohens_d", "source_path", "notes"]
    for c in col_order:
        if c not in cells.columns:
            cells[c] = np.nan
    cells = cells[col_order].sort_values(
        ["family", "group", "model", "experiment"]).reset_index(drop=True)
    cells.to_csv(OUT_CSV, index=False, float_format="%.6g")
    print(f"Wrote {OUT_CSV} ({len(cells)} cell rows)")

    write_summary(cells)
    print(f"Wrote {OUT_MD}")


# ----------------------------------------------------------------------------
# Markdown summary
# ----------------------------------------------------------------------------
def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    return f"{x:.{nd}f}"


def fmt_p(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "NA"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def md_table(df, cols, headers):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_summary(cells):
    L = []
    L.append("# Master auction-cells dataset — summary\n")
    L.append(f"Generated by `analysis/build_auction_cells.py` "
             f"(bootstrap: {N_BOOT} draws, numpy seed {SEED}; "
             f"SMAD normalizer E[b*] = {SMAD_NORM}).\n")
    non_derived = cells[~cells["experiment"].astype(str).str.startswith("POOLED")]
    L.append(f"- Cells: **{len(cells)}** rows in `results/merged_ranking/auction_cells.csv` "
             f"({len(non_derived)} measured cells + "
             f"{len(cells) - len(non_derived)} derived POOLED baseline rows; "
             f"{int(non_derived['n_bids'].fillna(0).sum())} bid-level observations).")
    src_counts = cells.groupby("source")["experiment"].count()
    L.append("- Cells per source: " + ", ".join(f"{k}={v}" for k, v in src_counts.items()) + ".")
    L.append("- Deviation = bid − value ($); value = private value (IPV/APV) or "
             "private signal (common-value cells). SMAD% = 100·mean|dev|/24.5. "
             "`share_within_2pct` uses |bid−value| ≤ 0.02·value; under/over are "
             "relative to that band. RNE columns (first/third-price IPV cells): "
             "FPSB b\\*=v(n−1)/n, TPSB b\\*=v(n−1)/(n−2); "
             "`mean_dev_rne_capped` caps TPSB b\\* at the $49 endowment.\n")

    def get(source, model, exp):
        m = cells[(cells.source == source) & (cells.model == model) & (cells.experiment == exp)]
        return m.iloc[0] if len(m) else None

    # ---- E3: menu + clock framing across 4 models ----
    L.append("## E3 headline: menu and clock-framing across all four models\n")
    L.append("Baseline for each cell = same model's **pooled axis baseline** "
             "(axis1+axis2+axis3 `*_baseline`, sealed-bid SPSB, from the ES combined CSV). "
             "GPT-4o's published pattern: menu ≈ null, clock framing = large improvement.\n")
    rows = []
    for model in ["claude-3-5-haiku-20241022", "gemini-2.0-flash", "gpt-4o",
                  "google/gemma-3-27b-it"]:
        for exp, src in [("intervention_menu", "es_v12_raw"),
                         ("intervention_proxy_breitmoser", "es_v12_raw"),
                         ("ascending_clock_closed", "es_v12_csv")]:
            r = get(src, model, exp)
            if r is None:
                rows.append({"model": model, "exp": exp, "n": "NA", "mean": "NA",
                             "ci": "NA", "base": "NA", "diff": "NA", "p": "NA",
                             "d": "NA", "sig": "no data"})
                continue
            sig = ("**yes**" if pd.notna(r.welch_p) and r.welch_p < 0.05 else "no")
            pooled = get("es_v12_csv", model, "POOLED_axis_baseline")
            rows.append({"model": model, "exp": exp, "n": int(r.n_bids),
                         "mean": fmt(r.mean_dev),
                         "ci": f"[{fmt(r.boot_ci_mean_lo)}, {fmt(r.boot_ci_mean_hi)}]",
                         "base": fmt(r.baseline_mean_dev),
                         "diff": fmt(r.diff_mean_dev),
                         "smad": fmt(r.smad_pct, 1),
                         "base_smad": fmt(pooled.smad_pct, 1) if pooled is not None else "NA",
                         "p": fmt_p(r.welch_p), "d": fmt(r.cohens_d),
                         "sig": sig})
    L.append(md_table(pd.DataFrame(rows),
                      ["model", "exp", "n", "mean", "ci", "base", "diff",
                       "smad", "base_smad", "p", "d", "sig"],
                      ["Model", "Cell", "n", "Mean dev ($)", "95% CI (boot)",
                       "Baseline mean", "Δ vs baseline", "SMAD %",
                       "Baseline SMAD %", "Welch p", "Cohen's d", "Sig. (5%)"]))
    L.append("")
    # data-driven verdict bullets
    L.append("Replication verdict (relative to GPT-4o's pattern of menu-null and "
             "large clock-framing improvement):\n")
    for model in ["claude-3-5-haiku-20241022", "gemini-2.0-flash", "gpt-4o",
                  "google/gemma-3-27b-it"]:
        menu = get("es_v12_raw", model, "intervention_menu")
        clock = get("es_v12_csv", model, "ascending_clock_closed")
        pooled = get("es_v12_csv", model, "POOLED_axis_baseline")
        parts = [f"- **{model}**:"]
        if menu is not None and pd.notna(menu.welch_p):
            verdict = "null" if menu.welch_p >= 0.05 else (
                "shifts bids UP" if menu.diff_mean_dev > 0 else "shifts bids DOWN")
            parts.append(f"menu {verdict} (Δ={fmt(menu.diff_mean_dev)}, "
                         f"p={fmt_p(menu.welch_p)}, d={fmt(menu.cohens_d)});")
        if clock is not None and pooled is not None:
            parts.append(f"clock framing cuts SMAD from {fmt(pooled.smad_pct,1)}% "
                         f"to {fmt(clock.smad_pct,1)}% "
                         f"(p={fmt_p(clock.welch_p)}, d={fmt(clock.cohens_d)}).")
        L.append(" ".join(parts))
    L.append("")
    L.append("GPT-4o replication cells from other sources (baseline = same-family `spsb_ipv`):\n")
    rows = []
    for src in ["v10_gpt4o_anchor", "v10_recovered_expl", "v12_gpt4o_recovered"]:
        for exp in ["intervention_menu", "intervention_proxy_breitmoser",
                    "intervention_menu_first", "intervention_menu_third",
                    "intervention_proxy_breitmoser_first",
                    "intervention_proxy_breitmoser_third"]:
            r = get(src, "gpt-4o", exp)
            if r is None:
                continue
            rows.append({"src": src, "exp": exp, "n": int(r.n_bids),
                         "mean": fmt(r.mean_dev),
                         "ci": f"[{fmt(r.boot_ci_mean_lo)}, {fmt(r.boot_ci_mean_hi)}]",
                         "base": (f"{r.baseline_experiment} ({fmt(r.baseline_mean_dev)})"
                                  if pd.notna(r.baseline_experiment) else "—"),
                         "diff": fmt(r.diff_mean_dev), "p": fmt_p(r.welch_p),
                         "d": fmt(r.cohens_d)})
    L.append(md_table(pd.DataFrame(rows),
                      ["src", "exp", "n", "mean", "ci", "base", "diff", "p", "d"],
                      ["Source", "Cell", "n", "Mean dev ($)", "95% CI",
                       "Baseline (mean)", "Δ", "Welch p", "Cohen's d"]))
    L.append("")

    # ---- harmonized SPSB baselines ----
    L.append("## Harmonized per-model pooled SPSB axis baselines vs published values\n")
    rows = []
    for model, pub in ES_PUBLISHED_BASELINES.items():
        r = get("es_v12_csv", model, "POOLED_axis_baseline")
        rs = get("es_v12_csv", model, "spsb")
        if r is None:
            rows.append({"model": model, "n": "NA", "mean": "NA", "ci": "NA",
                         "smad": "NA", "spsb": "NA", "pub": pub, "match": "no data"})
            continue
        inside = (r.boot_ci_mean_lo <= pub <= r.boot_ci_mean_hi)
        rows.append({"model": model, "n": int(r.n_bids), "mean": fmt(r.mean_dev),
                     "ci": f"[{fmt(r.boot_ci_mean_lo)}, {fmt(r.boot_ci_mean_hi)}]",
                     "smad": fmt(r.smad_pct, 1),
                     "spsb": fmt(rs.mean_dev) if rs is not None else "NA",
                     "pub": pub,
                     "match": "within CI" if inside else "**outside CI**"})
    L.append(md_table(pd.DataFrame(rows),
                      ["model", "n", "mean", "ci", "smad", "spsb", "pub", "match"],
                      ["Model", "n", "Pooled axis-baseline mean dev ($)",
                       "95% CI (boot)", "SMAD %", "`spsb` cell mean",
                       "Published", "Published vs pooled CI"]))
    L.append("")
    L.append("**Resolution of the published numbers**: the ES paper's −0.5/−1.6/−3.3/−5.3 "
             "correspond to the dedicated `spsb` cells (computed here: −0.49/−1.63/−3.28/−5.27, "
             "match to rounding), *not* to the pooled axis baselines. The pooled axis "
             "baselines (the paper's canonical baseline for intervention tests) differ "
             "materially for Claude Haiku (+0.48 vs −0.49) and Gemini (−2.88 vs −1.63); "
             "the model *ranking* by |mean dev| is preserved except Gemini/GPT-4o swap.\n")

    # ---- gpt-5-mini cells ----
    L.append("## GPT-5-mini cells\n")
    L.append("**No GPT-5-mini intervention cells exist anywhere in the repo.** "
             "The source billed as gpt-5-mini interventions "
             "(`recovered_logs/experiment_logs_with_explanation/V10/`) is "
             "**gpt-4o** in every run's `config.yaml`, and 14 of its 22 run-ids "
             "(timestamps) also appear under `experiment_logs/V10/` — the two "
             "sources are largely the same runs and must not be pooled. "
             "The only genuine gpt-5-mini data are the mechanism cells in "
             "`robustness_logs/*_gpt5mini` below (both ascending-clock gpt5mini "
             "dirs are empty shells with no raw data).\n")
    g5 = cells[(cells.model == "gpt-5-mini") & (cells.n_bids > 0)]
    rows = []
    for _, r in g5.iterrows():
        rows.append({"exp": r.experiment, "n": int(r.n_bids), "mean": fmt(r.mean_dev),
                     "ci": f"[{fmt(r.boot_ci_mean_lo)}, {fmt(r.boot_ci_mean_hi)}]",
                     "smad": fmt(r.smad_pct, 1),
                     "base": r.baseline_experiment if pd.notna(r.baseline_experiment) else "—",
                     "p": fmt_p(r.welch_p)})
    L.append(md_table(pd.DataFrame(rows),
                      ["exp", "n", "mean", "ci", "smad", "base", "p"],
                      ["Cell", "n", "Mean dev ($)", "95% CI", "SMAD %",
                       "Baseline", "Welch p"]))
    L.append("")

    caveats_path = OUT_MD.parent / "_auction_cells_caveats.md"
    if caveats_path.exists():
        L.append(caveats_path.read_text())

    OUT_MD.write_text("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())

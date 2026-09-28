"""
model_comparison_main.py -- Human vs five LLMs: SMAD by auction format.

Derived from scripts/plots/appendix2_model.py (the reference implementation of
SMAD that produced the paper's appendix model-comparison table).  Changes:

  * adds the GPT-4o (temperature 0.5, experiment_logs/V10) baseline as a model;
  * concatenates ALL results CSVs under each robustness directory (the reference
    script read only the first file), skipping "merged" files when non-merged
    files exist and de-duplicating on (repetition_id, round, player_name);
  * correct display names (the "claude_sonnet" cells are claude-3-5-haiku, the
    "gemini" cells are gemini-2.0-flash, "llama" is Meta-Llama-3-8B-Instruct);
  * removes the significance-star machinery (no tests against the reconstructed
    human anchor); human uncertainty is the 95% Monte-Carlo calibration band
    from results/reconstruction_bands/bands.csv;
  * missing cells (attempted, but every repetition failed) rendered as n/a;
    n reported per cell; n<30 flagged.

SMAD conventions (identical to appendix2_model.py):
  IPV/APV formats : SMAD = 100 * mean|b - b*(v)| / 25,  b* = (N-1)/N v (FPSB, N=3)
                    or b* = v (SPSB IPV, SP-APV, AC, AC-B); clock formats use
                    non-winners only (the winner's recorded bid is the closing price).
  CV formats      : profit-based deviation of the winner from the theoretical
                    profit 2eps/(n+1) (first price) or eps/(n+1) (second price),
                    eps = winner signal - common value, normaliser 20.
  95% CI          : smad +/- 1.96 * se (pandas std, ddof=1, for IPV/APV;
                    numpy std, ddof=0, for CV -- as in the reference script).

Outputs (all paths relative to the repo root):
  results/analysis/model_smad_results.csv
  writeup/tables/model_comparison.tex     (tabular-only fragment, booktabs)
  writeup/figures/model_comparison_smad.png / .pdf

Run (from anywhere):
    python3 scripts/plots/model_comparison_main.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
V10_DIR = PROJECT_ROOT / "experiment_logs" / "V10"
ROBUST_DIR = PROJECT_ROOT / "robustness_logs"
HUMAN_CSV = PROJECT_ROOT / "plots" / "auction_human.csv"
BANDS_CSV = PROJECT_ROOT / "results" / "reconstruction_bands" / "bands.csv"

OUT_CSV = PROJECT_ROOT / "results" / "analysis" / "model_smad_results.csv"
OUT_TEX = PROJECT_ROOT / "writeup" / "tables" / "model_comparison.tex"
OUT_FIG = PROJECT_ROOT / "writeup" / "figures" / "model_comparison_smad.png"

# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #
sns.set_theme(style="whitegrid", context="paper")
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "grid.linestyle": "-",
    "grid.linewidth": 0.6,
    "hatch.linewidth": 0.6,
    "pdf.fonttype": 42,
})

# --------------------------------------------------------------------------- #
# Formats (display order = human SMAD descending, as in the paper's Figure 1)
# --------------------------------------------------------------------------- #
auction_configs = {
    "common_value_first": {
        "name": "First-Price CV",
        "type": "cv",
        "use_profit": True,
    },
    "fpsb_ipv": {
        "name": "First-Price IPV",
        "theoretical_bid": lambda v, N=3: (N - 1) / N * v,
        "type": "ipv",
    },
    "common_value_second": {
        "name": "Second-Price CV",
        "type": "cv",
        "use_profit": True,
    },
    "spsb_apv": {
        "name": "Second-Price APV",
        "theoretical_bid": lambda v, N=3: v,
        "type": "apv",
    },
    "ascending_clock_apv_closed": {
        "name": "AC-Closed (AC-B) APV",
        "theoretical_bid": lambda v, N=3: v,
        "type": "apv",
        "is_clock": True,
    },
    "spsb_ipv": {
        "name": "Second-Price IPV",
        "theoretical_bid": lambda v, N=3: v,
        "type": "ipv",
    },
    "ascending_clock_apv": {
        "name": "Ascending Clock APV",
        "theoretical_bid": lambda v, N=3: v,
        "type": "apv",
        "is_clock": True,
    },
}
FORMAT_ORDER = [c["name"] for c in auction_configs.values()]

# Reconstruction-band anchors (same mapping as scripts/plots/figure1_bands.py).
FORMAT_TO_ANCHOR = {
    "First-Price IPV": "FPSB IPV",
    "Second-Price IPV": "SPSB IPV",
    "Second-Price APV": "SP-APV",
    "Ascending Clock APV": "AC",
    "AC-Closed (AC-B) APV": "AC-B",
    # CV formats: no reconstruction band (profit-based metric).
}

# --------------------------------------------------------------------------- #
# Models (bar order within a group).  Colours validated as an adjacent-pair
# categorical palette (dataviz validator, light surface): human blue and
# GPT-4o orange match the paper's Figure 1.
# --------------------------------------------------------------------------- #
model_configs = {
    "human": {
        "display_name": "Human",
        "color": "#2687B8",
        "source": "human",
    },
    "gpt4o": {
        "display_name": "GPT-4o",
        "color": "#F18F01",
        "source": "v10",
        "model_id": "gpt-4o",
    },
    "claude_sonnet": {
        "display_name": "Claude 3.5 Haiku",
        "color": "#2FA37A",
        "source": "robustness",
        "model_id": "claude-3-5-haiku-20241022",
    },
    "gemini": {
        "display_name": "Gemini 2.0 Flash",
        "color": "#5B4BA8",
        "source": "robustness",
        "model_id": "gemini-2.0-flash",
    },
    "gpt5mini": {
        "display_name": "GPT-5-mini",
        "color": "#D1709C",
        "source": "robustness",
        "model_id": "gpt-5-mini",
    },
    "llama": {
        "display_name": "Llama-3-8B",
        "color": "#3D7F1F",
        "source": "robustness",
        "model_id": "meta-llama/Meta-Llama-3-8B-Instruct",
    },
}
MODEL_ORDER = list(model_configs.keys())
LLM_KEYS = [k for k in MODEL_ORDER if k != "human"]
SMALL_N = 30  # cells with n < SMALL_N are flagged (dagger / hatch)
# GPT-5-mini's two ascending-clock cells (author's description, 2026-09-23): the model states the
# dominant strategy outright and does not complete the tick-by-tick clock procedure in any run,
# so no bids are recorded. Rendered as DS with a double dagger; excluded from every statistic;
# the results CSV keeps NaN for these cells.
ASSUMED_TRUTHFUL = {("gpt5mini", "Ascending Clock APV"), ("gpt5mini", "AC-Closed (AC-B) APV")}

# Published GPT-4o SMADs (plots/human_llm_comparison_summary.csv); asserted to 2 dp.
GPT4O_EXPECTED = {
    "First-Price IPV": 27.55,
    "Second-Price IPV": 8.69,
    "Second-Price APV": 10.73,
    "Ascending Clock APV": 0.81,
    "AC-Closed (AC-B) APV": 0.47,
    "First-Price CV": 59.99,
    "Second-Price CV": 40.60,
}
# Reference values from the existing appendix table (checked, tolerance 0.05).
REFERENCE_EXPECTED = {
    ("claude_sonnet", "First-Price IPV"): 24.09,
    ("claude_sonnet", "Second-Price IPV"): 9.72,
    ("claude_sonnet", "Second-Price APV"): 9.58,
    ("claude_sonnet", "Ascending Clock APV"): 5.74,
    ("claude_sonnet", "First-Price CV"): 54.07,
    ("claude_sonnet", "Second-Price CV"): 27.19,
    ("gemini", "First-Price IPV"): 27.05,
    ("gemini", "Second-Price IPV"): 3.01,
    ("gemini", "Second-Price APV"): 8.02,
    ("gemini", "AC-Closed (AC-B) APV"): 1.26,
    ("gemini", "First-Price CV"): 59.50,
    ("gemini", "Second-Price CV"): 30.89,
    ("gpt5mini", "First-Price IPV"): 0.08,
    ("gpt5mini", "Second-Price IPV"): 0.20,
    ("gpt5mini", "Second-Price APV"): 1.36,
    ("gpt5mini", "First-Price CV"): 30.22,
    ("gpt5mini", "Second-Price CV"): 14.80,
    ("llama", "First-Price IPV"): 38.16,
    ("llama", "Second-Price IPV"): 54.89,
    ("llama", "Second-Price APV"): 53.08,
    ("llama", "Ascending Clock APV"): 104.1,
    ("llama", "AC-Closed (AC-B) APV"): 67.0,
    ("llama", "First-Price CV"): 53.68,
    ("llama", "Second-Price CV"): 32.27,
}
REFERENCE_N = {
    ("claude_sonnet", "Ascending Clock APV"): 46,
    ("claude_sonnet", "AC-Closed (AC-B) APV"): 2,
    ("gemini", "Ascending Clock APV"): 2,
    ("gemini", "AC-Closed (AC-B) APV"): 46,
    ("llama", "Ascending Clock APV"): 8,
    ("llama", "AC-Closed (AC-B) APV"): 2,
}

ANOMALIES = []  # collected data anomalies, printed at the end


def note_anomaly(msg):
    ANOMALIES.append(msg)
    print(f"    [anomaly] {msg}")


# --------------------------------------------------------------------------- #
# SMAD computation (verbatim logic from appendix2_model.py)
# --------------------------------------------------------------------------- #
def calculate_cv_deviation_from_json(json_files, auction_type="first_price"):
    """
    Calculate CV auction deviation using theoretical profit benchmarks from JSON files.

    For First-Price CV: pi* ~ 2 eps/(n+1);  Second-Price CV: pi* ~ eps/(n+1),
    eps_i = signal_i - common_value.
    """
    if not json_files:
        return None

    all_deviations = []
    n_agents = 3  # number of players

    for json_file in json_files:
        with open(json_file, "r") as f:
            data = json.load(f)

        for round_key, round_data in data.items():
            if not round_key.startswith("round_"):
                continue

            signals = round_data["value"]
            common_value = round_data["common"]
            profits = round_data["profit"]
            winner_name = round_data["history"]["winner"]["winner"]

            bidding_history = round_data["history"]["bidding history"]
            winner_idx = None
            for idx, bid_info in enumerate(bidding_history):
                if bid_info["agent"] == winner_name:
                    winner_idx = idx
                    break
            if winner_idx is None:
                continue

            winner_signal = signals[winner_idx]
            epsilon = winner_signal - common_value

            if auction_type == "first_price":
                theoretical_profit = (2 * epsilon) / (n_agents + 1)
            else:
                theoretical_profit = epsilon / (n_agents + 1)

            actual_profit = profits[winner_idx]
            all_deviations.append(abs(actual_profit - theoretical_profit))

    if not all_deviations:
        return None

    deviations_array = np.array(all_deviations)
    mad = deviations_array.mean()
    scaling_factor = 20
    smad = 100 * mad / scaling_factor
    se_mad = deviations_array.std() / np.sqrt(len(deviations_array))
    se_smad = 100 * se_mad / scaling_factor
    return {
        "smad": smad,
        "se": se_smad,
        "ci_lower": smad - 1.96 * se_smad,
        "ci_upper": smad + 1.96 * se_smad,
        "n_observations": len(all_deviations),
    }


def calculate_deviation(df, config):
    """Scaled Mean Absolute Deviation for IPV/APV formats (bid-based)."""
    if config.get("use_profit", False):
        raise ValueError("CV auctions should use calculate_cv_deviation_from_json")

    df = df.copy()
    df["theoretical_bid"] = df["player_value"].apply(config["theoretical_bid"])
    df["deviation"] = np.abs(df["bid"] - df["theoretical_bid"])

    mad = df["deviation"].mean()
    scaling_factor = 25
    smad = 100 * mad / scaling_factor

    n = len(df)
    se_mad = df["deviation"].std() / np.sqrt(n)
    se_smad = 100 * se_mad / scaling_factor
    return {
        "smad": smad,
        "se": se_smad,
        "ci_lower": smad - 1.96 * se_smad,
        "ci_upper": smad + 1.96 * se_smad,
        "n_observations": n,
    }


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def _select_result_csvs(directory):
    """All **/results/*_results.csv under `directory`; if both merged and
    non-merged files exist, keep only the non-merged ones (avoid double count)."""
    files = sorted(directory.glob("**/results/*_results.csv"))
    non_merged = [f for f in files if "merged" not in f.name]
    if non_merged:
        return non_merged
    return files


def _concat_and_dedupe(files, label):
    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["_source_file"] = str(f.relative_to(PROJECT_ROOT))
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    key = [c for c in ("repetition_id", "round", "player_name") if c in df.columns]
    if key:
        n_dup = int(df.duplicated(subset=key).sum())
        if n_dup:
            note_anomaly(f"{label}: {n_dup} duplicate (repetition_id, round, player_name) rows "
                         f"across {len(files)} files -- dropped")
            df = df.drop_duplicates(subset=key).reset_index(drop=True)
    return df


def load_model_bids(auction_key, model_key):
    """Bid-level DataFrame for an IPV/APV cell, or None if the cell was not run."""
    cfg = model_configs[model_key]
    if cfg["source"] == "v10":
        auction_dir = V10_DIR / auction_key
        if auction_configs[auction_key].get("is_clock", False):
            merged = auction_dir / f"{auction_key}_merged_results.csv"
            files = [merged] if merged.exists() else []
        else:
            files = sorted(auction_dir.glob("run_*/results/*_results.csv"))
    else:
        auction_dir = ROBUST_DIR / f"{auction_key}_{model_key}"
        files = _select_result_csvs(auction_dir) if auction_dir.exists() else []

    if not files:
        return None

    label = f"{auction_key}/{model_key}"
    df = _concat_and_dedupe(files, label)

    # Sanity: model id column must match the expected id for this model key.
    if "model" in df.columns:
        ids = sorted(df["model"].dropna().unique().tolist())
        if ids != [cfg["model_id"]]:
            note_anomaly(f"{label}: unexpected model ids {ids} (expected {cfg['model_id']})")
    # Sanity: file names that do not carry this model's suffix (mis-labelled files).
    if cfg["source"] == "robustness":
        for f in files:
            if model_key not in f.name:
                note_anomaly(f"{label}: file {f.name} lacks '{model_key}' in its name "
                             f"(model column = {sorted(pd.read_csv(f)['model'].unique().tolist())}); included")
    return df


def compute_cell(auction_key, model_key):
    """Return SMAD stats dict for a (format, model) cell, or None if not run."""
    cfg = model_configs[model_key]
    acfg = auction_configs[auction_key]

    if acfg.get("use_profit", False):
        if cfg["source"] == "v10":
            auction_dir = V10_DIR / auction_key
        else:
            auction_dir = ROBUST_DIR / f"{auction_key}_{model_key}"
        if not auction_dir.exists():
            return None
        json_files = sorted(auction_dir.glob("**/raw_data/result_*.json"))
        auction_type = "first_price" if "first" in auction_key else "second_price"
        return calculate_cv_deviation_from_json(json_files, auction_type)

    df = load_model_bids(auction_key, model_key)
    if df is None or df.empty:
        return None
    if acfg.get("is_clock", False):
        df = df[~df["is_winner"].astype(bool)].copy()
        if df.empty:
            return None
    return calculate_deviation(df, acfg)


def parse_ci_string(ci_str):
    if pd.isna(ci_str) or "no CI" in str(ci_str):
        return None, None
    m = re.search(r"\[([0-9.]+),\s*([0-9.]+)\]", str(ci_str))
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def load_human_data():
    """Human anchors from plots/auction_human.csv with 95% MC calibration
    bands from results/reconstruction_bands/bands.csv (NaN where no band)."""
    df = pd.read_csv(HUMAN_CSV)
    bands = pd.read_csv(BANDS_CSV).set_index("anchor")

    format_mapping = {
        "First-Price IPV": "First-Price IPV",
        "Second-Price IPV": "Second-Price IPV",
        "AC-B (Breitmoser2022)": "AC-Closed (AC-B) APV",
        "SPSB (Li 2017)": "Second-Price APV",
        "Ascending Clock (Li 2017)": "Ascending Clock APV",
        "First-Price Common Value": "First-Price CV",
        "Second-Price Common Value": "Second-Price CV",
    }

    rows = []
    for _, row in df.iterrows():
        if pd.isna(row["Auction"]):
            continue
        name = format_mapping.get(row["Auction"].strip())
        if name is None:
            continue
        smad = float(row["SMAD"])
        anchor = FORMAT_TO_ANCHOR.get(name)
        if anchor is not None and anchor in bands.index:
            lo = float(bands.loc[anchor, "lo95"])
            hi = float(bands.loc[anchor, "hi95"])
        else:
            lo, hi = np.nan, np.nan
        rows.append(dict(auction=name, model_key="human", display_name="Human",
                         smad=smad, ci_lower=lo, ci_upper=hi, se=np.nan, n=0))
    out = pd.DataFrame(rows)
    missing = set(FORMAT_ORDER) - set(out["auction"])
    if missing:
        raise RuntimeError(f"Human anchors missing for {sorted(missing)}")
    return out


def process_all_models():
    print("=" * 78)
    print("Loading human anchors")
    human = load_human_data()
    print(human[["auction", "smad", "ci_lower", "ci_upper"]].to_string(index=False))

    rows = human.to_dict("records")
    for auction_key, acfg in auction_configs.items():
        print("\n" + "=" * 78)
        print(f"{acfg['name']}  ({auction_key})")
        for model_key in LLM_KEYS:
            cfg = model_configs[model_key]
            stats = compute_cell(auction_key, model_key)
            if stats is None:
                print(f"  {cfg['display_name']:<18s} n/a  not available")
                rows.append(dict(auction=acfg["name"], model_key=model_key,
                                 display_name=cfg["display_name"], smad=np.nan,
                                 ci_lower=np.nan, ci_upper=np.nan, se=np.nan, n=0))
                continue
            print(f"  {cfg['display_name']:<18s} SMAD {stats['smad']:7.2f}  "
                  f"[{stats['ci_lower']:.2f}, {stats['ci_upper']:.2f}]  n={stats['n_observations']}")
            rows.append(dict(auction=acfg["name"], model_key=model_key,
                             display_name=cfg["display_name"], smad=stats["smad"],
                             ci_lower=stats["ci_lower"], ci_upper=stats["ci_upper"],
                             se=stats["se"], n=int(stats["n_observations"])))

    res = pd.DataFrame(rows, columns=["auction", "model_key", "display_name", "smad",
                                      "ci_lower", "ci_upper", "se", "n"])
    # stable ordering: format order x model order
    res["_a"] = res["auction"].map({a: i for i, a in enumerate(FORMAT_ORDER)})
    res["_m"] = res["model_key"].map({m: i for i, m in enumerate(MODEL_ORDER)})
    res = res.sort_values(["_a", "_m"]).drop(columns=["_a", "_m"]).reset_index(drop=True)
    return res


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def run_checks(res):
    print("\n" + "=" * 78)
    print("GPT-4o assertions (published SMADs, 2 dp)")
    g = res[res["model_key"] == "gpt4o"].set_index("auction")
    for fmt, exp in GPT4O_EXPECTED.items():
        got = g.loc[fmt, "smad"]
        ok = round(float(got), 2) == exp
        print(f"  {fmt:<22s} computed {got:8.4f}  expected {exp:6.2f}  {'OK' if ok else 'MISMATCH'}")
        assert ok, f"GPT-4o {fmt}: computed {got:.4f} != published {exp:.2f}"
    print("  all GPT-4o assertions passed")

    print("\nReference-table cross-check (|diff| > 0.05 listed)")
    diffs = []
    idx = res.set_index(["model_key", "auction"])
    for (mk, fmt), exp in REFERENCE_EXPECTED.items():
        got = idx.loc[(mk, fmt), "smad"]
        if pd.isna(got) or abs(float(got) - exp) > 0.05:
            diffs.append((mk, fmt, got, exp))
    for (mk, fmt), n_exp in REFERENCE_N.items():
        n_got = int(idx.loc[(mk, fmt), "n"])
        if n_got != n_exp:
            diffs.append((mk, fmt, f"n={n_got}", f"n={n_exp}"))
    if diffs:
        for d in diffs:
            print(f"  DIFF {d[0]:<14s} {d[1]:<22s} got {d[2]}  expected {d[3]}")
    else:
        print("  none -- all reference cells reproduced within 0.05 (and n as expected)")
    return diffs


# --------------------------------------------------------------------------- #
# LaTeX fragment
# --------------------------------------------------------------------------- #
def fmt_human_cell(row):
    if pd.notna(row["ci_lower"]) and pd.notna(row["ci_upper"]):
        return f"{row['smad']:.2f} [{row['ci_lower']:.2f}, {row['ci_upper']:.2f}]"
    return f"{row['smad']:.2f}$^{{\\ast}}$"


def fmt_model_cell(row, mk=None, fmt=None):
    if pd.isna(row["smad"]):
        if (mk, fmt) in ASSUMED_TRUTHFUL:
            return "DS$^{\\ddagger}$"
        return "n/a"
    s = f"{row['smad']:.2f} {{\\scriptsize ({int(row['n'])})}}"
    if int(row["n"]) < SMALL_N:
        s += "$^{\\dagger}$"
    return s


def generate_latex_table(res):
    idx = res.set_index(["auction", "model_key"])
    header = ["Format", "Human"] + [model_configs[k]["display_name"] for k in LLM_KEYS]
    lines = []
    lines.append("\\begin{tabular}{l" + "c" * (len(header) - 1) + "}")
    lines.append("\\toprule")
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\midrule")
    for fmt in FORMAT_ORDER:
        cells = [fmt, fmt_human_cell(idx.loc[(fmt, "human")])]
        for mk in LLM_KEYS:
            cells.append(fmt_model_cell(idx.loc[(fmt, mk)], mk, fmt))
        lines.append(" & ".join(cells) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Figure
# --------------------------------------------------------------------------- #
def create_comparison_plot(res):
    idx = res.set_index(["auction", "model_key"])
    n_fmt = len(FORMAT_ORDER)
    n_mod = len(MODEL_ORDER)
    bar_h = 0.13
    group_gap = 1.0

    fig, ax = plt.subplots(figsize=(10, 8.2))

    x_max = float(np.nanmax(res["ci_upper"].fillna(res["smad"])))
    label_pad = 0.012 * x_max

    star_used = False
    small_used = False
    missing_used = False
    for i, fmt in enumerate(FORMAT_ORDER):
        y0 = i * group_gap
        for j, mk in enumerate(MODEL_ORDER):
            cfg = model_configs[mk]
            row = idx.loc[(fmt, mk)]
            y = y0 + (j - (n_mod - 1) / 2) * bar_h
            label = cfg["display_name"] if i == 0 else None

            if pd.isna(row["smad"]):
                assumed = (mk, fmt) in ASSUMED_TRUTHFUL
                missing_used = True
                ax.text(label_pad, y, "states dominant strategy; no bids recorded" if assumed else "not available",
                        va="center", ha="left", fontsize=7.5, style="italic", color="#666666")
                if label:  # keep legend entry
                    ax.barh(y, 0, bar_h, color=cfg["color"], label=label)
                continue

            small = (mk != "human") and (int(row["n"]) < SMALL_N)
            ax.barh(y, row["smad"], bar_h * 0.92, color=cfg["color"], label=label,
                    edgecolor="white" if small else "none", linewidth=0.5,
                    hatch="////" if small else None, zorder=2)

            has_ci = pd.notna(row["ci_lower"]) and pd.notna(row["ci_upper"])
            if has_ci:
                xerr = [[row["smad"] - row["ci_lower"]], [row["ci_upper"] - row["smad"]]]
                if mk == "human":
                    ax.errorbar(row["smad"], y, xerr=xerr, fmt="none", ecolor="black",
                                elinewidth=1.3, capsize=3, capthick=1.3, zorder=3)
                else:
                    ax.errorbar(row["smad"], y, xerr=xerr, fmt="none", ecolor="#333333",
                                elinewidth=0.9, capsize=2, capthick=0.9, zorder=3)
            elif mk == "human":
                ax.plot(row["smad"] + label_pad, y, marker="*", color="black",
                        markersize=7, linestyle="none", zorder=4)
                star_used = True

            if small:
                small_used = True
                x_txt = (row["ci_upper"] if has_ci else row["smad"]) + label_pad
                ax.text(x_txt, y, f"n={int(row['n'])}", va="center", ha="left",
                        fontsize=7.5, color="#333333")

    ax.set_yticks(np.arange(n_fmt) * group_gap)
    ax.set_yticklabels(FORMAT_ORDER)
    ax.invert_yaxis()  # first format (highest human SMAD) at the top
    ax.set_ylabel("")
    ax.set_xlabel("Scaled mean absolute deviation from equilibrium, SMAD (%)")
    ax.set_xlim(0, x_max * 1.08)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    ax.axvline(0, color="#888888", linewidth=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # thin separators between format groups
    for i in range(1, n_fmt):
        ax.axhline((i - 0.5) * group_gap, color="#E5E5E5", linewidth=0.6, zorder=1)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.07),
              ncol=6, frameon=False, columnspacing=1.2, handlelength=1.4)

    notes = ["Human whiskers: 95% Monte-Carlo reconstruction band; model whiskers: 95% CI."]
    if star_used:
        notes.append("$\\bigstar$ no reconstruction band (CV, profit-based SMAD).")
    if small_used:
        notes.append("Hatched: n < 30 (n shown).")
    if missing_used:
        notes.append("DS: GPT-5-mini states the dominant strategy outright and does not complete the clock procedure; no bids recorded.")
    fig.text(0.5, 0.005, "  ".join(notes), ha="center", va="bottom", fontsize=8,
             color="#444444")

    fig.tight_layout(rect=(0, 0.04, 1, 1))
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_FIG.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {OUT_FIG}")
    print(f"Saved: {OUT_FIG.with_suffix('.pdf')}")


# --------------------------------------------------------------------------- #
def main():
    res = process_all_models()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")

    diffs = run_checks(res)

    tex = generate_latex_table(res)
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(tex)
    print(f"Saved: {OUT_TEX}")
    print("\n" + tex)

    create_comparison_plot(res)

    print("\n" + "=" * 78)
    print("RESULTS")
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(res.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    print("\nData anomalies:" if ANOMALIES else "\nData anomalies: none")
    for a in ANOMALIES:
        print(f"  - {a}")
    return res, diffs


if __name__ == "__main__":
    main()

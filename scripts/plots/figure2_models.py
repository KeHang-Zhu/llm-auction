#!/usr/bin/env python3
"""
Deliverable A3: per-model bid-direction shares (Figure 2 extended to all models).

For every (format x source) cell we classify each bid relative to the
equilibrium bid b*(v):

    within band  iff  |b - b*(v)| <= 0.02 * b*(v)      (dropped)
    under        iff  b <  b*(v)                        (among the remainder)
    over         iff  b >  b*(v)                        (among the remainder)

and report the under/over split of the *deviating* bids together with the
within-band share of *all* bids and n (all bids).  This is exactly the rule
behind the published Figure 2 numbers (GPT-4o: FPSB 14.1/85.9, SPSB 81.3/18.7,
SP-APV 92.4/7.6, AC 50/50 with 71.7% within); the script asserts that it
reproduces them.

Equilibria (LLM runs use N=3 bidders):
    FPSB IPV                       b* = (N-1)/N * v = (2/3) v
    SPSB IPV, SP-APV, AC, AC-B     b* = v
Clock formats use non-winners only (the winner's "bid" is the closing price).

Human benchmarks -- provenance rule:
  * Truthful-benchmark formats (SPSB IPV, SP-APV, AC, AC-B): the source-reported
    frequencies in plots/auction_human.csv (Underbid / Equalbid / Overbid, percent
    of all bids relative to value = the benchmark).  Equalbid is treated as the
    within-band share; the remainder is split into under/over.  No n (reported).
  * FPSB IPV: the source reports direction relative to value, not to the RNNE, so
    we use the Kagel-Levin 1993 moment-matched synthetic bids
    (results/v12_interventions/moment_matching/, n_bidders == 5) relative to
    b* = 0.8 v.
  The KL93 SPSB synthetic file is degenerate (every bid > 1.08 v), which is why the
  synthetic reconstructions are NOT used for the truthful formats.

Outputs (paths relative to the repo root):
    results/analysis/direction_shares_models.csv
    writeup/tables/direction_shares.tex          (tabular-only fragment)
    writeup/figures/figure2_models_direction.{png,pdf}
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.transforms as mtransforms  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

# =============================================================================
# CONFIGURATION
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]
V10_DIR = ROOT / "experiment_logs" / "V10"
ROBUSTNESS_DIR = ROOT / "robustness_logs"
MOMENT_DIR = ROOT / "results" / "v12_interventions" / "moment_matching"
HUMAN_REPORTED_CSV = ROOT / "plots" / "auction_human.csv"
CELLS_CSV = ROOT / "results" / "analysis" / "cell_crosschecks.csv"

OUT_CSV = ROOT / "results" / "analysis" / "direction_shares_models.csv"
OUT_TEX = ROOT / "writeup" / "tables" / "direction_shares.tex"
OUT_FIG_STEM = ROOT / "writeup" / "figures" / "figure2_models_direction"

BAND = 0.02          # +/- 2% of b* counts as "within band"
THIN_N = 30          # cells with fewer bids are flagged
N_LLM_BIDDERS = 3    # all LLM runs use N=3
HUMAN_MIN_VALUE = 0.1  # same guard as analysis/plot_human_llm_no_equal_bid.py
HUMAN_SRC_REPORTED = "reported (source)"
HUMAN_SRC_RECON = "reconstruction vs RNNE"
# rows of plots/auction_human.csv used for the truthful-benchmark formats
HUMAN_REPORTED_ROWS = {
    "SPSB IPV": "Second-Price IPV",
    "SP-APV": "SPSB (Li 2017)",
    "AC": "Ascending Clock (Li 2017)",
    "AC-B": "AC-B (Breitmoser2022)",
}

# (dir key, display label, equilibrium bid/value ratio for the LLM runs, is clock format)
FORMATS = [
    ("fpsb_ipv", "FPSB IPV", (N_LLM_BIDDERS - 1) / N_LLM_BIDDERS, False),
    ("spsb_ipv", "SPSB IPV", 1.0, False),
    ("spsb_apv", "SP-APV", 1.0, False),
    ("ascending_clock_apv", "AC", 1.0, True),
    ("ascending_clock_apv_closed", "AC-B", 1.0, True),
]
FORMAT_LABELS = [f[1] for f in FORMATS]
TRUTHFUL_FORMATS = [f[1] for f in FORMATS if f[2] == 1.0]

SOURCES = ["Human", "GPT-4o", "Claude 3.5 Haiku", "Gemini 2.0 Flash", "GPT-5-mini", "Llama-3-8B"]
LLM_SOURCES = SOURCES[1:]

# robustness_logs/<key>_<suffix>/ ; GPT-4o lives in experiment_logs/V10/<key>/
ROBUSTNESS_SUFFIX = {
    "Claude 3.5 Haiku": "claude_sonnet",   # CSV model id is claude-3-5-haiku-20241022
    "Gemini 2.0 Flash": "gemini",
    "GPT-5-mini": "gpt5mini",
    "Llama-3-8B": "llama",
}
# (family, experiment-name builder) used to locate the cross-check row in auction_cells.csv
CELLS_LOOKUP = {
    "GPT-4o": ("v10", lambda key: key),
    "Claude 3.5 Haiku": ("robustness", lambda key: f"{key}_claude_sonnet"),
    "Gemini 2.0 Flash": ("robustness", lambda key: f"{key}_gemini"),
    "GPT-5-mini": ("robustness", lambda key: f"{key}_gpt5mini"),
    "Llama-3-8B": ("robustness", lambda key: f"{key}_llama"),
}

# Published numbers that must be reproduced (percent; tolerance 1 pp).
EXPECTED_GPT4O = {
    "FPSB IPV": {"over_share": 85.9, "under_share": 14.1},
    "SPSB IPV": {"under_share": 81.3, "over_share": 18.7},
    "SP-APV": {"under_share": 92.4, "over_share": 7.6},
    "AC": {"under_share": 50.0, "over_share": 50.0, "within_share": 71.7},
}
ASSERT_TOL_PP = 1.0

# Human numbers currently quoted in the paper text (reported, not asserted).
EXPECTED_HUMAN = {
    "FPSB IPV": {"over_share": 56.5, "under_share": 43.5, "within_share": 10.4},
    "SPSB IPV": {"over_share": 96.0, "under_share": 4.0},
    "SP-APV": {"over_share": 64.7, "under_share": 35.3},
    "AC": {"under_share": 49.2, "over_share": 50.8, "within_share": 26.8},
}

COLORS = {"under": "#E74C3C", "over": "#3498DB"}   # as in the paper's Figure 2


# =============================================================================
# DIRECTION RULE
# =============================================================================

def direction_shares(value, bid, ratio: float) -> dict:
    """Apply the +/-2% band rule. Shares are returned in percent."""
    v = np.asarray(value, dtype=float)
    b = np.asarray(bid, dtype=float)
    ok = np.isfinite(v) & np.isfinite(b)
    v, b = v[ok], b[ok]
    b_star = ratio * v
    within = np.abs(b - b_star) <= BAND * b_star
    dev = ~within
    n_all = int(len(b))
    n_dev = int(dev.sum())
    under = int((b[dev] < b_star[dev]).sum())
    over = int((b[dev] > b_star[dev]).sum())
    return {
        "n_all": n_all,
        "within_share": 100.0 * within.mean() if n_all else np.nan,
        "n_deviating": n_dev,
        "under_share": 100.0 * under / n_dev if n_dev else np.nan,
        "over_share": 100.0 * over / n_dev if n_dev else np.nan,
    }


def empty_cell() -> dict:
    return {"n_all": 0, "within_share": np.nan, "n_deviating": 0,
            "under_share": np.nan, "over_share": np.nan}


# =============================================================================
# LLM DATA
# =============================================================================

def load_results_dir(directory: Path) -> tuple[pd.DataFrame, dict]:
    """Concatenate every *_results.csv under `directory`.

    Non-merged files are preferred; merged files are used only when no
    non-merged file exists.  Rows are de-duplicated on
    (repetition_id, round, player_name) and NaN bids are dropped.
    """
    meta = {"n_files": 0, "n_rows_raw": 0, "n_dupes_dropped": 0, "n_nan_bid": 0, "files": []}
    if not directory.exists():
        return pd.DataFrame(), meta
    files = sorted(directory.rglob("*_results.csv"))
    non_merged = [f for f in files if "merged" not in f.name]
    files = non_merged if non_merged else files
    if not files:
        return pd.DataFrame(), meta
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    meta["n_files"] = len(files)
    meta["files"] = [str(f.relative_to(ROOT)) for f in files]
    meta["n_rows_raw"] = len(df)
    before = len(df)
    df = df.drop_duplicates(subset=["repetition_id", "round", "player_name"])
    meta["n_dupes_dropped"] = before - len(df)
    df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
    df["player_value"] = pd.to_numeric(df["player_value"], errors="coerce")
    meta["n_nan_bid"] = int(df["bid"].isna().sum())
    df = df.dropna(subset=["bid", "player_value"])
    return df.reset_index(drop=True), meta


def is_winner_mask(df: pd.DataFrame) -> pd.Series:
    return df["is_winner"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])


def llm_dir(source: str, key: str) -> Path:
    if source == "GPT-4o":
        return V10_DIR / key
    return ROBUSTNESS_DIR / f"{key}_{ROBUSTNESS_SUFFIX[source]}"


def compute_llm_cells() -> tuple[list[dict], list[dict], list[str]]:
    """Return (primary rows, all-bids rows for clock cross-check, log lines)."""
    rows, allbid_rows, log = [], [], []
    for key, label, ratio, is_clock in FORMATS:
        for source in LLM_SOURCES:
            d = llm_dir(source, key)
            df, meta = load_results_dir(d)
            if df.empty:
                cell = empty_cell()
                rows.append({"format": label, "source": source, **cell, "missing": True})
                log.append(f"  [{label:8s}] {source:17s} MISSING (no results CSV under {d.relative_to(ROOT)})")
                continue
            models = sorted(df["model"].astype(str).unique())
            if is_clock:
                sub = df.loc[~is_winner_mask(df)]
                allbid_rows.append({"format": label, "source": source,
                                    **direction_shares(df["player_value"], df["bid"], ratio)})
            else:
                sub = df
            cell = direction_shares(sub["player_value"], sub["bid"], ratio)
            rows.append({"format": label, "source": source, **cell, "missing": False})
            note = ""
            if meta["n_dupes_dropped"]:
                note += f" dupes_dropped={meta['n_dupes_dropped']}"
            if meta["n_nan_bid"]:
                note += f" nan_bids_dropped={meta['n_nan_bid']}"
            misnamed = [f for f in meta["files"] if ROBUSTNESS_SUFFIX.get(source, "gpt-4o") not in Path(f).name
                        and source != "GPT-4o"]
            if misnamed:
                note += f" MISNAMED_CSV={[Path(f).name for f in misnamed]}"
            log.append(
                f"  [{label:8s}] {source:17s} files={meta['n_files']} rows={meta['n_rows_raw']}"
                f" used={cell['n_all']}{' (non-winners)' if is_clock else ''}"
                f" within={cell['within_share']:.1f}% under/over={cell['under_share']:.1f}/{cell['over_share']:.1f}"
                f" model={models}{note}"
            )
    return rows, allbid_rows, log


# =============================================================================
# HUMAN DATA (moment-matched synthetic reconstructions)
# =============================================================================

def _std_value_col(df: pd.DataFrame) -> pd.DataFrame:
    if "player_value" not in df.columns and "value" in df.columns:
        df = df.rename(columns={"value": "player_value"})
    return df[df["player_value"] > HUMAN_MIN_VALUE].copy()


def compute_human_cells() -> tuple[list[dict], list[str]]:
    rows, log = [], []

    # FPSB IPV: KL93 synthetic bids relative to the RNNE b* = 0.8 v (n_bidders == 5)
    kl = _std_value_col(pd.read_csv(MOMENT_DIR / "kagel_levin_1993_synthetic_bids.csv"))
    kl = kl[(kl["n_bidders"] == 5) & (kl["auction_type"] == "FPSB")]
    ratio = (5 - 1) / 5
    cell = direction_shares(kl["player_value"], kl["bid"], ratio)
    rows.append({"format": "FPSB IPV", "source": "Human", **cell, "missing": False,
                 "human_source": HUMAN_SRC_RECON})
    log.append(f"  [FPSB IPV] Kagel-Levin 1993 FPSB n_bidders=5 b*={ratio:.2f}v (synthetic) -> {fmt_cell(cell)}")

    # Truthful-benchmark formats: source-reported Underbid / Equalbid / Overbid (percent of all bids)
    rep = pd.read_csv(HUMAN_REPORTED_CSV)
    rep.columns = [c.strip() for c in rep.columns]
    rep = rep.set_index(rep["Auction"].astype(str).str.strip())
    for label, row_name in HUMAN_REPORTED_ROWS.items():
        if row_name not in rep.index:
            raise KeyError(f"{row_name!r} not found in {HUMAN_REPORTED_CSV}; rows: {list(rep.index)}")
        r = rep.loc[row_name]
        under, equal, over = (float(r["Underbid"]), float(r["Equalbid"]), float(r["Overbid"]))
        dev = under + over
        cell = {"n_all": np.nan, "within_share": equal, "n_deviating": np.nan,
                "under_share": 100.0 * under / dev if dev else np.nan,
                "over_share": 100.0 * over / dev if dev else np.nan}
        rows.append({"format": label, "source": "Human", **cell, "missing": False,
                     "human_source": HUMAN_SRC_REPORTED})
        log.append(f"  [{label:8s}] reported ({row_name}): under/equal/over={under:g}/{equal:g}/{over:g}"
                   f" -> within={equal:.1f}% under/over={cell['under_share']:.1f}/{cell['over_share']:.1f}")
    return rows, log


def fmt_cell(c: dict) -> str:
    if not c["n_all"]:
        return "missing"
    return (f"n={c['n_all']} within={c['within_share']:.1f}% n_dev={c['n_deviating']} "
            f"under/over={c['under_share']:.1f}/{c['over_share']:.1f}")


# =============================================================================
# CHECKS
# =============================================================================

def check_expected(table: pd.DataFrame, expected: dict, source: str, hard: bool) -> list[str]:
    log, failures = [], []
    for label, exp in expected.items():
        row = table[(table["format"] == label) & (table["source"] == source)].iloc[0]
        for col, target in exp.items():
            got = row[col]
            diff = abs(got - target)
            ok = diff <= ASSERT_TOL_PP
            log.append(f"  {source:7s} {label:8s} {col:12s} expected {target:5.1f} got {got:5.1f} "
                       f"(diff {diff:4.1f} pp) {'OK' if ok else 'MISMATCH'}")
            if not ok:
                failures.append(f"{source} {label} {col}: expected {target}, got {got:.2f}")
    if hard and failures:
        raise AssertionError("Published GPT-4o numbers not reproduced:\n  " + "\n  ".join(failures))
    return log


def cross_check_cells(table: pd.DataFrame, allbid_rows: list[dict]) -> list[str]:
    """Compare within/under/over shares of ALL bids with results/merged_ranking/auction_cells.csv."""
    log = []
    if not CELLS_CSV.exists():
        return [f"  auction_cells.csv not found at {CELLS_CSV}"]
    cells = pd.read_csv(CELLS_CSV)
    allbid = pd.DataFrame(allbid_rows)
    key_of = {f[1]: f[0] for f in FORMATS}
    for label in TRUTHFUL_FORMATS:
        for source in LLM_SOURCES:
            family, exp_name = CELLS_LOOKUP[source]
            ref = cells[(cells["family"] == family) & (cells["experiment"] == exp_name(key_of[label]))]
            mine = table[(table["format"] == label) & (table["source"] == source)].iloc[0]
            if ref.empty or mine["missing"] or pd.isna(ref.iloc[0]["share_under"]):
                log.append(f"  [{label:8s}] {source:17s} no comparable row (missing on one side)")
                continue
            ref = ref.iloc[0]
            candidates = [("non-winners" if label in ("AC", "AC-B") else "all bids", mine)]
            if label in ("AC", "AC-B") and not allbid.empty:
                ab = allbid[(allbid["format"] == label) & (allbid["source"] == source)]
                if not ab.empty:
                    candidates.append(("all bids incl. winners", ab.iloc[0]))
            for tag, m in candidates:
                w = m["within_share"]
                u = m["under_share"] * (100 - w) / 100.0   # under share of ALL bids
                o = m["over_share"] * (100 - w) / 100.0
                du, do, dw = (u - 100 * ref["share_under"], o - 100 * ref["share_over"],
                              w - 100 * ref["share_within_2pct"])
                flag = "MISMATCH>2pp" if max(abs(du), abs(do), abs(dw)) > 2.0 else "ok"
                log.append(
                    f"  [{label:8s}] {source:17s} ({tag:22s}) n={int(m['n_all']):4d} vs cells n={int(ref['n_bids']):4d}"
                    f" | under {u:5.1f} vs {100*ref['share_under']:5.1f} | over {o:5.1f} vs {100*ref['share_over']:5.1f}"
                    f" | within {w:5.1f} vs {100*ref['share_within_2pct']:5.1f} -> {flag}"
                )
    return log


# =============================================================================
# OUTPUTS
# =============================================================================

def write_csv(table: pd.DataFrame) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out = table[["format", "source", "n_all", "within_share", "n_deviating",
                 "under_share", "over_share", "thin", "missing", "human_source"]].copy()
    for c in ["within_share", "under_share", "over_share"]:
        out[c] = out[c].round(2)
    for c in ["n_all", "n_deviating"]:
        out[c] = out[c].astype("Int64")   # nullable: reported human cells have no n
    out["human_source"] = out["human_source"].fillna("")
    out.to_csv(OUT_CSV, index=False)


def tex_escape(s: str) -> str:
    return s.replace("%", r"\%")


def write_tex(table: pd.DataFrame) -> None:
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    idx = table.set_index(["format", "source"])
    lines = [
        "% Auto-generated by scripts/plots/figure2_models.py -- do not edit by hand.",
        "% Cell = under / over (% of bids outside the +/-2% equilibrium band); second line = within-band share of all bids and n (all bids).",
        "% Clock formats (AC, AC-B): non-winners only.",
        "% Human provenance rule: SPSB IPV, SP-APV, AC, AC-B use the source-reported Underbid/Equalbid/Overbid frequencies",
        "%   (plots/auction_human.csv; percent of all bids relative to value = the benchmark); Equalbid = within share, remainder split under/over;",
        "%   no n is reported. FPSB IPV uses the Kagel-Levin (1993) n=5 moment-matched synthetic bids relative to the RNNE b*=0.8v,",
        "%   because the source reports direction relative to value, not to equilibrium.",
        r"% $^{\dagger}$ = n < 30; DS$^{\ddagger}$ = GPT-5-mini states the dominant strategy outright and does not complete the clock procedure (author's description); no bids recorded; define in the caption.",
        r"\begin{tabular}{@{}l*{6}{c}@{}}",
        r"\toprule",
        "Format & " + " & ".join(SOURCES) + r" \\",
        r"\midrule",
    ]
    for label in FORMAT_LABELS:
        main, small = [label], [""]
        for source in SOURCES:
            r = idx.loc[(label, source)]
            if r["missing"]:
                # no usable runs: assumption, flagged with a double dagger (defined in the paper caption)
                main.append(r"DS$^{\ddagger}$")
                small.append("")
                continue
            dagger = r"$^{\dagger}$" if r["thin"] else ""
            if source == "Human":   # reported / reconstructed: no n line
                within_txt = r"{\scriptsize within " + f"{r['within_share']:.0f}" + r"\%"
            else:
                within_txt = r"{\scriptsize within " + f"{r['within_share']:.0f}" + r"\%, n=" + f"{int(r['n_all'])}"
            if r["n_deviating"] == 0:
                # every bid inside the +/-2% band: direction split undefined
                main.append(r"n/a" + dagger)
                small.append(within_txt + r" (no deviating bids)}")
                continue
            under = int(round(r["under_share"]))
            over = 100 - under
            main.append(f"{under} / {over}{dagger}")
            small.append(within_txt + "}")
        lines.append(" & ".join(main) + r" \\")
        lines.append(" & ".join(small) + r" \\")
        if label != FORMAT_LABELS[-1]:
            lines.append(r"\addlinespace")
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    OUT_TEX.write_text("\n".join(lines))


def make_figure(table: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams["hatch.linewidth"] = 1.2

    bar_h = 0.74
    group_gap = 1.1
    y_positions, tick_labels, group_centers, separators = {}, [], [], []
    y = 0.0
    for gi, label in enumerate(FORMAT_LABELS):
        ys = []
        for source in SOURCES:
            y_positions[(label, source)] = y
            tick_labels.append((y, source))
            ys.append(y)
            y -= 1.0
        group_centers.append((np.mean(ys), label))
        if gi < len(FORMAT_LABELS) - 1:
            separators.append(y + 0.5 - (group_gap - 1.0) / 2.0)
        y -= (group_gap - 1.0)

    fig_h = 0.34 * len(tick_labels) + 2.6
    fig, ax = plt.subplots(figsize=(10.5, fig_h))
    idx = table.set_index(["format", "source"])

    for (label, source), yy in y_positions.items():
        r = idx.loc[(label, source)]
        if r["missing"]:
            # no usable runs: rendered as an assumption and explicitly labelled as not observed
            ax.barh(yy, 100, height=bar_h, facecolor="none", edgecolor="#bbbbbb",
                    linewidth=1.0, linestyle="--", zorder=3)
            ax.text(50, yy, "states the dominant strategy; no bids recorded", ha="center",
                    va="center", fontsize=8.5, color="#555555", style="italic", zorder=4)
            continue
        thin = bool(r["thin"])
        if r["n_deviating"] == 0:
            # all bids within the band: nothing to split; draw an empty outline + note
            ax.barh(yy, 100, height=bar_h, facecolor="none", edgecolor="#bbbbbb",
                    linewidth=1.0, linestyle="--", zorder=3)
            ax.text(50, yy, f"no deviating bids (all within ±2%)", ha="center", va="center",
                    fontsize=8.5, color="#555555", style="italic", zorder=4)
            ax.text(101.5, yy, "within 100%", ha="left", va="center", fontsize=8,
                    color="#555555", clip_on=False)
            continue
        u, o = r["under_share"], r["over_share"]
        hatch = "//" if thin else None
        ax.barh(yy, u, height=bar_h, color=COLORS["under"], edgecolor="white",
                linewidth=1.2, hatch=hatch, alpha=0.9, zorder=3)
        ax.barh(yy, o, left=u, height=bar_h, color=COLORS["over"], edgecolor="white",
                linewidth=1.2, hatch=hatch, alpha=0.9, zorder=3)
        # on hatched bars give the label a solid backing so hatch lines do not cross it
        box_u = dict(facecolor=COLORS["under"], edgecolor="none", pad=1.5) if thin else None
        box_o = dict(facecolor=COLORS["over"], edgecolor="none", pad=1.5) if thin else None
        if u >= 10:
            ax.text(u / 2, yy, f"{u:.0f}%", ha="center", va="center", fontsize=8.5,
                    fontweight="bold", color="white", zorder=4, bbox=box_u)
        if o >= 10:
            ax.text(u + o / 2, yy, f"{o:.0f}%", ha="center", va="center", fontsize=8.5,
                    fontweight="bold", color="white", zorder=4, bbox=box_o)
        if source == "Human":
            tag = "reported" if r["human_source"] == HUMAN_SRC_REPORTED else "reconstruction vs RNNE"
            note = f"{tag}, within {r['within_share']:.0f}%"
        else:
            note = f"within {r['within_share']:.0f}%"   # thin cells are signalled by hatching only
        ax.text(101.5, yy, note, ha="left", va="center", fontsize=8,
                color="#555555", clip_on=False)

    # separators between format groups and group labels on the left
    trans = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    for s in separators:
        ax.axhline(s, color="#cfcfcf", linewidth=0.8, zorder=1)
    for yc, label in group_centers:
        ax.text(-0.215, yc, label, transform=trans, ha="right", va="center",
                fontsize=11, fontweight="bold", color="#222222")

    ax.axvline(50, color="#9a9a9a", linestyle="--", linewidth=0.9, zorder=2)
    ax.set_xlim(0, 100)
    ax.set_ylim(min(yp for yp in y_positions.values()) - 0.7, 0.7)
    ax.set_yticks([t[0] for t in tick_labels])
    ax.set_yticklabels([t[1] for t in tick_labels], fontsize=9)
    for tl in ax.get_yticklabels():
        if tl.get_text() == "Human":
            tl.set_fontweight("bold")
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels([f"{t}%" for t in [0, 25, 50, 75, 100]])
    ax.set_xlabel("Share of deviating bids (bids within ±2% of equilibrium removed)")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#e6e6e6", zorder=0)
    sns.despine(ax=ax, left=True)
    ax.set_title("Direction of deviation from equilibrium, by format and bidder",
                 fontsize=13, fontweight="bold", loc="left", pad=14)

    legend_handles = [
        Patch(facecolor=COLORS["under"], alpha=0.9, label="Underbid (b < b*)"),
        Patch(facecolor=COLORS["over"], alpha=0.9, label="Overbid (b > b*)"),
        Patch(facecolor="#bbbbbb", edgecolor="white", hatch="//", label=f"n < {THIN_N} (thin cell)"),
    ]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.045),
              ncol=3, frameon=False, fontsize=9)

    fig.subplots_adjust(left=0.27, right=0.80, top=0.94, bottom=0.10)
    OUT_FIG_STEM.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG_STEM.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(OUT_FIG_STEM.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    print("=" * 78)
    print("A3: per-model bid-direction shares (+/-2% band rule)")
    print("=" * 78)

    print("\nHuman cells (reported frequencies; FPSB IPV = KL93 synthetic vs RNNE):")
    human_rows, human_log = compute_human_cells()
    print("\n".join(human_log))

    print("\nLLM cells:")
    llm_rows, allbid_rows, llm_log = compute_llm_cells()
    print("\n".join(llm_log))

    table = pd.DataFrame(human_rows + llm_rows)
    table["thin"] = table["n_all"] < THIN_N
    table["missing"] = table["missing"].astype(bool)
    order_f = {f: i for i, f in enumerate(FORMAT_LABELS)}
    order_s = {s: i for i, s in enumerate(SOURCES)}
    table = table.sort_values(["format", "source"],
                              key=lambda c: c.map(order_f if c.name == "format" else order_s)
                              ).reset_index(drop=True)

    print("\nGPT-4o reproduction check (published Figure 2 numbers, tolerance 1 pp):")
    print("\n".join(check_expected(table, EXPECTED_GPT4O, "GPT-4o", hard=True)))

    print("\nHuman numbers vs current paper text (reported, not asserted):")
    print("\n".join(check_expected(table, EXPECTED_HUMAN, "Human", hard=False)))

    print("\nCross-check vs results/merged_ranking/auction_cells.csv (shares of ALL bids, truthful formats):")
    print("\n".join(cross_check_cells(table, allbid_rows)))

    thin = table[table["thin"] & ~table["missing"]]
    print("\nThin cells (n < 30):")
    for _, r in thin.iterrows():
        print(f"  {r['format']:8s} {r['source']:17s} n={int(r['n_all'])}")
    miss = table[table["missing"]]
    print("Missing cells:")
    for _, r in miss.iterrows():
        print(f"  {r['format']:8s} {r['source']:17s}")

    write_csv(table)
    write_tex(table)
    make_figure(table)

    pd.set_option("display.width", 200)
    print("\nFull table (percent):")
    print(table.to_string(index=False, float_format=lambda x: f"{x:6.2f}"))
    print(f"\nWrote {OUT_CSV.relative_to(ROOT)}")
    print(f"Wrote {OUT_TEX.relative_to(ROOT)}")
    print(f"Wrote {OUT_FIG_STEM.relative_to(ROOT)}.png / .pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())

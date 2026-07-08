#!/usr/bin/env python3
"""figure3_intervention_comparison.png -- menu vs clock-framing, four models.

Upgrades the old missing GPT-4o-only figure (writeup fig:intervention /
fig:ranking-framing): deviation (b - v, $) distributions for the two
presentation-only descriptions of the same SPSB mechanism,

    row 1  Menu restatement (B1)      -- intervention_menu
    row 2  Clock framing   (B3)       -- intervention_proxy_breitmoser

across GPT-4o, Claude 3.5 Haiku, Gemini 2.0 Flash and Gemma 3 27B, each
against the same model's POOLED axis baseline (gray overlay) --
axis1_contingent_baseline + axis2_forward_baseline + axis3_beliefs_baseline,
the paper's canonical baseline for cells without an axis-specific baseline.

Data: bid-level.
  Baselines from Engineering_simplicity .../results/all_experiments_combined_*.csv
  Treatments parsed from the raw ES intervention logs
  (experiment_logs/<model>/<exp>/result_*.json) with the SAME parsing logic as
  analysis/build_auction_cells.py (imported, not duplicated).
Stats annotated per panel (mean deviation, Mann-Whitney p vs baseline) are
recomputed here from the bid-level data and match auction_cells.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from build_auction_cells import (_rows_from_raw_json, ES, ES_CSV,  # noqa: E402
                                 ES_MODEL_DIRS)

OUT = ROOT / "writeup" / "figures" / "figure3_intervention_comparison.png"

BASELINES = ["axis1_contingent_baseline", "axis2_forward_baseline",
             "axis3_beliefs_baseline"]
TREATMENTS = [("intervention_menu", "Menu restatement (B1)"),
              ("intervention_proxy_breitmoser", "Clock framing (B3)")]
MODEL_ORDER = ["gpt-4o", "claude-3-5-haiku-20241022", "gemini-2.0-flash",
               "google/gemma-3-27b-it"]
MODEL_SHORT = {"gpt-4o": "GPT-4o",
               "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
               "gemini-2.0-flash": "Gemini 2.0 Flash",
               "google/gemma-3-27b-it": "Gemma 3 27B"}
# same model colors as ranking_forest.py (validated palette)
MODEL_COLOR = {"gpt-4o": "#2a78d6", "claude-3-5-haiku-20241022": "#1baf7a",
               "gemini-2.0-flash": "#008300",
               "google/gemma-3-27b-it": "#4a3aa7"}
INK, INK2, MUTED, GRID, AXIS = ("#0b0b0b", "#52514e", "#898781", "#e1e0d9",
                                "#c3c2b7")
BASE_GRAY = "#b9b7b0"

XLIM = (-26, 16)          # $ deviations; share outside annotated per panel
BINS = np.arange(-26, 16.5, 1.0)


def load_baselines():
    df = pd.read_csv(ES_CSV)
    df = df[df["experiment"].isin(BASELINES)].copy()
    df["dev"] = pd.to_numeric(df["bid"], errors="coerce") - \
        pd.to_numeric(df["player_value"], errors="coerce")
    df = df.dropna(subset=["dev"])
    return {m: g["dev"].values for m, g in df.groupby("model")}


def load_treatment(mdir: str, model: str, exp: str) -> np.ndarray:
    exp_dir = ES / "experiment_logs" / mdir / exp
    cfg = yaml.safe_load(open(ES / "configs_auction" / f"interventions_{mdir}"
                              / f"{exp}.yaml"))
    frames = [
        _rows_from_raw_json(j, cfg, "es_v12_raw", "es_v12", model, exp)
        for j in sorted(exp_dir.glob("result_*.json"))]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    dev = (df["bid"] - df["player_value"]).dropna().values
    return dev


def main():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8.5, "axes.linewidth": 0.8,
    })
    base = load_baselines()
    fig, axes = plt.subplots(2, 4, figsize=(11.5, 5.6), sharex=True,
                             sharey="row")
    fig.subplots_adjust(left=0.075, right=0.985, top=0.855, bottom=0.155,
                        hspace=0.18, wspace=0.08)

    for i, (exp, row_label) in enumerate(TREATMENTS):
        for j, model in enumerate(MODEL_ORDER):
            ax = axes[i, j]
            mdir = [k for k, v in ES_MODEL_DIRS.items() if v == model][0]
            dev_t = load_treatment(mdir, model, exp)
            dev_b = base[model]
            c = MODEL_COLOR[model]

            ax.hist(dev_b, bins=BINS, density=True, color=BASE_GRAY,
                    alpha=0.45, zorder=2)
            ax.hist(dev_t, bins=BINS, density=True, histtype="step",
                    color=c, lw=1.6, zorder=4)
            ax.hist(dev_t, bins=BINS, density=True, color=c, alpha=0.10,
                    zorder=3)
            ax.axvline(0, color=AXIS, lw=0.8, zorder=1)
            ax.axvline(np.mean(dev_b), color=INK2, lw=1.0, ls=(0, (4, 2.5)),
                       zorder=5)
            ax.axvline(np.mean(dev_t), color=c, lw=1.2, ls=(0, (4, 2.5)),
                       zorder=5)

            mw = stats.mannwhitneyu(dev_t, dev_b).pvalue
            we = stats.ttest_ind(dev_t, dev_b, equal_var=False).pvalue

            def pfmt(p):
                return f"{p:.3f}" if p >= 1e-3 else f"{p:.0e}"
            ax.text(0.035, 0.955,
                    f"$\\mu$: {np.mean(dev_b):+.1f} $\\to$ "
                    f"{np.mean(dev_t):+.1f}\nMW $p$ = {pfmt(mw)} $\\cdot$ "
                    f"Welch $p$ = {pfmt(we)}",
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=7.0, color=INK2, zorder=8,
                    bbox=dict(fc="white", alpha=0.65, ec="none", pad=1.5))
            out_t = np.mean((dev_t < XLIM[0]) | (dev_t > XLIM[1]))
            out_b = np.mean((dev_b < XLIM[0]) | (dev_b > XLIM[1]))
            if max(out_t, out_b) >= 0.001:
                ax.text(0.035, 0.62,
                        f"{100 * max(out_t, out_b):.1f}% off-scale",
                        transform=ax.transAxes, fontsize=6.2, color=MUTED)

            ax.set_xlim(*XLIM)
            for s in ["top", "right"]:
                ax.spines[s].set_visible(False)
            for s in ["left", "bottom"]:
                ax.spines[s].set_color(AXIS)
            ax.tick_params(colors=INK2, labelsize=7.5)
            ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
            ax.set_axisbelow(True)
            if i == 0:
                ax.set_title(MODEL_SHORT[model], fontsize=9.5, color=INK,
                             pad=8)
            if j == 0:
                ax.set_ylabel("density", fontsize=8, color=INK2)
                ax.text(-0.24, 0.5, row_label, transform=ax.transAxes,
                        rotation=90, ha="center", va="center", fontsize=9.5,
                        color=INK, weight="semibold")
            if i == 1:
                ax.set_xlabel("deviation from truthful bid,  $b-v$  (\\$)",
                              fontsize=8, color=INK2)

    fig.text(0.075, 0.965,
             "Presentation-only descriptions of the same second-price auction",
             fontsize=12, color=INK, weight="semibold")
    fig.text(0.075, 0.935,
             "Menu restatement leaves bidding unchanged or worse; clock framing "
             "compresses deviations toward truthful play in every model. "
             "Gray: the same model's pooled axis baseline.",
             fontsize=8.2, color=INK2)
    handles = [
        Patch(facecolor=BASE_GRAY, alpha=0.45,
              label="SPSB baseline (pooled axis baselines, same model)"),
        Patch(facecolor="#dddbd4", edgecolor=INK2,
              label="intervention (outline + wash; color = model, as in the ranking figure)"),
        Line2D([], [], color=INK2, lw=1.1, ls=(0, (4, 2.5)),
               label="dashed: means"),
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.07, 0.0),
               ncol=3, frameon=False, fontsize=7.4, labelcolor=INK2)
    fig.text(0.985, 0.012,
             "raw ES V12 intervention logs; deviations in $ "
             "(SMAD normalizer 24.5)",
             fontsize=6.4, color=MUTED, ha="right")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=220)
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

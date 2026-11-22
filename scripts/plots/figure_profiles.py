"""
figure_profiles.py -- small-multiple figures: one panel per model, the human
anchor repeated in every panel as the grey reference.

  smad3      : SMAD by format, three non-reasoning large models   (main text)
  smad5      : SMAD by format, all five models                    (appendix)
  direction  : under / within-band / over shares by format        (main text)
  temperature: SMAD by format, GPT-4o at three temperatures        (appendix)

SMAD panels: rows are auction formats in two blocks (private value, ordered by
human SMAD; common value).  Grey diamond = reconstructed human anchor with its
95% reconstruction band, blue dot = model with its 95% CI.  A thin line joins
each series across the private-value block, so a model that keeps the human
ordering shows a profile that falls from top to bottom like the human one.
The x-axis is on a square-root scale so that the clock formats (SMAD near 1%)
and the common-value formats (SMAD near 50%) are readable in the same panel.

Direction panels: one panel per format, one row per bidder; each bar splits all
bids into below benchmark / within +-2% / above benchmark.

Inputs :  results/analysis/model_smad_results[_one_llm].csv
          results/analysis/direction_shares_models[_one_llm].csv
          results/analysis/difficulty_concordance_models[_one_llm].csv
          results/reconstruction_bands/bands.csv
Outputs:  results/figures/smad_profiles_gp[_one_llm].png/.pdf
          results/figures/smad_profiles_all[_one_llm].png/.pdf
          results/figures/direction_grid[_one_llm].png/.pdf
          results/figures/smad_profiles_temperature[_one_llm].png/.pdf

Run:  CLOCK_DESIGN=one_llm python scripts/plots/figure_profiles.py [smad3|smad5|direction]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import clock_data as cd  # noqa: E402

AN = ROOT / "results" / "analysis"
FIG = ROOT / "results" / "figures"

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
HUMAN, MODEL = "#52514e", "#2a78d6"
UNDER, WITHIN, OVER = "#e34948", "#e4e3de", "#2a78d6"

# (label in results CSV, label on the figure, anchor in bands.csv)
PRIVATE = [
    ("First-Price IPV", "First-price IPV", "FPSB IPV"),
    ("Second-Price APV", "Second-price APV", "SP-APV"),
    ("AC-Closed (AC-B) APV", "Closed clock APV", "AC-B"),
    ("Second-Price IPV", "Second-price IPV", "SPSB IPV"),
    ("Ascending Clock APV", "Open clock APV", "AC"),
]
COMMON = [
    ("First-Price CV", "First-price CV", None),
    ("Second-Price CV", "Second-price CV", None),
]
MODELS = [
    ("gpt4o", "GPT-4o"), ("claude_sonnet", "Claude 3.5 Haiku"),
    ("gemini", "Gemini 2.0 Flash"), ("gpt5mini", "GPT-5-mini"), ("llama", "Llama-3-8B"),
]
GROUP = {"gpt4o": "Non-reasoning large models", "gpt5mini": "Reasoning model",
         "llama": "Small model"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8, "xtick.color": MUTED, "ytick.color": INK,
    "xtick.labelsize": 7.5, "ytick.labelsize": 8.5, "pdf.fonttype": 42,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def save(fig, name):
    out = FIG / cd.out_name(name)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def taus():
    t = pd.read_csv(AN / cd.out_name("difficulty_concordance_models.csv"))
    t = t[t["format_set"] == "all_usable"].set_index("model")
    return t["tau_point"].to_dict()


def model_panels(model_keys):
    """(results indexed by (auction, key), panels) for the cross-model figures."""
    res = pd.read_csv(AN / cd.out_name("model_smad_results.csv")).set_index(["auction", "model_key"])
    tau = taus()
    names = dict(MODELS)
    panels = [(mk, names[mk], tau[names[mk]], GROUP.get(mk) if len(model_keys) > 3 else None)
              for mk in model_keys]
    return res, panels


def temperature_panels():
    """GPT-4o at T = 0.1, 0.5, 1.0 (Appendix temperature figure)."""
    res = pd.read_csv(ROOT / "results" / "figures" / cd.out_name("appendix2_temperature_results.csv"))
    res = res.set_index(["auction", "model_key"])
    t = pd.read_csv(AN / cd.out_name("temperature_concordance.csv"))
    tau = t.groupby("temperature")["tau_all_usable"].first().to_dict()
    panels = [(k, f"GPT-4o, $T$ = {T}", tau[T], None)
              for k, T in (("gpt4o_temp01", 0.1), ("gpt4o", 0.5), ("gpt4o_temp10", 1.0))]
    return res, panels


def smad_figure(res, panels, name, width):
    bands = pd.read_csv(ROOT / "results" / "reconstruction_bands" / "bands.csv").set_index("anchor")
    # private-value rows follow the human ordering, hardest first
    priv = sorted(PRIVATE, key=lambda r: -res.loc[(r[0], "human"), "smad"])
    rows = priv + COMMON
    gap = 0.9
    ys = np.r_[np.arange(len(priv)), len(priv) + gap + np.arange(len(COMMON))]

    fig, axes = plt.subplots(1, len(panels), figsize=(width, 3.5), sharey=True)
    fwd, inv = (lambda v: np.sqrt(np.clip(v, 0, None))), (lambda v: np.square(v))
    ticks = [0, 1, 5, 15, 30, 50, 75]
    for ax, (mk, disp, tau_k, group) in zip(axes, panels):
        ax.set_xscale("function", functions=(fwd, inv))
        ax.set_xlim(0, 80)
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks])
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", length=2.5, color=AXIS)
        ax.axhline(len(priv) - 0.5 + gap / 2, color=AXIS, linewidth=0.8)

        hx = np.array([res.loc[(r[0], "human"), "smad"] for r in rows])
        mx = np.array([res.loc[(r[0], mk), "smad"] for r in rows])
        k = len(priv)
        ax.plot(hx[:k], ys[:k], color=HUMAN, linewidth=0.9, alpha=0.45, zorder=2)
        ax.plot(mx[:k], ys[:k], color=MODEL, linewidth=1.1, alpha=0.55, zorder=2)
        for i, r in enumerate(rows):
            if r[2] is not None:
                ax.plot([bands.loc[r[2], "lo95"], bands.loc[r[2], "hi95"]], [ys[i]] * 2,
                        color=HUMAN, linewidth=1.3, solid_capstyle="butt", zorder=3)
            row = res.loc[(r[0], mk)]
            ax.plot([max(row["ci_lower"], 0), row["ci_upper"]], [ys[i]] * 2,
                    color=MODEL, linewidth=1.3, solid_capstyle="butt", zorder=3)
        ax.scatter(hx, ys, marker="D", s=26, facecolor="white", edgecolor=HUMAN,
                   linewidth=1.3, zorder=4)
        ax.scatter(mx, ys, marker="o", s=30, facecolor=MODEL, edgecolor="white",
                   linewidth=0.8, zorder=5)
        ax.set_title(disp, loc="left", fontsize=9, fontweight="bold", color=INK, pad=14)
        ax.text(0, 1.015, rf"Kendall $\tau_b$ = {tau_k:.2f}".replace("-", "\u2212"), transform=ax.transAxes,
                fontsize=8, color=INK2, va="bottom")
        if group:
            ax.text(0, 1.17, group.upper(), transform=ax.transAxes, fontsize=6.8,
                    color=MUTED, fontweight="bold", va="bottom")
    ax0 = axes[0]
    ax0.set_yticks(ys)
    ax0.set_yticklabels([r[1] for r in rows])
    ax0.set_ylim(ys[-1] + 0.6, -0.6)
    tr = ax0.get_yaxis_transform()
    for y, lab in ((-0.62, "PRIVATE VALUE"), (len(priv) + gap - 0.62, "COMMON VALUE")):
        ax0.text(-0.02, y, lab, transform=tr, ha="right", va="bottom", fontsize=6.8,
                 color=MUTED, fontweight="bold")
    fig.supxlabel("SMAD from the theoretical benchmark (%, square-root scale)",
                  fontsize=8.5, color=INK2, y=-0.03)
    handles = [
        Line2D([], [], marker="D", color=HUMAN, markerfacecolor="white", markeredgewidth=1.3,
               markersize=5, linewidth=1.3, label="Human (reconstructed, 95% band)"),
        Line2D([], [], marker="o", color=MODEL, markeredgecolor="white", markersize=6,
               linewidth=1.3, label="LLM (95% CI)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, -0.14), handlelength=2.2, columnspacing=2.5)
    fig.subplots_adjust(wspace=0.12)
    save(fig, name)


def direction_figure():
    d = pd.read_csv(AN / cd.out_name("direction_shares_models.csv"))
    formats = [("FPSB IPV", "First-price IPV"), ("SPSB IPV", "Second-price IPV"),
               ("SP-APV", "Second-price APV"), ("AC-B", "Closed clock APV"),
               ("AC", "Open clock APV")]
    bidders = ["Human"] + [m[1] for m in MODELS]
    ys = np.r_[0, 1.35 + np.arange(len(MODELS))]
    fig, axes = plt.subplots(1, len(formats), figsize=(7.4, 2.5), sharey=True)
    for ax, (fk, flab) in zip(axes, formats):
        sub = d[d["format"] == fk].set_index("source")
        for y, b in zip(ys, bidders):
            r = sub.loc[b]
            w = float(r["within_share"])
            dev = 100.0 - w
            u = dev * float(r["under_share"]) / 100.0 if dev > 0 and pd.notna(r["under_share"]) else 0.0
            o = dev - u
            left = 0.0
            for val, col in ((u, UNDER), (w, WITHIN), (o, OVER)):
                if val > 0:
                    ax.barh(y, val, left=left, height=0.72, color=col, edgecolor="white",
                            linewidth=0.8, zorder=2)
                    if val >= 22:
                        ax.text(left + val / 2, y, f"{val:.0f}", ha="center", va="center",
                                fontsize=6.8, color=INK if col == WITHIN else "white", zorder=3)
                left += val
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 50, 100])
        for lab, ha in zip(ax.set_xticklabels(["0", "50", "100"]), ("left", "center", "right")):
            lab.set_ha(ha)
        ax.set_title(flab, loc="left", fontsize=7.6, fontweight="bold", color=INK, pad=5)
        for s in ("top", "right", "left", "bottom"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="both", length=0)
        ax.axhline((ys[0] + ys[1]) / 2, color=AXIS, linewidth=0.8)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(bidders)
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    axes[0].set_ylim(ys[-1] + 0.55, -0.55)
    handles = [Patch(color=UNDER, label="Below the benchmark"),
               Patch(color=WITHIN, label="Within ±2% of the benchmark"),
               Patch(color=OVER, label="Above the benchmark")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, -0.19), handlelength=1.2, columnspacing=2.2)
    fig.supxlabel("Share of bids (%)", fontsize=8.5, color=INK2, y=-0.06)
    fig.subplots_adjust(wspace=0.1)
    save(fig, "direction_grid.png")


if __name__ == "__main__":
    which = sys.argv[1:] or ["smad3", "smad5", "direction", "temperature"]
    if "smad3" in which:
        smad_figure(*model_panels(["gpt4o", "claude_sonnet", "gemini"]), "smad_profiles_gp.png", 6.6)
    if "smad5" in which:
        smad_figure(*model_panels([m[0] for m in MODELS]), "smad_profiles_all.png", 9.2)
    if "temperature" in which:
        smad_figure(*temperature_panels(), "smad_profiles_temperature.png", 6.6)
    if "direction" in which:
        direction_figure()

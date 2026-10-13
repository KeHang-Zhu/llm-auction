"""
figure1_bands_models.py -- The paper's Figure 1 (human vs GPT-4o SMAD by format,
with Monte-Carlo reconstruction bands on the human bars) redesigned as two panels:

  LEFT  : Human (blue; black whiskers = 95% MC calibration band; CV rows carry a
          star = no reconstruction band) vs GPT-4o (orange; 95% CI).
  RIGHT : the same seven formats for Claude 3.5 Haiku, Gemini 2.0 Flash,
          GPT-5-mini and Llama-3-8B (95% CIs), with GPT-4o drawn as a thin
          reference tick per row.  Cells with no usable repetitions (GPT-5-mini AC /
          AC-B) show a small "not available" note; cells with n < 30 are hatched and
          annotated with n.

Rows share the same order in both panels (human SMAD descending, as in Figure 1).

Second entry point (main_gp): the paper's Figure 1 as a SINGLE panel with the
human anchors and the three general-purpose, non-reasoning models only
(GPT-4o, Claude 3.5 Haiku, Gemini 2.0 Flash); GPT-5-mini and Llama stay in
Table 1 / the appendix figure.  Same row order, same whisker/star/hatch rules.

Inputs :  results/analysis/model_smad_results.csv   (scripts/plots/model_comparison_main.py)
          results/reconstruction_bands/bands.csv
Outputs:  writeup/figures/figure1_bands_models.png / .pdf   (two panels, all models)
          writeup/figures/figure1_bands_gp.png / .pdf       (single panel, GP models)

Band-whisker logic and FORMAT_TO_ANCHOR are reused from scripts/plots/figure1_bands.py.

Run (from anywhere):
    python3 scripts/plots/figure1_bands_models.py            # both figures
    python3 scripts/plots/figure1_bands_models.py two-panel  # figure1_bands_models only
    python3 scripts/plots/figure1_bands_models.py gp         # figure1_bands_gp only
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure1_bands import FORMAT_TO_ANCHOR  # noqa: E402  (same anchor mapping as Figure 1)
from model_comparison_main import model_configs, FORMAT_ORDER, SMALL_N  # noqa: E402

RESULTS_CSV = PROJECT_ROOT / "results" / "analysis" / "model_smad_results.csv"
BANDS_CSV = PROJECT_ROOT / "results" / "reconstruction_bands" / "bands.csv"
FIG_OUT = PROJECT_ROOT / "writeup" / "figures" / "figure1_bands_models.png"
FIG_OUT_GP = PROJECT_ROOT / "writeup" / "figures" / "figure1_bands_gp.png"

# figure1_bands.py applies the seaborn "talk" theme on import; reset to a
# paper-sized theme so the two-panel figure is readable at \linewidth.
sns.set_theme(style="whitegrid", context="paper")
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 10.5,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 8.5,
    "grid.linestyle": "-",
    "grid.linewidth": 0.6,
    "hatch.linewidth": 0.6,
    "pdf.fonttype": 42,
})

HUMAN_COLOR = model_configs["human"]["color"]
GPT4O_COLOR = model_configs["gpt4o"]["color"]
OTHER_MODELS = ["claude_sonnet", "gemini", "gpt5mini", "llama"]
# Single-panel Figure 1: human + general-purpose non-reasoning models (bar order).
GP_MODELS = ["human", "gpt4o", "claude_sonnet", "gemini"]


def load_inputs():
    res = pd.read_csv(RESULTS_CSV)
    bands = pd.read_csv(BANDS_CSV).set_index("anchor")
    missing = set(FORMAT_ORDER) - set(res["auction"])
    if missing:
        raise RuntimeError(f"results CSV lacks formats: {sorted(missing)}")
    return res, bands


def human_band(fmt, bands):
    """(lo95, hi95) from bands.csv via FORMAT_TO_ANCHOR, or (nan, nan)."""
    anchor = FORMAT_TO_ANCHOR.get(fmt)
    if anchor is not None and anchor in bands.index:
        return float(bands.loc[anchor, "lo95"]), float(bands.loc[anchor, "hi95"])
    return np.nan, np.nan


def draw_whisker(ax, x, y, lo, hi, color, lw, cap):
    """Same construction as figure1_bands.py: asymmetric xerr about the point."""
    xerr = [[x - lo], [hi - x]]
    ax.errorbar(x, y, xerr=xerr, fmt="none", ecolor=color, elinewidth=lw,
                capsize=cap, capthick=lw, zorder=3)


def style_axis(ax, x_max, n_rows, group_gap):
    ax.set_xlim(0, x_max)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    ax.axvline(0, color="#888888", linewidth=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for i in range(1, n_rows):
        ax.axhline((i - 0.5) * group_gap, color="#E5E5E5", linewidth=0.6, zorder=1)


def main():
    res, bands = load_inputs()
    idx = res.set_index(["auction", "model_key"])
    n_rows = len(FORMAT_ORDER)
    group_gap = 1.0
    ys = np.arange(n_rows) * group_gap

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(11, 6.2), sharey=True,
        gridspec_kw={"width_ratios": [1, 1.25]})

    # ------------------------------------------------------------------ LEFT
    bar_h = 0.34
    star_used = False
    left_vals = []
    for i, fmt in enumerate(FORMAT_ORDER):
        h = idx.loc[(fmt, "human")]
        g = idx.loc[(fmt, "gpt4o")]
        lo, hi = human_band(fmt, bands)
        y_h = ys[i] - bar_h / 2
        y_g = ys[i] + bar_h / 2

        axL.barh(y_h, h["smad"], bar_h * 0.92, color=HUMAN_COLOR,
                 label="Human" if i == 0 else None, zorder=2)
        if np.isfinite(lo) and np.isfinite(hi):
            draw_whisker(axL, h["smad"], y_h, lo, hi, "black", 1.4, 3.5)
            left_vals.append(hi)
        else:
            axL.plot(h["smad"] + 1.0, y_h, marker="*", color="black", markersize=8,
                     linestyle="none", zorder=4)
            star_used = True
            left_vals.append(h["smad"] + 2.0)

        axL.barh(y_g, g["smad"], bar_h * 0.92, color=GPT4O_COLOR,
                 label="GPT-4o" if i == 0 else None, zorder=2)
        draw_whisker(axL, g["smad"], y_g, g["ci_lower"], g["ci_upper"], "#333333", 1.0, 2.5)
        left_vals.append(g["ci_upper"])

    xL = max(left_vals) * 1.10
    style_axis(axL, xL, n_rows, group_gap)
    axL.set_yticks(ys)
    axL.set_yticklabels(FORMAT_ORDER)
    axL.invert_yaxis()
    axL.set_title("Human vs GPT-4o", loc="left", fontweight="bold")
    axL.set_xlabel("SMAD (%)")
    axL.legend(loc="lower right", frameon=True, framealpha=0.9, edgecolor="#DDDDDD")

    # ----------------------------------------------------------------- RIGHT
    n_mod = len(OTHER_MODELS)
    bar_h2 = 0.17
    small_used = False
    missing_used = False
    right_vals = []
    for i, fmt in enumerate(FORMAT_ORDER):
        g = idx.loc[(fmt, "gpt4o")]
        # GPT-4o reference tick spanning the group
        axR.vlines(g["smad"], ys[i] - 0.42, ys[i] + 0.42, color=GPT4O_COLOR,
                   linewidth=1.6, zorder=4, label="GPT-4o (reference)" if i == 0 else None)
        for j, mk in enumerate(OTHER_MODELS):
            cfg = model_configs[mk]
            row = idx.loc[(fmt, mk)]
            y = ys[i] + (j - (n_mod - 1) / 2) * bar_h2
            label = cfg["display_name"] if i == 0 else None
            if pd.isna(row["smad"]):
                missing_used = True
                axR.barh(y, 0, bar_h2, color=cfg["color"], label=label)  # legend only
                axR.text(max(2.0, g["smad"] + 1.5), y, "not available", va="center", ha="left",
                         fontsize=7.5, style="italic", color="#666666")
                continue
            small = int(row["n"]) < SMALL_N
            axR.barh(y, row["smad"], bar_h2 * 0.92, color=cfg["color"], label=label,
                     edgecolor="white" if small else "none", linewidth=0.5,
                     hatch="////" if small else None, zorder=2)
            draw_whisker(axR, row["smad"], y, row["ci_lower"], row["ci_upper"], "#333333", 0.9, 2)
            right_vals.append(row["ci_upper"])
            if small:
                small_used = True
                x_txt = max(row["ci_upper"], g["smad"]) + 1.5
                axR.text(x_txt, y, f"n={int(row['n'])}", va="center",
                         ha="left", fontsize=7.5, color="#333333")

    xR = max(right_vals) * 1.10
    style_axis(axR, xR, n_rows, group_gap)
    axR.set_title("Other LLMs", loc="left", fontweight="bold")
    axR.set_xlabel("SMAD (%)")
    axR.tick_params(axis="y", length=0)
    axR.legend(loc="upper right", frameon=True, framealpha=0.9, edgecolor="#DDDDDD")

    # --------------------------------------------------------------- footnote
    notes = ["Human whiskers: 95% Monte-Carlo reconstruction band; LLM whiskers: 95% CI."]
    if star_used:
        notes.append("$\\bigstar$ no reconstruction band (CV, profit-based SMAD).")
    if small_used:
        notes.append("Hatched: n < 30.")
    if missing_used:
        notes.append("“not available”: no usable repetitions.")
    fig.text(0.5, 0.005, "  ".join(notes), ha="center", va="bottom", fontsize=8,
             color="#444444")

    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.subplots_adjust(wspace=0.06)
    FIG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_OUT, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_OUT.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {FIG_OUT}")
    print(f"Saved: {FIG_OUT.with_suffix('.pdf')}")


def main_gp():
    """Single panel: Human vs GPT-4o, Claude 3.5 Haiku and Gemini 2.0 Flash.

    Human bars carry black 95% Monte-Carlo reconstruction-band whiskers (star on
    the CV rows = no band); LLM bars carry 95% CIs; cells with n < SMALL_N are
    hatched (no n annotation).  Row order = FORMAT_ORDER (human SMAD desc.).
    """
    res, bands = load_inputs()
    idx = res.set_index(["auction", "model_key"])
    n_rows = len(FORMAT_ORDER)
    n_mod = len(GP_MODELS)
    group_gap = 1.0
    bar_h = 0.20
    ys = np.arange(n_rows) * group_gap

    fig, ax = plt.subplots(figsize=(9, 6.4))
    star_used = False
    small_used = False
    x_vals = []
    for i, fmt in enumerate(FORMAT_ORDER):
        for j, mk in enumerate(GP_MODELS):
            cfg = model_configs[mk]
            row = idx.loc[(fmt, mk)]
            if pd.isna(row["smad"]):
                raise RuntimeError(f"{fmt} / {mk}: cell missing in {RESULTS_CSV}")
            y = ys[i] + (j - (n_mod - 1) / 2) * bar_h
            label = cfg["display_name"] if i == 0 else None
            small = (mk != "human") and int(row["n"]) < SMALL_N

            ax.barh(y, row["smad"], bar_h * 0.92, color=cfg["color"], label=label,
                    edgecolor="white" if small else "none", linewidth=0.5,
                    hatch="////" if small else None, zorder=2)

            if mk == "human":
                lo, hi = human_band(fmt, bands)
                if np.isfinite(lo) and np.isfinite(hi):
                    draw_whisker(ax, row["smad"], y, lo, hi, "black", 1.4, 3.5)
                    x_vals.append(hi)
                else:
                    ax.plot(row["smad"] + 1.0, y, marker="*", color="black", markersize=8,
                            linestyle="none", zorder=4)
                    star_used = True
                    x_vals.append(row["smad"] + 2.0)
                continue

            draw_whisker(ax, row["smad"], y, row["ci_lower"], row["ci_upper"], "#333333", 1.0, 2.5)
            x_vals.append(row["ci_upper"])
            if small:
                small_used = True  # hatched only; no n annotation in the GP figure

    x_max = max(x_vals) * 1.10
    style_axis(ax, x_max, n_rows, group_gap)
    ax.set_yticks(ys)
    ax.set_yticklabels(FORMAT_ORDER)
    ax.invert_yaxis()
    ax.set_xlabel("Scaled mean absolute deviation from equilibrium, SMAD (%)")
    ax.legend(loc="lower right", frameon=True, framealpha=0.9, edgecolor="#DDDDDD")

    notes = ["Human whiskers: 95% Monte-Carlo reconstruction band; LLM whiskers: 95% CI."]
    if star_used:
        notes.append("$\\bigstar$ no reconstruction band (CV, profit-based SMAD).")
    if small_used:
        notes.append("Hatched: n < 30.")
    fig.text(0.5, 0.005, "  ".join(notes), ha="center", va="bottom", fontsize=8,
             color="#444444")

    fig.tight_layout(rect=(0, 0.035, 1, 1))
    FIG_OUT_GP.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_OUT_GP, dpi=300, bbox_inches="tight")
    fig.savefig(FIG_OUT_GP.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {FIG_OUT_GP}")
    print(f"Saved: {FIG_OUT_GP.with_suffix('.pdf')}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which not in ("all", "two-panel", "gp"):
        sys.exit(f"usage: {Path(__file__).name} [all|two-panel|gp]")
    if which in ("all", "two-panel"):
        main()
    if which in ("all", "gp"):
        main_gp()

#!/usr/bin/env python3
"""eBay-style environment, closing-rule treatments only (T1 vs T2).

The paper's eBay section is reduced to the two closing-rule treatments
(hidden-reserve treatments T3/T4 dropped):

  T1  ebay_proxy          hard close  (standard eBay proxy bidding, no reserve)
  T2  ebay_closing_rule   soft close  (auction-extension rule, no reserve)

Data: experiment_logs/V10/<dir>/result_*.csv, one file
per auction run (GPT-4o bidders, n = 3, IPV Unif[0,99], 10 scheduled periods
stored as period_id 0..9; soft-close runs extend past period_id 9).
Columns: period_id, turn_id, current_price, reserve_price, agent_selected,
action, bid, max_bids (str dict), highest_bidder.

Periods are reported 1-indexed throughout (period 1 .. 10 scheduled, 11+ are
soft-close extensions), matching the paper's T = 10 and the prompt's "day k".

Three timing definitions are in circulation for the "final winning bid":
  winner_last  (paper text; PLOTTED)  last period in which the eventual
               winner changes her maximum bid
  price_final  (existing Figs/ebay_*.png, notebooks/ebay_analysis.ipynb)
               first period in which current_price reaches its final value
  any_last     (notebooks/eBay_dynamics.ipynb hard-coded lists)
               last period in which any bidder places a bid
All three are computed and written to the summary CSV so the text can be
matched to whichever definition it quotes.

Outputs
  writeup/figures/ebay_cdf_closing_only.png / .pdf
  writeup/figures/ebay_hist_closing_only.png / .pdf   (two-panel histogram, T1 | T2)
  results/analysis/ebay_closing_rule_summary.csv
"""

import ast
import glob
import os

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(REPO, "experiment_logs/V10")
FIGDIR = os.path.join(REPO, "writeup/figures")
OUTDIR = os.path.join(REPO, "results/analysis")

TREATMENTS = {
    "T1": dict(dir="ebay_proxy", close="hard", label="T1 hard close (standard proxy bidding)"),
    "T2": dict(dir="ebay_closing_rule", close="soft", label="T2 soft close (auction extension)"),
}
SCHEDULED_PERIODS = 10  # period_id 0..9 -> periods 1..10

DEFINITIONS = {
    "winner_last": "last period the eventual winner raises her maximum bid (paper definition)",
    "price_final": "first period the price reaches its final value (existing figure PNGs)",
    "any_last": "last period any bidder places a bid (eBay_dynamics notebook)",
}
PLOT_DEF = "winner_last"

# --- style: same as scripts/plots/regenerate_ebay_figures.py (dataviz palette) ---
C_BLUE = "#2a78d6"   # T1 / hard close
C_AQUA = "#1baf7a"   # T2 / soft close
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#ffffff"
COLORS = {"T1": C_BLUE, "T2": C_AQUA}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11, "text.color": INK,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 1.0, "grid.linestyle": "-",
    "axes.axisbelow": True, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "savefig.dpi": 200,
})


def style_axes(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)


def add_titles(fig, ax, title, subtitle_lines):
    x0 = ax.get_position().x0
    fig.text(x0, 0.955, title, fontsize=13, color=INK, va="top", ha="left")
    fig.text(x0, 0.895, "\n".join(subtitle_lines), fontsize=9.5, color=MUTED,
             va="top", ha="left", linespacing=1.35)


# ----------------------------------------------------------------------------
# Load runs and compute the three timing definitions (1-indexed periods)
# ----------------------------------------------------------------------------
def load_runs():
    records = []
    for t, meta in TREATMENTS.items():
        files = sorted(glob.glob(os.path.join(BASE, meta["dir"], "result_*.csv")))
        if not files:
            raise FileNotFoundError(f"no result_*.csv under {os.path.join(BASE, meta['dir'])}")
        for f in files:
            df = pd.read_csv(f).sort_values(["period_id", "turn_id"]).reset_index(drop=True)
            period = df["period_id"].astype(int) + 1  # 1-indexed
            winner = df["highest_bidder"].iloc[-1]
            final_price = float(df["current_price"].iloc[-1])
            maxes = [ast.literal_eval(s) for s in df["max_bids"]]

            # (a) last period the eventual winner changes her max bid
            prev, t_winner = 0.0, np.nan
            for i, mb in enumerate(maxes):
                cur = float(mb.get(winner, 0.0))
                if cur != prev:
                    t_winner = int(period.iloc[i])
                prev = cur
            # (b) first period the price reaches its final value
            t_price = int(period[df["current_price"] == final_price].min())
            # (c) last period any bidder places a bid
            t_any = int(period[df["action"] == "bid"].max())

            records.append(dict(
                treatment=t, close=meta["close"], file=os.path.basename(f),
                winner=winner, final_price=final_price,
                winner_last=int(t_winner), price_final=t_price, any_last=t_any,
                last_period=int(period.max()),
            ))
    return pd.DataFrame(records)


def summarize(g: pd.Series) -> dict:
    return dict(
        n=int(len(g)),
        share_period10=float((g == SCHEDULED_PERIODS).mean()),
        share_periods_9_10=float(g.isin([SCHEDULED_PERIODS - 1, SCHEDULED_PERIODS]).mean()),
        share_ge_period10=float((g >= SCHEDULED_PERIODS).mean()),
        share_extension=float((g > SCHEDULED_PERIODS).mean()),
        mean_period=float(g.mean()),
        median_period=float(g.median()),
        max_period=int(g.max()),
    )


def build_summary(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, desc in DEFINITIONS.items():
        a = runs.loc[runs["treatment"] == "T1", d]
        b = runs.loc[runs["treatment"] == "T2", d]
        mw = stats.mannwhitneyu(a, b, alternative="two-sided")
        ks = stats.ks_2samp(a, b)
        for t, g in (("T1", a), ("T2", b)):
            row = dict(definition=d, definition_desc=desc, treatment=t,
                       closing_rule=TREATMENTS[t]["close"],
                       max_period_observed=int(runs.loc[runs["treatment"] == t, "last_period"].max()))
            row.update(summarize(g))
            row.update(mw_U=float(mw.statistic), mw_p=float(mw.pvalue),
                       ks_D=float(ks.statistic), ks_p=float(ks.pvalue))
            rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Figure: CDF of the final-winning-bid period, T1 vs T2
# ----------------------------------------------------------------------------
def plot_cdf(runs: pd.DataFrame, summary: pd.DataFrame, path_stem: str):
    kmax = int(runs["last_period"].max())  # keep soft-close extension periods on the axis
    ks_grid = np.arange(1, kmax + 1)

    fig, ax = plt.subplots(figsize=(7.2, 4.7))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.81, bottom=0.13)

    for t, meta in TREATMENTS.items():
        g = runs.loc[runs["treatment"] == t, PLOT_DEF].values
        F = np.array([(g <= k).mean() for k in ks_grid])
        xs = np.concatenate([[0], ks_grid, [kmax + 1]])
        ys = np.concatenate([[0], F, [F[-1]]])
        ax.step(xs, ys, where="post", color=COLORS[t], linewidth=2,
                solid_joinstyle="round", solid_capstyle="round",
                label=f"{meta['label']}  (N = {len(g)})", zorder=3)
        ax.scatter(ks_grid, F, s=18, color=COLORS[t], edgecolors=SURFACE,
                   linewidths=1.0, zorder=4)

    # scheduled-close reference + selective direct labels at period 10
    ax.axvline(SCHEDULED_PERIODS, color=AXIS, linewidth=1.0, zorder=2)
    ax.text(SCHEDULED_PERIODS - 0.15, 0.03, "scheduled close (period 10)", rotation=90,
            va="bottom", ha="right", fontsize=8.5, color=MUTED)
    s = summary[summary["definition"] == PLOT_DEF].set_index("treatment")
    p1, p2 = s.loc["T1", "share_period10"], s.loc["T2", "share_period10"]
    # T1: the jump at period 10 (from F(9) to F(10))
    g1 = runs.loc[runs["treatment"] == "T1", PLOT_DEF].values
    f9 = (g1 <= SCHEDULED_PERIODS - 1).mean()
    ax.annotate(f"{p1*100:.0f}% of hard-close auctions\ndecided in period 10",
                xy=(SCHEDULED_PERIODS, (f9 + 1) / 2), xytext=(SCHEDULED_PERIODS + 0.35, 0.55),
                fontsize=9, color=INK2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=AXIS, lw=1.0))
    g2 = runs.loc[runs["treatment"] == "T2", PLOT_DEF].values
    ax.annotate(f"{p2*100:.0f}% under soft close",
                xy=(SCHEDULED_PERIODS, (g2 <= SCHEDULED_PERIODS).mean()),
                xytext=(SCHEDULED_PERIODS + 0.35, 0.86),
                fontsize=9, color=INK2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=AXIS, lw=1.0))

    ax.set_xlim(0.5, kmax + 0.6)
    ax.set_ylim(0, 1.02)
    ax.set_xticks(ks_grid)
    ax.set_xticklabels([str(k) if k <= SCHEDULED_PERIODS else f"{k}\n(ext.)" for k in ks_grid],
                       fontsize=9.5)
    ax.set_xlabel("Period of the final winning bid (10 scheduled periods; 11+ are soft-close extensions)")
    ax.set_ylabel("Cumulative share of auctions")
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    style_axes(ax)
    add_titles(fig, ax, "Soft close moves the decisive bid earlier",
               ["Empirical CDF of the last period in which the eventual winner raises her maximum bid;",
                "eBay-style proxy auctions, GPT-4o bidders (n = 3), IPV values Unif[0, 99], no reserve"])
    fig.savefig(path_stem + ".png")
    fig.savefig(path_stem + ".pdf")
    plt.close(fig)


# ----------------------------------------------------------------------------
# Figure: side-by-side histograms of the final-winning-bid period, T1 | T2
# ----------------------------------------------------------------------------
def plot_hist(runs: pd.DataFrame, path_stem: str):
    """Two-panel histogram (T1 | T2) of the final-winning-bid period.

    No figure-level title or subtitle; short panel titles; large fonts so the
    figure stays legible at \\linewidth in a two-column-width figure.
    """
    kmax = int(runs["last_period"].max())
    ks_grid = np.arange(1, kmax + 1)
    panels = [("T1", "Standard hard close (T1)"), ("T2", "Soft-close extension rule (T2)")]
    fs_title, fs_label, fs_tick, fs_count, fs_note = 16, 16, 14, 13, 13

    counts_by_t = {}
    for t, _ in panels:
        g = runs.loc[runs["treatment"] == t, PLOT_DEF].values
        counts_by_t[t] = np.array([(g == k).sum() for k in ks_grid])
    ymax = max(c.max() for c in counts_by_t.values())
    ylim = ymax * 1.18
    xmax = kmax + 0.75

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.9), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.90, bottom=0.165, wspace=0.08)
    for ax, (t, ttl) in zip(axes, panels):
        counts = counts_by_t[t]
        n = int(counts.sum())
        ax.bar(ks_grid, counts, width=0.85, color=COLORS[t], zorder=3)
        # soft-close extension periods (11+) shaded; dashed line at the scheduled close
        ax.axvspan(SCHEDULED_PERIODS + 0.5, xmax, color=GRID, alpha=0.45, linewidth=0, zorder=1)
        ax.axvline(SCHEDULED_PERIODS + 0.5, color=INK2, linewidth=1.2,
                   linestyle=(0, (4, 3)), zorder=2)
        ax.text(SCHEDULED_PERIODS + 0.62, ylim * 0.55, "scheduled\nclose", va="center",
                ha="left", fontsize=fs_note, color=INK2, linespacing=1.25)
        # direct label on the period-10 bar; lifted above taller neighbours if needed
        i10 = SCHEDULED_PERIODS - 1
        c10 = int(counts[i10])
        y_text = max(counts[max(i10 - 1, 0):i10 + 2]) + ylim * 0.02
        ax.annotate(f"{c10} ({c10 / n * 100:.0f}%)", xy=(SCHEDULED_PERIODS, c10),
                    xytext=(SCHEDULED_PERIODS, y_text), textcoords="data",
                    ha="center", va="bottom", fontsize=fs_count, color=INK2, zorder=5,
                    bbox=dict(boxstyle="square,pad=0.15", fc=SURFACE, ec="none"),
                    arrowprops=dict(arrowstyle="-", color=AXIS, lw=1.0, shrinkA=0, shrinkB=0))
        ax.set_title(f"{ttl}, n = {n}", fontsize=fs_title, color=INK, loc="left", pad=10)
        ax.set_xlim(0.4, xmax)
        ax.set_ylim(0, ylim)
        ax.set_xticks(ks_grid)
        ax.set_xticklabels([str(k) for k in ks_grid], fontsize=fs_tick)
        ax.tick_params(axis="y", labelsize=fs_tick)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))  # counts
        style_axes(ax)
    axes[0].set_ylabel("Number of auctions", fontsize=fs_label)
    axes[1].tick_params(labelleft=False)
    fig.text(0.53, 0.03, "Period of the final winning bid (shaded: soft-close extension periods)",
             ha="center", va="bottom", fontsize=fs_label, color=INK2)
    fig.savefig(path_stem + ".png")
    fig.savefig(path_stem + ".pdf")
    plt.close(fig)

def main():
    os.makedirs(FIGDIR, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    runs = load_runs()
    summary = build_summary(runs)

    csv_path = os.path.join(OUTDIR, "ebay_closing_rule_summary.csv")
    summary.to_csv(csv_path, index=False, float_format="%.4f")
    plot_cdf(runs, summary, os.path.join(FIGDIR, "ebay_cdf_closing_only"))
    plot_hist(runs, os.path.join(FIGDIR, "ebay_hist_closing_only"))

    pd.set_option("display.width", 200)
    cols = ["definition", "treatment", "n", "share_period10", "share_periods_9_10",
            "share_ge_period10", "share_extension", "mean_period", "median_period",
            "max_period", "mw_U", "mw_p", "ks_D", "ks_p"]
    print(summary[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nper-run last period observed (soft close extensions):")
    print(runs.groupby("treatment")["last_period"].value_counts().sort_index().to_string())
    print(f"\nWrote {csv_path}")
    print(f"Wrote {os.path.join(FIGDIR, 'ebay_cdf_closing_only')}.png/.pdf")
    print(f"Wrote {os.path.join(FIGDIR, 'ebay_hist_closing_only')}.png/.pdf")


if __name__ == "__main__":
    main()

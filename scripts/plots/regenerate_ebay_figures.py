#!/usr/bin/env python3
"""Regenerate the four eBay figures referenced by the merged paper draft
(writeup/auction-v2.tex; plan E5/E10).

Data
----
Per-turn auction transcripts recovered from git (commit 734c0e88, path
experiment_logs/V10/ebay_*), now stored under
recovered_logs/old/experiment_logs_old/V10/:

  ebay_proxy                                -> T1  basic_proxy            (hard close, no reserve)
  ebay_closing_rule                         -> T2  closing_rule           (soft close, no reserve)
  ebay_proxy_with_hidden_reserve_{40,50,60} -> T3  hidden_reserve_r       (hard close, hidden reserve r)
  ebay_closing_rule_with_hidden_reserve_{40,50,60} -> T4 closing_rule_hidden_r (soft close, hidden reserve r)

Each result_*.csv is one auction run (GPT-4o bidders, n=3, IPV Unif[0,99],
10 scheduled days = periods 0..9; soft-close runs extend past period 9).
Columns: period_id, turn_id, current_price, reserve_price, agent_selected,
action, bid, [value], max_bids (str dict), highest_bidder.

Statistic
---------
Final-winning-bid time = the LAST period in which the eventual winner
(final highest_bidder) changes her maximum bid (paper definition,
writeup/contents_v2/05_validation.tex). The older notebooks
(notebooks/ebay_analysis.ipynb) used a price-based proxy (first period at
which current_price reaches its final value); both are computed and
cross-checked, the paper definition is plotted.

Revenue = final current_price of the run (original convention used by the
appendix t-test table, which counts reserve-blocked runs at their closing
price). A "strict" revenue (unsold => 0) is also computed for the summary.

Outputs
-------
  writeup/figures/ebay-winning-bid-non-closing.png   (hard-close histogram)
  writeup/figures/ebay-final-winning-closing.png     (soft-close histogram)
  writeup/figures/ebay_cdf_final_bid.png             (CDF, four treatments)
  writeup/figures/ebay_revenue_by_type.png           (revenue by auction type)
  results/merged_ranking/ebay_figure_stats.json      (all statistics printed below)

Reproducible: numpy seed 1299 (jitter in the revenue plot only; all
statistics are deterministic).
"""

import ast
import glob
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

np.random.seed(1299)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(REPO, "recovered_logs/old/experiment_logs_old/V10")
FIGDIR = os.path.join(REPO, "writeup/figures")
OUTDIR = os.path.join(REPO, "results/merged_ranking")
os.makedirs(FIGDIR, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)

# treatment name (appendix table convention) -> (directory, closing rule, reserve)
TREATMENTS = {
    "basic_proxy": ("ebay_proxy", "hard", 0),
    "closing_rule": ("ebay_closing_rule", "soft", 0),
    "hidden_reserve_40": ("ebay_proxy_with_hidden_reserve_40", "hard", 40),
    "hidden_reserve_50": ("ebay_proxy_with_hidden_reserve_50", "hard", 50),
    "hidden_reserve_60": ("ebay_proxy_with_hidden_reserve_60", "hard", 60),
    "closing_rule_hidden_40": ("ebay_closing_rule_with_hidden_reserve_40", "soft", 40),
    "closing_rule_hidden_50": ("ebay_closing_rule_with_hidden_reserve_50", "soft", 50),
    "closing_rule_hidden_60": ("ebay_closing_rule_with_hidden_reserve_60", "soft", 60),
}

SCHEDULED_LAST_DAY = 9  # 10 scheduled days, periods 0..9

# ----------------------------------------------------------------------------
# dataviz-skill reference palette (light surface), fixed categorical order
# ----------------------------------------------------------------------------
C_BLUE = "#2a78d6"   # slot 1 -> T1 / hard close
C_AQUA = "#1baf7a"   # slot 2 -> T2 / soft close
C_YELLOW = "#eda100" # slot 3 -> T3
C_GREEN = "#008300"  # slot 4 -> T4
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#ffffff"  # paper figure surface (LaTeX page)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "text.color": INK,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 1.0,
    "grid.linestyle": "-",
    "axes.axisbelow": True,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "savefig.dpi": 200,
})


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)


def add_titles(fig, ax, title, subtitle_lines):
    """Figure-level title + muted subtitle, left-aligned with the axes.

    Placed in figure coords so long subtitles never shrink the axes
    (tight_layout would otherwise squeeze the plot to fit them).
    """
    x0 = ax.get_position().x0
    fig.text(x0, 0.955, title, fontsize=13, color=INK, va="top", ha="left")
    fig.text(x0, 0.895, "\n".join(subtitle_lines), fontsize=9.5, color=MUTED,
             va="top", ha="left", linespacing=1.35)


# ----------------------------------------------------------------------------
# Load runs
# ----------------------------------------------------------------------------
def load_runs():
    """Return one record per auction run."""
    records = []
    for tname, (d, close, reserve) in TREATMENTS.items():
        files = sorted(glob.glob(os.path.join(BASE, d, "result_*.csv")))
        for f in files:
            df = pd.read_csv(f)
            df = df.sort_values(["period_id", "turn_id"]).reset_index(drop=True)
            winner = df["highest_bidder"].iloc[-1]
            final_price = float(df["current_price"].iloc[-1])
            maxes = [ast.literal_eval(s) for s in df["max_bids"]]
            final_max = maxes[-1]
            sorted_max = sorted(final_max.values(), reverse=True)
            highest_max, second_max = sorted_max[0], sorted_max[1]

            # paper definition: last period in which the eventual winner
            # changes her maximum bid (initial max is 0 for everyone)
            prev = 0.0
            t_final = np.nan
            for row_i, mb in enumerate(maxes):
                cur = float(mb.get(winner, 0.0))
                if cur != prev:
                    t_final = int(df["period_id"].iloc[row_i])
                prev = cur
            # notebook proxy: first period at which current_price == final price
            t_price = int(df.loc[df["current_price"] == final_price, "period_id"].min())

            sold = highest_max >= reserve  # hidden reserve met?
            records.append(dict(
                treatment=tname, close=close, reserve=reserve, file=os.path.basename(f),
                winner=winner, final_price=final_price,
                highest_max=highest_max, second_max=second_max,
                t_final=t_final, t_price=t_price, sold=sold,
                last_period=int(df["period_id"].max()),
                revenue_strict=final_price if sold else 0.0,
            ))
    return pd.DataFrame(records)


runs = load_runs()
assert runs["t_final"].notna().all(), "some run has no winner max-bid change"
runs["t_final"] = runs["t_final"].astype(int)

hard = runs[runs["close"] == "hard"]
soft = runs[runs["close"] == "soft"]

# ----------------------------------------------------------------------------
# Figure 1 & 2: final-winning-bid timing histograms (hard vs soft close)
# ----------------------------------------------------------------------------
XMAX = int(runs["t_final"].max())
bins = np.arange(-0.5, XMAX + 1.5, 1)


def timing_hist(data, color, title, subtitle_lines, path):
    fig, ax = plt.subplots(figsize=(6.9, 4.4))
    fig.subplots_adjust(left=0.10, right=0.97, top=0.80, bottom=0.14)
    counts, _ = np.histogram(data, bins=bins)
    share = counts / counts.sum()
    ymax = 0.58
    ax.bar(np.arange(0, XMAX + 1), share, width=0.85, color=color, zorder=3)
    # scheduled-deadline reference
    ax.axvline(SCHEDULED_LAST_DAY + 0.5, color=AXIS, linewidth=1.0, zorder=2)
    ax.text(SCHEDULED_LAST_DAY + 0.68, ymax * 0.99, "scheduled\nclose",
            va="top", ha="left", fontsize=8.5, color=MUTED, linespacing=1.3)
    # selective direct label: the final scheduled day
    i = SCHEDULED_LAST_DAY
    ax.annotate(f"{share[i]*100:.0f}%", xy=(i, share[i]), xytext=(0, 4),
                textcoords="offset points", ha="center", fontsize=10, color=INK2)
    ax.set_xlim(-0.7, XMAX + 0.7)
    ax.set_ylim(0, ymax)
    ax.set_xticks(np.arange(0, XMAX + 1))
    ax.set_xlabel("Final-winning-bid time (auction day)")
    ax.set_ylabel("Share of auctions")
    style_axes(ax)
    add_titles(fig, ax, title, subtitle_lines)
    fig.savefig(path)
    plt.close(fig)
    return share


share_hard = timing_hist(
    hard["t_final"], C_BLUE,
    "Hard close: decisive bids cluster at the deadline",
    ["Last day the eventual winner raises her maximum bid; standard eBay closing rule,",
     f"pooled over reserve treatments (N = {len(hard)} auctions, GPT-4o bidders, IPV)"],
    os.path.join(FIGDIR, "ebay-winning-bid-non-closing.png"),
)
share_soft = timing_hist(
    soft["t_final"], C_AQUA,
    "Soft close: decisive bids spread over the auction",
    ["Last day the eventual winner raises her maximum bid; auction-extension closing rule,",
     f"pooled over reserve treatments (N = {len(soft)} auctions, GPT-4o bidders, IPV)"],
    os.path.join(FIGDIR, "ebay-final-winning-closing.png"),
)

# ----------------------------------------------------------------------------
# Figure 3: CDF of final-winning-bid time across the four treatments
# ----------------------------------------------------------------------------
groups = [
    ("T1 proxy (hard close)", runs[runs["treatment"] == "basic_proxy"], C_BLUE),
    ("T2 soft close", runs[runs["treatment"] == "closing_rule"], C_AQUA),
    ("T3 hidden reserve (hard close)", runs[(runs["close"] == "hard") & (runs["reserve"] > 0)], C_YELLOW),
    ("T4 hidden reserve + soft close", runs[(runs["close"] == "soft") & (runs["reserve"] > 0)], C_GREEN),
]

fig, ax = plt.subplots(figsize=(7.2, 4.7))
fig.subplots_adjust(left=0.09, right=0.97, top=0.81, bottom=0.13)
for label, g, color in groups:
    x = np.sort(g["t_final"].values)
    y = np.arange(1, len(x) + 1) / len(x)
    ax.step(np.concatenate([[-0.001], x]), np.concatenate([[0], y]), where="post",
            color=color, linewidth=2, solid_joinstyle="round", solid_capstyle="round",
            label=f"{label}  (N={len(g)})", zorder=3)
ax.axvline(SCHEDULED_LAST_DAY, color=AXIS, linewidth=1.0, zorder=2)
ax.text(SCHEDULED_LAST_DAY - 0.15, 0.03, "scheduled final day", rotation=90,
        va="bottom", ha="right", fontsize=8.5, color=MUTED)
ax.set_xlim(-0.3, XMAX + 0.3)
ax.set_ylim(0, 1.02)
ax.set_xticks(np.arange(0, XMAX + 1))
ax.set_xlabel("Final-winning-bid time (auction day)")
ax.set_ylabel("Cumulative share of auctions")
ax.legend(loc="upper left", frameon=False, fontsize=9.5)
style_axes(ax)
add_titles(fig, ax, "Soft close moves the decisive bid earlier",
           ["Empirical CDF of the last day the eventual winner raises her maximum bid,",
            "by eBay treatment (GPT-4o bidders, IPV); hidden-reserve treatments pool r ∈ {40, 50, 60}"])
fig.savefig(os.path.join(FIGDIR, "ebay_cdf_final_bid.png"))
plt.close(fig)

# ----------------------------------------------------------------------------
# Figure 4: seller revenue by auction type (original final-price convention)
# ----------------------------------------------------------------------------
order = ["basic_proxy", "closing_rule", "hidden_reserve_40", "hidden_reserve_50",
         "hidden_reserve_60", "closing_rule_hidden_40", "closing_rule_hidden_50",
         "closing_rule_hidden_60"]
labels = ["T1\nproxy", "T2\nsoft close", "T3\nr=40", "T3\nr=50", "T3\nr=60",
          "T4\nr=40", "T4\nr=50", "T4\nr=60"]
colors = [C_BLUE, C_AQUA, C_YELLOW, C_YELLOW, C_YELLOW, C_GREEN, C_GREEN, C_GREEN]

fig, ax = plt.subplots(figsize=(7.6, 4.7))
fig.subplots_adjust(left=0.09, right=0.97, top=0.81, bottom=0.13)
data = [runs.loc[runs["treatment"] == t, "final_price"].values for t in order]
bp = ax.boxplot(data, positions=np.arange(len(order)), widths=0.5, patch_artist=True,
                showfliers=False, medianprops=dict(color=INK, linewidth=1.4),
                whiskerprops=dict(color=AXIS, linewidth=1.2),
                capprops=dict(color=AXIS, linewidth=1.2),
                boxprops=dict(linewidth=0))
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.28)
for i, (vals, c) in enumerate(zip(data, colors)):
    x = i + np.random.uniform(-0.13, 0.13, size=len(vals))
    ax.scatter(x, vals, s=14, color=c, alpha=0.55, linewidths=0, zorder=3)
    ax.scatter([i], [vals.mean()], s=42, color=c, edgecolors="white",
               linewidths=1.6, zorder=4)
ax.set_xticks(np.arange(len(order)))
ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("Seller revenue (final price, $)")
ax.set_ylim(0, 102)
style_axes(ax)
add_titles(fig, ax, "Seller revenue is flat across eBay treatments",
           ["Final auction price per run (dots); box = interquartile range and median, white-ringed",
            "dot = mean; N = 30 runs per cell (29 for T4 r=60); GPT-4o bidders, IPV values Unif[0,99]"])
fig.savefig(os.path.join(FIGDIR, "ebay_revenue_by_type.png"))
plt.close(fig)

# ----------------------------------------------------------------------------
# Statistics for the summary (printed + JSON)
# ----------------------------------------------------------------------------
out = {"n_runs": {t: int((runs["treatment"] == t).sum()) for t in order}}

# timing stats (paper definition)
def tstats(g):
    return dict(n=int(len(g)), mean=float(g.mean()), median=float(g.median()),
                share_ge_day9=float((g >= SCHEDULED_LAST_DAY).mean()),
                share_day9=float((g == SCHEDULED_LAST_DAY).mean()))

out["timing"] = {
    "hard_pooled": tstats(hard["t_final"]),
    "soft_pooled": tstats(soft["t_final"]),
    "T1_only": tstats(runs.loc[runs["treatment"] == "basic_proxy", "t_final"]),
    "T2_only": tstats(runs.loc[runs["treatment"] == "closing_rule", "t_final"]),
    "T3_pooled": tstats(groups[2][1]["t_final"]),
    "T4_pooled": tstats(groups[3][1]["t_final"]),
}
mw = stats.mannwhitneyu(hard["t_final"], soft["t_final"], alternative="two-sided")
ks = stats.ks_2samp(hard["t_final"], soft["t_final"])
mw12 = stats.mannwhitneyu(runs.loc[runs["treatment"] == "basic_proxy", "t_final"],
                          runs.loc[runs["treatment"] == "closing_rule", "t_final"],
                          alternative="two-sided")
out["timing_tests"] = {
    "MW_hard_vs_soft_pooled": dict(U=float(mw.statistic), p=float(mw.pvalue)),
    "KS_hard_vs_soft_pooled": dict(D=float(ks.statistic), p=float(ks.pvalue)),
    "MW_T1_vs_T2": dict(U=float(mw12.statistic), p=float(mw12.pvalue)),
}
# cross-check vs notebook price-based proxy
out["definition_crosscheck"] = {
    "spearman_t_final_vs_t_price": float(stats.spearmanr(runs["t_final"], runs["t_price"]).statistic),
    "share_equal": float((runs["t_final"] == runs["t_price"]).mean()),
    "hard_share_ge_day9_price_def": float((hard["t_price"] >= SCHEDULED_LAST_DAY).mean()),
    "soft_share_ge_day9_price_def": float((soft["t_price"] >= SCHEDULED_LAST_DAY).mean()),
}

# revenue: pairwise Welch t-tests + Mann-Whitney (final-price convention)
pairs = []
for i in range(len(order)):
    for j in range(i + 1, len(order)):
        a = runs.loc[runs["treatment"] == order[i], "final_price"]
        b = runs.loc[runs["treatment"] == order[j], "final_price"]
        t = stats.ttest_ind(a, b, equal_var=False)
        m = stats.mannwhitneyu(a, b, alternative="two-sided")
        pairs.append(dict(a=order[i], b=order[j], n_a=len(a), n_b=len(b),
                          t=round(float(t.statistic), 3), p_t=round(float(t.pvalue), 3),
                          df=round(float(t.df), 1),
                          U=float(m.statistic), p_mw=round(float(m.pvalue), 3)))
out["revenue_pairwise"] = pairs
kw = stats.kruskal(*data)
out["revenue_overall"] = dict(
    means={t: round(float(runs.loc[runs["treatment"] == t, "final_price"].mean()), 2) for t in order},
    sds={t: round(float(runs.loc[runs["treatment"] == t, "final_price"].std(ddof=1)), 2) for t in order},
    kruskal_H=float(kw.statistic), kruskal_p=float(kw.pvalue),
)

# strict revenue (unsold => 0)
out["revenue_strict"] = {
    "means": {t: round(float(runs.loc[runs["treatment"] == t, "revenue_strict"].mean()), 2) for t in order},
    "n_unsold": {t: int((~runs.loc[runs["treatment"] == t, "sold"]).sum()) for t in order},
}
strict_pairs = []
for t in order[2:]:
    a = runs.loc[runs["treatment"] == "basic_proxy", "revenue_strict"]
    b = runs.loc[runs["treatment"] == t, "revenue_strict"]
    tt = stats.ttest_ind(a, b, equal_var=False)
    strict_pairs.append(dict(a="basic_proxy", b=t, t=round(float(tt.statistic), 3),
                             p=round(float(tt.pvalue), 4)))
out["revenue_strict_vs_T1"] = strict_pairs

# hidden-reserve audit
audit = {}
for t in order[2:]:
    g = runs[runs["treatment"] == t]
    r = g["reserve"].iloc[0]
    blocked = (g["highest_max"] < r)
    liftable = (g["second_max"] < r) & (g["highest_max"] >= r)
    lifted = liftable & (g["final_price"] >= r)
    audit[t] = dict(n=len(g), reserve=int(r),
                    blocked=int(blocked.sum()),
                    liftable=int(liftable.sum()),
                    price_reached_reserve_when_liftable=int(lifted.sum()))
out["reserve_audit"] = audit

with open(os.path.join(OUTDIR, "ebay_figure_stats.json"), "w") as fh:
    json.dump(out, fh, indent=2)

print(json.dumps(out, indent=2))
print("\nWrote figures to", FIGDIR)

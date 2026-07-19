"""
v3 split-domain figure exhibits for writeup/auction-v3.tex.

Regenerates the four main-text figure exhibits as AUCTION-ONLY versions
(the previous assets mixed a Deferred Acceptance row into each figure),
plus ONE combined DA-counterpart figure for the appendix.

Outputs (written to writeup/figures/):
  1. v3_osp_auction.pdf      1x4  spsb (gray) vs ascending_clock_closed (colored)
  2. v3_safety_auction.pdf   1x4  spsb vs axis2_forward_onestep   (Payoff Safety)
  3. v3_tree_auction.pdf     1x4  spsb vs axis2_forward_tree      (Payoff Tree)
  4. v3_beliefs_auction.pdf  2x4  spsb vs axis3_beliefs_{first,second}order
  5. v3_da_counterparts.pdf  5x4  DA cells vs direct_baseline (Kendall tau)

Style matches Engineering_simplicity/engineer_simplicity-main/plots/plot_osp_comparison.py.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ============================================================================
# STYLE CONFIGURATION (matches plot_osp_comparison.py)
# ============================================================================

plt.style.use('seaborn-v0_8-whitegrid')

plt.rcParams.update({
    'figure.facecolor': 'white',
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,

    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,

    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'axes.edgecolor': '#555555',
    'axes.labelcolor': '#333333',

    'grid.alpha': 0.4,
    'grid.linewidth': 0.5,
    'axes.grid': True,
    'axes.axisbelow': True,
})

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / 'Engineering_simplicity' / 'engineer_simplicity-main'
OUTPUT_DIR = REPO_ROOT / 'writeup' / 'figures'

BASELINE_COLOR = '#888888'

MODEL_ORDER = ['Claude 3.5 Haiku', 'Gemini 2.0 Flash', 'GPT-4o', 'Gemma 3 27B']

MODEL_COLORS = {
    'Claude 3.5 Haiku': '#4363d8',
    'Gemini 2.0 Flash': '#e6194B',
    'GPT-4o': '#f58231',
    'Gemma 3 27B': '#3cb44b',
}

MODEL_COLORS_DARK = {
    'Claude 3.5 Haiku': '#2a3d8a',
    'Gemini 2.0 Flash': '#a11232',
    'GPT-4o': '#c46820',
    'Gemma 3 27B': '#297a33',
}

AUCTION_BINS = np.linspace(-20, 20, 30)
DA_BINS = np.linspace(0, 1, 21)

# ============================================================================
# DATA LOADING - AUCTIONS
# ============================================================================

AUCTION_MODEL_NAMES = {
    'claude-3-5-haiku-20241022': 'Claude 3.5 Haiku',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'google/gemma-3-27b-it': 'Gemma 3 27B',
    'gpt-4o': 'GPT-4o',
}


def load_auction_data():
    """Load the combined auction experimental results (bid-level)."""
    data_path = (DATA_ROOT / 'results' /
                 'all_experiments_combined_20260204_114522.csv')
    print(f"Auctions: {data_path.name}")
    df = pd.read_csv(data_path)
    df['model_short'] = df['model'].map(AUCTION_MODEL_NAMES)
    df['deviation'] = df['bid'] - df['player_value']
    return df


# ============================================================================
# DATA LOADING - DA (Kendall tau parsing copied from plot_osp_comparison.py)
# ============================================================================

DA_MODEL_NAMES = {
    'claude': 'Claude 3.5 Haiku',
    'gemini': 'Gemini 2.0 Flash',
    'gpt4o': 'GPT-4o',
    'gemma': 'Gemma 3 27B',
}


def get_true_ranking(values):
    """Convert values dict to true ranking (sorted by value, descending)."""
    return sorted(values.keys(), key=lambda x: values[x], reverse=True)


def kendall_tau_distance(true_ranking, submitted_ranking):
    """Count discordant pairs between two rankings."""
    common = set(true_ranking) & set(submitted_ranking)
    n = len(common)
    if n < 2:
        return 0, 0

    true_pos = {item: i for i, item in enumerate(true_ranking) if item in common}
    sub_pos = {item: i for i, item in enumerate(submitted_ranking) if item in common}

    items = list(common)
    discordant = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            true_order = true_pos[a] < true_pos[b]
            sub_order = sub_pos[a] < sub_pos[b]
            if true_order != sub_order:
                discordant += 1

    n_pairs = n * (n - 1) // 2
    return discordant, n_pairs


def load_da_data():
    """Load all DA experiment results from JSON files."""
    da_dir = DATA_ROOT / 'experiment_logs' / 'da'
    rows = []

    for model_dir in sorted(da_dir.iterdir()):
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name
        if model_name not in DA_MODEL_NAMES:
            continue

        model_short = DA_MODEL_NAMES[model_name]

        for exp_dir in sorted(model_dir.iterdir()):
            if not exp_dir.is_dir():
                continue

            exp_name = exp_dir.name
            raw_data_dir = exp_dir / 'raw_data'

            if not raw_data_dir.exists():
                continue

            for json_file in sorted(raw_data_dir.glob('*.json')):
                try:
                    with open(json_file) as f:
                        data = json.load(f)

                    mechanism_type = data.get('mechanism_type', 'direct')
                    values = data.get('values', {})

                    if mechanism_type == 'osp':
                        rankings = data.get('osp_choices', {})
                    else:
                        rankings = data.get('rankings', {})

                    for student, student_values in values.items():
                        true_ranking = get_true_ranking(student_values)
                        submitted = rankings.get(student, [])

                        if not submitted:
                            continue

                        if mechanism_type == 'osp':
                            revealed_items = set(submitted)
                            true_ranking_truncated = [
                                s for s in true_ranking if s in revealed_items]
                        else:
                            true_ranking_truncated = true_ranking

                        discordant, n_pairs = kendall_tau_distance(
                            true_ranking_truncated, submitted)
                        normalized = discordant / n_pairs if n_pairs > 0 else 0.0

                        rows.append({
                            'model_short': model_short,
                            'experiment': exp_name,
                            'kendall_tau_normalized': normalized,
                            'mechanism_type': mechanism_type,
                        })

                except Exception:
                    continue

    return pd.DataFrame(rows)


# ============================================================================
# PANEL PRIMITIVES
# ============================================================================

def draw_hist_pair(ax, treat, base, bins, color, color_dark):
    """Weighted (% of obs) histograms: colored treatment FIRST, gray baseline
    SECOND on top; dashed mean lines. Returns (base_mean, treat_mean)."""
    treat_mean = np.nan
    if len(treat) > 0:
        weights = np.ones_like(treat) * 100 / len(treat)
        ax.hist(treat, bins=bins, alpha=0.6, color=color,
                edgecolor=color_dark, linewidth=0.6, weights=weights)
        treat_mean = np.mean(treat)
        ax.axvline(treat_mean, color=color, linestyle='--', linewidth=2, alpha=0.9)

    base_mean = np.nan
    if len(base) > 0:
        weights = np.ones_like(base) * 100 / len(base)
        ax.hist(base, bins=bins, alpha=0.5, color=BASELINE_COLOR,
                edgecolor='#333333', linewidth=0.6, weights=weights)
        base_mean = np.mean(base)
        ax.axvline(base_mean, color=BASELINE_COLOR, linestyle='--',
                   linewidth=2, alpha=0.9)

    return base_mean, treat_mean


def annotate_means(ax, base_label, treat_label, color):
    """Two stacked white-boxed bold labels, baseline (gray) on top."""
    box = dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9,
               edgecolor='none')
    if base_label is not None:
        ax.text(0.97, 0.95, base_label, transform=ax.transAxes, fontsize=9,
                fontweight='bold', ha='right', va='top', color=BASELINE_COLOR,
                bbox=box)
    if treat_label is not None:
        ax.text(0.97, 0.75, treat_label, transform=ax.transAxes, fontsize=9,
                fontweight='bold', ha='right', va='top', color=color, bbox=box)


def style_auction_axis(ax):
    ax.set_xlim(-20, 20)
    ax.set_xticks([-20, -10, 0, 10, 20])
    ax.set_xticklabels(['-20', '', '0', '', '20'])
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))


def style_da_axis(ax):
    # Reference line at 0 (perfect ranking), as in plot_osp_comparison.py
    ax.axvline(0, color='#2d8a2d', linestyle='-', linewidth=1.5, alpha=0.7)
    ax.set_xlim(0, 1)
    # 4 students -> 6 pairs: ticks at k/6, sparse labels for legibility
    ax.set_xticks([0, 1/6, 2/6, 3/6, 4/6, 5/6, 1])
    ax.set_xticklabels(['0%', '', '', '50%', '', '', '100%'])
    # Hide y 0% tick to avoid overlap with the x-axis 0% label
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))


def add_legend(fig, bottom_anchor=-0.02):
    """Bottom legend: gray Baseline patch, multi-color Intervention patch,
    dashed Mean line (matches the existing assets)."""

    class MultiColorPatch:
        pass

    class MultiColorHandler:
        def __init__(self, colors):
            self.colors = colors

        def legend_artist(self, legend, orig_handle, fontsize, handlebox):
            x0, y0 = handlebox.xdescent, handlebox.ydescent
            width, height = handlebox.width, handlebox.height
            n = len(self.colors)
            patches = []
            for i, color in enumerate(self.colors):
                patch = mpatches.FancyBboxPatch(
                    (x0 + i * width / n, y0), width / n, height,
                    boxstyle="square,pad=0", facecolor=color, alpha=0.6,
                    edgecolor='none', transform=handlebox.get_transform())
                handlebox.add_artist(patch)
                patches.append(patch)
            return patches[0] if patches else None

    multi_patch = MultiColorPatch()
    handles = [
        mpatches.Patch(facecolor=BASELINE_COLOR, alpha=0.5,
                       edgecolor='#333333', linewidth=0.6),
        multi_patch,
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=2),
    ]
    labels = ['Baseline', 'Intervention', 'Mean']
    handler = MultiColorHandler([MODEL_COLORS[m] for m in MODEL_ORDER])
    fig.legend(handles, labels, loc='lower center', ncol=3,
               frameon=True, framealpha=0.95, edgecolor='#cccccc',
               bbox_to_anchor=(0.5, bottom_anchor), fontsize=9,
               handler_map={MultiColorPatch: handler})


# ============================================================================
# AUCTION FIGURES
# ============================================================================

def make_auction_figure(auction_df, rows, out_name, fig_height,
                        legend_anchor):
    """Generic auction figure: rows = [(row_label, treatment_experiment)],
    models as columns, gray spsb baseline in every panel."""
    nrows = len(rows)
    fig, axes = plt.subplots(nrows, 4, figsize=(5.8, fig_height),
                             squeeze=False)

    stats = []
    for row_idx, (row_label, treat_exp) in enumerate(rows):
        for col_idx, model in enumerate(MODEL_ORDER):
            ax = axes[row_idx, col_idx]
            color = MODEL_COLORS[model]
            color_dark = MODEL_COLORS_DARK[model]

            mdf = auction_df[auction_df['model_short'] == model]
            base = mdf[mdf['experiment'] == 'spsb']['deviation'].values
            treat = mdf[mdf['experiment'] == treat_exp]['deviation'].values

            base_mean, treat_mean = draw_hist_pair(
                ax, treat, base, AUCTION_BINS, color, color_dark)
            style_auction_axis(ax)

            annotate_means(
                ax,
                None if np.isnan(base_mean) else f'μ = {base_mean:+.1f}',
                None if np.isnan(treat_mean) else f'μ = {treat_mean:+.1f}',
                color)

            if row_idx == 0:
                ax.set_title(model, fontweight='bold', fontsize=10,
                             color=color, pad=6)
            if col_idx == 0:
                ax.set_ylabel(f'{row_label}\n(% of obs)', fontsize=9,
                              fontweight='bold')
            if row_idx == nrows - 1:
                ax.set_xlabel('bid − value ($)', fontsize=9)

            stats.append((row_label, model, 'spsb', len(base), base_mean))
            stats.append((row_label, model, treat_exp, len(treat), treat_mean))
            print(f"  [{out_name}] {row_label} | {model}: "
                  f"spsb n={len(base)}, μ={base_mean:+.3f} | "
                  f"{treat_exp} n={len(treat)}, μ={treat_mean:+.3f}")

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.30 / fig_height * 2.2)
    add_legend(fig, legend_anchor)

    out_path = OUTPUT_DIR / out_name
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved: {out_path}")
    return stats


# ============================================================================
# DA COUNTERPARTS FIGURE
# ============================================================================

DA_ROWS = [
    ('Iterative (OSP)', 'osp_yesno_fixed'),
    ('Rejection Safety', 'axis2_monotonic_safety'),
    ('Payoff Tree', 'axis1_tree'),
    ('First-Order Beliefs', 'axis3_firstorder'),
    ('Second-Order Beliefs', 'axis3_secondorder'),
]


def make_da_figure(da_df, out_name='v3_da_counterparts.pdf'):
    nrows = len(DA_ROWS)
    fig_height = 1.28 * nrows + 0.9
    fig, axes = plt.subplots(nrows, 4, figsize=(5.8, fig_height),
                             squeeze=False)

    stats = []
    for row_idx, (row_label, treat_exp) in enumerate(DA_ROWS):
        for col_idx, model in enumerate(MODEL_ORDER):
            ax = axes[row_idx, col_idx]
            color = MODEL_COLORS[model]
            color_dark = MODEL_COLORS_DARK[model]

            mdf = da_df[da_df['model_short'] == model]
            base = mdf[mdf['experiment'] == 'direct_baseline'][
                'kendall_tau_normalized'].values
            treat = mdf[mdf['experiment'] == treat_exp][
                'kendall_tau_normalized'].values

            base_mean, treat_mean = draw_hist_pair(
                ax, treat, base, DA_BINS, color, color_dark)
            style_da_axis(ax)

            base_label = (None if np.isnan(base_mean)
                          else f'μ = {base_mean * 100:.0f}%')
            if len(treat) > 0:
                treat_label = f'μ = {treat_mean * 100:.0f}%'
            else:
                treat_label = None
                ax.text(0.5, 0.45, 'no data', transform=ax.transAxes,
                        fontsize=9, style='italic', ha='center', va='center',
                        color='#777777')
            annotate_means(ax, base_label, treat_label, color)

            if row_idx == 0:
                ax.set_title(model, fontweight='bold', fontsize=10,
                             color=color, pad=6)
            if col_idx == 0:
                ax.set_ylabel(f'{row_label}\n(% of obs)', fontsize=9,
                              fontweight='bold')
            if row_idx == nrows - 1:
                ax.set_xlabel('Kendall τ distance', fontsize=9)

            stats.append((row_label, model, 'direct_baseline',
                          len(base), base_mean))
            stats.append((row_label, model, treat_exp, len(treat), treat_mean))
            print(f"  [{out_name}] {row_label} | {model}: "
                  f"direct n={len(base)}, μ={base_mean * 100:.2f}% | "
                  f"{treat_exp} n={len(treat)}, μ={treat_mean * 100:.2f}%")

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)
    add_legend(fig, -0.005)

    out_path = OUTPUT_DIR / out_name
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved: {out_path}")
    return stats


# ============================================================================
# VERIFICATION AGAINST CANONICAL MEANS
# ============================================================================

CANON = {
    # experiment -> means in MODEL_ORDER (Claude, Gemini, GPT-4o, Gemma)
    'spsb': [-0.49, -1.63, -3.28, -5.27],
    'ascending_clock_closed': [-0.05, -1.24, -0.45, -0.33],
    'axis2_forward_tree': [-0.82, -0.53, -0.86, -2.34],
    'axis2_forward_onestep': [+0.30, -0.38, -1.88, -4.17],
    'axis3_beliefs_firstorder': [-0.005, -2.40, -3.27, -6.85],
    'axis3_beliefs_secondorder': [-0.59, -1.31, -4.54, -7.43],
}


def verify_auction_means(auction_df):
    print("\nVerifying auction means against canon (tolerance 0.05):")
    ok = True
    for exp, canon_means in CANON.items():
        for model, canon_mean in zip(MODEL_ORDER, canon_means):
            dev = auction_df[
                (auction_df['model_short'] == model) &
                (auction_df['experiment'] == exp)
            ]['deviation'].values
            mean = np.mean(dev)
            diff = abs(mean - canon_mean)
            flag = 'OK' if diff <= 0.05 else 'MISMATCH'
            if diff > 0.05:
                ok = False
            print(f"  {exp:28s} {model:18s} n={len(dev):4d} "
                  f"computed={mean:+.3f} canon={canon_mean:+.3f} [{flag}]")
    if not ok:
        raise SystemExit("Canonical mean mismatch — investigate before shipping.")
    print("All auction means match canon.\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    auction_df = load_auction_data()
    verify_auction_means(auction_df)

    da_df = load_da_data()
    print(f"DA observations loaded: {len(da_df)}")

    # 1. OSP (Ascending Clock)
    make_auction_figure(
        auction_df, [('Ascending Clock', 'ascending_clock_closed')],
        'v3_osp_auction.pdf', fig_height=1.95, legend_anchor=-0.05)

    # 2. Payoff Safety
    make_auction_figure(
        auction_df, [('Payoff Safety', 'axis2_forward_onestep')],
        'v3_safety_auction.pdf', fig_height=1.95, legend_anchor=-0.05)

    # 3. Payoff Tree
    make_auction_figure(
        auction_df, [('Payoff Tree', 'axis2_forward_tree')],
        'v3_tree_auction.pdf', fig_height=1.95, legend_anchor=-0.05)

    # 4. Beliefs (2 rows)
    make_auction_figure(
        auction_df,
        [('First-Order Beliefs', 'axis3_beliefs_firstorder'),
         ('Second-Order Beliefs', 'axis3_beliefs_secondorder')],
        'v3_beliefs_auction.pdf', fig_height=3.3, legend_anchor=-0.03)

    # 5. DA counterparts (5 rows)
    make_da_figure(da_df)


if __name__ == '__main__':
    main()

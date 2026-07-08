"""
OSP Mechanisms Comparison Plot

Creates a grid figure showing:
- Rows: One per model (Claude, Gemini, GPT-4o, Gemma)
- Left column: Auctions - SPSB (gray) vs Ascending Clock (colored)
- Right column: DA - Direct baseline (gray) vs OSP (colored)

Shows that OSP mechanisms improve play in both domains across all models.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# ============================================================================
# STYLE CONFIGURATION
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

OUTPUT_DIR = Path(__file__).parent

# Colors
BASELINE_COLOR = '#888888'      # Gray for baselines

# Model configuration
MODEL_ORDER = ['Claude 3.5 Haiku', 'Gemini 2.0 Flash', 'GPT-4o', 'Gemma 3 27B']

MODEL_COLORS = {
    'Claude 3.5 Haiku': '#4363d8',    # Blue
    'Gemini 2.0 Flash': '#e6194B',    # Red
    'GPT-4o': '#f58231',              # Orange
    'Gemma 3 27B': '#3cb44b',         # Green
}

MODEL_COLORS_DARK = {
    'Claude 3.5 Haiku': '#2a3d8a',
    'Gemini 2.0 Flash': '#a11232',
    'GPT-4o': '#c46820',
    'Gemma 3 27B': '#297a33',
}

# ============================================================================
# DATA LOADING - AUCTIONS
# ============================================================================

AUCTION_MODEL_NAMES = {
    'claude-3-5-haiku-20241022': 'Claude 3.5 Haiku',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'google/gemma-3-27b-it': 'Gemma 3 27B',
    'gpt-4o': 'GPT-4o'
}

def load_auction_data():
    """Load the combined auction experimental results."""
    results_dir = Path(__file__).parent.parent / 'results'
    combined_files = sorted(results_dir.glob('all_experiments_combined_*.csv'))
    if not combined_files:
        raise FileNotFoundError("No combined results files found")
    data_path = combined_files[-1]
    print(f"Auctions: {data_path.name}")
    df = pd.read_csv(data_path)
    df['model_short'] = df['model'].map(AUCTION_MODEL_NAMES)
    df['deviation'] = df['bid'] - df['player_value']
    return df


# ============================================================================
# DATA LOADING - DA
# ============================================================================

DA_MODEL_NAMES = {
    'claude': 'Claude 3.5 Haiku',
    'gemini': 'Gemini 2.0 Flash',
    'gpt4o': 'GPT-4o',
    'gemma': 'Gemma 3 27B',
    'others': 'GPT-4o',
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
        for j in range(i+1, len(items)):
            a, b = items[i], items[j]
            true_order = true_pos[a] < true_pos[b]
            sub_order = sub_pos[a] < sub_pos[b]
            if true_order != sub_order:
                discordant += 1

    n_pairs = n * (n - 1) // 2
    return discordant, n_pairs


def load_da_data():
    """Load all DA experiment results from JSON files."""
    da_dir = Path(__file__).parent.parent / 'experiment_logs' / 'da'
    rows = []

    for model_dir in da_dir.iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name
        if model_name not in DA_MODEL_NAMES:
            continue

        model_short = DA_MODEL_NAMES[model_name]

        for exp_dir in model_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            exp_name = exp_dir.name
            raw_data_dir = exp_dir / 'raw_data'

            if not raw_data_dir.exists():
                continue

            for json_file in raw_data_dir.glob('*.json'):
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
                            true_ranking_truncated = [s for s in true_ranking if s in revealed_items]
                        else:
                            true_ranking_truncated = true_ranking

                        discordant, n_pairs = kendall_tau_distance(true_ranking_truncated, submitted)
                        normalized = discordant / n_pairs if n_pairs > 0 else 0.0

                        rows.append({
                            'model_short': model_short,
                            'experiment': exp_name,
                            'kendall_tau_normalized': normalized,
                            'mechanism_type': mechanism_type,
                        })

                except Exception as e:
                    continue

    return pd.DataFrame(rows)


# ============================================================================
# MAIN PLOT
# ============================================================================

def plot_osp_comparison():
    """
    Create grid comparison showing OSP mechanisms improve play.

    Rows: One per model
    Left column: Auctions (SPSB baseline vs Ascending Clock)
    Right column: DA (Direct baseline vs OSP)
    """
    print("Loading data...")

    # Load data
    auction_df = load_auction_data()
    da_df = load_da_data()

    # Create figure: 4 rows (models) x 2 columns (auctions, DA)
    fig, axes = plt.subplots(4, 2, figsize=(10, 12))

    x_limit = 20
    auction_bins = np.linspace(-x_limit, x_limit, 30)
    da_bins = np.linspace(0, 1, 21)

    for row_idx, model in enumerate(MODEL_ORDER):
        color = MODEL_COLORS[model]
        color_dark = MODEL_COLORS_DARK[model]

        ax_auction = axes[row_idx, 0]
        ax_da = axes[row_idx, 1]

        # ─────────────────────────────────────────────────────────────────────
        # LEFT COLUMN: Auctions
        # ─────────────────────────────────────────────────────────────────────
        spsb_dev = auction_df[
            (auction_df['model_short'] == model) &
            (auction_df['experiment'].isin(['spsb_apv', 'spsb']))
        ]['deviation'].values

        ac_dev = auction_df[
            (auction_df['model_short'] == model) &
            (auction_df['experiment'].isin(['ascending_clock_apv', 'ascending_clock_closed']))
        ]['deviation'].values

        # Plot Ascending Clock FIRST (colored, behind)
        if len(ac_dev) > 0:
            ac_weights = np.ones_like(ac_dev) * 100 / len(ac_dev)
            ax_auction.hist(ac_dev, bins=auction_bins, alpha=0.6, color=color,
                           edgecolor=color_dark, linewidth=0.6, weights=ac_weights)
            ac_mean = np.mean(ac_dev)
            ax_auction.axvline(ac_mean, color=color, linestyle='--', linewidth=2, alpha=0.9)
        else:
            ac_mean = np.nan

        # Plot SPSB SECOND (gray, in front)
        if len(spsb_dev) > 0:
            spsb_weights = np.ones_like(spsb_dev) * 100 / len(spsb_dev)
            ax_auction.hist(spsb_dev, bins=auction_bins, alpha=0.5, color=BASELINE_COLOR,
                           edgecolor='#333333', linewidth=0.6, weights=spsb_weights)
            spsb_mean = np.mean(spsb_dev)
            ax_auction.axvline(spsb_mean, color=BASELINE_COLOR, linestyle='--', linewidth=2, alpha=0.9)
        else:
            spsb_mean = np.nan

        # No reference line at 0 for auctions (reduces clutter)

        ax_auction.set_xlim(-x_limit, x_limit)
        ax_auction.set_ylim(0, 100)
        ax_auction.set_yticks([0, 20, 40, 60, 80, 100])
        ax_auction.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))

        # Model label on left
        ax_auction.set_ylabel(model, fontsize=11, fontweight='bold')

        # Annotation
        if not np.isnan(spsb_mean) and not np.isnan(ac_mean):
            ax_auction.text(0.97, 0.95, f'SPSB μ = {spsb_mean:+.1f}',
                           transform=ax_auction.transAxes, fontsize=9, fontweight='bold',
                           ha='right', va='top', color=BASELINE_COLOR,
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor='none'))
            ax_auction.text(0.97, 0.75, f'AC μ = {ac_mean:+.1f}',
                           transform=ax_auction.transAxes, fontsize=9, fontweight='bold',
                           ha='right', va='top', color=color,
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor='none'))

        print(f"  {model} Auctions: SPSB n={len(spsb_dev)}, μ={spsb_mean:+.2f} | AC n={len(ac_dev)}, μ={ac_mean:+.2f}")

        # ─────────────────────────────────────────────────────────────────────
        # RIGHT COLUMN: DA
        # ─────────────────────────────────────────────────────────────────────
        direct_tau = da_df[
            (da_df['model_short'] == model) &
            (da_df['experiment'] == 'direct_baseline')
        ]['kendall_tau_normalized'].values

        osp_tau = da_df[
            (da_df['model_short'] == model) &
            (da_df['experiment'] == 'osp_yesno_fixed')
        ]['kendall_tau_normalized'].values

        # Plot OSP FIRST (colored, behind)
        if len(osp_tau) > 0:
            osp_weights = np.ones_like(osp_tau) * 100 / len(osp_tau)
            ax_da.hist(osp_tau, bins=da_bins, alpha=0.6, color=color,
                      edgecolor=color_dark, linewidth=0.6, weights=osp_weights)
            osp_mean = np.mean(osp_tau)
            ax_da.axvline(osp_mean, color=color, linestyle='--', linewidth=2, alpha=0.9)
        else:
            osp_mean = np.nan

        # Plot Direct SECOND (gray, in front)
        if len(direct_tau) > 0:
            direct_weights = np.ones_like(direct_tau) * 100 / len(direct_tau)
            ax_da.hist(direct_tau, bins=da_bins, alpha=0.5, color=BASELINE_COLOR,
                      edgecolor='#333333', linewidth=0.6, weights=direct_weights)
            direct_mean = np.mean(direct_tau)
            ax_da.axvline(direct_mean, color=BASELINE_COLOR, linestyle='--', linewidth=2, alpha=0.9)
        else:
            direct_mean = np.nan

        # Reference line at 0
        ax_da.axvline(0, color='#2d8a2d', linestyle='-', linewidth=1.5, alpha=0.7)

        ax_da.set_xlim(0, 1)
        # Kendall tau for 4 items has 6 pairs: ticks at 0/6, 1/6, 2/6, 3/6, 4/6, 5/6, 6/6
        ax_da.set_xticks([0, 1/6, 2/6, 3/6, 4/6, 5/6, 1])
        ax_da.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
        ax_da.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.0f}%'))

        # Annotation
        if not np.isnan(direct_mean) and not np.isnan(osp_mean):
            ax_da.text(0.97, 0.95, f'Full Report μ = {direct_mean*100:.0f}%',
                      transform=ax_da.transAxes, fontsize=9, fontweight='bold',
                      ha='right', va='top', color=BASELINE_COLOR,
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor='none'))
            ax_da.text(0.97, 0.75, f'Iterative μ = {osp_mean*100:.0f}%',
                      transform=ax_da.transAxes, fontsize=9, fontweight='bold',
                      ha='right', va='top', color=color,
                      bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor='none'))

        # Set y-axis max to 100% and hide the 0% tick to avoid overlap with x-axis 0%
        ax_da.set_ylim(0, 100)
        ax_da.set_yticks([20, 40, 60, 80, 100])

        print(f"  {model} DA: Direct n={len(direct_tau)}, μ={direct_mean*100:.1f}% | OSP n={len(osp_tau)}, μ={osp_mean*100:.1f}%")

    # Column titles (top row only)
    axes[0, 0].set_title('Second-Price Auction', fontweight='bold', fontsize=13, pad=10)
    axes[0, 1].set_title('Deferred Acceptance', fontweight='bold', fontsize=13, pad=10)

    # X-axis labels (bottom row only)
    axes[-1, 0].set_xlabel('bid − value', fontsize=11)
    axes[-1, 1].set_xlabel('Kendall τ (% pairs wrong)', fontsize=11)

    # ─────────────────────────────────────────────────────────────────────────
    # LEGEND
    # ─────────────────────────────────────────────────────────────────────────
    # Create a multi-colored patch for OSP mechanism
    from matplotlib.patches import Rectangle
    from matplotlib.collections import PatchCollection

    class MultiColorPatch:
        """Custom handler to create a multi-colored legend patch."""
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
            return patches[0] if patches else None

    osp_colors = [MODEL_COLORS[m] for m in MODEL_ORDER]
    multi_patch = MultiColorPatch()

    legend_elements = [
        mpatches.Patch(facecolor=BASELINE_COLOR, alpha=0.5, edgecolor='#333333',
                      linewidth=0.6, label='Base Mechanism (SPSB / Full Report)'),
        (multi_patch, 'OSP Mechanism (AC / Iterative)'),
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=2,
                  label='Mean'),
    ]

    # Separate handles and labels for custom handler
    handles = [legend_elements[0], multi_patch, legend_elements[2]]
    labels = ['Base Mechanism (SPSB / Full Report)', 'OSP Mechanism (AC / Iterative)', 'Mean']

    fig.legend(handles, labels, loc='lower center', ncol=3,
              frameon=True, framealpha=0.95, edgecolor='#cccccc',
              bbox_to_anchor=(0.5, -0.01), fontsize=9,
              handler_map={MultiColorPatch: MultiColorHandler(osp_colors)})

    # Main title
    fig.suptitle('Comparing Base vs. OSP Mechanisms across Models',
                fontweight='bold', fontsize=14, y=1.01)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08, hspace=0.3)

    output_path = OUTPUT_DIR / 'osp_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"\n✓ Saved: {output_path}")


if __name__ == '__main__':
    plot_osp_comparison()

"""
Generate beautiful SMAD comparison figure across ALL auction types.
Horizontal bar chart with human baseline comparisons.

Order:
1. First-Price IPV
2. Second-Price IPV
3. Third-Price IPV
4. SPSB APV
5. Ascending Clock APV
6. First-Price CV
7. Second-Price CV (English)

Model order: GPT-5-mini, Gemini, GPT-4o, Claude Sonnet, Llama
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'papers' / 'figures'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ROBUSTNESS_DIR = PROJECT_ROOT / 'robustness_logs' / 'V10'
EXPERIMENT_DIR = PROJECT_ROOT / 'experiment_logs_with_explanation' / 'V10'
GPT4O_V10_DIR = PROJECT_ROOT / 'experiment_logs_gpt_4o' / 'V10'

# Human SMAD data from moment matching
HUMAN_SMAD = {
    'First-Price IPV': 14.09,      # Kagel-Levin 1993, n=5
    'Second-Price IPV': 18.30,     # Kagel-Levin 1993, n=5 (or Li 2017: 9.26)
    'Third-Price IPV': 9.33,       # Kagel-Levin 1993, n=5
    'SPSB APV': 9.26,              # Li 2017 2P
    'Ascending Clock APV': 7.33,   # Li 2017 AC
    'First-Price CV': None,        # Different metric (profit-based)
    'Second-Price CV': None,       # Different metric (profit-based)
}

# Auction configurations
AUCTION_ORDER = [
    'First-Price IPV',
    'Second-Price IPV',
    'Third-Price IPV',
    'SPSB APV',
    'Ascending Clock APV',
    'First-Price CV',
    'Second-Price CV',
]

# Model order as specified
MODEL_ORDER = ['GPT-5-mini', 'Gemini', 'GPT-4o', 'Claude Sonnet', 'Llama']

# Beautiful color palette
MODEL_COLORS = {
    'GPT-5-mini': '#2ecc71',      # Green
    'Gemini': '#3498db',          # Blue
    'GPT-4o': '#e74c3c',          # Red
    'Claude Sonnet': '#9b59b6',   # Purple
    'Llama': '#f39c12',           # Orange
    'Human': '#34495e',           # Dark gray
}

# Mapping from auction name to directory patterns
AUCTION_TO_DIR = {
    'First-Price IPV': ('fpsb_ipv', 2/3, 3),
    'Second-Price IPV': ('spsb_ipv', 1.0, 3),
    'Third-Price IPV': ('third_price_ipv', 2.0, 3),
    'SPSB APV': ('spsb_apv', 1.0, 4),
    'Ascending Clock APV': ('ascending_clock_apv', 1.0, 4),
    'First-Price CV': ('common_value_first', None, 4),
    'Second-Price CV': ('common_value_second', None, 4),
}

# Model suffixes in robustness logs
MODEL_SUFFIX = {
    'GPT-5-mini': 'gpt5mini',
    'Gemini': 'gemini',
    'Claude Sonnet': 'claude_sonnet',
    'Llama': 'llama',
}


def load_csv_from_dir(base_dir: Path) -> Optional[pd.DataFrame]:
    """Load all CSV files from a directory."""
    if not base_dir.exists():
        return None

    csv_files = list(base_dir.rglob("*_results.csv"))
    if not csv_files:
        return None

    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception:
            continue

    return pd.concat(dfs, ignore_index=True) if dfs else None


def compute_smad(df: pd.DataFrame, optimal_ratio: Optional[float]) -> Tuple[float, float, int]:
    """Compute SMAD and mean ratio."""
    if df is None or len(df) == 0:
        return np.nan, np.nan, 0

    values = pd.to_numeric(df['player_value'], errors='coerce').dropna().values
    bids = pd.to_numeric(df['bid'], errors='coerce').dropna().values

    min_len = min(len(values), len(bids))
    values = values[:min_len]
    bids = bids[:min_len]

    # Filter valid
    valid = values > 0.1
    values = values[valid]
    bids = bids[valid]

    if len(values) == 0:
        return np.nan, np.nan, 0

    mean_ratio = np.mean(bids / values)

    if optimal_ratio is not None:
        optimal_bids = values * optimal_ratio
        mean_optimal = np.mean(optimal_bids)
        smad = 100 * np.mean(np.abs(bids - optimal_bids)) / mean_optimal if mean_optimal > 0 else np.nan
    else:
        smad = np.nan

    return smad, mean_ratio, len(values)


def collect_all_data() -> pd.DataFrame:
    """Collect SMAD for all auction types and models."""
    results = []

    for auction_name in AUCTION_ORDER:
        dir_pattern, optimal_ratio, n_bidders = AUCTION_TO_DIR[auction_name]
        print(f"\n{auction_name}:")

        for model in MODEL_ORDER:
            df = None

            if model == 'GPT-4o':
                # GPT-4o data is in experiment_logs_with_explanation for baseline auctions
                # and experiment_logs_gpt_4o for interventions
                if auction_name in ['First-Price IPV', 'Second-Price IPV', 'Third-Price IPV',
                                    'SPSB APV', 'Ascending Clock APV']:
                    # Try experiment_logs_with_explanation first (this is GPT-4o default)
                    df = load_csv_from_dir(EXPERIMENT_DIR / dir_pattern)
                elif auction_name in ['First-Price CV', 'Second-Price CV']:
                    df = load_csv_from_dir(EXPERIMENT_DIR / dir_pattern)
            else:
                # Other models are in robustness_logs
                suffix = MODEL_SUFFIX.get(model)
                if suffix:
                    df = load_csv_from_dir(ROBUSTNESS_DIR / f"{dir_pattern}_{suffix}")

            if df is not None and len(df) > 0:
                smad, ratio, n = compute_smad(df, optimal_ratio)
                print(f"  {model}: N={n}, Ratio={ratio:.3f}, SMAD={smad:.1f}%" if not np.isnan(smad) else f"  {model}: N={n}, Ratio={ratio:.3f}")
                results.append({
                    'Auction': auction_name,
                    'Model': model,
                    'N': n,
                    'Mean_Ratio': ratio,
                    'Optimal_Ratio': optimal_ratio,
                    'SMAD': smad,
                })
            else:
                print(f"  {model}: No data")

    return pd.DataFrame(results)


def plot_smad_horizontal(df: pd.DataFrame):
    """Create beautiful horizontal bar chart."""

    # Filter valid SMAD
    df_valid = df[df['SMAD'].notna()].copy()

    # Setup figure
    fig, ax = plt.subplots(figsize=(14, 10))

    # Get auctions that have data
    auctions_with_data = [a for a in AUCTION_ORDER if a in df_valid['Auction'].values]
    n_auctions = len(auctions_with_data)

    # Bar settings
    bar_height = 0.12
    n_models = len(MODEL_ORDER)
    group_height = (n_models + 1) * bar_height + 0.15  # Extra space for human

    y_positions = np.arange(n_auctions) * group_height

    # Plot each model
    for i, model in enumerate(MODEL_ORDER):
        model_data = df_valid[df_valid['Model'] == model]

        smad_vals = []
        for auction in auctions_with_data:
            row = model_data[model_data['Auction'] == auction]
            smad_vals.append(row['SMAD'].values[0] if len(row) > 0 else 0)

        offset = (i - n_models/2) * bar_height
        color = MODEL_COLORS[model]

        bars = ax.barh(y_positions + offset, smad_vals, bar_height,
                       label=model, color=color, edgecolor='white', linewidth=0.5,
                       alpha=0.9)

        # Add value labels
        for bar, val in zip(bars, smad_vals):
            if val > 0:
                ax.text(val + 0.8, bar.get_y() + bar.get_height()/2,
                       f'{val:.1f}', va='center', fontsize=8, fontweight='bold')

    # Plot human baseline as markers
    human_y = []
    human_x = []
    for idx, auction in enumerate(auctions_with_data):
        if HUMAN_SMAD.get(auction) is not None:
            human_y.append(y_positions[idx] + (n_models/2 + 0.5) * bar_height)
            human_x.append(HUMAN_SMAD[auction])

    if human_x:
        ax.scatter(human_x, human_y, marker='D', s=100, c=MODEL_COLORS['Human'],
                  edgecolors='white', linewidths=1.5, zorder=5, label='Human')
        for x, y in zip(human_x, human_y):
            ax.text(x + 0.8, y, f'{x:.1f}', va='center', fontsize=8,
                   fontweight='bold', color=MODEL_COLORS['Human'])

    # Formatting
    ax.set_yticks(y_positions)
    ax.set_yticklabels(auctions_with_data, fontsize=12, fontweight='bold')
    ax.set_xlabel('SMAD (%) — Lower is Better', fontsize=13, fontweight='bold')
    ax.set_title('Scaled Mean Absolute Deviation (SMAD) by Auction Type\nComparing LLM Models to Human Baselines',
                fontsize=15, fontweight='bold', pad=20)

    # Add environment labels
    env_labels = {
        'First-Price IPV': 'IPV',
        'Second-Price IPV': 'IPV',
        'Third-Price IPV': 'IPV',
        'SPSB APV': 'APV',
        'Ascending Clock APV': 'APV',
        'First-Price CV': 'CV',
        'Second-Price CV': 'CV',
    }

    env_colors = {'IPV': '#e8f4f8', 'APV': '#f8f4e8', 'CV': '#f4e8f8'}

    # Draw environment background bands
    current_env = None
    band_start = -0.5
    for idx, auction in enumerate(auctions_with_data):
        env = env_labels[auction]
        if env != current_env:
            if current_env is not None:
                ax.axhspan(band_start, y_positions[idx] - group_height/2,
                          alpha=0.2, color=env_colors[current_env], zorder=0)
            current_env = env
            band_start = y_positions[idx] - group_height/2 if idx > 0 else -group_height/2

    # Final band
    ax.axhspan(band_start, y_positions[-1] + group_height/2,
              alpha=0.2, color=env_colors[current_env], zorder=0)

    # Add env text on right
    xlim = ax.get_xlim()
    for idx, auction in enumerate(auctions_with_data):
        env = env_labels[auction]
        ax.text(xlim[1] * 1.02, y_positions[idx], env,
               va='center', ha='left', fontsize=10, fontweight='bold',
               color='#666666')

    # Legend
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc='lower right', fontsize=10,
             framealpha=0.95, edgecolor='gray', title='Model/Source',
             title_fontsize=11)

    # Grid and styling
    ax.xaxis.grid(True, alpha=0.3, linestyle='-')
    ax.set_axisbelow(True)
    ax.axvline(x=0, color='#2ecc71', linestyle='-', linewidth=2, alpha=0.7)

    # Expand x limit for labels
    ax.set_xlim(-2, xlim[1] * 1.15)

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'smad_all_auctions_beautiful.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight', facecolor='white')
    print(f"\nSaved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def plot_grouped_comparison(df: pd.DataFrame):
    """Alternative: cleaner grouped bar chart."""

    df_valid = df[df['SMAD'].notna()].copy()

    # Use all auctions in order (show all even if some models missing)
    auctions_with_data = [a for a in AUCTION_ORDER if a in df_valid['Auction'].values or HUMAN_SMAD.get(a) is not None]

    fig, ax = plt.subplots(figsize=(16, 8))

    n_auctions = len(auctions_with_data)
    n_models = len(MODEL_ORDER) + 1  # +1 for human
    bar_width = 0.8 / n_models

    x = np.arange(n_auctions)

    # Plot models
    for i, model in enumerate(MODEL_ORDER):
        model_data = df_valid[df_valid['Model'] == model]
        smad_vals = []
        for auction in auctions_with_data:
            row = model_data[model_data['Auction'] == auction]
            smad_vals.append(row['SMAD'].values[0] if len(row) > 0 else 0)

        offset = (i - n_models/2 + 0.5) * bar_width
        bars = ax.bar(x + offset, smad_vals, bar_width,
                     label=model, color=MODEL_COLORS[model],
                     edgecolor='white', linewidth=0.5)

        # Value labels
        for bar, val in zip(bars, smad_vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, val + 1,
                       f'{val:.0f}', ha='center', va='bottom', fontsize=7,
                       fontweight='bold', rotation=0)

    # Plot human as separate bars
    human_vals = [HUMAN_SMAD.get(a, 0) or 0 for a in auctions_with_data]
    offset = (n_models - 1 - n_models/2 + 0.5) * bar_width
    bars = ax.bar(x + offset, human_vals, bar_width,
                 label='Human', color=MODEL_COLORS['Human'],
                 edgecolor='white', linewidth=0.5, hatch='///')

    for bar, val in zip(bars, human_vals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, val + 1,
                   f'{val:.0f}', ha='center', va='bottom', fontsize=7,
                   fontweight='bold', rotation=0)

    # Formatting
    ax.set_xticks(x)
    ax.set_xticklabels([a.replace(' IPV', '\n(IPV)').replace(' APV', '\n(APV)').replace(' CV', '\n(CV)')
                        for a in auctions_with_data], fontsize=10, fontweight='bold')
    ax.set_ylabel('SMAD (%) — Lower is Better', fontsize=12, fontweight='bold')
    ax.set_title('SMAD Comparison: LLMs vs Humans Across Auction Types',
                fontsize=14, fontweight='bold', pad=15)

    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    output_path = OUTPUT_DIR / 'smad_all_auctions_grouped.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_path}")

    plt.close()


def main():
    print("="*70)
    print("SMAD ALL AUCTIONS - COMPREHENSIVE PLOT")
    print("="*70)

    df = collect_all_data()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if len(df) > 0:
        pivot = df.pivot_table(index='Auction', columns='Model', values='SMAD')
        pivot = pivot.reindex(columns=MODEL_ORDER)
        pivot = pivot.reindex([a for a in AUCTION_ORDER if a in pivot.index])
        print("\nSMAD by Auction and Model:")
        print(pivot.round(1).to_string())

        # Add human column
        print("\nHuman baselines:")
        for auction, smad in HUMAN_SMAD.items():
            if smad is not None:
                print(f"  {auction}: {smad:.1f}%")

    print("\n" + "="*70)
    print("Generating plots...")
    print("="*70)

    plot_smad_horizontal(df)
    plot_grouped_comparison(df)

    # Save data
    df.to_csv(OUTPUT_DIR / 'smad_all_auctions_v2_data.csv', index=False)

    print("\n" + "="*70)
    print("COMPLETE!")
    print("="*70)


if __name__ == '__main__':
    main()

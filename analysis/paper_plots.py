"""
Generate plots for the two auction papers:
1. Engineering Complexity (OSP/behavioral interventions)
2. LLMs as Auction Players (benchmark paper)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['figure.figsize'] = (10, 6)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / 'results' / 'v12_interventions'
OUTPUT_DIR = PROJECT_ROOT / 'papers' / 'figures'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load all relevant CSV data."""
    data = {}

    # Model comparison
    model_file = RESULTS_DIR / 'model_comparison' / 'model_comparison_summary.csv'
    if model_file.exists():
        data['model_comparison'] = pd.read_csv(model_file)

    # Intervention rankings
    rankings_file = RESULTS_DIR / 'intervention_rankings.csv'
    if rankings_file.exists():
        data['rankings'] = pd.read_csv(rankings_file)

    # Bid vs value summary
    bvv_file = RESULTS_DIR / 'bid_vs_value' / 'bid_vs_value_summary.csv'
    if bvv_file.exists():
        data['bid_vs_value'] = pd.read_csv(bvv_file)

    # Claude comparison
    claude_file = RESULTS_DIR / 'claude_comparison' / 'claude_all_auctions_summary.csv'
    if claude_file.exists():
        data['claude'] = pd.read_csv(claude_file)

    # Human vs LLM
    human_file = RESULTS_DIR / 'moment_matching' / 'human_vs_llm_comparison.csv'
    if human_file.exists():
        data['human_vs_llm'] = pd.read_csv(human_file)

    # Kagel-Levin 1993
    kl93_file = RESULTS_DIR / 'moment_matching' / 'kagel_levin_1993_moment_matching.csv'
    if kl93_file.exists():
        data['kl93'] = pd.read_csv(kl93_file)

    # Li 2017 OSP
    li17_file = RESULTS_DIR / 'moment_matching' / 'li_2017_osp_moment_matching.csv'
    if li17_file.exists():
        data['li17'] = pd.read_csv(li17_file)

    # Breitmoser 2022
    breit_file = RESULTS_DIR / 'moment_matching' / 'breitmoser_2022_clock_moment_matching.csv'
    if breit_file.exists():
        data['breitmoser'] = pd.read_csv(breit_file)

    return data


def plot_model_comparison_bar(data):
    """Bar chart comparing models across auction types."""
    if 'model_comparison' not in data:
        print("No model comparison data")
        return

    df = data['model_comparison']
    df = df[df['N'] > 0]  # Filter out empty rows

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    auctions = ['First-Price IPV', 'Second-Price IPV', 'Third-Price IPV']
    optimal_ratios = [0.667, 1.0, 2.0]
    titles = ['First-Price (FPSB)', 'Second-Price (SPSB)', 'Third-Price (TPSB)']

    for idx, (auction, opt, title) in enumerate(zip(auctions, optimal_ratios, titles)):
        ax = axes[idx]
        subset = df[df['Auction'] == auction].copy()

        if len(subset) == 0:
            continue

        # Sort by distance from optimal
        subset['abs_distance'] = np.abs(subset['Mean_Bid_Ratio'] - opt)
        subset = subset.sort_values('abs_distance')

        colors = ['#2ecc71' if d < 0.05 else '#3498db' if d < 0.2 else '#e74c3c'
                  for d in subset['abs_distance']]

        bars = ax.barh(subset['Model'], subset['Mean_Bid_Ratio'], color=colors, edgecolor='black')
        ax.axvline(x=opt, color='red', linestyle='--', linewidth=2, label=f'Optimal = {opt:.2f}')

        ax.set_xlabel('Mean Bid/Value Ratio')
        ax.set_title(title)
        ax.legend(loc='best')

        # Add value labels
        for bar, val in zip(bars, subset['Mean_Bid_Ratio']):
            ax.text(val + 0.02, bar.get_y() + bar.get_height()/2,
                   f'{val:.3f}', va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'model_comparison_bar.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(OUTPUT_DIR / 'model_comparison_bar.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: model_comparison_bar.pdf/png")


def plot_intervention_heatmap(data):
    """Heatmap of intervention effects by axis and auction type."""
    if 'bid_vs_value' not in data:
        print("No bid vs value data")
        return

    df = data['bid_vs_value']

    # Pivot for FPSB
    fpsb = df[df['Auction'] == 'FPSB'].copy()
    spsb_data = data.get('claude', pd.DataFrame())

    if len(spsb_data) > 0:
        spsb = spsb_data[spsb_data['Auction'] == 'SPSB'].copy()
    else:
        spsb = pd.DataFrame()

    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    # FPSB heatmap
    if len(fpsb) > 0:
        pivot_fpsb = fpsb.pivot_table(
            values='Distance_from_Optimal',
            index='Intervention',
            columns='Axis',
            aggfunc='mean'
        )

        ax = axes[0]
        sns.heatmap(pivot_fpsb, annot=True, fmt='.3f', cmap='RdYlGn_r',
                   ax=ax, cbar_kws={'label': 'Distance from Optimal'})
        ax.set_title('FPSB: Distance from Optimal by Intervention')
        ax.set_xlabel('')
        ax.set_ylabel('Intervention')

    # SPSB from Claude data
    if len(spsb) > 0:
        # Calculate distance (optimal = 1.0)
        spsb['Distance'] = np.abs(spsb['Mean_Ratio'] - 1.0)

        pivot_spsb = spsb.pivot_table(
            values='Distance',
            index='Intervention',
            columns='Axis',
            aggfunc='mean'
        )

        ax = axes[1]
        sns.heatmap(pivot_spsb, annot=True, fmt='.3f', cmap='RdYlGn_r',
                   ax=ax, cbar_kws={'label': 'Distance from Optimal'})
        ax.set_title('SPSB: Distance from Optimal by Intervention')
        ax.set_xlabel('')
        ax.set_ylabel('')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'intervention_heatmap.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(OUTPUT_DIR / 'intervention_heatmap.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: intervention_heatmap.pdf/png")


def plot_human_vs_llm_comparison(data):
    """Compare human and LLM bidding behavior."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    # Data from papers and our results
    human_data = {
        'FPSB': {'ratio': 0.815, 'optimal': 0.80, 'source': 'Kagel-Levin 1993'},
        'SPSB': {'ratio': 1.038, 'optimal': 1.00, 'source': 'Li 2017'},
        'TPSB': {'ratio': 1.545, 'optimal': 1.33, 'source': 'Kagel-Levin 1993'},
    }

    llm_data = {
        'FPSB': {'ratio': 0.879, 'optimal': 0.667},
        'SPSB': {'ratio': 0.829, 'optimal': 1.00},
        'TPSB': {'ratio': 0.829, 'optimal': 2.00},
    }

    auctions = ['FPSB', 'SPSB', 'TPSB']
    titles = ['First-Price', 'Second-Price', 'Third-Price']

    for idx, (auction, title) in enumerate(zip(auctions, titles)):
        ax = axes[idx]

        h = human_data[auction]
        l = llm_data[auction]

        x = [0, 1]
        heights = [h['ratio'], l['ratio']]
        colors = ['#3498db', '#e74c3c']
        labels = ['Human', 'LLM']

        bars = ax.bar(x, heights, color=colors, edgecolor='black', width=0.6)

        # Optimal line
        ax.axhline(y=l['optimal'], color='green', linestyle='--', linewidth=2,
                  label=f'Optimal = {l["optimal"]:.2f}')

        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel('Mean Bid/Value Ratio')
        ax.set_title(f'{title}\n(Human: {h["source"]})')
        ax.legend(loc='best')

        # Add value labels
        for bar, val in zip(bars, heights):
            ax.text(bar.get_x() + bar.get_width()/2, val + 0.02,
                   f'{val:.3f}', ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'human_vs_llm_comparison.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(OUTPUT_DIR / 'human_vs_llm_comparison.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: human_vs_llm_comparison.pdf/png")


def plot_osp_effect_comparison(data):
    """Compare OSP intervention effects for humans vs LLMs."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Data from papers
    categories = ['Human\n(2P)', 'Human\n(AC)', 'LLM\n(Baseline)', 'LLM\n(Decision Tree)']
    smad_values = [9.3, 7.3, 12.7, 3.3]
    colors = ['#3498db', '#2ecc71', '#e74c3c', '#27ae60']

    bars = ax.bar(categories, smad_values, color=colors, edgecolor='black', width=0.6)

    # Add value labels
    for bar, val in zip(bars, smad_values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.3,
               f'{val:.1f}%', ha='center', fontsize=11, fontweight='bold')

    ax.set_ylabel('SMAD (%)', fontsize=12)
    ax.set_title('OSP Effect: SMAD Reduction in Second-Price Auctions', fontsize=13)

    # Add annotations
    ax.annotate('', xy=(1, 7.3), xytext=(0, 9.3),
               arrowprops=dict(arrowstyle='->', color='gray', lw=2))
    ax.text(0.5, 10.5, 'Human OSP\nEffect: -21%', ha='center', fontsize=9)

    ax.annotate('', xy=(3, 3.3), xytext=(2, 12.7),
               arrowprops=dict(arrowstyle='->', color='gray', lw=2))
    ax.text(2.5, 14, 'LLM OSP\nEffect: -74%', ha='center', fontsize=9)

    ax.set_ylim(0, 16)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'osp_effect_comparison.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(OUTPUT_DIR / 'osp_effect_comparison.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: osp_effect_comparison.pdf/png")


def plot_intervention_by_axis(data):
    """Grouped bar chart showing best intervention per axis for SPSB."""
    if 'rankings' not in data:
        print("No rankings data")
        return

    df = data['rankings']
    df = df[~df['Is_Baseline']]  # Remove baseline

    fig, ax = plt.subplots(figsize=(12, 6))

    # Group by axis and get best (lowest distance)
    axes_order = ['Contingent Reasoning', 'Forward Planning', 'Higher-Order Beliefs', 'Loss Aversion']

    # Get all interventions with their axis
    plot_data = []
    for axis in axes_order:
        subset = df[df['Axis'] == axis].nsmallest(3, 'Distance_from_Optimal')
        for _, row in subset.iterrows():
            plot_data.append({
                'Axis': axis.replace(' ', '\n'),
                'Intervention': row['Intervention'],
                'Distance': row['Distance_from_Optimal'],
                'Ratio': row['Mean_Bid_Ratio']
            })

    plot_df = pd.DataFrame(plot_data)

    # Color by axis
    axis_colors = {
        'Contingent\nReasoning': '#e74c3c',
        'Forward\nPlanning': '#2ecc71',
        'Higher-Order\nBeliefs': '#3498db',
        'Loss\nAversion': '#9b59b6'
    }

    x = np.arange(len(plot_df))
    bars = ax.bar(x, plot_df['Ratio'],
                  color=[axis_colors.get(a, '#95a5a6') for a in plot_df['Axis']],
                  edgecolor='black')

    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='Optimal = 1.0')
    ax.axhline(y=0.829, color='orange', linestyle=':', linewidth=2, label='Baseline = 0.829')

    ax.set_xticks(x)
    ax.set_xticklabels([f"{row['Intervention']}\n({row['Axis']})"
                        for _, row in plot_df.iterrows()],
                       rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Mean Bid/Value Ratio (SPSB)')
    ax.set_title('Top 3 Interventions per Cognitive Axis (SPSB)')
    ax.legend(loc='upper right')
    ax.set_ylim(0.7, 1.1)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'intervention_by_axis.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(OUTPUT_DIR / 'intervention_by_axis.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: intervention_by_axis.pdf/png")


def plot_smad_comparison_table(data):
    """Create a visual table comparing SMAD across sources."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('off')

    # Data
    table_data = [
        ['Source', 'Auction', 'n', 'Mean Ratio', 'Optimal', 'SMAD'],
        ['', '', '', '', '', ''],
        ['\\textbf{Human Data}', '', '', '', '', ''],
        ['Kagel-Levin 1993', 'FPSB', '5', '0.815', '0.80', '14.1'],
        ['Kagel-Levin 1993', 'SPSB', '5', '1.377', '1.00', '18.3'],
        ['Kagel-Levin 1993', 'TPSB', '5', '1.545', '1.33', '9.3'],
        ['Li 2017', 'SPSB (2P)', '4', '1.038', '1.00', '9.3'],
        ['Li 2017', 'SPSB (AC)', '4', '0.999', '1.00', '7.3'],
        ['Breitmoser 2022', 'SPSB (2P)', '4', '1.044', '1.00', '10.0'],
        ['Breitmoser 2022', 'SPSB (AC)', '4', '1.001', '1.00', '3.0'],
        ['', '', '', '', '', ''],
        ['\\textbf{LLM Data}', '', '', '', '', ''],
        ['GPT-5-mini', 'FPSB', '3', '0.667', '0.667', '0.1'],
        ['GPT-5-mini', 'SPSB', '3', '0.996', '1.00', '0.2'],
        ['Claude Sonnet', 'FPSB', '3', '0.899', '0.667', '35.2'],
        ['Claude Sonnet', 'SPSB', '3', '0.829', '1.00', '12.7'],
        ['Claude + Decision Tree', 'SPSB', '3', '0.967', '1.00', '3.3'],
    ]

    # Create table
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    # Style header
    for j in range(6):
        table[(0, j)].set_facecolor('#34495e')
        table[(0, j)].set_text_props(color='white', fontweight='bold')

    # Style section headers
    for i in [2, 11]:
        for j in range(6):
            table[(i, j)].set_facecolor('#ecf0f1')

    plt.title('SMAD Comparison: Human vs LLM Bidding', fontsize=14, fontweight='bold', pad=20)

    plt.savefig(OUTPUT_DIR / 'smad_comparison_table.pdf', bbox_inches='tight', dpi=300)
    plt.savefig(OUTPUT_DIR / 'smad_comparison_table.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: smad_comparison_table.pdf/png")


def main():
    """Generate all paper plots."""
    print("Loading data...")
    data = load_data()
    print(f"Loaded: {list(data.keys())}")

    print("\nGenerating plots...")

    plot_model_comparison_bar(data)
    plot_intervention_heatmap(data)
    plot_human_vs_llm_comparison(data)
    plot_osp_effect_comparison(data)
    plot_intervention_by_axis(data)
    plot_smad_comparison_table(data)

    print(f"\nAll plots saved to: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()

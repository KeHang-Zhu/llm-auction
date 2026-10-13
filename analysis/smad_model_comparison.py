"""
Generate SMAD comparison figure across all auction types and models.
Creates a grouped bar chart showing SMAD for each model across FP, SP, TP auctions.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / 'results' / 'v12_interventions'
OUTPUT_DIR = PROJECT_ROOT / 'papers' / 'figures'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_model_comparison_data():
    """Load model comparison data from CSV."""
    csv_path = RESULTS_DIR / 'model_comparison' / 'model_comparison_summary.csv'
    if csv_path.exists():
        return pd.read_csv(csv_path)
    else:
        print(f"File not found: {csv_path}")
        return None


def plot_smad_grouped_bar(df):
    """Create grouped bar chart of SMAD across models and auction types."""

    # Filter out rows with no data
    df = df[df['N'] > 0].copy()

    # Rename auctions for cleaner labels
    auction_map = {
        'First-Price IPV': 'FPSB',
        'Second-Price IPV': 'SPSB',
        'Third-Price IPV': 'TPSB'
    }
    df['Auction_Short'] = df['Auction'].map(auction_map)

    # Get unique models and auctions
    models = df['Model'].unique()
    auctions = ['FPSB', 'SPSB', 'TPSB']

    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Bar width and positions
    n_models = len(models)
    n_auctions = len(auctions)
    bar_width = 0.2

    # X positions for auction groups
    x = np.arange(n_auctions)

    # Color palette
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12']

    # Plot bars for each model
    for i, model in enumerate(models):
        model_data = df[df['Model'] == model]
        smad_values = []

        for auction in auctions:
            row = model_data[model_data['Auction_Short'] == auction]
            if len(row) > 0:
                smad_values.append(row['SMAD'].values[0])
            else:
                smad_values.append(0)

        offset = (i - n_models/2 + 0.5) * bar_width
        bars = ax.bar(x + offset, smad_values, bar_width,
                     label=model, color=colors[i % len(colors)],
                     edgecolor='black', linewidth=0.5)

        # Add value labels on bars
        for bar, val in zip(bars, smad_values):
            if val > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{val:.1f}',
                       ha='center', va='bottom', fontsize=8, rotation=0)

    # Formatting
    ax.set_xlabel('Auction Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('SMAD (%)', fontsize=12, fontweight='bold')
    ax.set_title('Scaled Mean Absolute Deviation (SMAD) by Model and Auction Type\n(Lower is Better)',
                fontsize=14, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(auctions, fontsize=11)
    ax.legend(title='Model', loc='upper right', fontsize=10)

    # Add optimal reference line at 0
    ax.axhline(y=0, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Optimal')

    # Grid
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Set y-axis limit
    ax.set_ylim(0, max(df['SMAD'].max() * 1.15, 90))

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'smad_model_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"Saved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def plot_smad_heatmap(df):
    """Create heatmap of SMAD values."""

    # Filter out rows with no data
    df = df[df['N'] > 0].copy()

    # Rename auctions
    auction_map = {
        'First-Price IPV': 'FPSB',
        'Second-Price IPV': 'SPSB',
        'Third-Price IPV': 'TPSB'
    }
    df['Auction_Short'] = df['Auction'].map(auction_map)

    # Pivot for heatmap
    pivot = df.pivot(index='Model', columns='Auction_Short', values='SMAD')
    pivot = pivot[['FPSB', 'SPSB', 'TPSB']]  # Ensure column order

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create heatmap manually with better control
    im = ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto')

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('SMAD (%)', rotation=-90, va="bottom", fontsize=11)

    # Set ticks
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, fontsize=11)
    ax.set_yticklabels(pivot.index, fontsize=11)

    # Add text annotations
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                text_color = 'white' if val > 40 else 'black'
                ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                       color=text_color, fontsize=12, fontweight='bold')

    ax.set_title('SMAD (%) by Model and Auction Type\n(Lower = Closer to Optimal)',
                fontsize=14, fontweight='bold')
    ax.set_xlabel('Auction Type', fontsize=12)
    ax.set_ylabel('Model', fontsize=12)

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'smad_model_heatmap.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"Saved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def plot_smad_by_auction(df):
    """Create separate subplot for each auction type."""

    # Filter out rows with no data
    df = df[df['N'] > 0].copy()

    # Rename auctions
    auction_map = {
        'First-Price IPV': 'FPSB',
        'Second-Price IPV': 'SPSB',
        'Third-Price IPV': 'TPSB'
    }
    df['Auction_Short'] = df['Auction'].map(auction_map)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    auctions = ['FPSB', 'SPSB', 'TPSB']
    optimal_ratios = [0.667, 1.0, 2.0]

    for idx, (auction, opt_ratio) in enumerate(zip(auctions, optimal_ratios)):
        ax = axes[idx]

        subset = df[df['Auction_Short'] == auction].copy()
        subset = subset.sort_values('SMAD')

        # Color based on performance
        colors = ['#2ecc71' if s < 5 else '#f39c12' if s < 20 else '#e74c3c'
                  for s in subset['SMAD']]

        bars = ax.barh(subset['Model'], subset['SMAD'], color=colors, edgecolor='black')

        ax.set_xlabel('SMAD (%)', fontsize=11)
        ax.set_title(f'{auction}\n(Optimal b/v = {opt_ratio:.2f})', fontsize=12, fontweight='bold')

        # Add value labels
        for bar, val in zip(bars, subset['SMAD']):
            ax.text(val + 1, bar.get_y() + bar.get_height()/2,
                   f'{val:.1f}%', va='center', fontsize=10)

        ax.set_xlim(0, max(subset['SMAD'].max() * 1.2, 10))
        ax.grid(axis='x', alpha=0.3)

    plt.suptitle('SMAD by Model for Each Auction Type (Lower is Better)',
                fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'smad_by_auction.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"Saved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def print_summary_table(df):
    """Print summary table of results."""
    df = df[df['N'] > 0].copy()

    print("\n" + "="*70)
    print("SMAD SUMMARY TABLE")
    print("="*70)

    auction_map = {
        'First-Price IPV': 'FPSB',
        'Second-Price IPV': 'SPSB',
        'Third-Price IPV': 'TPSB'
    }
    df['Auction_Short'] = df['Auction'].map(auction_map)

    # Pivot and display
    pivot = df.pivot(index='Model', columns='Auction_Short', values='SMAD')
    pivot = pivot[['FPSB', 'SPSB', 'TPSB']]

    print("\nSMAD (%) by Model and Auction:")
    print(pivot.to_string())

    # Best model per auction
    print("\n" + "-"*40)
    print("Best Model per Auction (lowest SMAD):")
    for auction in ['FPSB', 'SPSB', 'TPSB']:
        best_idx = pivot[auction].idxmin()
        best_val = pivot[auction].min()
        print(f"  {auction}: {best_idx} ({best_val:.2f}%)")


def main():
    """Main execution."""
    print("="*70)
    print("SMAD MODEL COMPARISON PLOTS")
    print("="*70 + "\n")

    # Load data
    df = load_model_comparison_data()
    if df is None:
        return

    print(f"Loaded {len(df)} rows of model comparison data")
    print(f"Models: {df['Model'].unique().tolist()}")
    print(f"Auctions: {df['Auction'].unique().tolist()}")

    # Print summary
    print_summary_table(df)

    # Generate plots
    print("\n" + "="*70)
    print("Generating plots...")
    print("="*70)

    plot_smad_grouped_bar(df)
    plot_smad_heatmap(df)
    plot_smad_by_auction(df)

    print("\n" + "="*70)
    print("COMPLETE!")
    print("="*70)


if __name__ == '__main__':
    main()

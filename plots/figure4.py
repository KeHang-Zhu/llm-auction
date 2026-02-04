"""
Generate vertical distribution plots comparing human and LLM auction data.

Shows distributions of (2nd highest bid - 2nd highest value) / 25,
with rows stacked vertically and mean deviation lines.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Paths
EXPERIMENT_DIR = Path("../experiment_logs/V10")
OUTPUT_DIR = Path("../results/distribution_comparison")

# LLM Experiments
LLM_EXPERIMENTS = {
    "LLM AC": ("ascending_clock_apv", "AC"),
    "LLM 2P": ("spsb_apv", "2P"),
}

# Interventions (all are 2P variants)
INTERVENTIONS = {
    "Menu": "intervention_menu",
    "Proxy": "intervention_proxy_breitmoser",
}


def create_human_data_from_distribution() -> Dict[str, Dict]:
    """
    Create human data based on provided bin percentages.

    Human AC:
    - deviation ≤ -8.7%: 4.3%
    - deviation > -8.7% and ≤ -2.9%: 7.1%
    - deviation > -2.9% and ≤ 2.9%: 70%
    - deviation > 2.9% and ≤ 8.7%: 11.4%
    - deviation > 8.7%: 7.1%

    Human 2P:
    - deviation ≤ -8.7%: 12.9%
    - deviation > -8.7% and ≤ -2.9%: 10%
    - deviation > -2.9% and ≤ 2.9%: 38.6%
    - deviation > 2.9% and ≤ 8.7%: 17.1%
    - deviation > 8.7%: 21.4%

    Note: -8.7% corresponds to -$6/25 = -0.24 (normalized)
          -2.9% corresponds to -$2/25 = -0.08 (normalized)
          2.9% corresponds to $2/25 = 0.08 (normalized)
          8.7% corresponds to $6/25 = 0.24 (normalized)
    """
    # Define bin edges in normalized units
    bin_edges = [-0.5, -0.24, -0.08, 0.08, 0.24, 0.5]

    # Human 2P percentages for each bin
    human_ac_percentages = [4.3, 7.1, 70.0, 11.4, 7.1]

    # Human AC percentages for each bin
    human_2p_percentages = [12.9, 10.0, 38.6, 17.1, 21.4]

    return {
        'Human 2P': {
            'type': 'bins',
            'bin_edges': bin_edges,
            'percentages': human_2p_percentages,
        },
        'Human AC': {
            'type': 'bins',
            'bin_edges': bin_edges,
            'percentages': human_ac_percentages,
        }
    }


def load_experiment_data(exp_dir: Path, exp_name: str) -> pd.DataFrame:
    """Load experiment data from merged file or individual runs."""
    # Try merged file
    merged_file = exp_dir / exp_name / f"{exp_name}_merged_results.csv"
    if merged_file.exists():
        return pd.read_csv(merged_file)

    # Otherwise collect all runs
    dfs = []
    for csv_file in (exp_dir / exp_name).rglob("*_results.csv"):
        if "merged" not in csv_file.name:
            dfs.append(pd.read_csv(csv_file))

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def calculate_2nd_deviation(df: pd.DataFrame) -> np.ndarray:
    """
    Calculate (2nd highest bid - 2nd highest value) / 25 for each auction.
    """
    deviations = []

    # Group by repetition_id (unique identifier for each auction)
    if 'repetition_id' not in df.columns:
        group_by = 'round' if 'round' in df.columns else None
    else:
        group_by = 'repetition_id'

    if group_by is None:
        groups = [(0, df)]
    else:
        groups = df.groupby(group_by)

    for group_id, group_df in groups:
        if len(group_df) < 2:
            continue

        try:
            # Extract and sort values and bids
            values = pd.to_numeric(group_df['player_value'], errors='coerce').dropna().values
            bids = pd.to_numeric(group_df['bid'], errors='coerce').dropna().values

            if len(values) >= 2 and len(bids) >= 2:
                sorted_values = np.sort(values)
                sorted_bids = np.sort(bids)

                # Get 2nd highest
                second_value = sorted_values[-2]
                second_bid = sorted_bids[-2]

                # Normalize and store
                deviation = (second_bid - second_value) / 25.0
                deviations.append(deviation)
        except (KeyError, ValueError):
            continue

    return np.array(deviations)


def load_all_data() -> Tuple[Dict[str, Dict], Dict[str, np.ndarray]]:
    """Load all human and LLM experiment data."""

    print("📊 Loading human experiment data...")
    human_data = create_human_data_from_distribution()
    print(f"  ✓ Human AC: bin-based distribution")
    print(f"  ✓ Human 2P: bin-based distribution")

    print("\n📊 Loading LLM experiment data...")
    llm_data = {}

    # Load main LLM experiments
    for display_name, (exp_name, auction_type) in LLM_EXPERIMENTS.items():
        print(f"  Loading {display_name}...")
        df = load_experiment_data(EXPERIMENT_DIR, exp_name)
        if not df.empty:
            deviations = calculate_2nd_deviation(df)
            if len(deviations) > 0:
                llm_data[display_name] = deviations
                print(f"    ✓ {len(deviations)} auctions")
            else:
                print(f"    ⚠️  No valid data")
        else:
            print(f"    ⚠️  No data found")

    # Load interventions
    print(f"\n  Loading interventions (all 2P variants)...")
    for display_name, exp_name in INTERVENTIONS.items():
        print(f"    {display_name}...", end=" ")
        df = load_experiment_data(EXPERIMENT_DIR, exp_name)
        if not df.empty:
            deviations = calculate_2nd_deviation(df)
            if len(deviations) > 0:
                llm_data[display_name] = deviations
                print(f"✓ {len(deviations)} auctions")
            else:
                print(f"⚠️  No valid data")
        else:
            print(f"⚠️  Not found")

    return human_data, llm_data


def plot_vertical_comparison(human_data: Dict[str, Dict],
                             llm_data: Dict[str, np.ndarray],
                             output_path: Path):
    """Create vertical stacked distribution plots."""

    # Define row order
    row_order = ["Human AC", "Human 2P", "LLM AC", "LLM 2P"]
    row_order.extend(sorted(INTERVENTIONS.keys()))

    # Collect data
    plot_data = []
    plot_labels = []
    plot_types = []  # Track if human or LLM

    for row_name in row_order:
        data = human_data.get(row_name)
        if data is None:
            data = llm_data.get(row_name)

        # Check if data exists
        if data is not None:
            if isinstance(data, dict):  # Human bin-based data
                plot_data.append(data)
                plot_labels.append(row_name)
                plot_types.append("human")
            elif isinstance(data, np.ndarray) and len(data) > 0:  # LLM array data
                plot_data.append(data)
                plot_labels.append(row_name)
                plot_types.append("llm")

    if not plot_data:
        print("❌ No data to plot!")
        return

    # Create figure - vertical layout (n_rows x 1)
    n_rows = len(plot_data)
    fig, axes = plt.subplots(n_rows, 1, figsize=(10, 2.5 * n_rows), sharex=True)

    if n_rows == 1:
        axes = [axes]

    # Define bins
    bins = np.linspace(-0.5, 0.5, 10)

    # Colors matching the original image
    human_color = '#4472C4'  # Blue
    llm_color = '#ED7D31'    # Orange

    for idx, (label, data, dtype) in enumerate(zip(plot_labels, plot_data, plot_types)):
        ax = axes[idx]

        color = human_color if dtype == "human" else llm_color

        if dtype == "human":
            # Human data: bar plot with bin percentages
            bin_edges = data['bin_edges']
            percentages = data['percentages']

            # Calculate bin centers and widths
            bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]
            bin_widths = [bin_edges[i+1] - bin_edges[i] for i in range(len(bin_edges)-1)]

            # Draw bars (outlined with lighter fill)
            ax.bar(bin_centers, percentages, width=bin_widths,
                   alpha=0.3, facecolor=color, edgecolor=color, linewidth=2.5, align='center')

            # No mean line for human data

        else:
            # LLM data: histogram
            # Calculate weights to get percentage density
            weights = 100.0 * np.ones(len(data)) / len(data)

            # LLM: filled (like SP in original image)
            ax.hist(data, bins=bins, weights=weights, alpha=0.7, color=color,
                   edgecolor=color, linewidth=0.8)

            # Mean deviation line (black) - only for LLM
            mean_val = np.mean(data)
            ax.axvline(mean_val, color='black', linestyle='-', linewidth=2, alpha=0.8)

        # Zero line
        ax.axvline(0, color='gray', linestyle='--', linewidth=1, alpha=0.4)

        # Labels
        ax.set_ylabel('Density (%)', fontsize=11, fontweight='bold')
        if idx == n_rows - 1:  # Only label x-axis on bottom plot
            ax.set_xlabel('Deviation', fontsize=12, fontweight='bold')

        # Title on the left side
        title = label.replace("LLM ", "").replace("Intervention ", "")
        ax.text(0.02, 0.95, title,
               transform=ax.transAxes,
               verticalalignment='top',
               horizontalalignment='left',
               fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                        edgecolor='gray', alpha=0.9, linewidth=1))

        # Statistics box on the right (only for LLM)
        if dtype == "llm":
            mean_val = np.mean(data)
            stats_text = ( f'μ={mean_val:.3f}\n'
                         f'σ={np.std(data):.3f}')
            ax.text(0.98, 0.95, stats_text,
                   transform=ax.transAxes,
                   verticalalignment='top',
                   horizontalalignment='right',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                            edgecolor='gray', alpha=0.9, linewidth=0.5),
                   fontsize=9, family='monospace')

        # Grid
        ax.grid(True, alpha=0.15, axis='y')
        ax.set_axisbelow(True)

        # Limits
        ax.set_xlim(-0.48, 0.48)
        ax.set_ylim(0, 100)  # Unified y-axis scale 0-100%

    # Overall title
    fig.suptitle('AC versus 2P: 2nd highest bid - 2nd highest value (normalized)',
                fontsize=15, fontweight='bold', y=0.995)

    # Legend in top right
    from matplotlib.patches import Rectangle
    from matplotlib.lines import Line2D
    legend_elements = [
        Rectangle((0, 0), 1, 1, fc='none', ec=human_color,
                 linewidth=2.5, label='Human'),
        Rectangle((0, 0), 1, 1, fc=llm_color, ec=llm_color,
                 alpha=0.7, linewidth=0.8, label='LLM'),
        Line2D([0], [0], color='black', linewidth=2, label='Mean')
    ]
    fig.legend(handles=legend_elements, loc='upper right',
              bbox_to_anchor=(0.98, 0.99), framealpha=0.95,
              fontsize=10, edgecolor='gray', ncol=1)

    plt.tight_layout(rect=[0, 0, 1, 0.99])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')

    print(f"\n✓ Saved: {output_path}")
    print(f"✓ Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def print_statistics(human_data: Dict[str, Dict],
                     llm_data: Dict[str, np.ndarray]):
    """Print summary statistics."""
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    for name in ["Human AC", "Human 2P"]:
        data = human_data.get(name)
        if data is None:
            continue

        print(f"\n{name}:")
        print(f"  Type: Binned distribution")
        bin_edges = data['bin_edges']
        percentages = data['percentages']
        for i, pct in enumerate(percentages):
            print(f"    Bin [{bin_edges[i]:.3f}, {bin_edges[i+1]:.3f}]: {pct:.1f}%")

    for name in ["LLM AC", "LLM 2P"] + sorted(INTERVENTIONS.keys()):
        data = llm_data.get(name)
        if data is None or len(data) == 0:
            continue

        print(f"\n{name}:")
        print(f"  N:        {len(data):6d}")
        print(f"  Mean:     {np.mean(data):7.4f}")
        print(f"  Std:      {np.std(data):7.4f}")
        print(f"  Median:   {np.median(data):7.4f}")
        print(f"  Min:      {np.min(data):7.4f}")
        print(f"  Max:      {np.max(data):7.4f}")


def main():
    """Main execution."""
    print("="*70)
    print("AUCTION DATA VERTICAL DISTRIBUTION COMPARISON")
    print("="*70 + "\n")

    human_data, llm_data = load_all_data()

    print_statistics(human_data, llm_data)

    print("\n📊 Generating vertical comparison plot...")
    output_path = OUTPUT_DIR / "vertical_distribution_comparison.png"
    plot_vertical_comparison(human_data, llm_data, output_path)

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()

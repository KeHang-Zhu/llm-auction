"""
Generate distribution plots comparing human and LLM auction data.

Shows distributions of (2nd highest bid - 2nd highest value) / 25,
with separate columns for Human AC, Human 2P, and LLM experiments.
"""

from pathlib import Path
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Paths
EXPERIMENT_DIR = Path("experiment_logs_with_explanation/V10")
OUTPUT_DIR = Path("results/distribution_comparison")

# Mapping of experiment types
EXPERIMENTS = {
    "LLM AC": "ascending_clock_apv",
    "LLM 2P": "spsb_ipv",
    "Menu": "intervention_menu",
    "Proxy Breitmoser": "intervention_proxy_breitmoser",
    "Nash Deviation": "intervention_nash_deviation",
    "Wrong Strategy": "intervention_wrong_strategy",
    "Dominant Strategy": "intervention_dominant_strategy",
    "Risk Averse": "intervention_risk_averse",
    "Risk Neutrality": "intervention_risk_neutrality",
    "Risk Seeking": "intervention_risk_seeking",
}


def load_merged_or_all_runs(exp_path: Path, exp_name: str) -> pd.DataFrame:
    """Load merged results or combine all run results."""
    # Try merged file first
    merged_file = exp_path / f"{exp_name}_merged_results.csv"
    if merged_file.exists():
        print(f"    Loading merged file: {merged_file.name}")
        return pd.read_csv(merged_file)

    # Otherwise collect all run results
    dfs = []
    results_files = list(exp_path.rglob("*_results.csv"))
    for csv_file in results_files:
        if "merged" not in csv_file.name:
            dfs.append(pd.read_csv(csv_file))

    if dfs:
        print(f"    Loaded {len(dfs)} run files")
        return pd.concat(dfs, ignore_index=True)

    return pd.DataFrame()


def calculate_2nd_deviation_per_round(df: pd.DataFrame) -> np.ndarray:
    """
    Calculate (2nd highest bid - 2nd highest value) / 25 for each auction round.

    Returns: Array of normalized deviations, one per auction round
    """
    deviations = []

    # Determine grouping column - prioritize repetition_id
    group_col = None
    if 'repetition_id' in df.columns:
        group_col = 'repetition_id'
    elif 'round' in df.columns:
        # Check if round actually varies
        if df['round'].nunique() > 1:
            group_col = 'round'
        else:
            # round is constant, look for other identifiers
            group_col = 'repetition_id' if 'repetition_id' in df.columns else None

    if group_col is None:
        # Fallback: treat entire dataset as one round
        groups = [(0, df)]
    else:
        groups = df.groupby(group_col)

    for group_id, group_df in groups:
        if len(group_df) < 2:
            continue

        # Extract values and bids
        try:
            values = pd.to_numeric(group_df['player_value'], errors='coerce').dropna().values
            bids = pd.to_numeric(group_df['bid'], errors='coerce').dropna().values

            if len(values) >= 2 and len(bids) >= 2:
                # Sort and get 2nd highest
                sorted_values = np.sort(values)
                sorted_bids = np.sort(bids)

                second_value = sorted_values[-2]
                second_bid = sorted_bids[-2]

                # Normalize by 25 and add to list
                deviation = (second_bid - second_value) / 25.0
                deviations.append(deviation)
        except (KeyError, ValueError) as e:
            continue

    return np.array(deviations)


def load_human_data() -> Dict[str, np.ndarray]:
    """
    Load human experiment data.

    Returns dict with 'Human AC' and 'Human 2P' keys.
    Currently returns empty placeholders - user should provide actual human data.
    """
    human_data = {}

    # Placeholder for human data
    # User should replace this with actual human experiment data loading
    # For now, return empty arrays which will be filtered out in plotting
    human_data['Human AC'] = np.array([])
    human_data['Human 2P'] = np.array([])

    print("⚠️  Human data placeholders used. Please provide actual human experiment data.")

    return human_data


def load_all_llm_experiments() -> Dict[str, np.ndarray]:
    """Load all LLM experiment data."""
    llm_data = {}

    for display_name, exp_dir in EXPERIMENTS.items():
        print(f"Loading {display_name}...")
        exp_path = EXPERIMENT_DIR / exp_dir

        if not exp_path.exists():
            print(f"    ⚠️  Directory not found: {exp_path}")
            continue

        df = load_merged_or_all_runs(exp_path, exp_dir)

        if df.empty:
            print(f"    ⚠️  No data found")
            continue

        deviations = calculate_2nd_deviation_per_round(df)

        if len(deviations) > 0:
            llm_data[display_name] = deviations
            print(f"    ✓ Loaded {len(deviations)} auction rounds")
        else:
            print(f"    ⚠️  No valid auction data")

    return llm_data


def plot_distributions(human_data: Dict[str, np.ndarray],
                       llm_data: Dict[str, np.ndarray],
                       output_path: Path):
    """
    Create distribution plots with separate columns.

    Layout: [Human AC] [Human 2P] [LLM AC] [LLM 2P] [Interventions...]
    """
    # Define column order
    column_order = ["Human AC", "Human 2P", "LLM AC", "LLM 2P"]

    # Add interventions in sorted order
    intervention_keys = sorted([k for k in llm_data.keys()
                               if k not in ["LLM AC", "LLM 2P"]])
    column_order.extend(intervention_keys)

    # Collect columns with data
    plot_data = []
    plot_labels = []

    for col_name in column_order:
        data = None
        if col_name in human_data:
            data = human_data[col_name]
        elif col_name in llm_data:
            data = llm_data[col_name]

        if data is not None and len(data) > 0:
            plot_data.append(data)
            plot_labels.append(col_name)

    if not plot_data:
        print("❌ No data to plot!")
        return

    # Create figure
    n_cols = len(plot_data)
    fig, axes = plt.subplots(1, n_cols, figsize=(3.5 * n_cols, 5), sharey=True)

    if n_cols == 1:
        axes = [axes]

    # Define bins based on the image ranges
    # Image shows: < -$6, (-$6, -$2], (-$2, $2], ($2, $6], > $6
    # Normalized by 25: < -0.24, (-0.24, -0.08], (-0.08, 0.08], (0.08, 0.24], > 0.24
    bins = np.linspace(-0.4, 0.4, 40)

    # Colors
    human_color = '#4472C4'  # Blue (matching OSP in image)
    llm_color = '#ED7D31'    # Orange (matching SP in image)

    for idx, (label, data) in enumerate(zip(plot_labels, plot_data)):
        ax = axes[idx]

        # Choose color and alpha
        is_human = "Human" in label
        color = human_color if is_human else llm_color
        alpha = 0.4 if is_human else 0.7
        edgecolor = human_color if is_human else llm_color

        # Plot histogram
        if is_human:
            # Human: outlined (unfilled)
            ax.hist(data, bins=bins, density=True, alpha=0, color=color,
                   edgecolor=edgecolor, linewidth=2, histtype='step')
        else:
            # LLM: filled
            ax.hist(data, bins=bins, density=True, alpha=alpha, color=color,
                   edgecolor=edgecolor, linewidth=0.8)

        # Add vertical line at 0
        ax.axvline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        # Labels
        if idx == 0:
            ax.set_ylabel('Density', fontsize=11)
        ax.set_xlabel('$(b_2 - v_2) / 25$', fontsize=10)

        # Title - wrap if too long
        title_text = label.replace("LLM ", "").replace("Intervention ", "")
        if len(title_text) > 15:
            words = title_text.split()
            if len(words) > 2:
                mid = len(words) // 2
                title_text = ' '.join(words[:mid]) + '\n' + ' '.join(words[mid:])

        ax.set_title(title_text, fontsize=11, fontweight='bold', pad=10)

        # Grid
        ax.grid(True, alpha=0.2, axis='y')
        ax.set_axisbelow(True)

        # Add statistics box
        mean_val = np.mean(data)
        std_val = np.std(data)
        median_val = np.median(data)
        n_val = len(data)

        stats_text = f'n={n_val}\nμ={mean_val:.3f}\nσ={std_val:.3f}'
        ax.text(0.97, 0.97, stats_text,
               transform=ax.transAxes,
               verticalalignment='top',
               horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
               fontsize=8)

        # Set reasonable x-limits
        ax.set_xlim(-0.35, 0.35)

    # Overall title
    fig.suptitle('Auction Comparison: 2nd Highest Bid - 2nd Highest Value (normalized by 25)',
                fontsize=13, fontweight='bold', y=0.98)

    # Add legend in the first subplot
    if len(axes) > 0:
        from matplotlib.patches import Rectangle
        legend_elements = [
            Rectangle((0, 0), 1, 1, fc=human_color, ec=human_color,
                     alpha=0, linewidth=2, label='Human'),
            Rectangle((0, 0), 1, 1, fc=llm_color, ec=llm_color,
                     alpha=0.7, linewidth=0.8, label='LLM')
        ]
        axes[0].legend(handles=legend_elements, loc='upper left',
                      framealpha=0.9, fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot to: {output_path}")

    # Also save as PDF
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ Saved PDF to: {pdf_path}")

    plt.close()


def print_summary_statistics(human_data: Dict[str, np.ndarray],
                             llm_data: Dict[str, np.ndarray]):
    """Print summary statistics for all datasets."""
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    all_data = {**human_data, **llm_data}

    for name, data in sorted(all_data.items()):
        if len(data) == 0:
            continue

        print(f"\n{name}:")
        print(f"  N auctions: {len(data)}")
        print(f"  Mean:       {np.mean(data):.4f}")
        print(f"  Std:        {np.std(data):.4f}")
        print(f"  Median:     {np.median(data):.4f}")
        print(f"  Min:        {np.min(data):.4f}")
        print(f"  Max:        {np.max(data):.4f}")
        print(f"  25th pct:   {np.percentile(data, 25):.4f}")
        print(f"  75th pct:   {np.percentile(data, 75):.4f}")


def main():
    """Main execution function."""
    print("="*70)
    print("AUCTION DATA DISTRIBUTION COMPARISON")
    print("="*70)

    print("\n📊 Loading human experiment data...")
    human_data = load_human_data()

    print("\n📊 Loading LLM experiment data...")
    llm_data = load_all_llm_experiments()

    # Print summary
    print_summary_statistics(human_data, llm_data)

    # Create plot
    print("\n📊 Generating distribution plot...")
    output_path = OUTPUT_DIR / "bid_value_distribution_comparison.png"
    plot_distributions(human_data, llm_data, output_path)

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()

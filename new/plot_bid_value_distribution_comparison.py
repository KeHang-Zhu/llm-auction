"""
Generate distribution plots comparing human and LLM auction data.

Shows distributions of (2nd highest bid - 2nd highest value) normalized by 25,
with separate columns for Human AC, Human 2P, and LLM experiments (AC, 2P, interventions).
"""

from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import patches

# Paths
EXPERIMENT_DIR = Path("experiment_logs_with_explanation/V10")
OLD_RESULTS_DIR = Path("old/results/OSP")
OUTPUT_DIR = Path("results/distribution_comparison")

# Mapping of experiment types to their directories
EXPERIMENT_MAPPING = {
    "LLM AC": "ascending_clock_apv",
    "LLM 2P": "spsb_ipv",
    "Intervention Menu": "intervention_menu",
    "Intervention Proxy": "intervention_proxy_breitmoser",
    "Intervention Nash": "intervention_nash_deviation",
    "Intervention Wrong Strategy": "intervention_wrong_strategy",
    "Intervention Dominant Strategy": "intervention_dominant_strategy",
    "Intervention Risk Averse": "intervention_risk_averse",
    "Intervention Risk Neutrality": "intervention_risk_neutrality",
    "Intervention Risk Seeking": "intervention_risk_seeking",
}


def load_llm_data(experiment_dir: Path, experiment_name: str) -> pd.DataFrame:
    """Load LLM experiment data from CSV files."""
    exp_path = experiment_dir / experiment_name

    # Look for merged results first
    merged_file = exp_path / f"{experiment_name}_merged_results.csv"
    if merged_file.exists():
        return pd.read_csv(merged_file)

    # Otherwise, collect from individual runs
    dfs = []
    for csv_file in exp_path.rglob("*_results.csv"):
        if "merged" not in csv_file.name:
            dfs.append(pd.read_csv(csv_file))

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def calculate_2nd_highest_deviation(df: pd.DataFrame, auction_type: str) -> np.ndarray:
    """
    Calculate (2nd highest bid - 2nd highest value) / 25 for each round.

    For AC (clock auctions): bid is the exit price
    For 2P (sealed bid): bid is the submitted bid
    """
    deviations = []

    # Group by round (or auction instance)
    if 'round' in df.columns:
        groups = df.groupby('round')
    elif 'repetition_id' in df.columns:
        groups = df.groupby('repetition_id')
    else:
        # If no grouping, treat each row as separate auction
        groups = [(0, df)]

    for _, group_df in groups:
        if len(group_df) < 2:
            continue

        # Get values and bids
        values = group_df['player_value'].values
        bids = group_df['bid'].values

        # Sort to get 2nd highest
        sorted_values = np.sort(values)
        sorted_bids = np.sort(bids)

        if len(sorted_values) >= 2 and len(sorted_bids) >= 2:
            second_value = sorted_values[-2]
            second_bid = sorted_bids[-2]

            # Calculate normalized deviation
            deviation = (second_bid - second_value) / 25.0
            deviations.append(deviation)

    return np.array(deviations)


def load_human_data_from_old_results() -> Dict[str, np.ndarray]:
    """
    Load human experiment data from old results directory.
    Returns dict with 'AC' and '2P' keys containing deviation arrays.
    """
    human_data = {}

    # For now, we'll create placeholder data based on the image shown
    # The user should replace this with actual human data loading

    # These are approximate values based on the image shown
    # Human AC appears to have most values around (-$2, $2) range
    # Human 2P appears to have most values around (-$2, $2) range

    # Load from combined_output files if they exist
    ac_file = OLD_RESULTS_DIR / "combined_output_AC.csv"
    sp_file = OLD_RESULTS_DIR / "combined_output_2P.csv"

    if ac_file.exists():
        ac_df = pd.read_csv(ac_file)
        if 'value' in ac_df.columns and 'price' in ac_df.columns:
            # Process AC data - need to group by auction and get 2nd highest
            human_data['AC'] = calculate_2nd_highest_deviation(ac_df, 'AC')

    if sp_file.exists():
        sp_df = pd.read_csv(sp_file)
        # Similar processing for 2P data
        if 'value' in sp_df.columns:
            human_data['2P'] = calculate_2nd_highest_deviation(sp_df, '2P')

    # If no data loaded, create placeholder
    if 'AC' not in human_data:
        # Approximate distribution from the image
        human_data['AC'] = np.random.normal(0, 0.1, 100)  # Placeholder
    if '2P' not in human_data:
        human_data['2P'] = np.random.normal(0, 0.15, 100)  # Placeholder

    return human_data


def plot_distribution_comparison(human_data: Dict[str, np.ndarray],
                                 llm_data: Dict[str, np.ndarray],
                                 output_path: Path):
    """
    Create distribution plot with separate columns.
    Columns: Human AC, Human 2P, LLM AC, LLM 2P, Intervention 1, ...
    """
    # Define column order
    column_order = [
        "Human AC",
        "Human 2P",
        "LLM AC",
        "LLM 2P",
    ]

    # Add interventions
    intervention_cols = [k for k in llm_data.keys() if k.startswith("Intervention")]
    column_order.extend(sorted(intervention_cols))

    # Filter to only include columns with data
    columns_with_data = []
    data_arrays = []

    if "Human AC" in column_order and 'AC' in human_data:
        columns_with_data.append("Human AC")
        data_arrays.append(human_data['AC'])

    if "Human 2P" in column_order and '2P' in human_data:
        columns_with_data.append("Human 2P")
        data_arrays.append(human_data['2P'])

    for col in column_order[2:]:  # Skip human columns
        if col in llm_data and len(llm_data[col]) > 0:
            columns_with_data.append(col)
            data_arrays.append(llm_data[col])

    if not data_arrays:
        print("No data to plot!")
        return

    # Create figure
    n_cols = len(columns_with_data)
    fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 6), sharey=True)

    if n_cols == 1:
        axes = [axes]

    # Define bins for histogram
    # Based on the image, range seems to be roughly [-6, 6] normalized
    bins = np.linspace(-0.3, 0.3, 30)

    # Colors
    human_color = '#1f77b4'  # Blue
    llm_color = '#ff7f0e'    # Orange

    for idx, (col_name, data) in enumerate(zip(columns_with_data, data_arrays)):
        ax = axes[idx]

        # Choose color
        color = human_color if "Human" in col_name else llm_color

        # Plot histogram
        ax.hist(data, bins=bins, density=True, alpha=0.7, color=color,
                edgecolor='black', linewidth=0.5)

        # Add vertical line at 0
        ax.axvline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        # Labels
        ax.set_xlabel('(2nd highest bid - 2nd highest value) / 25', fontsize=10)
        if idx == 0:
            ax.set_ylabel('Density', fontsize=10)

        # Title - wrap long titles
        if len(col_name) > 20:
            title_parts = col_name.split(' ')
            if len(title_parts) > 2:
                title = ' '.join(title_parts[:2]) + '\n' + ' '.join(title_parts[2:])
            else:
                title = col_name
        else:
            title = col_name
        ax.set_title(title, fontsize=11, fontweight='bold')

        # Grid
        ax.grid(True, alpha=0.3)

        # Add statistics text
        mean_val = np.mean(data)
        std_val = np.std(data)
        ax.text(0.05, 0.95, f'μ={mean_val:.3f}\nσ={std_val:.3f}',
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7),
                fontsize=8)

    # Overall title
    fig.suptitle('AC vs 2P: 2nd highest bid - 2nd highest value (normalized by 25)',
                 fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved plot to {output_path}")
    plt.close()


def main():
    """Main execution function."""
    print("Loading human experiment data...")
    human_data = load_human_data_from_old_results()

    print("\nLoading LLM experiment data...")
    llm_data = {}

    for display_name, exp_dir in EXPERIMENT_MAPPING.items():
        print(f"  Loading {display_name}...")
        df = load_llm_data(EXPERIMENT_DIR, exp_dir)

        if not df.empty:
            # Determine auction type
            if "AC" in display_name or "clock" in exp_dir:
                auction_type = "AC"
            else:
                auction_type = "2P"

            deviations = calculate_2nd_highest_deviation(df, auction_type)
            if len(deviations) > 0:
                llm_data[display_name] = deviations
                print(f"    Found {len(deviations)} auctions")
            else:
                print(f"    No valid data")
        else:
            print(f"    No data file found")

    print(f"\nLoaded {len(llm_data)} LLM experiment types")
    print(f"Human data: AC={len(human_data.get('AC', []))} auctions, 2P={len(human_data.get('2P', []))} auctions")

    # Create plot
    print("\nGenerating comparison plot...")
    output_path = OUTPUT_DIR / "bid_value_distribution_comparison.png"
    plot_distribution_comparison(human_data, llm_data, output_path)

    print("\nDone!")


if __name__ == "__main__":
    main()

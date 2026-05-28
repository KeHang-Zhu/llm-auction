"""
Generate distribution plots comparing human and LLM auction data.

Creates side-by-side distribution plots showing (2nd highest bid - 2nd highest value) / 25.
Layout: [Human AC] [Human 2P] [LLM AC] [LLM 2P] [Interventions (all 2P)...]
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Paths
EXPERIMENT_DIR = Path("experiment_logs_with_explanation/V10")
OLD_RESULTS_DIR = Path("old/results/OSP")
OUTPUT_DIR = Path("results/distribution_comparison")

# LLM Experiments
LLM_EXPERIMENTS = {
    "LLM AC": ("ascending_clock_apv", "AC"),
    "LLM 2P": ("spsb_ipv", "2P"),
}

# Interventions (all are 2P variants)
INTERVENTIONS = {
    "Menu": "intervention_menu",
    "Proxy": "intervention_proxy_breitmoser",
    "Nash Dev": "intervention_nash_deviation",
    "Wrong Strat": "intervention_wrong_strategy",
    "Dom Strat": "intervention_dominant_strategy",
    "Risk Averse": "intervention_risk_averse",
    "Risk Neutral": "intervention_risk_neutrality",
    "Risk Seeking": "intervention_risk_seeking",
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

    Groups by repetition_id and calculates the deviation for each auction.
    """
    deviations = []

    # Group by repetition_id (unique identifier for each auction)
    if 'repetition_id' not in df.columns:
        print("    Warning: No repetition_id column, treating as single auction")
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


def load_human_ac_data() -> Optional[np.ndarray]:
    """
    Load human AC auction data.

    Expected format: CSV with columns 'value', 'price', where each row represents
    a bidder's decision at a given price point.
    """
    ac_file = OLD_RESULTS_DIR / "combined_output_AC.csv"
    if not ac_file.exists():
        return None

    try:
        df = pd.read_csv(ac_file)

        # The AC data has format: answer, comment, bidder, value, price
        # We need to identify complete auctions and calculate 2nd highest bid - value

        # This is complex because AC data shows decision points, not final bids
        # For now, return None and user should provide processed data
        return None

    except Exception as e:
        print(f"    Error loading AC data: {e}")
        return None


def load_human_2p_data() -> Optional[np.ndarray]:
    """
    Load human 2P (Second Price) auction data.

    Expected format: CSV with Round, Bidder, Value, Bid columns.
    """
    sp_file = OLD_RESULTS_DIR / "combined_output_2P.csv"
    if not sp_file.exists():
        return None

    try:
        df = pd.read_csv(sp_file)

        if 'Round' not in df.columns or 'Value' not in df.columns or 'Bid' not in df.columns:
            print("    Warning: Missing required columns in 2P data")
            return None

        deviations = []

        # Group by Round
        for round_id, group_df in df.groupby('Round'):
            if len(group_df) < 2:
                continue

            values = pd.to_numeric(group_df['Value'], errors='coerce').dropna().values
            bids = pd.to_numeric(group_df['Bid'], errors='coerce').dropna().values

            if len(values) >= 2 and len(bids) >= 2:
                sorted_values = np.sort(values)
                sorted_bids = np.sort(bids)

                second_value = sorted_values[-2]
                second_bid = sorted_bids[-2]

                deviation = (second_bid - second_value) / 25.0
                deviations.append(deviation)

        return np.array(deviations) if deviations else None

    except Exception as e:
        print(f"    Error loading 2P data: {e}")
        return None


def load_all_data() -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """Load all human and LLM experiment data."""

    print("�� Loading human experiment data...")
    human_data = {}

    # Load human AC
    human_ac = load_human_ac_data()
    if human_ac is not None and len(human_ac) > 0:
        human_data['Human AC'] = human_ac
        print(f"  ✓ Human AC: {len(human_ac)} auctions")
    else:
        print("  ⚠️  Human AC: No data available")

    # Load human 2P
    human_2p = load_human_2p_data()
    if human_2p is not None and len(human_2p) > 0:
        human_data['Human 2P'] = human_2p
        print(f"  ✓ Human 2P: {len(human_2p)} auctions")
    else:
        print("  ⚠️  Human 2P: No data available")

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


def plot_comparison(human_data: Dict[str, np.ndarray],
                    llm_data: Dict[str, np.ndarray],
                    output_path: Path):
    """Create side-by-side distribution plots."""

    # Define column order
    column_order = ["Human AC", "Human 2P", "LLM AC", "LLM 2P"]
    column_order.extend(sorted(INTERVENTIONS.keys()))

    # Collect data
    plot_data = []
    plot_labels = []
    plot_types = []  # Track if human or LLM

    for col_name in column_order:
        data = human_data.get(col_name)
        if data is None:
            data = llm_data.get(col_name)
        if data is not None and len(data) > 0:
            plot_data.append(data)
            plot_labels.append(col_name)
            plot_types.append("human" if "Human" in col_name else "llm")

    if not plot_data:
        print("❌ No data to plot!")
        return

    # Create figure
    n_cols = len(plot_data)
    fig, axes = plt.subplots(1, n_cols, figsize=(3 * n_cols, 5), sharey=True)

    if n_cols == 1:
        axes = [axes]

    # Define bins
    bins = np.linspace(-0.5, 0.5, 45)

    # Colors matching the original image
    human_color = '#4472C4'  # Blue
    llm_color = '#ED7D31'    # Orange

    for idx, (label, data, dtype) in enumerate(zip(plot_labels, plot_data, plot_types)):
        ax = axes[idx]

        color = human_color if dtype == "human" else llm_color

        if dtype == "human":
            # Human: outlined only (like OSP in original image)
            ax.hist(data, bins=bins, density=True, alpha=0, color=color,
                   edgecolor=color, linewidth=2.5, histtype='step')
        else:
            # LLM: filled (like SP in original image)
            ax.hist(data, bins=bins, density=True, alpha=0.7, color=color,
                   edgecolor=color, linewidth=0.8)

        # Zero line
        ax.axvline(0, color='gray', linestyle='--', linewidth=1, alpha=0.4)

        # Labels
        if idx == 0:
            ax.set_ylabel('Density', fontsize=12, fontweight='bold')
        ax.set_xlabel('$(b_2 - v_2) / 25$', fontsize=10)

        # Title
        title = label.replace("LLM ", "").replace("Intervention ", "")
        ax.set_title(title, fontsize=11, fontweight='bold', pad=8)

        # Grid
        ax.grid(True, alpha=0.15, axis='y')
        ax.set_axisbelow(True)

        # Statistics
        stats_text = (f'n={len(data)}\n'
                     f'μ={np.mean(data):.3f}\n'
                     f'σ={np.std(data):.3f}')
        ax.text(0.97, 0.97, stats_text,
               transform=ax.transAxes,
               verticalalignment='top',
               horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                        edgecolor='gray', alpha=0.9, linewidth=0.5),
               fontsize=8, family='monospace')

        # Limits
        ax.set_xlim(-0.45, 0.45)

    # Overall title
    fig.suptitle('AC versus 2P: 2nd highest bid - 2nd highest value (normalized)',
                fontsize=14, fontweight='bold', y=0.98)

    # Legend
    from matplotlib.patches import Rectangle
    legend_elements = [
        Rectangle((0, 0), 1, 1, fc='none', ec=human_color,
                 linewidth=2.5, label='Human'),
        Rectangle((0, 0), 1, 1, fc=llm_color, ec=llm_color,
                 alpha=0.7, linewidth=0.8, label='LLM')
    ]
    fig.legend(handles=legend_elements, loc='upper right',
              bbox_to_anchor=(0.98, 0.95), framealpha=0.95,
              fontsize=10, edgecolor='gray', ncol=2)

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')

    print(f"\n✓ Saved: {output_path}")
    print(f"✓ Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def print_statistics(human_data: Dict[str, np.ndarray],
                     llm_data: Dict[str, np.ndarray]):
    """Print summary statistics."""
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    all_data = {**human_data, **llm_data}

    for name in ["Human AC", "Human 2P", "LLM AC", "LLM 2P"] + sorted(INTERVENTIONS.keys()):
        data = all_data.get(name)
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
    print("AUCTION DATA DISTRIBUTION COMPARISON")
    print("="*70 + "\n")

    human_data, llm_data = load_all_data()

    print_statistics(human_data, llm_data)

    print("\n📊 Generating comparison plot...")
    output_path = OUTPUT_DIR / "human_llm_distribution_comparison.png"
    plot_comparison(human_data, llm_data, output_path)

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()

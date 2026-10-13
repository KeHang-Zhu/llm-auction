"""
Create figure2-style stacked bar plots comparing Human vs LLM bidding
after removing the "equal bid" category at different threshold levels.

Following the style from llm-auct_ec26/Figs/figure2.py:
- Horizontal stacked bars
- Human data with hatched pattern '//'
- LLM data with solid fill
- Colors: Underbid (red #E74C3C), Equalbid (green #2ECC71), Overbid (blue #3498DB)

Outputs a SINGLE vertically stacked plot with all 4 thresholds.

Author: Analysis for LLM Auction Project
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from matplotlib.patches import Patch
from scipy import stats

# Set style - match figure2.py exactly
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'results' / 'v12_interventions' / 'no_equal_bid'

# Moment-matched human data paths
HUMAN_DATA_PATHS = {
    'Li 2017': PROJECT_ROOT / 'results' / 'v12_interventions' / 'moment_matching' / 'li_2017_osp_synthetic_bids.csv',
    'Breitmoser 2022': PROJECT_ROOT / 'results' / 'v12_interventions' / 'moment_matching' / 'breitmoser_2022_clock_synthetic_bids.csv',
    'Kagel-Levin 1993': PROJECT_ROOT / 'results' / 'v12_interventions' / 'moment_matching' / 'kagel_levin_1993_synthetic_bids.csv',
}

# LLM data path
LLM_DATA_DIR = PROJECT_ROOT / 'experiment_logs' / 'V12' / 'intervention_claude'

# Equilibrium ratios by auction type
OPTIMAL_RATIOS = {
    'FPSB': lambda n: (n - 1) / n,
    'SPSB': lambda n: 1.0,
    'TPSB': lambda n: (n - 1) / (n - 2),
    'AC': lambda n: 1.0,
    '2P': lambda n: 1.0,
    '2P+C': lambda n: 1.0,
    '2P+DC': lambda n: 1.0,
    'AC-DO': lambda n: 1.0,
}

# Thresholds for removing "equal bid" category
EQUILIBRIUM_THRESHOLDS = {
    '2%': 0.02,
    '10%': 0.10,
    '15%': 0.15,
    '25%': 0.25,
}

# Colors - match figure2.py exactly
COLORS = {
    'Underbid': '#E74C3C',   # Red
    'Equalbid': '#2ECC71',   # Green
    'Overbid': '#3498DB'     # Blue
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_human_data():
    """Load and combine all moment-matched human synthetic data."""
    all_data = []

    for source_name, path in HUMAN_DATA_PATHS.items():
        if not path.exists():
            print(f"  Warning: {source_name} data not found at {path}")
            continue

        df = pd.read_csv(path)
        df['source'] = source_name

        # Standardize column names
        if 'player_value' not in df.columns and 'value' in df.columns:
            df = df.rename(columns={'value': 'player_value'})

        # Get n_bidders (default to 4 if not present)
        if 'n_bidders' not in df.columns:
            df['n_bidders'] = 4

        all_data.append(df)
        print(f"  Loaded {source_name}: {len(df)} rows")

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


def load_llm_data():
    """Load LLM baseline data from V12 experiments."""
    all_data = []

    baseline_patterns = ['axis1_contingent_baseline', 'axis2_forward_baseline', 'axis3_beliefs_baseline']

    for pattern in baseline_patterns:
        exp_dir = LLM_DATA_DIR / pattern
        if not exp_dir.exists():
            continue

        merged_file = exp_dir / f"{pattern}_merged_results.csv"
        if merged_file.exists():
            df = pd.read_csv(merged_file)
            df['experiment'] = pattern
            all_data.append(df)
        else:
            for run_dir in exp_dir.iterdir():
                if run_dir.is_dir() and run_dir.name.startswith('run_'):
                    results_dir = run_dir / 'results'
                    if results_dir.exists():
                        for csv_file in results_dir.glob('*_results.csv'):
                            df = pd.read_csv(csv_file)
                            df['experiment'] = pattern
                            all_data.append(df)

    if not all_data:
        # Fallback to V10
        v10_dir = PROJECT_ROOT / 'experiment_logs_with_explanation' / 'V10'
        for exp_name in ['spsb_ipv']:
            exp_dir = v10_dir / exp_name
            if not exp_dir.exists():
                continue
            merged_file = exp_dir / f"{exp_name}_merged_results.csv"
            if merged_file.exists():
                df = pd.read_csv(merged_file)
                df['experiment'] = exp_name
                all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


# =============================================================================
# EQUILIBRIUM NORMALIZATION
# =============================================================================

def get_optimal_ratio(auction_type, n_bidders):
    """Get the equilibrium bid/value ratio for a given auction type and n."""
    type_mapping = {
        '2P': '2P', 'SPSB': 'SPSB', 'AC': 'AC', 'FPSB': 'FPSB', 'TPSB': 'TPSB',
        '2P+C': '2P+C', '2P+DC': '2P+DC', 'AC-DO': 'AC-DO',
    }
    normalized_type = type_mapping.get(str(auction_type).upper(), str(auction_type))

    if normalized_type in OPTIMAL_RATIOS:
        return OPTIMAL_RATIOS[normalized_type](n_bidders)
    return 1.0


def compute_equilibrium_deviation(df):
    """Add equilibrium deviation column to dataframe."""
    df = df.copy()
    df['bid_ratio'] = df['bid'] / df['player_value'].replace(0, np.nan)

    # Get auction type
    auction_col = None
    for col in ['auction_type', 'experiment', 'seal_clock']:
        if col in df.columns:
            auction_col = col
            break

    if auction_col is None:
        df['auction_type'] = 'SPSB'
        auction_col = 'auction_type'

    if 'n_bidders' not in df.columns:
        df['n_bidders'] = df.get('number_agents', 3)

    def compute_dev(row):
        auction = row.get(auction_col, 'SPSB')
        n = row.get('n_bidders', 3)
        optimal = get_optimal_ratio(str(auction), int(n))
        if pd.isna(row['bid_ratio']) or optimal == 0:
            return np.nan
        return row['bid_ratio'] / optimal - 1

    df['eq_deviation'] = df.apply(compute_dev, axis=1)
    return df


# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify_bids(df, threshold):
    """Classify bids as Underbid, Equalbid, or Overbid based on equilibrium deviation."""
    df = df.copy()
    df = df.dropna(subset=['eq_deviation'])

    def classify(dev):
        if dev < -threshold:
            return 'Underbid'
        elif dev > threshold:
            return 'Overbid'
        else:
            return 'Equalbid'

    df['classification'] = df['eq_deviation'].apply(classify)
    return df


def calculate_proportions(df_classified):
    """Calculate Underbid/Equalbid/Overbid proportions."""
    if len(df_classified) == 0:
        return {'Underbid': 0, 'Equalbid': 0, 'Overbid': 0, 'n': 0}

    counts = df_classified['classification'].value_counts()
    total = len(df_classified)

    return {
        'Underbid': (counts.get('Underbid', 0) / total) * 100,
        'Equalbid': (counts.get('Equalbid', 0) / total) * 100,
        'Overbid': (counts.get('Overbid', 0) / total) * 100,
        'n': total
    }


def calculate_proportions_no_equalbid(df_classified):
    """Calculate proportions after removing Equalbid category."""
    df_filtered = df_classified[df_classified['classification'] != 'Equalbid']

    if len(df_filtered) == 0:
        return {'Underbid': 0, 'Overbid': 0, 'n': 0, 'n_removed': len(df_classified)}

    counts = df_filtered['classification'].value_counts()
    total = len(df_filtered)

    return {
        'Underbid': (counts.get('Underbid', 0) / total) * 100,
        'Overbid': (counts.get('Overbid', 0) / total) * 100,
        'n': total,
        'n_removed': len(df_classified) - total,
        'pct_removed': (len(df_classified) - total) / len(df_classified) * 100
    }


# =============================================================================
# PLOTTING - FIGURE 2 STYLE (SINGLE VERTICAL OUTPUT)
# =============================================================================

def create_single_stacked_plot(human_df, llm_df, output_path):
    """
    Create a single vertically stacked plot with all 4 thresholds.

    Following figure2.py style exactly:
    - Human bars with '//' hatch pattern
    - LLM bars solid
    - Colors: Underbid=#E74C3C, Equalbid=#2ECC71, Overbid=#3498DB
    """

    # Row labels (one per threshold, showing Human and LLM for each)
    threshold_labels = [f'±{name}' for name in EQUILIBRIUM_THRESHOLDS.keys()]
    n_thresholds = len(threshold_labels)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))

    bar_height = 0.35
    y_positions = np.arange(n_thresholds)

    all_stats = []

    for i, (thresh_name, thresh_val) in enumerate(EQUILIBRIUM_THRESHOLDS.items()):
        # Classify bids
        human_classified = classify_bids(human_df, thresh_val)
        llm_classified = classify_bids(llm_df, thresh_val)

        # Calculate proportions after removing equal bid
        human_props = calculate_proportions_no_equalbid(human_classified)
        llm_props = calculate_proportions_no_equalbid(llm_classified)

        # Store stats
        all_stats.append({
            'threshold': thresh_name,
            'human_underbid': human_props['Underbid'],
            'human_overbid': human_props['Overbid'],
            'human_n': human_props['n'],
            'human_pct_removed': human_props['pct_removed'],
            'llm_underbid': llm_props['Underbid'],
            'llm_overbid': llm_props['Overbid'],
            'llm_n': llm_props['n'],
            'llm_pct_removed': llm_props['pct_removed'],
        })

        # Plot Human bar (top position within each threshold group) with hatch
        y_human = i + bar_height/2

        ax.barh(y_human, human_props['Underbid'], bar_height,
               color=COLORS['Underbid'], alpha=0.7, hatch='//', edgecolor='white')
        ax.barh(y_human, human_props['Overbid'], bar_height,
               left=human_props['Underbid'],
               color=COLORS['Overbid'], alpha=0.7, hatch='//', edgecolor='white')

        # Plot LLM bar (bottom position) solid
        y_llm = i - bar_height/2

        ax.barh(y_llm, llm_props['Underbid'], bar_height,
               color=COLORS['Underbid'], alpha=0.7, edgecolor='white')
        ax.barh(y_llm, llm_props['Overbid'], bar_height,
               left=llm_props['Underbid'],
               color=COLORS['Overbid'], alpha=0.7, edgecolor='white')

        # Add percentage labels for Human
        if human_props['Underbid'] > 8:
            ax.text(human_props['Underbid']/2, y_human, f"{human_props['Underbid']:.0f}%",
                   ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        if human_props['Overbid'] > 8:
            mid_over = human_props['Underbid'] + human_props['Overbid']/2
            ax.text(mid_over, y_human, f"{human_props['Overbid']:.0f}%",
                   ha='center', va='center', fontsize=9, fontweight='bold', color='white')

        # Add percentage labels for LLM
        if llm_props['Underbid'] > 8:
            ax.text(llm_props['Underbid']/2, y_llm, f"{llm_props['Underbid']:.0f}%",
                   ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        if llm_props['Overbid'] > 8:
            mid_over = llm_props['Underbid'] + llm_props['Overbid']/2
            ax.text(mid_over, y_llm, f"{llm_props['Overbid']:.0f}%",
                   ha='center', va='center', fontsize=9, fontweight='bold', color='white')

        # Add n and % removed annotations on the right
        ax.text(102, y_human, f"n={human_props['n']} ({human_props['pct_removed']:.0f}% removed)",
               ha='left', va='center', fontsize=8, color='gray')
        ax.text(102, y_llm, f"n={llm_props['n']} ({llm_props['pct_removed']:.0f}% removed)",
               ha='left', va='center', fontsize=8, color='gray')

    # Customize plot
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f'Threshold {label}' for label in threshold_labels])
    ax.set_xlabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.set_title('Bid Classification After Removing Equal-Bid Category\nHuman (Moment-Matched) vs LLM',
                fontsize=14, fontweight='bold', pad=20)

    # Add legend (outside the plot, on the right)
    legend_elements = [
        Patch(facecolor=COLORS['Underbid'], alpha=0.7, label='Underbid'),
        Patch(facecolor=COLORS['Overbid'], alpha=0.7, label='Overbid'),
        Patch(facecolor='gray', alpha=0.7, label='LLM (solid)'),
        Patch(facecolor='gray', alpha=0.7, hatch='//', edgecolor='black', label='Human (hatched)')
    ]
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.25, 0.5),
             frameon=True, fontsize=10)

    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")

    return all_stats


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*70)
    print("FIGURE 2 STYLE: Human vs LLM No Equal Bid Comparison")
    print("="*70)

    # Load data
    print("\nLoading human data...")
    human_df = load_human_data()

    print("\nLoading LLM data...")
    llm_df = load_llm_data()

    if human_df.empty or llm_df.empty:
        print("Error: Missing data!")
        return

    # Compute equilibrium deviations
    print("\nComputing equilibrium deviations...")
    human_df = compute_equilibrium_deviation(human_df)
    llm_df = compute_equilibrium_deviation(llm_df)

    # Remove invalid
    human_df = human_df.dropna(subset=['eq_deviation'])
    llm_df = llm_df.dropna(subset=['eq_deviation'])

    print(f"  Human: {len(human_df)} valid rows")
    print(f"  LLM: {len(llm_df)} valid rows")

    # Generate single vertically stacked plot
    print("\nGenerating figure2-style stacked plot...")
    output_path = OUTPUT_DIR / "no_equal_bid_comparison.png"
    all_stats = create_single_stacked_plot(human_df, llm_df, output_path)

    # Save statistics
    stats_df = pd.DataFrame(all_stats)
    stats_path = OUTPUT_DIR / "no_equal_bid_stats.csv"
    stats_df.to_csv(stats_path, index=False)
    print(f"  Saved statistics: {stats_path}")

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY: Underbid vs Overbid After Removing Equal Bid")
    print("="*70)
    print(stats_df.to_string(index=False))

    print("\n" + "="*70)
    print("COMPLETE!")
    print(f"Output: {output_path}")
    print("="*70)


if __name__ == '__main__':
    main()

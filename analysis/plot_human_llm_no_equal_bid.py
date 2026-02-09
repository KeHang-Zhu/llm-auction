"""
Compare Human vs LLM bidding distributions after removing the "equal bid" category.

This script:
1. Loads moment-matched synthetic human data from empirical papers
2. Loads LLM baseline data from V12 experiments
3. Normalizes all bids to equilibrium deviation: (bid/value) / optimal_ratio - 1
4. Removes bids near equilibrium (the "equal bid" category)
5. Compares the remaining tails (underbid vs overbid)

Key insight: Equilibrium normalization allows pooling across different n values
and auction mechanisms because 0 always means equilibrium play.

Author: Analysis for LLM Auction Project
"""

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional


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
# For SPSB/AC: optimal is truthful bidding (ratio = 1.0)
# For FPSB: optimal is bid shading (ratio = (n-1)/n)
# For TPSB: optimal is overbidding (ratio = (n-1)/(n-2))
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

# Thresholds for removing "equal bid" category (% deviation from equilibrium)
EQUILIBRIUM_THRESHOLDS = {
    'narrow_2pct': 0.02,
    'medium_10pct': 0.10,
    'wide_15pct': 0.15,
    'very_wide_25pct': 0.25,
}

# Plot colors
HUMAN_COLOR = '#4472C4'  # Blue
LLM_COLOR = '#ED7D31'    # Orange


# =============================================================================
# DATA LOADING
# =============================================================================

def load_human_data() -> pd.DataFrame:
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
            df['n_bidders'] = 4  # Li 2017 and Breitmoser use n=4

        all_data.append(df)
        print(f"  Loaded {source_name}: {len(df)} rows")

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


def load_llm_data() -> pd.DataFrame:
    """Load LLM baseline data from V12 experiments."""
    all_data = []

    # Find baseline experiments
    baseline_patterns = ['axis1_contingent_baseline', 'axis2_forward_baseline', 'axis3_beliefs_baseline']

    for pattern in baseline_patterns:
        exp_dir = LLM_DATA_DIR / pattern
        if not exp_dir.exists():
            print(f"  Warning: {pattern} not found")
            continue

        # Look for merged results or individual run results
        merged_file = exp_dir / f"{pattern}_merged_results.csv"
        if merged_file.exists():
            df = pd.read_csv(merged_file)
            df['experiment'] = pattern
            all_data.append(df)
            print(f"  Loaded {pattern} (merged): {len(df)} rows")
        else:
            # Load from individual runs
            for run_dir in exp_dir.iterdir():
                if run_dir.is_dir() and run_dir.name.startswith('run_'):
                    results_dir = run_dir / 'results'
                    if results_dir.exists():
                        for csv_file in results_dir.glob('*_results.csv'):
                            df = pd.read_csv(csv_file)
                            df['experiment'] = pattern
                            all_data.append(df)

    if not all_data:
        print("  Warning: No LLM data found, trying V10 data...")
        return load_llm_data_v10()

    combined = pd.concat(all_data, ignore_index=True)
    print(f"  Total LLM rows: {len(combined)}")
    return combined


def load_llm_data_v10() -> pd.DataFrame:
    """Fallback: Load LLM data from V10 experiments."""
    v10_dir = PROJECT_ROOT / 'experiment_logs_with_explanation' / 'V10'
    all_data = []

    for exp_name in ['spsb_ipv', 'ascending_clock_apv']:
        exp_dir = v10_dir / exp_name
        if not exp_dir.exists():
            continue

        merged_file = exp_dir / f"{exp_name}_merged_results.csv"
        if merged_file.exists():
            df = pd.read_csv(merged_file)
            df['experiment'] = exp_name
            all_data.append(df)
            print(f"  Loaded V10 {exp_name}: {len(df)} rows")

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


# =============================================================================
# EQUILIBRIUM NORMALIZATION
# =============================================================================

def get_optimal_ratio(auction_type: str, n_bidders: int) -> float:
    """Get the equilibrium bid/value ratio for a given auction type and n."""
    auction_type = auction_type.upper() if auction_type not in OPTIMAL_RATIOS else auction_type

    # Handle various naming conventions
    type_mapping = {
        '2P': '2P',
        'SPSB': 'SPSB',
        'SECOND-PRICE': 'SPSB',
        'AC': 'AC',
        'ASCENDING': 'AC',
        'ASCENDING_CLOCK': 'AC',
        'FPSB': 'FPSB',
        'FIRST-PRICE': 'FPSB',
        'TPSB': 'TPSB',
        'THIRD-PRICE': 'TPSB',
        '2P+C': '2P+C',
        '2P+DC': '2P+DC',
        'AC-DO': 'AC-DO',
    }

    normalized_type = type_mapping.get(auction_type, auction_type)

    if normalized_type in OPTIMAL_RATIOS:
        return OPTIMAL_RATIOS[normalized_type](n_bidders)
    else:
        print(f"  Warning: Unknown auction type '{auction_type}', defaulting to truthful")
        return 1.0


def compute_equilibrium_deviation(df: pd.DataFrame) -> pd.DataFrame:
    """Add equilibrium deviation column to dataframe.

    eq_deviation = (bid/value) / optimal_ratio - 1

    - 0 means equilibrium play
    - Positive means overbidding relative to equilibrium
    - Negative means underbidding relative to equilibrium
    """
    df = df.copy()

    # Compute bid/value ratio
    df['bid_ratio'] = df['bid'] / df['player_value'].replace(0, np.nan)

    # Get auction type column
    auction_col = None
    for col in ['auction_type', 'experiment', 'seal_clock']:
        if col in df.columns:
            auction_col = col
            break

    if auction_col is None:
        # Default to SPSB if no auction type found
        df['auction_type'] = 'SPSB'
        auction_col = 'auction_type'

    # Get n_bidders
    if 'n_bidders' not in df.columns:
        if 'number_agents' in df.columns:
            df['n_bidders'] = df['number_agents']
        else:
            df['n_bidders'] = 3  # Default for LLM experiments

    # Compute equilibrium deviation for each row
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
# FILTERING
# =============================================================================

def filter_remove_equilibrium_band(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Remove bids within ±threshold of equilibrium.

    Returns filtered dataframe with 'category' column ('underbid' or 'overbid').
    """
    df = df.copy()

    # Remove NaN deviations
    df = df.dropna(subset=['eq_deviation'])

    # Filter out bids near equilibrium
    mask = np.abs(df['eq_deviation']) > threshold
    filtered = df[mask].copy()

    # Categorize remaining bids
    filtered['category'] = np.where(filtered['eq_deviation'] < 0, 'underbid', 'overbid')

    return filtered


def compute_statistics(df: pd.DataFrame, label: str) -> Dict:
    """Compute summary statistics for a filtered dataset."""
    if len(df) == 0:
        return {
            'label': label,
            'n_total': 0,
            'n_underbid': 0,
            'n_overbid': 0,
            'pct_underbid': 0,
            'pct_overbid': 0,
            'mean_underbid_dev': np.nan,
            'mean_overbid_dev': np.nan,
            'std_underbid_dev': np.nan,
            'std_overbid_dev': np.nan,
        }

    underbid = df[df['category'] == 'underbid']
    overbid = df[df['category'] == 'overbid']

    return {
        'label': label,
        'n_total': len(df),
        'n_underbid': len(underbid),
        'n_overbid': len(overbid),
        'pct_underbid': 100 * len(underbid) / len(df) if len(df) > 0 else 0,
        'pct_overbid': 100 * len(overbid) / len(df) if len(df) > 0 else 0,
        'mean_underbid_dev': underbid['eq_deviation'].mean() if len(underbid) > 0 else np.nan,
        'mean_overbid_dev': overbid['eq_deviation'].mean() if len(overbid) > 0 else np.nan,
        'std_underbid_dev': underbid['eq_deviation'].std() if len(underbid) > 0 else np.nan,
        'std_overbid_dev': overbid['eq_deviation'].std() if len(overbid) > 0 else np.nan,
    }


# =============================================================================
# PLOTTING
# =============================================================================

def plot_comparison(human_filtered: pd.DataFrame,
                   llm_filtered: pd.DataFrame,
                   threshold_name: str,
                   threshold_value: float,
                   output_path: Path):
    """Create side-by-side distribution comparison plot."""

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    # Define bins for equilibrium deviation
    bins = np.linspace(-1.0, 1.0, 41)

    # Human distribution
    ax = axes[0]
    if len(human_filtered) > 0:
        ax.hist(human_filtered['eq_deviation'], bins=bins, density=True,
               alpha=0.7, color=HUMAN_COLOR, edgecolor=HUMAN_COLOR, linewidth=0.8,
               label='Human (Moment-Matched)')

    ax.axvline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Equilibrium')
    ax.axvline(-threshold_value, color='gray', linestyle=':', linewidth=1, alpha=0.5)
    ax.axvline(threshold_value, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    ax.set_xlabel('Equilibrium Deviation\n(bid/value)/optimal - 1', fontsize=11)
    ax.set_ylabel('Density', fontsize=11)
    ax.set_title('Human (Synthetic from Papers)', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-1.0, 1.0)

    # Stats box
    human_stats = compute_statistics(human_filtered, 'Human')
    stats_text = (f"n={human_stats['n_total']}\n"
                 f"Under: {human_stats['pct_underbid']:.1f}%\n"
                 f"Over: {human_stats['pct_overbid']:.1f}%")
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', fontfamily='monospace',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

    # LLM distribution
    ax = axes[1]
    if len(llm_filtered) > 0:
        ax.hist(llm_filtered['eq_deviation'], bins=bins, density=True,
               alpha=0.7, color=LLM_COLOR, edgecolor=LLM_COLOR, linewidth=0.8,
               label='LLM (V12 Baseline)')

    ax.axvline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Equilibrium')
    ax.axvline(-threshold_value, color='gray', linestyle=':', linewidth=1, alpha=0.5)
    ax.axvline(threshold_value, color='gray', linestyle=':', linewidth=1, alpha=0.5)

    ax.set_xlabel('Equilibrium Deviation\n(bid/value)/optimal - 1', fontsize=11)
    ax.set_title('LLM (V12 Baseline)', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-1.0, 1.0)

    # Stats box
    llm_stats = compute_statistics(llm_filtered, 'LLM')
    stats_text = (f"n={llm_stats['n_total']}\n"
                 f"Under: {llm_stats['pct_underbid']:.1f}%\n"
                 f"Over: {llm_stats['pct_overbid']:.1f}%")
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', fontfamily='monospace',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

    # Overall title
    fig.suptitle(f'Human vs LLM: Bidding Tails After Removing Equal-Bid Category\n'
                f'(Threshold: ±{threshold_value*100:.0f}% of equilibrium removed)',
                fontsize=14, fontweight='bold')

    plt.tight_layout(rect=[0, 0, 1, 0.93])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")


def plot_threshold_grid(human_df: pd.DataFrame,
                        llm_df: pd.DataFrame,
                        output_path: Path):
    """Create grid showing all thresholds side by side."""

    n_thresholds = len(EQUILIBRIUM_THRESHOLDS)
    fig, axes = plt.subplots(2, n_thresholds, figsize=(4*n_thresholds, 8), sharey='row')

    bins = np.linspace(-1.0, 1.0, 41)

    for col_idx, (thresh_name, thresh_val) in enumerate(EQUILIBRIUM_THRESHOLDS.items()):
        human_filtered = filter_remove_equilibrium_band(human_df, thresh_val)
        llm_filtered = filter_remove_equilibrium_band(llm_df, thresh_val)

        # Human row
        ax = axes[0, col_idx]
        if len(human_filtered) > 0:
            ax.hist(human_filtered['eq_deviation'], bins=bins, density=True,
                   alpha=0.7, color=HUMAN_COLOR, edgecolor=HUMAN_COLOR)
        ax.axvline(0, color='red', linestyle='--', linewidth=1)
        ax.set_title(f'±{thresh_val*100:.0f}%', fontsize=11, fontweight='bold')
        if col_idx == 0:
            ax.set_ylabel('Human\nDensity', fontsize=10, fontweight='bold')
        ax.set_xlim(-1.0, 1.0)
        ax.grid(True, alpha=0.2)

        # Stats
        h_stats = compute_statistics(human_filtered, 'H')
        ax.text(0.98, 0.98, f"n={h_stats['n_total']}", transform=ax.transAxes,
               fontsize=8, ha='right', va='top')

        # LLM row
        ax = axes[1, col_idx]
        if len(llm_filtered) > 0:
            ax.hist(llm_filtered['eq_deviation'], bins=bins, density=True,
                   alpha=0.7, color=LLM_COLOR, edgecolor=LLM_COLOR)
        ax.axvline(0, color='red', linestyle='--', linewidth=1)
        ax.set_xlabel('Eq. Deviation', fontsize=9)
        if col_idx == 0:
            ax.set_ylabel('LLM\nDensity', fontsize=10, fontweight='bold')
        ax.set_xlim(-1.0, 1.0)
        ax.grid(True, alpha=0.2)

        # Stats
        l_stats = compute_statistics(llm_filtered, 'L')
        ax.text(0.98, 0.98, f"n={l_stats['n_total']}", transform=ax.transAxes,
               fontsize=8, ha='right', va='top')

    fig.suptitle('Bidding Tails at Different Equal-Bid Thresholds\n'
                '(Gray area removed from each)', fontsize=14, fontweight='bold')

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*70)
    print("HUMAN vs LLM COMPARISON: Removing Equal-Bid Category")
    print("="*70)

    # Load data
    print("\n📊 Loading human (moment-matched) data...")
    human_df = load_human_data()

    print("\n📊 Loading LLM data...")
    llm_df = load_llm_data()

    if human_df.empty:
        print("❌ No human data found!")
        return

    if llm_df.empty:
        print("❌ No LLM data found!")
        return

    # Compute equilibrium deviations
    print("\n🔧 Computing equilibrium deviations...")
    human_df = compute_equilibrium_deviation(human_df)
    llm_df = compute_equilibrium_deviation(llm_df)

    # Remove invalid rows
    human_df = human_df.dropna(subset=['eq_deviation'])
    llm_df = llm_df.dropna(subset=['eq_deviation'])

    print(f"  Human: {len(human_df)} valid rows")
    print(f"  LLM: {len(llm_df)} valid rows")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate plots for each threshold
    print("\n📈 Generating comparison plots...")
    all_stats = []

    for thresh_name, thresh_val in EQUILIBRIUM_THRESHOLDS.items():
        print(f"\n  Processing threshold: {thresh_name} (±{thresh_val*100:.0f}%)")

        human_filtered = filter_remove_equilibrium_band(human_df, thresh_val)
        llm_filtered = filter_remove_equilibrium_band(llm_df, thresh_val)

        # Individual comparison plot
        output_path = OUTPUT_DIR / f"human_vs_llm_eq_normalized_{thresh_name}.png"
        plot_comparison(human_filtered, llm_filtered, thresh_name, thresh_val, output_path)

        # Collect statistics
        human_stats = compute_statistics(human_filtered, f'Human_{thresh_name}')
        human_stats['threshold'] = thresh_name
        human_stats['threshold_value'] = thresh_val
        human_stats['source'] = 'Human'
        human_stats['total_before_filter'] = len(human_df)
        human_stats['pct_removed'] = 100 * (1 - len(human_filtered) / len(human_df))
        all_stats.append(human_stats)

        llm_stats = compute_statistics(llm_filtered, f'LLM_{thresh_name}')
        llm_stats['threshold'] = thresh_name
        llm_stats['threshold_value'] = thresh_val
        llm_stats['source'] = 'LLM'
        llm_stats['total_before_filter'] = len(llm_df)
        llm_stats['pct_removed'] = 100 * (1 - len(llm_filtered) / len(llm_df))
        all_stats.append(llm_stats)

    # Generate grid comparison
    print("\n📈 Generating threshold grid comparison...")
    grid_path = OUTPUT_DIR / "threshold_grid_comparison.png"
    plot_threshold_grid(human_df, llm_df, grid_path)

    # Save statistics
    stats_df = pd.DataFrame(all_stats)
    stats_path = OUTPUT_DIR / "statistics_summary.csv"
    stats_df.to_csv(stats_path, index=False)
    print(f"\n✓ Saved statistics: {stats_path}")

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(stats_df[['source', 'threshold', 'n_total', 'pct_removed',
                    'pct_underbid', 'pct_overbid']].to_string(index=False))

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print(f"✓ All outputs saved to: {OUTPUT_DIR}")
    print("="*70)


if __name__ == '__main__':
    main()

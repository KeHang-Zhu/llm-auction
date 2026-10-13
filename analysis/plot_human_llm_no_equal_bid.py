"""
Human vs LLM Comparison: No Equal Bid Analysis

This script compares human and LLM bidding distributions AFTER removing the
"equal bid" (equilibrium) category, to examine if tail distributions (underbidders
and overbidders) look similar.

Key Features:
1. Equilibrium-Normalized Deviation: Normalizes all bids relative to mechanism-specific
   equilibrium, allowing comparison across mechanisms and n values
2. Multi-Threshold Analysis: Tests ±2%, ±10%, ±15%, ±25% thresholds
3. Multi-n Merging: Combines data from different n values after normalization

Data Sources:
- Li 2017 OSP (2P, AC): n=4
- Breitmoser 2022 Clock (2P, 2P+C, 2P+DC, AC-DO, AC): n=4
- Kagel-Levin 1993 (FPSB, SPSB, TPSB): n=5, n=10
- Gonczarowski 2022 (SPSB Traditional, SPSB Menu): n=5
- LLM (V10): n=3

Author: Analysis for LLM Auction Project
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from matplotlib.patches import Patch

# Set style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
MOMENT_MATCHING_DIR = PROJECT_ROOT / 'results' / 'v12_interventions' / 'moment_matching'
LLM_DATA_DIR = PROJECT_ROOT / 'experiment_logs' / 'V10'
OUTPUT_DIR = PROJECT_ROOT / 'results' / 'v12_interventions' / 'no_equal_bid'

# Optimal bid ratios by auction type and n
# For SPSB/AC: b* = v (ratio = 1.0 for all n)
# For FPSB: b* = (n-1)/n * v
# For TPSB: b* = (n-1)/(n-2) * v
OPTIMAL_RATIOS = {
    'FPSB': lambda n: (n - 1) / n,
    'SPSB': lambda n: 1.0,
    '2P': lambda n: 1.0,  # Same as SPSB
    'TPSB': lambda n: (n - 1) / (n - 2) if n > 2 else float('inf'),
    'AC': lambda n: 1.0,  # Ascending clock = truthful
    '2P+C': lambda n: 1.0,
    '2P+DC': lambda n: 1.0,
    'AC-DO': lambda n: 1.0,
}

# Threshold configurations (percentage deviation from equilibrium)
EQUILIBRIUM_THRESHOLDS = {
    'narrow_2pct': 0.02,
    'medium_10pct': 0.10,
    'wide_15pct': 0.15,
    'very_wide_25pct': 0.25,
}

# Colors
COLORS = {
    'Underbid': '#E74C3C',   # Red
    'Equalbid': '#2ECC71',   # Green
    'Overbid': '#3498DB',    # Blue
    'Human': '#34495e',
    'LLM': '#9b59b6',
}


# =============================================================================
# EQUILIBRIUM DEVIATION CALCULATION
# =============================================================================

def compute_equilibrium_deviation(df, auction_type, n):
    """Compute equilibrium-normalized deviation for each bid.

    eq_deviation = (bid/value) / optimal_ratio - 1

    This normalizes all bids relative to their mechanism-specific equilibrium:
    - 0 = equilibrium play
    - Positive = overbidding relative to equilibrium
    - Negative = underbidding relative to equilibrium
    """
    df = df.copy()

    # Get optimal ratio for this auction type and n
    if auction_type in OPTIMAL_RATIOS:
        optimal_ratio = OPTIMAL_RATIOS[auction_type](n)
    else:
        # Default to truthful
        optimal_ratio = 1.0

    # Compute equilibrium deviation
    # Filter out zero/very small values to avoid division issues
    valid_mask = df['player_value'] > 0.1
    df = df[valid_mask].copy()

    df['bid_value_ratio'] = df['bid'] / df['player_value']
    df['optimal_ratio'] = optimal_ratio
    df['eq_deviation'] = (df['bid_value_ratio'] / optimal_ratio) - 1

    return df


def filter_remove_equilibrium_band(df, threshold):
    """Remove bids within ±threshold of equilibrium.

    Returns filtered dataframe with only underbid/overbid observations.
    """
    mask = np.abs(df['eq_deviation']) > threshold
    filtered = df[mask].copy()
    filtered['category'] = np.where(filtered['eq_deviation'] < 0, 'Underbid', 'Overbid')
    return filtered


# =============================================================================
# DATA LOADING
# =============================================================================

def load_human_synthetic_data():
    """Load all human synthetic data from moment matching.

    Returns dict of DataFrames keyed by source name.
    """
    human_data = {}

    # Li 2017 OSP
    li_2017_path = MOMENT_MATCHING_DIR / 'li_2017_osp_synthetic_bids.csv'
    if li_2017_path.exists():
        df = pd.read_csv(li_2017_path)
        # Standardize column names
        if 'player_value' not in df.columns and 'value' in df.columns:
            df = df.rename(columns={'value': 'player_value'})
        df['n_bidders'] = 4  # Li 2017 uses n=4
        human_data['Li_2017'] = df
        print(f"Loaded Li 2017: {len(df)} observations")

    # Breitmoser 2022
    breitmoser_path = MOMENT_MATCHING_DIR / 'breitmoser_2022_clock_synthetic_bids.csv'
    if breitmoser_path.exists():
        df = pd.read_csv(breitmoser_path)
        if 'player_value' not in df.columns and 'value' in df.columns:
            df = df.rename(columns={'value': 'player_value'})
        df['n_bidders'] = 4  # Breitmoser 2022 uses n=4
        human_data['Breitmoser_2022'] = df
        print(f"Loaded Breitmoser 2022: {len(df)} observations")

    # Kagel-Levin 1993
    kagel_path = MOMENT_MATCHING_DIR / 'kagel_levin_1993_synthetic_bids.csv'
    if kagel_path.exists():
        df = pd.read_csv(kagel_path)
        if 'player_value' not in df.columns and 'value' in df.columns:
            df = df.rename(columns={'value': 'player_value'})
        # n_bidders should already be in the data
        human_data['Kagel_Levin_1993'] = df
        print(f"Loaded Kagel-Levin 1993: {len(df)} observations")

    # Gonczarowski 2022 (if exists)
    gonczarowski_path = MOMENT_MATCHING_DIR / 'gonczarowski_2022_synthetic_bids.csv'
    if gonczarowski_path.exists():
        df = pd.read_csv(gonczarowski_path)
        if 'player_value' not in df.columns and 'value' in df.columns:
            df = df.rename(columns={'value': 'player_value'})
        df['n_bidders'] = 5  # Gonczarowski uses n=5
        human_data['Gonczarowski_2022'] = df
        print(f"Loaded Gonczarowski 2022: {len(df)} observations")

    return human_data


def load_llm_data():
    """Load LLM experimental data from V10.

    Returns DataFrame with all LLM bid data.
    """
    llm_dfs = []

    # Load from different auction directories
    auction_dirs = {
        'spsb_ipv': ('SPSB', 3),
        'spsb_apv': ('SPSB', 4),
        'fpsb_ipv': ('FPSB', 3),
        'third_price_ipv': ('TPSB', 3),
        'ascending_clock_apv': ('AC', 4),
    }

    for dir_name, (auction_type, n_bidders) in auction_dirs.items():
        auction_dir = LLM_DATA_DIR / dir_name
        if not auction_dir.exists():
            continue

        csv_files = list(auction_dir.rglob('*_results.csv'))
        for csv_file in csv_files:
            if 'merged' in csv_file.name:
                continue
            try:
                df = pd.read_csv(csv_file)
                df['auction_type'] = auction_type
                df['n_bidders'] = n_bidders
                df['source'] = 'LLM_V10'
                llm_dfs.append(df)
            except Exception as e:
                print(f"Error loading {csv_file}: {e}")

    if llm_dfs:
        llm_data = pd.concat(llm_dfs, ignore_index=True)
        print(f"Loaded LLM data: {len(llm_data)} total observations")
        return llm_data
    else:
        print("Warning: No LLM data found")
        return pd.DataFrame()


# =============================================================================
# PROCESSING
# =============================================================================

def process_human_data(human_data_dict):
    """Process all human data with equilibrium normalization.

    Returns DataFrame with eq_deviation computed for all observations.
    """
    processed_dfs = []

    for source, df in human_data_dict.items():
        # Get auction type column name
        if 'auction_type' in df.columns:
            auction_col = 'auction_type'
        elif 'Auction' in df.columns:
            auction_col = 'Auction'
        else:
            # Default to SPSB for unknown auction type
            df['auction_type'] = 'SPSB'
            auction_col = 'auction_type'

        # Process each auction type separately
        for auction_type in df[auction_col].unique():
            subset = df[df[auction_col] == auction_type].copy()

            # Get n_bidders
            if 'n_bidders' in subset.columns:
                n_values = subset['n_bidders'].unique()
            else:
                n_values = [4]  # Default assumption

            for n in n_values:
                if 'n_bidders' in subset.columns:
                    n_subset = subset[subset['n_bidders'] == n].copy()
                else:
                    n_subset = subset.copy()
                    n_subset['n_bidders'] = n

                # Compute equilibrium deviation
                n_subset = compute_equilibrium_deviation(n_subset, auction_type, n)
                n_subset['source'] = source
                n_subset['auction_type'] = auction_type
                processed_dfs.append(n_subset)

    if processed_dfs:
        return pd.concat(processed_dfs, ignore_index=True)
    return pd.DataFrame()


def process_llm_data(llm_df):
    """Process LLM data with equilibrium normalization."""
    if llm_df.empty:
        return pd.DataFrame()

    processed_dfs = []

    for auction_type in llm_df['auction_type'].unique():
        subset = llm_df[llm_df['auction_type'] == auction_type].copy()

        for n in subset['n_bidders'].unique():
            n_subset = subset[subset['n_bidders'] == n].copy()
            n_subset = compute_equilibrium_deviation(n_subset, auction_type, n)
            processed_dfs.append(n_subset)

    if processed_dfs:
        return pd.concat(processed_dfs, ignore_index=True)
    return pd.DataFrame()


def compute_statistics(df, threshold, group_name):
    """Compute statistics for a filtered dataset."""
    # Filter to remove equilibrium band
    filtered = filter_remove_equilibrium_band(df, threshold)

    total_n = len(df)
    filtered_n = len(filtered)
    pct_removed = 100 * (1 - filtered_n / total_n) if total_n > 0 else 0

    underbid = filtered[filtered['category'] == 'Underbid']
    overbid = filtered[filtered['category'] == 'Overbid']

    return {
        'group': group_name,
        'threshold': threshold,
        'total_n': total_n,
        'filtered_n': filtered_n,
        'pct_removed': pct_removed,
        'underbid_count': len(underbid),
        'overbid_count': len(overbid),
        'underbid_pct': 100 * len(underbid) / filtered_n if filtered_n > 0 else 0,
        'overbid_pct': 100 * len(overbid) / filtered_n if filtered_n > 0 else 0,
        'mean_underbid_dev': underbid['eq_deviation'].mean() if len(underbid) > 0 else np.nan,
        'mean_overbid_dev': overbid['eq_deviation'].mean() if len(overbid) > 0 else np.nan,
    }


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_deviation_distributions(human_df, llm_df, threshold, output_path):
    """Plot distribution of equilibrium deviations for human vs LLM.

    After removing the equilibrium band, shows:
    - Left side: Underbidding distribution
    - Right side: Overbidding distribution
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Filter both datasets
    human_filtered = filter_remove_equilibrium_band(human_df, threshold)
    llm_filtered = filter_remove_equilibrium_band(llm_df, threshold) if not llm_df.empty else pd.DataFrame()

    # Underbid distribution
    ax = axes[0]
    human_under = human_filtered[human_filtered['category'] == 'Underbid']['eq_deviation']
    if not llm_filtered.empty:
        llm_under = llm_filtered[llm_filtered['category'] == 'Underbid']['eq_deviation']
    else:
        llm_under = pd.Series([])

    if len(human_under) > 0:
        ax.hist(human_under, bins=30, alpha=0.6, color=COLORS['Human'],
                label=f'Human (n={len(human_under)})', density=True)
    if len(llm_under) > 0:
        ax.hist(llm_under, bins=30, alpha=0.6, color=COLORS['LLM'],
                label=f'LLM (n={len(llm_under)})', density=True)

    ax.axvline(x=-threshold, color='red', linestyle='--', alpha=0.5, label=f'Threshold ({threshold*100:.0f}%)')
    ax.set_xlabel('Equilibrium Deviation (negative = underbid)')
    ax.set_ylabel('Density')
    ax.set_title('Underbidding Distribution')
    ax.legend()
    ax.set_xlim(-1, -threshold)

    # Overbid distribution
    ax = axes[1]
    human_over = human_filtered[human_filtered['category'] == 'Overbid']['eq_deviation']
    if not llm_filtered.empty:
        llm_over = llm_filtered[llm_filtered['category'] == 'Overbid']['eq_deviation']
    else:
        llm_over = pd.Series([])

    if len(human_over) > 0:
        ax.hist(human_over, bins=30, alpha=0.6, color=COLORS['Human'],
                label=f'Human (n={len(human_over)})', density=True)
    if len(llm_over) > 0:
        ax.hist(llm_over, bins=30, alpha=0.6, color=COLORS['LLM'],
                label=f'LLM (n={len(llm_over)})', density=True)

    ax.axvline(x=threshold, color='red', linestyle='--', alpha=0.5, label=f'Threshold ({threshold*100:.0f}%)')
    ax.set_xlabel('Equilibrium Deviation (positive = overbid)')
    ax.set_ylabel('Density')
    ax.set_title('Overbidding Distribution')
    ax.legend()
    ax.set_xlim(threshold, 1)

    plt.suptitle(f'Human vs LLM Deviation Distributions\n(After Removing ±{threshold*100:.0f}% Equilibrium Band)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def plot_stacked_bar_comparison(human_df, llm_df, threshold, output_path):
    """Create stacked bar plot comparing Underbid vs Overbid proportions."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Filter both datasets
    human_filtered = filter_remove_equilibrium_band(human_df, threshold)
    llm_filtered = filter_remove_equilibrium_band(llm_df, threshold) if not llm_df.empty else pd.DataFrame()

    # Calculate proportions
    groups = []
    underbid_pcts = []
    overbid_pcts = []

    if len(human_filtered) > 0:
        human_under_pct = 100 * len(human_filtered[human_filtered['category'] == 'Underbid']) / len(human_filtered)
        human_over_pct = 100 * len(human_filtered[human_filtered['category'] == 'Overbid']) / len(human_filtered)
        groups.append('Human')
        underbid_pcts.append(human_under_pct)
        overbid_pcts.append(human_over_pct)

    if len(llm_filtered) > 0:
        llm_under_pct = 100 * len(llm_filtered[llm_filtered['category'] == 'Underbid']) / len(llm_filtered)
        llm_over_pct = 100 * len(llm_filtered[llm_filtered['category'] == 'Overbid']) / len(llm_filtered)
        groups.append('LLM')
        underbid_pcts.append(llm_under_pct)
        overbid_pcts.append(llm_over_pct)

    if not groups:
        print("No data to plot")
        return

    x = np.arange(len(groups))
    width = 0.6

    # Plot stacked bars
    bars1 = ax.bar(x, underbid_pcts, width, label='Underbid', color=COLORS['Underbid'])
    bars2 = ax.bar(x, overbid_pcts, width, bottom=underbid_pcts, label='Overbid', color=COLORS['Overbid'])

    # Add labels
    for i, (u, o) in enumerate(zip(underbid_pcts, overbid_pcts)):
        if u > 5:
            ax.text(i, u/2, f'{u:.1f}%', ha='center', va='center', fontweight='bold', color='white')
        if o > 5:
            ax.text(i, u + o/2, f'{o:.1f}%', ha='center', va='center', fontweight='bold', color='white')

    ax.set_ylabel('Percentage')
    ax.set_title(f'Underbid vs Overbid After Removing ±{threshold*100:.0f}% Equilibrium Band')
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.legend()
    ax.set_ylim(0, 105)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def plot_threshold_grid(human_df, llm_df, output_path):
    """Create grid of plots showing effect of different thresholds."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()

    for idx, (thresh_name, threshold) in enumerate(EQUILIBRIUM_THRESHOLDS.items()):
        ax = axes[idx]

        # Filter both datasets
        human_filtered = filter_remove_equilibrium_band(human_df, threshold)
        llm_filtered = filter_remove_equilibrium_band(llm_df, threshold) if not llm_df.empty else pd.DataFrame()

        # Calculate proportions
        data = []

        if len(human_filtered) > 0:
            human_under = 100 * len(human_filtered[human_filtered['category'] == 'Underbid']) / len(human_filtered)
            human_over = 100 * len(human_filtered[human_filtered['category'] == 'Overbid']) / len(human_filtered)
            data.append(('Human', human_under, human_over, len(human_filtered)))

        if len(llm_filtered) > 0:
            llm_under = 100 * len(llm_filtered[llm_filtered['category'] == 'Underbid']) / len(llm_filtered)
            llm_over = 100 * len(llm_filtered[llm_filtered['category'] == 'Overbid']) / len(llm_filtered)
            data.append(('LLM', llm_under, llm_over, len(llm_filtered)))

        if not data:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            continue

        groups = [d[0] for d in data]
        underbids = [d[1] for d in data]
        overbids = [d[2] for d in data]
        ns = [d[3] for d in data]

        x = np.arange(len(groups))
        width = 0.6

        ax.bar(x, underbids, width, label='Underbid', color=COLORS['Underbid'])
        ax.bar(x, overbids, width, bottom=underbids, label='Overbid', color=COLORS['Overbid'])

        # Add labels
        for i, (u, o, n) in enumerate(zip(underbids, overbids, ns)):
            if u > 5:
                ax.text(i, u/2, f'{u:.0f}%', ha='center', va='center', fontweight='bold', color='white', fontsize=10)
            if o > 5:
                ax.text(i, u + o/2, f'{o:.0f}%', ha='center', va='center', fontweight='bold', color='white', fontsize=10)
            ax.text(i, 102, f'n={n}', ha='center', va='bottom', fontsize=9, color='gray')

        ax.set_ylabel('Percentage')
        ax.set_title(f'Threshold: ±{threshold*100:.0f}%')
        ax.set_xticks(x)
        ax.set_xticklabels(groups)
        ax.set_ylim(0, 110)
        ax.legend(loc='upper right', fontsize=9)

    plt.suptitle('Effect of Different Equilibrium Thresholds on Underbid/Overbid Proportions',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def plot_by_mechanism(human_df, llm_df, threshold, output_dir):
    """Create separate plots for each auction mechanism."""
    mechanisms = ['SPSB', 'FPSB', 'TPSB', '2P', 'AC']

    for mech in mechanisms:
        human_mech = human_df[human_df['auction_type'] == mech] if 'auction_type' in human_df.columns else pd.DataFrame()
        llm_mech = llm_df[llm_df['auction_type'] == mech] if not llm_df.empty and 'auction_type' in llm_df.columns else pd.DataFrame()

        if len(human_mech) == 0 and len(llm_mech) == 0:
            continue

        fig, ax = plt.subplots(figsize=(8, 6))

        # Filter
        human_filtered = filter_remove_equilibrium_band(human_mech, threshold) if len(human_mech) > 0 else pd.DataFrame()
        llm_filtered = filter_remove_equilibrium_band(llm_mech, threshold) if len(llm_mech) > 0 else pd.DataFrame()

        data = []
        if len(human_filtered) > 0:
            h_under = 100 * len(human_filtered[human_filtered['category'] == 'Underbid']) / len(human_filtered)
            h_over = 100 * len(human_filtered[human_filtered['category'] == 'Overbid']) / len(human_filtered)
            data.append(('Human', h_under, h_over, len(human_filtered)))

        if len(llm_filtered) > 0:
            l_under = 100 * len(llm_filtered[llm_filtered['category'] == 'Underbid']) / len(llm_filtered)
            l_over = 100 * len(llm_filtered[llm_filtered['category'] == 'Overbid']) / len(llm_filtered)
            data.append(('LLM', l_under, l_over, len(llm_filtered)))

        if not data:
            plt.close()
            continue

        groups = [d[0] for d in data]
        underbids = [d[1] for d in data]
        overbids = [d[2] for d in data]

        x = np.arange(len(groups))
        width = 0.5

        ax.bar(x, underbids, width, label='Underbid', color=COLORS['Underbid'])
        ax.bar(x, overbids, width, bottom=underbids, label='Overbid', color=COLORS['Overbid'])

        for i, (u, o) in enumerate(zip(underbids, overbids)):
            if u > 5:
                ax.text(i, u/2, f'{u:.1f}%', ha='center', va='center', fontweight='bold', color='white')
            if o > 5:
                ax.text(i, u + o/2, f'{o:.1f}%', ha='center', va='center', fontweight='bold', color='white')

        ax.set_ylabel('Percentage')
        ax.set_title(f'{mech}: Underbid vs Overbid (±{threshold*100:.0f}% threshold)')
        ax.set_xticks(x)
        ax.set_xticklabels(groups)
        ax.legend()
        ax.set_ylim(0, 105)

        plt.tight_layout()

        mech_dir = output_dir / 'by_mechanism'
        mech_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(mech_dir / f'{mech.lower()}_comparison.png', dpi=300, bbox_inches='tight')
        print(f"Saved: {mech_dir / f'{mech.lower()}_comparison.png'}")
        plt.close()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main execution function."""
    print("=" * 70)
    print("HUMAN VS LLM NO EQUAL BID ANALYSIS")
    print("Equilibrium-Normalized Deviation Comparison")
    print("=" * 70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\n" + "=" * 70)
    print("LOADING DATA")
    print("=" * 70)

    human_data = load_human_synthetic_data()
    llm_data = load_llm_data()

    if not human_data:
        print("Error: No human data found")
        return

    # Process data with equilibrium normalization
    print("\n" + "=" * 70)
    print("PROCESSING DATA")
    print("=" * 70)

    human_processed = process_human_data(human_data)
    llm_processed = process_llm_data(llm_data)

    print(f"\nProcessed Human data: {len(human_processed)} observations")
    print(f"Processed LLM data: {len(llm_processed)} observations")

    # Compute and save statistics for each threshold
    print("\n" + "=" * 70)
    print("COMPUTING STATISTICS")
    print("=" * 70)

    all_stats = []
    for thresh_name, threshold in EQUILIBRIUM_THRESHOLDS.items():
        print(f"\n{thresh_name} (±{threshold*100:.0f}%):")

        human_stats = compute_statistics(human_processed, threshold, 'Human')
        print(f"  Human: {human_stats['underbid_pct']:.1f}% underbid, {human_stats['overbid_pct']:.1f}% overbid "
              f"(n={human_stats['filtered_n']}, {human_stats['pct_removed']:.1f}% removed)")
        all_stats.append({**human_stats, 'threshold_name': thresh_name})

        if not llm_processed.empty:
            llm_stats = compute_statistics(llm_processed, threshold, 'LLM')
            print(f"  LLM: {llm_stats['underbid_pct']:.1f}% underbid, {llm_stats['overbid_pct']:.1f}% overbid "
                  f"(n={llm_stats['filtered_n']}, {llm_stats['pct_removed']:.1f}% removed)")
            all_stats.append({**llm_stats, 'threshold_name': thresh_name})

    # Save statistics
    stats_df = pd.DataFrame(all_stats)
    stats_df.to_csv(OUTPUT_DIR / 'statistics_summary.csv', index=False)
    print(f"\nStatistics saved to: {OUTPUT_DIR / 'statistics_summary.csv'}")

    # Generate plots
    print("\n" + "=" * 70)
    print("GENERATING PLOTS")
    print("=" * 70)

    # Main threshold grid comparison
    plot_threshold_grid(human_processed, llm_processed, OUTPUT_DIR / 'threshold_grid_comparison.png')

    # Individual threshold plots
    for thresh_name, threshold in EQUILIBRIUM_THRESHOLDS.items():
        # Distribution plot
        plot_deviation_distributions(
            human_processed, llm_processed, threshold,
            OUTPUT_DIR / f'human_vs_llm_eq_normalized_{thresh_name}.png'
        )

        # Stacked bar plot
        plot_stacked_bar_comparison(
            human_processed, llm_processed, threshold,
            OUTPUT_DIR / f'human_vs_llm_stacked_{thresh_name}.png'
        )

    # By mechanism plots (using 10% threshold)
    plot_by_mechanism(human_processed, llm_processed, 0.10, OUTPUT_DIR)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Quick sanity checks
    if 'auction_type' in human_processed.columns:
        print("\nBy Auction Type (10% threshold):")
        for mech in human_processed['auction_type'].unique():
            mech_data = human_processed[human_processed['auction_type'] == mech]
            filtered = filter_remove_equilibrium_band(mech_data, 0.10)
            if len(filtered) > 0:
                under_pct = 100 * len(filtered[filtered['category'] == 'Underbid']) / len(filtered)
                over_pct = 100 * len(filtered[filtered['category'] == 'Overbid']) / len(filtered)
                print(f"  {mech}: {under_pct:.1f}% underbid, {over_pct:.1f}% overbid (n={len(filtered)})")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nOutput saved to: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()

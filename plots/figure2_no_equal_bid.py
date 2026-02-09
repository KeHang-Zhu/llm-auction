"""
Create figure2-style stacked bar plots showing Overbid vs Underbid proportions
AFTER removing Equal Bid category (±10% threshold) for all auction types.

This script:
1. Loads data for all 6 auction types from figure2.py
2. Classifies bids using ±10% threshold
3. REMOVES Equal Bid category
4. Calculates Underbid/Overbid proportions (only these two categories)
5. Creates horizontal stacked bar plot comparing Human vs LLM

Author: Analysis for LLM Auction Project
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from matplotlib.patches import Patch

# Set style - match figure2.py exactly
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
BASE_DIR = PROJECT_ROOT / 'experiment_logs' / 'V10'
# OUTPUT_DIR = Path(__file__).parent  # Save outputs to plots folder

# Auction configurations - same as figure2.py
AUCTION_CONFIGS = {
    'fpsb_ipv': {
        'name': 'First-Price IPV',
        'human_name': 'First-Price IPV',
        'theoretical_bid': lambda v, N=3: (N-1)/N * v,  # 2/3 * v
        'tolerance': 0.1,  # ±10% for classification
        'is_clock': False,
    },
    'spsb_ipv': {
        'name': 'Second-Price IPV',
        'human_name': 'Second-Price IPV',
        'theoretical_bid': lambda v, N=3: v,  # Truthful
        'tolerance': 0.1,
        'is_clock': False,
    },
    'spsb_apv': {
        'name': 'Second-Price APV',
        'human_name': 'SPSB (Li 2017)',
        'theoretical_bid': lambda v, N=3: v,  # Truthful
        'tolerance': 0.1,
        'is_clock': False,
    },
    'ascending_clock_apv': {
        'name': 'Ascending Clock APV',
        'human_name': 'Ascending Clock (Li 2017)',
        'theoretical_bid': lambda v, N=3: v,  # Exit at value
        'tolerance': 0.1,  # Changed from 0.5 to 0.1 for consistency
        'is_clock': True,
        'use_merged': True,
    },
    'ascending_clock_apv_closed': {
        'name': 'AC-Closed (AC-B) APV',
        'human_name': 'AC-B (Breitmoser2022)',
        'theoretical_bid': lambda v, N=3: v,  # Exit at value
        'tolerance': 0.1,  # Changed from 0.5 to 0.1 for consistency
        'is_clock': True,
        'use_merged': True,
    },
}

# Colors - match figure2.py exactly
COLORS = {
    'Underbid': '#E74C3C',   # Red
    'Equalbid': '#2ECC71',   # Green (won't be used after removal)
    'Overbid': '#3498DB'     # Blue
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_llm_data(auction_key, config):
    """
    Load LLM experimental data for a given auction type.

    Args:
        auction_key: Directory name (e.g., 'fpsb_ipv')
        config: Auction configuration dict

    Returns:
        DataFrame with columns: player_value, bid, is_winner, seal_clock
    """
    auction_dir = BASE_DIR / auction_key

    # Try merged file first (for ascending clock auctions)
    if config.get('use_merged', False):
        merged_file = auction_dir / f"{auction_key}_merged_results.csv"
        if merged_file.exists():
            return pd.read_csv(merged_file)

    # Otherwise, load and concatenate individual run results
    csv_files = list(auction_dir.glob('**/results/*_results.csv'))
    dfs = []
    for csv_file in csv_files:
        if 'merged' not in csv_file.name:
            dfs.append(pd.read_csv(csv_file))

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def classify_bids(df, config):
    """
    Classify each bid as Underbid, Equalbid, or Overbid.

    Args:
        df: DataFrame with player_value, bid, is_winner columns
        config: Auction configuration with theoretical_bid and tolerance

    Returns:
        DataFrame with added 'classification' column
    """
    df = df.copy()

    # For clock auctions, filter to non-winners only
    if config['is_clock']:
        df = df[~df['is_winner']].copy()

    # Calculate theoretical optimal bid for each observation
    df['theoretical_bid'] = df['player_value'].apply(config['theoretical_bid'])

    # Calculate deviation
    df['deviation'] = df['bid'] - df['theoretical_bid']
    tolerance = config['tolerance']

    # Classify
    def classify_row(deviation):
        if deviation < -tolerance:
            return 'Underbid'
        elif deviation > tolerance:
            return 'Overbid'
        else:
            return 'Equalbid'

    df['classification'] = df['deviation'].apply(classify_row)

    return df


def calculate_proportions_no_equalbid(df_classified):
    """
    Calculate proportions AFTER removing Equalbid category.

    Returns only Underbid and Overbid proportions (should sum to 100%).
    """
    # Remove Equalbid
    df_filtered = df_classified[df_classified['classification'] != 'Equalbid'].copy()

    if len(df_filtered) == 0:
        return {
            'Underbid': 0,
            'Overbid': 0,
            'n': 0,
            'n_total': len(df_classified),
            'n_removed': len(df_classified),
            'pct_removed': 100.0
        }

    counts = df_filtered['classification'].value_counts()
    total = len(df_filtered)

    return {
        'Underbid': (counts.get('Underbid', 0) / total) * 100,
        'Overbid': (counts.get('Overbid', 0) / total) * 100,
        'n': total,
        'n_total': len(df_classified),
        'n_removed': len(df_classified) - total,
        'pct_removed': ((len(df_classified) - total) / len(df_classified)) * 100
    }


def load_human_data():
    """
    Load human data from auction_human.csv.

    Returns:
        DataFrame with columns: Auction, Source, Underbid, Equalbid, Overbid
    """
    human_csv = PROJECT_ROOT / 'plots' / 'auction_human.csv'
    if not human_csv.exists():
        print(f"Warning: Human data not found at {human_csv}")
        return pd.DataFrame()

    df = pd.read_csv(human_csv)

    # Filter out common value auctions (N/A values)
    df = df[df['Underbid'] != 'N/A'].copy()

    # Convert to numeric
    df['Underbid'] = pd.to_numeric(df['Underbid'])
    df['Equalbid'] = pd.to_numeric(df['Equalbid'])
    df['Overbid'] = pd.to_numeric(df['Overbid'])

    # Map human auction names to match LLM names
    name_mapping = {
        'First-Price IPV': 'First-Price IPV',
        'Second-Price IPV': 'Second-Price IPV',
        'SPSB (Li 2017)': 'Second-Price APV',
        'Ascending Clock (Li 2017)': 'Ascending Clock APV',
        'AC-B (Breitmoser2022)': 'AC-Closed (AC-B) APV',
    }
    df['Auction'] = df['Auction'].map(name_mapping)
    df['Source'] = 'Human'

    return df[['Auction', 'Source', 'Underbid', 'Equalbid', 'Overbid']]


def process_human_data_no_equalbid(human_df):
    """
    Recalculate human proportions after removing Equalbid category.
    """
    results = []

    for _, row in human_df.iterrows():
        # Calculate proportions without Equalbid
        total_no_eq = row['Underbid'] + row['Overbid']

        if total_no_eq == 0:
            underbid_pct = 0
            overbid_pct = 0
        else:
            underbid_pct = (row['Underbid'] / total_no_eq) * 100
            overbid_pct = (row['Overbid'] / total_no_eq) * 100

        results.append({
            'Auction': row['Auction'],
            'Source': 'Human',
            'Underbid': underbid_pct,
            'Overbid': overbid_pct,
            'pct_removed': row['Equalbid']
        })

    return pd.DataFrame(results)


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_all_auctions():
    """
    Process all auction types and return results WITHOUT Equalbid category.

    Returns:
        DataFrame with columns: Auction, Source, Underbid, Overbid, N, pct_removed
    """
    results = []

    for auction_key, config in AUCTION_CONFIGS.items():
        print(f"\nProcessing {config['name']}...")

        # Load LLM data
        df = load_llm_data(auction_key, config)
        if df.empty:
            print(f"  Warning: No data found for {auction_key}")
            continue

        print(f"  Loaded {len(df)} observations")

        # Classify bids (with ±10% threshold)
        df_classified = classify_bids(df, config)
        print(f"  After filtering: {len(df_classified)} observations")

        # Calculate proportions WITHOUT Equalbid
        proportions = calculate_proportions_no_equalbid(df_classified)

        results.append({
            'Auction': config['name'],
            'Source': 'LLM',
            'Underbid': proportions['Underbid'],
            'Overbid': proportions['Overbid'],
            'N': proportions['n'],
            'N_total': proportions['n_total'],
            'N_removed': proportions['n_removed'],
            'pct_removed': proportions['pct_removed']
        })

        print(f"  After removing Equalbid ({proportions['pct_removed']:.1f}%):")
        print(f"    Underbid: {proportions['Underbid']:.1f}%, "
              f"Overbid: {proportions['Overbid']:.1f}% (n={proportions['n']})")

    return pd.DataFrame(results)


# =============================================================================
# VISUALIZATION
# =============================================================================

def create_stacked_bar_plot(combined_df, output_path):
    """
    Create horizontal stacked bar plot showing Underbid vs Overbid
    (after removing Equalbid) for all auction types.

    Style matches figure2.py:
    - Human bars with '//' hatch pattern
    - LLM bars solid
    - Horizontal stacked bars
    """
    # Define auction order (reversed for barh to show top to bottom correctly)
    auction_order = [
        'Ascending Clock APV',
        'AC-Closed (AC-B) APV',
        'Second-Price APV',
        'Second-Price IPV',
        'First-Price IPV',
    ]

    # Filter and ensure order
    combined_df = combined_df[combined_df['Auction'].isin(auction_order)].copy()

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))

    n_auctions = len(auction_order)
    y_positions = np.arange(n_auctions)
    bar_height = 0.35

    for i, auction in enumerate(auction_order):
        auction_data = combined_df[combined_df['Auction'] == auction]

        # Plot Human bar (top) with hatch pattern
        human_data = auction_data[auction_data['Source'] == 'Human']
        if not human_data.empty:
            row = human_data.iloc[0]
            y_pos = i + bar_height/2

            # Stack: Underbid + Overbid (should sum to 100%)
            ax.barh(y_pos, row['Underbid'], bar_height,
                   color=COLORS['Underbid'], alpha=0.7, hatch='//', edgecolor='white')
            ax.barh(y_pos, row['Overbid'], bar_height,
                   left=row['Underbid'], color=COLORS['Overbid'], alpha=0.7,
                   hatch='//', edgecolor='white')

            # Add percentage labels
            if row['Underbid'] > 8:
                ax.text(row['Underbid']/2, y_pos, f"{row['Underbid']:.0f}%",
                       ha='center', va='center', fontsize=9, fontweight='bold', color='white')
            if row['Overbid'] > 8:
                ax.text(row['Underbid'] + row['Overbid']/2, y_pos, f"{row['Overbid']:.0f}%",
                       ha='center', va='center', fontsize=9, fontweight='bold', color='white')

            # Add annotation showing % removed
            if 'pct_removed' in row:
                ax.text(102, y_pos, f"({row['pct_removed']:.0f}% removed)",
                       ha='left', va='center', fontsize=8, color='gray')

        # Plot LLM bar (bottom) solid fill
        llm_data = auction_data[auction_data['Source'] == 'LLM']
        if not llm_data.empty:
            row = llm_data.iloc[0]
            y_pos = i - bar_height/2

            # Stack: Underbid + Overbid
            ax.barh(y_pos, row['Underbid'], bar_height,
                   color=COLORS['Underbid'], alpha=0.7, edgecolor='white')
            ax.barh(y_pos, row['Overbid'], bar_height,
                   left=row['Underbid'], color=COLORS['Overbid'], alpha=0.7,
                   edgecolor='white')

            # Add percentage labels
            if row['Underbid'] > 8:
                ax.text(row['Underbid']/2, y_pos, f"{row['Underbid']:.0f}%",
                       ha='center', va='center', fontsize=9, fontweight='bold', color='white')
            if row['Overbid'] > 8:
                ax.text(row['Underbid'] + row['Overbid']/2, y_pos, f"{row['Overbid']:.0f}%",
                       ha='center', va='center', fontsize=9, fontweight='bold', color='white')

            # Add annotation
            if 'N' in row:
                ax.text(102, y_pos, f"n={row['N']} ({row['pct_removed']:.0f}% removed)",
                       ha='left', va='center', fontsize=8, color='gray')

    # Customize plot
    ax.set_yticks(y_positions)
    ax.set_yticklabels(auction_order)
    ax.set_xlabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_xlim(0, 100)
    # ax.set_title('Underbid vs Overbid After Removing Equal Bid (±10% Threshold)\nHuman vs LLM Across All Auction Types',
    #             fontsize=14, fontweight='bold', pad=20)

    # Add legend
    legend_elements = [
        Patch(facecolor=COLORS['Underbid'], alpha=0.7, label='Underbid'),
        Patch(facecolor=COLORS['Overbid'], alpha=0.7, label='Overbid'),
        Patch(facecolor='gray', alpha=0.7, label='GPT-4o (solid)'),
        Patch(facecolor='gray', alpha=0.7, hatch='//', edgecolor='black', label='Human (hatched)')
    ]
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.15, 0.5),
             frameon=True, fontsize=10)

    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save
    # output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")

    plt.close()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main execution function."""
    print("="*80)
    print("NO EQUAL BID ANALYSIS: All Auction Types (±10% Threshold)")
    print("="*80)

    # Process LLM data
    print("\n" + "="*80)
    print("PROCESSING LLM DATA")
    print("="*80)
    llm_results = process_all_auctions()

    # Load and process human data
    print("\n" + "="*80)
    print("PROCESSING HUMAN DATA")
    print("="*80)
    human_df = load_human_data()
    if not human_df.empty:
        human_results = process_human_data_no_equalbid(human_df)
        print(f"Processed {len(human_results)} human auction types")
    else:
        human_results = pd.DataFrame()

    # Combine data
    if not human_results.empty:
        combined_df = pd.concat([human_results, llm_results], ignore_index=True)
    else:
        combined_df = llm_results

    # Save combined data
    output_csv = 'figure2_by_auction_type_10pct.csv'
    # output_csv.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_csv, index=False)
    print(f"\nData saved to: {output_csv}")

    # Create plot
    print("\n" + "="*80)
    print("CREATING VISUALIZATION")
    print("="*80)
    output_plot =  'figure2_by_auction_type_10pct.png'
    create_stacked_bar_plot(combined_df, output_plot)

    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(combined_df.to_string(index=False))

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

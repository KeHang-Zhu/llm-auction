import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# Constants and Configuration
BASE_DIR = Path('/Users/kehangzh/Desktop/llm-auction/experiment_logs/V10')

# Auction configurations with theoretical bid functions
AUCTION_CONFIGS = {
    'fpsb_ipv': {
        'name': 'First-Price IPV',
        'human_name': 'First-Price IPV',
        'theoretical_bid': lambda v, N=3: (N-1)/N * v,  # 2/3 * v
        'tolerance': 0.1,
        'is_clock': False,
    },
    'spsb_ipv': {
        'name': 'Second-Price IPV',
        'human_name': 'Second-Price IPV',
        'theoretical_bid': lambda v, N=3: v,  # Truthful
        'tolerance': 0.1,
        'is_clock': False,
    },
    'third_price_ipv': {
        'name': 'Third-Price IPV',
        'human_name': 'Third-Price IPV',
        'theoretical_bid': lambda v, N=3: (N-1)/(N-2) * v,  # 2 * v
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
        'tolerance': 0.5,  # One clock cycle
        'is_clock': True,
        'use_merged': True,
    },
    'ascending_clock_apv_closed': {
        'name': 'AC-Closed (AC-B) APV',
        'human_name': 'AC-B (Breitmoser2022)',
        'theoretical_bid': lambda v, N=3: v,  # Exit at value
        'tolerance': 0.5,  # One clock cycle
        'is_clock': True,
        'use_merged': True,
    },
}


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


def calculate_proportions(df_classified):
    """
    Calculate Underbid/Equalbid/Overbid proportions.

    Args:
        df_classified: DataFrame with 'classification' column

    Returns:
        Dict with keys: underbid, equalbid, overbid (percentages 0-100)
    """
    if len(df_classified) == 0:
        return {'underbid': 0, 'equalbid': 0, 'overbid': 0, 'n': 0}

    counts = df_classified['classification'].value_counts()
    total = len(df_classified)

    return {
        'underbid': (counts.get('Underbid', 0) / total) * 100,
        'equalbid': (counts.get('Equalbid', 0) / total) * 100,
        'overbid': (counts.get('Overbid', 0) / total) * 100,
        'n': total
    }


def process_all_auctions():
    """
    Process all auction types and return combined results.

    Returns:
        DataFrame with columns: Auction, Source, Underbid, Equalbid, Overbid, N
    """
    results = []

    for auction_key, config in AUCTION_CONFIGS.items():
        print(f"Processing {config['name']}...")

        # Load LLM data
        df = load_llm_data(auction_key, config)
        if df.empty:
            print(f"  Warning: No data found for {auction_key}")
            continue

        print(f"  Loaded {len(df)} observations")

        # Classify bids
        df_classified = classify_bids(df, config)
        print(f"  After filtering: {len(df_classified)} observations")

        # Calculate proportions
        proportions = calculate_proportions(df_classified)

        results.append({
            'Auction': config['name'],
            'Source': 'LLM',
            'Underbid': proportions['underbid'],
            'Equalbid': proportions['equalbid'],
            'Overbid': proportions['overbid'],
            'N': proportions['n']
        })

        print(f"  Underbid: {proportions['underbid']:.1f}%, "
              f"Equalbid: {proportions['equalbid']:.1f}%, "
              f"Overbid: {proportions['overbid']:.1f}%")

    return pd.DataFrame(results)


def load_human_data():
    """
    Load human data from auction_human.csv.

    Returns:
        DataFrame with columns: Auction, Source, Underbid, Equalbid, Overbid
    """
    df = pd.read_csv('./auction_human.csv')

    # Filter out common value auctions (N/A values)
    df = df[df['Underbid'] != 'N/A'].copy()

    # Convert to numeric
    df['Underbid'] = pd.to_numeric(df['Underbid'])
    df['Equalbid'] = pd.to_numeric(df['Equalbid'])
    df['Overbid'] = pd.to_numeric(df['Overbid'])

    # Map human auction names to simpler LLM names
    name_mapping = {
        'First-Price IPV': 'First-Price IPV',
        'Second-Price IPV': 'Second-Price IPV',
        'Third-Price IPV': 'Third-Price IPV',
        'SPSB (Li 2017)': 'Second-Price APV',
        'Ascending Clock (Li 2017)': 'Ascending Clock APV',
        'AC-B (Breitmoser2022)': 'AC-B',
    }
    df['Auction'] = df['Auction'].map(name_mapping)

    df['Source'] = 'Human'

    return df[['Auction', 'Source', 'Underbid', 'Equalbid', 'Overbid']]


def create_stacked_bar_plot(combined_df):
    """
    Create 100% stacked bar plot with vertical layout.

    Args:
        combined_df: DataFrame with Human and LLM data
    """
    # Define auction order (custom order specified, top to bottom)
    auction_order = [
        'Ascending Clock APV',
        'Second-Price IPV',
        'AC-B',
        'Third-Price IPV',
        'Second-Price APV',
        'First-Price IPV',
    ]

    # Filter and sort
    combined_df = combined_df[combined_df['Auction'].isin(auction_order)]

    # Color scheme
    colors = {
        'Underbid': '#E74C3C',   # Red
        'Equalbid': '#2ECC71',   # Green
        'Overbid': '#3498DB'     # Blue
    }

    # Create figure (wider to accommodate legend on the right)
    fig, ax = plt.subplots(figsize=(12, 8))

    n_auctions = len(auction_order)
    y_positions = np.arange(n_auctions)
    bar_height = 0.35

    for i, auction in enumerate(auction_order):
        auction_data = combined_df[combined_df['Auction'] == auction]

        # Plot Human bar (bottom) with hatch pattern
        human_data = auction_data[auction_data['Source'] == 'Human']
        if not human_data.empty:
            row = human_data.iloc[0]
            y_pos = i + bar_height/2

            # Stack segments with hatch pattern '//'
            ax.barh(y_pos, row['Underbid'], bar_height,
                   color=colors['Underbid'], alpha=0.7, hatch='//', edgecolor='white')
            ax.barh(y_pos, row['Equalbid'], bar_height,
                   left=row['Underbid'], color=colors['Equalbid'], alpha=0.7,
                   hatch='//', edgecolor='white')
            ax.barh(y_pos, row['Overbid'], bar_height,
                   left=row['Underbid']+row['Equalbid'],
                   color=colors['Overbid'], alpha=0.7, hatch='//', edgecolor='white')

        # Plot LLM bar (top) solid fill
        llm_data = auction_data[auction_data['Source'] == 'LLM']
        if not llm_data.empty:
            row = llm_data.iloc[0]
            y_pos = i - bar_height/2

            # Stack segments (solid fill, no hatch)
            ax.barh(y_pos, row['Underbid'], bar_height,
                   color=colors['Underbid'], alpha=0.7, edgecolor='white')
            ax.barh(y_pos, row['Equalbid'], bar_height,
                   left=row['Underbid'], color=colors['Equalbid'], alpha=0.7,
                   edgecolor='white')
            ax.barh(y_pos, row['Overbid'], bar_height,
                   left=row['Underbid']+row['Equalbid'],
                   color=colors['Overbid'], alpha=0.7, edgecolor='white')

    # Customize plot
    ax.set_yticks(y_positions)
    ax.set_yticklabels(auction_order)
    ax.set_xlabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.set_title('Bid Classification: Human vs LLM\nUnderbid, Equalbid, and Overbid Proportions',
                fontsize=14, fontweight='bold', pad=20)

    # Add legend (outside the plot, on the right)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors['Underbid'], alpha=0.7, label='Underbid'),
        Patch(facecolor=colors['Equalbid'], alpha=0.7, label='Equalbid'),
        Patch(facecolor=colors['Overbid'], alpha=0.7, label='Overbid'),
        Patch(facecolor='gray', alpha=0.7, label='LLM (solid)'),
        Patch(facecolor='gray', alpha=0.7, hatch='//', edgecolor='black', label='Human (hatched)')
    ]
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5),
             frameon=True, fontsize=10)

    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save
    output_path = Path('./figure2_stacked_bars.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")

    plt.show()


def main():
    """Main execution function."""
    print("="*80)
    print("FIGURE 2: BID CLASSIFICATION - 100% STACKED BAR PLOTS")
    print("="*80)

    # Process LLM data
    print("\n" + "="*80)
    print("PROCESSING LLM DATA")
    print("="*80)
    llm_results = process_all_auctions()

    # Load human data
    print("\n" + "="*80)
    print("LOADING HUMAN DATA")
    print("="*80)
    human_results = load_human_data()
    print(f"Loaded {len(human_results)} human auction types")

    # Combine data
    combined_df = pd.concat([human_results, llm_results], ignore_index=True)

    # Save combined data
    output_csv = Path('./figure2_classification_data.csv')
    combined_df.to_csv(output_csv, index=False)
    print(f"\nData saved to: {output_csv}")

    # Create plot
    print("\n" + "="*80)
    print("CREATING VISUALIZATION")
    print("="*80)
    create_stacked_bar_plot(combined_df)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

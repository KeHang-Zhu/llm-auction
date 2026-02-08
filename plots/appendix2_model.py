import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import json
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# Base directory
base_dir = Path('/Users/kehangzh/Desktop/llm-auction/robustness_logs')

# Define auction types and their parameters
auction_configs = {
    'fpsb_ipv': {
        'name': 'First-Price IPV',
        'theoretical_bid': lambda v, N=3: (N-1)/N * v,
        'type': 'ipv',
    },
    'spsb_ipv': {
        'name': 'Second-Price IPV',
        'theoretical_bid': lambda v, N=3: v,
        'type': 'ipv',
    },
    'spsb_apv': {
        'name': 'Second-Price APV',
        'theoretical_bid': lambda v, N=3: v,
        'type': 'apv',
    },
    'ascending_clock_apv': {
        'name': 'Ascending Clock APV',
        'theoretical_bid': lambda v, N=3: v,
        'type': 'apv',
        'is_clock': True,
    },
    'ascending_clock_apv_closed': {
        'name': 'AC-Closed (AC-B) APV',
        'theoretical_bid': lambda v, N=3: v,
        'type': 'apv',
        'is_clock': True,
    },
    'third_price_ipv': {
        'name': 'Third-Price IPV',
        'theoretical_bid': lambda v, N=5: (N-1)/(N-2) * v,
        'type': 'ipv',
    },
    'common_value_first': {
        'name': 'First-Price CV',
        'type': 'cv',
        'use_profit': True,
    },
    'common_value_second': {
        'name': 'Second-Price CV',
        'type': 'cv',
        'use_profit': True,
    },
}

# Define models
model_configs = {
    'human': {
        'display_name': 'Human',
        'color': '#2E86AB',  # Blue for human
    },
    'claude_sonnet': {
        'display_name': 'Claude Sonnet',
        'color': '#A23B72',
    },
    'gemini': {
        'display_name': 'Gemini',
        'color': '#F18F01',
    },
    'gpt4o_temp01': {
        'display_name': 'GPT-4o (temp=0.1)',
        'color': '#9B59B6',
    },
    'gpt4o_temp10': {
        'display_name': 'GPT-4o (temp=1.0)',
        'color': '#3498DB',
    },
    'gpt5mini': {
        'display_name': 'GPT-5-mini',
        'color': '#2ECC71',
    },
    'llama': {
        'display_name': 'Llama',
        'color': '#C73E1D',
    },
}


def calculate_cv_deviation_from_json(auction_dir, auction_type='first_price'):
    """
    Calculate CV auction deviation using theoretical profit benchmarks from JSON files.

    For First-Price CV: π* ≈ 2ε/(n+1)
    For Second-Price CV: π* ≈ ε/(n+1)

    where ε_i = signal_i - common_value
    """
    # Find all JSON result files
    json_files = list(auction_dir.glob('**/raw_data/result_*.json'))

    if not json_files:
        return None

    all_deviations = []
    n_agents = 3  # number of players

    for json_file in json_files:
        with open(json_file, 'r') as f:
            data = json.load(f)

        # Process each round in the file
        for round_key, round_data in data.items():
            if not round_key.startswith('round_'):
                continue

            # Extract data
            signals = round_data['value']  # private signals for each player
            common_value = round_data['common']  # true common value
            profits = round_data['profit']  # actual profits
            winner_name = round_data['history']['winner']['winner']

            # Find winner index
            bidding_history = round_data['history']['bidding history']
            winner_idx = None
            for idx, bid_info in enumerate(bidding_history):
                if bid_info['agent'] == winner_name:
                    winner_idx = idx
                    break

            if winner_idx is None:
                continue

            # Calculate winner's epsilon
            winner_signal = signals[winner_idx]
            epsilon = winner_signal - common_value

            # Calculate theoretical profit
            if auction_type == 'first_price':
                theoretical_profit = (2 * epsilon) / (n_agents + 1)
            else:  # second_price
                theoretical_profit = epsilon / (n_agents + 1)

            # Actual profit
            actual_profit = profits[winner_idx]

            # Absolute deviation
            deviation = abs(actual_profit - theoretical_profit)

            all_deviations.append(deviation)

    if not all_deviations:
        return None

    # Calculate summary statistics
    deviations_array = np.array(all_deviations)

    # Mean absolute deviation
    mad = deviations_array.mean()

    # Fixed scaling factor for CV auctions
    scaling_factor = 20

    # SMAD
    smad = 100 * mad / scaling_factor

    # Standard error
    se_mad = deviations_array.std() / np.sqrt(len(deviations_array))
    se_smad = 100 * se_mad / scaling_factor

    # 95% CI
    ci_lower = smad - 1.96 * se_smad
    ci_upper = smad + 1.96 * se_smad

    return {
        'smad': smad,
        'se': se_smad,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'n_observations': len(all_deviations)
    }


def calculate_deviation(df, config):
    """
    Calculate the Scaled Mean Absolute Deviation (SMAD).

    Args:
        df: DataFrame with player_value, bid, is_winner columns
        config: Auction configuration

    Returns:
        Dict with smad, se, ci_lower, ci_upper, n_observations
    """
    if config.get('use_profit', False):
        # For common value auctions, this should not be used
        # CV auctions should use calculate_cv_deviation_from_json
        raise ValueError("CV auctions should use calculate_cv_deviation_from_json")
    else:
        # For IPV/APV auctions, use bid-based deviation
        df = df.copy()
        df['theoretical_bid'] = df['player_value'].apply(config['theoretical_bid'])
        df['deviation'] = np.abs(df['bid'] - df['theoretical_bid'])

        # Calculate MAD
        mad = df['deviation'].mean()

        # Fixed scaling factor for IPV/APV auctions
        scaling_factor = 25
        smad = 100 * mad / scaling_factor

        # Calculate standard error
        n = len(df)
        se_mad = df['deviation'].std() / np.sqrt(n)
        se_smad = 100 * se_mad / scaling_factor

    # Calculate 95% confidence interval
    ci_lower = smad - 1.96 * se_smad
    ci_upper = smad + 1.96 * se_smad

    return {
        'smad': smad,
        'se': se_smad,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'n_observations': len(df)
    }


def parse_ci_string(ci_str):
    """Parse CI string like '[29.4, 127.4]' or 'MC, no CI'"""
    if pd.isna(ci_str) or 'no CI' in str(ci_str):
        return None, None

    # Extract numbers from [lower, upper] format
    match = re.search(r'\[([0-9.]+),\s*([0-9.]+)\]', str(ci_str))
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def load_human_data():
    """
    Load human data from auction_human.csv.

    Returns:
        DataFrame with columns: auction, smad, ci_lower, ci_upper, has_ci
    """
    df = pd.read_csv('./auction_human.csv')

    # Map human format names to standard names
    format_mapping = {
        'First-Price IPV': 'First-Price IPV',
        'Second-Price IPV': 'Second-Price IPV',
        'Third-Price IPV': 'Third-Price IPV',
        'AC-B (Breitmoser2022)': 'AC-Closed (AC-B) APV',
        'SPSB (Li 2017)': 'Second-Price APV',
        'Ascending Clock (Li 2017)': 'Ascending Clock APV',
        'First-Price Common Value': 'First-Price CV',
        'Second-Price Common Value': 'Second-Price CV',
    }

    human_data = []
    for _, row in df.iterrows():
        if pd.isna(row['Auction']):
            continue

        auction_format = row['Auction'].strip()
        standard_name = format_mapping.get(auction_format, auction_format)

        # Skip if not in our mapping
        if standard_name not in format_mapping.values():
            continue

        smad = row['SMAD']
        ci_lower, ci_upper = parse_ci_string(row['CI'])

        human_data.append({
            'auction': standard_name,
            'model': 'Human',
            'model_key': 'human',
            'smad': smad,
            'ci_lower': ci_lower if ci_lower is not None else smad,
            'ci_upper': ci_upper if ci_upper is not None else smad,
            'has_ci': ci_lower is not None,
            'se': 0,  # Not available for human data
            'n': 0  # Not available for human data
        })

    return pd.DataFrame(human_data)


def load_model_data(auction_key, model_key):
    """
    Load experimental data for a given auction type and model.

    Args:
        auction_key: Auction type (e.g., 'fpsb_ipv')
        model_key: Model identifier (e.g., 'claude_sonnet')

    Returns:
        DataFrame or None if not found
    """
    # Construct directory name
    dir_name = f"{auction_key}_{model_key}"
    auction_dir = base_dir / dir_name

    if not auction_dir.exists():
        return None

    # Find CSV file
    csv_files = list(auction_dir.glob('**/results/*_results.csv'))
    if not csv_files:
        return None

    # Read the first CSV file found
    df = pd.read_csv(csv_files[0])
    return df


def process_all_models():
    """
    Process all auction types and models, calculate SMAD.

    Returns:
        DataFrame with columns: auction, model, smad, ci_lower, ci_upper, n
    """
    results = []

    # First, load human data
    print(f"\n{'='*80}")
    print("Loading Human Data")
    print('='*80)
    human_df = load_human_data()
    results.extend(human_df.to_dict('records'))
    print(f"Loaded {len(human_df)} human auction results")

    # Then process LLM models
    for auction_key, auction_config in auction_configs.items():
        print(f"\n{'='*80}")
        print(f"Processing {auction_config['name']}")
        print('='*80)

        for model_key, model_config in model_configs.items():
            # Skip human (already processed)
            if model_key == 'human':
                continue

            print(f"  {model_config['display_name']}...", end=" ")

            # For CV auctions, use JSON-based calculation
            if auction_config.get('use_profit', False):
                # Construct directory path
                dir_name = f"{auction_key}_{model_key}"
                auction_dir = base_dir / dir_name

                if not auction_dir.exists():
                    print("No data found")
                    continue

                # Determine auction type
                auction_type = 'first_price' if 'first' in auction_key else 'second_price'

                # Calculate deviation from JSON files
                deviation_stats = calculate_cv_deviation_from_json(auction_dir, auction_type)

                if deviation_stats is None:
                    print("No data found")
                    continue

                print(f"Loaded {deviation_stats['n_observations']} observations", end=" ")
            else:
                # For IPV/APV auctions, use CSV-based calculation
                # Load data
                df = load_model_data(auction_key, model_key)

                if df is None or df.empty:
                    print("No data found")
                    continue

                print(f"Loaded {len(df)} observations", end=" ")

                # For ascending clock auctions, filter to non-winners only
                if auction_config.get('is_clock', False):
                    original_count = len(df)
                    df = df[~df['is_winner']].copy()
                    filtered_count = len(df)
                    print(f"→ {filtered_count} non-winners", end=" ")

                # Calculate deviation
                deviation_stats = calculate_deviation(df, auction_config)

            results.append({
                'auction': auction_config['name'],
                'model': model_config['display_name'],
                'model_key': model_key,
                'smad': deviation_stats['smad'],
                'se': deviation_stats['se'],
                'ci_lower': deviation_stats['ci_lower'],
                'ci_upper': deviation_stats['ci_upper'],
                'n': deviation_stats['n_observations']
            })

            print(f"SMAD: {deviation_stats['smad']:.2f}%")

    return pd.DataFrame(results)


def create_comparison_plot(results_df):
    """
    Create horizontal bar plot comparing models across auction types.

    Args:
        results_df: DataFrame with SMAD results for all models
    """
    # Sort auctions by human SMAD values (to match figure1.py)
    human_data = results_df[results_df['model'] == 'Human'].copy()
    auction_order = human_data.sort_values('smad')['auction'].tolist()

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))

    # Set up y positions
    n_auctions = len(auction_order)
    n_models = len(model_configs)
    y = np.arange(n_auctions)
    bar_height = 0.12  # Thinner bars for multiple models

    # Plot bars for each model
    for i, (model_key, model_config) in enumerate(model_configs.items()):
        model_name = model_config['display_name']
        model_data = results_df[results_df['model'] == model_name]

        y_positions = []
        smads = []
        ci_lowers = []
        ci_uppers = []
        has_ci_list = []

        for j, auction in enumerate(auction_order):
            auction_data = model_data[model_data['auction'] == auction]
            if len(auction_data) > 0:
                row = auction_data.iloc[0]
                # Offset position for each model
                y_pos = j + (i - n_models/2 + 0.5) * bar_height
                y_positions.append(y_pos)
                smads.append(row['smad'])
                ci_lowers.append(row['smad'] - row['ci_lower'])
                ci_uppers.append(row['ci_upper'] - row['smad'])
                has_ci_list.append(row.get('has_ci', True))

        # Plot bars
        ax.barh(y_positions, smads, bar_height,
                color=model_config['color'], alpha=0.7,
                label=model_name)

        # Add error bars (only for data with CI)
        if len(smads) > 0:
            ax.errorbar(smads, y_positions,
                       xerr=[ci_lowers, ci_uppers],
                       fmt='none', ecolor='black', capsize=3,
                       capthick=1, linewidth=1, alpha=0.6)

            # Add markers for data without CI
            for pos, smad, has_ci in zip(y_positions, smads, has_ci_list):
                if not has_ci:
                    ax.plot(smad, pos, 'k*', markersize=8)

    # Customize plot
    ax.set_ylabel('Auction Format', fontsize=13, fontweight='bold')
    ax.set_xlabel('Scaled Mean Absolute Deviation (SMAD) from Theoretical Optimum (%)',
                  fontsize=13, fontweight='bold')
    ax.set_title('Model Comparison: Bidding Deviation from Theoretical Equilibrium',
                 fontsize=15, fontweight='bold', pad=20)

    # Set y-axis
    ax.set_yticks(y)
    ax.set_yticklabels(auction_order)

    # Add legend
    ax.legend(loc='lower right', frameon=True, fontsize=10, ncol=2)

    # Add vertical line at 0
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.5)

    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save figure
    output_path = Path('./appendix2_model_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n\nPlot saved to: {output_path}")

    plt.show()


def main():
    """Main execution function."""
    print("="*80)
    print("APPENDIX 2: MODEL COMPARISON ANALYSIS")
    print("="*80)

    # Process all models and auctions
    results_df = process_all_models()

    # Save results to CSV
    output_csv = Path('./appendix2_model_results.csv')
    results_df.to_csv(output_csv, index=False)
    print(f"\n\nResults saved to: {output_csv}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY BY MODEL")
    print("="*80)
    summary = results_df.groupby('model')['smad'].agg(['mean', 'std', 'min', 'max'])
    print(summary.to_string())

    # Create visualization
    print("\n" + "="*80)
    print("CREATING VISUALIZATION")
    print("="*80)
    create_comparison_plot(results_df)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

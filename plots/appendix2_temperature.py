import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import json
from pathlib import Path
from scipy import stats

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
    'gpt4o_temp01': {
        'display_name': 'GPT-4o (temp=0.1)',
        'color': '#C44569',  # Red-pink for low temperature
    },
    'gpt4o': {
        'display_name': 'GPT-4o (temp=0.5)',
        'color': '#F18F01',  # Orange for medium temperature
    },
    'gpt4o_temp10': {
        'display_name': 'GPT-4o (temp=1.0)',
        'color': '#6C5CE7',  # Purple for high temperature
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


def load_gpt4o_base_data():
    """
    Load GPT-4o (temp=0.5) data from theoretical_deviation_results_updated.csv.

    Returns:
        DataFrame with columns: auction, model, smad, ci_lower, ci_upper, n
    """
    df = pd.read_csv('./theoretical_deviation_results_updated.csv')

    gpt4o_data = []
    for _, row in df.iterrows():
        gpt4o_data.append({
            'auction': row['auction'],
            'model': 'GPT-4o (temp=0.5)',
            'model_key': 'gpt4o',
            'smad': row['smad'],
            'se': row['se'],
            'ci_lower': row['ci_lower'],
            'ci_upper': row['ci_upper'],
            'has_ci': True,
            'n': row['n']
        })

    return pd.DataFrame(gpt4o_data)


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

    # Load GPT-4o (temp=0.5) data from CSV
    print(f"\n{'='*80}")
    print("Loading GPT-4o (temp=0.5) Data from CSV")
    print('='*80)
    gpt4o_df = load_gpt4o_base_data()
    results.extend(gpt4o_df.to_dict('records'))
    print(f"Loaded {len(gpt4o_df)} GPT-4o (temp=0.5) auction results")

    # Then process other temperature LLM models from robustness_logs
    for auction_key, auction_config in auction_configs.items():
        print(f"\n{'='*80}")
        print(f"Processing {auction_config['name']}")
        print('='*80)

        for model_key, model_config in model_configs.items():
            # Skip human (already processed)
            if model_key == 'human':
                continue

            # Skip gpt4o base (already loaded from CSV)
            if model_key == 'gpt4o':
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
    # Filter out Third-Price IPV
    results_df = results_df[results_df['auction'] != 'Third-Price IPV'].copy()

    # Sort auctions by human SMAD values (to match figure1.py)
    human_data = results_df[results_df['model'] == 'Human'].copy()
    auction_order = human_data.sort_values('smad')['auction'].tolist()

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 11))

    # Set up y positions
    n_auctions = len(auction_order)
    n_models = len(model_configs)
    y = np.arange(n_auctions)
    bar_height = 0.15  # Adjusted for 4 models

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
    ax.set_title('Temperature Comparison: Human vs GPT-4o Bidding Behavior',
                 fontsize=15, fontweight='bold', pad=20)

    # Set y-axis
    ax.set_yticks(y)
    ax.set_yticklabels(auction_order)

    # Add legend (arranged in 2x2 grid for 4 models)
    ax.legend(loc='lower right', frameon=True, fontsize=10.5, ncol=2,
              columnspacing=1.0, handlelength=1.5)

    # Add vertical line at 0
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.5)

    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save figure
    output_path = Path('./appendix2_temperature_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n\nPlot saved to: {output_path}")

    plt.show()


def perform_statistical_tests(results_df):
    """
    Perform statistical tests comparing different temperatures.

    Returns:
        DataFrame with test results and LaTeX table string
    """
    # Filter out Third-Price IPV
    results_df = results_df[results_df['auction'] != 'Third-Price IPV'].copy()

    # Get unique auctions
    auctions = results_df[results_df['model_key'].str.startswith('gpt4o')]['auction'].unique()

    test_results = []

    for auction in auctions:
        auction_data = results_df[results_df['auction'] == auction].copy()

        # Get data for each temperature
        temp01_data = auction_data[auction_data['model_key'] == 'gpt4o_temp01']
        temp05_data = auction_data[auction_data['model_key'] == 'gpt4o']
        temp10_data = auction_data[auction_data['model_key'] == 'gpt4o_temp10']

        # Get SMAD values
        smad_01 = temp01_data['smad'].values[0] if len(temp01_data) > 0 else None
        smad_05 = temp05_data['smad'].values[0] if len(temp05_data) > 0 else None
        smad_10 = temp10_data['smad'].values[0] if len(temp10_data) > 0 else None

        # Get sample sizes
        n_01 = temp01_data['n'].values[0] if len(temp01_data) > 0 else 0
        n_05 = temp05_data['n'].values[0] if len(temp05_data) > 0 else 0
        n_10 = temp10_data['n'].values[0] if len(temp10_data) > 0 else 0

        # Get standard errors
        se_01 = temp01_data['se'].values[0] if len(temp01_data) > 0 else None
        se_05 = temp05_data['se'].values[0] if len(temp05_data) > 0 else None
        se_10 = temp10_data['se'].values[0] if len(temp10_data) > 0 else None

        # Calculate z-tests for comparing means
        # Test 1: temp=0.1 vs temp=0.5
        if smad_01 is not None and smad_05 is not None and se_01 is not None and se_05 is not None:
            z_01_05 = (smad_01 - smad_05) / np.sqrt(se_01**2 + se_05**2)
            p_01_05 = 2 * (1 - stats.norm.cdf(abs(z_01_05)))
        else:
            z_01_05, p_01_05 = None, None

        # Test 2: temp=0.5 vs temp=1.0
        if smad_05 is not None and smad_10 is not None and se_05 is not None and se_10 is not None:
            z_05_10 = (smad_05 - smad_10) / np.sqrt(se_05**2 + se_10**2)
            p_05_10 = 2 * (1 - stats.norm.cdf(abs(z_05_10)))
        else:
            z_05_10, p_05_10 = None, None

        # Test 3: temp=0.1 vs temp=1.0
        if smad_01 is not None and smad_10 is not None and se_01 is not None and se_10 is not None:
            z_01_10 = (smad_01 - smad_10) / np.sqrt(se_01**2 + se_10**2)
            p_01_10 = 2 * (1 - stats.norm.cdf(abs(z_01_10)))
        else:
            z_01_10, p_01_10 = None, None

        test_results.append({
            'auction': auction,
            'smad_01': smad_01,
            'smad_05': smad_05,
            'smad_10': smad_10,
            'n_01': n_01,
            'n_05': n_05,
            'n_10': n_10,
            'p_01_vs_05': p_01_05,
            'p_05_vs_10': p_05_10,
            'p_01_vs_10': p_01_10,
        })

    test_df = pd.DataFrame(test_results)
    return test_df


def generate_latex_table(test_df):
    """Generate LaTeX table for statistical test results."""

    latex = []
    latex.append("\\begin{table}[htbp]")
    latex.append("\\centering")
    latex.append("\\caption{Temperature Effects on Bidding Behavior: Statistical Comparison}")
    latex.append("\\label{tab:temperature_comparison}")
    latex.append("\\begin{tabular}{l|ccc|ccc}")
    latex.append("\\hline")
    latex.append("\\multirow{2}{*}{Auction Format} & \\multicolumn{3}{c|}{SMAD (\\%)} & \\multicolumn{3}{c}{P-values} \\\\")
    latex.append(" & $T=0.1$ & $T=0.5$ & $T=1.0$ & 0.1 vs 0.5 & 0.5 vs 1.0 & 0.1 vs 1.0 \\\\")
    latex.append("\\hline")

    for _, row in test_df.iterrows():
        auction_name = row['auction']
        # Format SMAD values (use 0 for missing data instead of --)
        smad_01_str = f"{row['smad_01']:.2f}" if pd.notna(row['smad_01']) else "0"
        smad_05_str = f"{row['smad_05']:.2f}" if pd.notna(row['smad_05']) else "0"
        smad_10_str = f"{row['smad_10']:.2f}" if pd.notna(row['smad_10']) else "0"

        # Format p-values with significance stars
        def format_pvalue(p):
            if pd.isna(p):
                return "--"
            if p < 0.001:
                return f"{p:.2f}***"
            elif p < 0.01:
                return f"{p:.2f}**"
            elif p < 0.05:
                return f"{p:.2f}*"
            else:
                return f"{p:.2f}"

        p_01_05_str = format_pvalue(row['p_01_vs_05'])
        p_05_10_str = format_pvalue(row['p_05_vs_10'])
        p_01_10_str = format_pvalue(row['p_01_vs_10'])

        latex.append(f"{auction_name} & {smad_01_str} & {smad_05_str} & {smad_10_str} & "
                    f"{p_01_05_str} & {p_05_10_str} & {p_01_10_str} \\\\")

    latex.append("\\hline")
    latex.append("\\end{tabular}")
    latex.append("\\begin{tablenotes}")
    latex.append("\\small")
    latex.append("\\item Note: SMAD = Scaled Mean Absolute Deviation from theoretical equilibrium. ")
    latex.append("P-values from two-sided z-tests comparing temperature effects. ")
    latex.append("Significance levels: * p<0.05, ** p<0.01, *** p<0.001.")
    latex.append("\\end{tablenotes}")
    latex.append("\\end{table}")

    return "\n".join(latex)


def generate_text_description(test_df):
    """Generate text description of statistical results."""

    text = []
    text.append("\n" + "="*80)
    text.append("STATISTICAL ANALYSIS: TEMPERATURE EFFECTS")
    text.append("="*80 + "\n")

    text.append("We examined the effect of temperature parameter (T ∈ {0.1, 0.5, 1.0}) on GPT-4o's")
    text.append("bidding behavior across seven auction formats. The temperature parameter controls")
    text.append("the randomness of the model's outputs, with lower values producing more deterministic")
    text.append("responses and higher values introducing more variability.\n")

    # Overall findings
    overall_01 = test_df['smad_01'].mean()
    overall_05 = test_df['smad_05'].mean()
    overall_10 = test_df['smad_10'].mean()

    text.append(f"Overall Performance (Mean SMAD across all auction formats):")
    text.append(f"  • Temperature 0.1: {overall_01:.2f}%")
    text.append(f"  • Temperature 0.5: {overall_05:.2f}%")
    text.append(f"  • Temperature 1.0: {overall_10:.2f}%\n")

    text.append("Key Findings:\n")

    # Count significant differences
    sig_01_05 = (test_df['p_01_vs_05'] < 0.05).sum()
    sig_05_10 = (test_df['p_05_vs_10'] < 0.05).sum()
    sig_01_10 = (test_df['p_01_vs_10'] < 0.05).sum()

    total_comparisons = len(test_df[test_df['p_01_vs_05'].notna()])

    text.append(f"1. Temperature 0.1 vs 0.5: {sig_01_05}/{total_comparisons} auction formats show")
    text.append(f"   statistically significant differences (p < 0.05).")

    temp_comparisons_05_10 = len(test_df[test_df['p_05_vs_10'].notna()])
    text.append(f"\n2. Temperature 0.5 vs 1.0: {sig_05_10}/{temp_comparisons_05_10} auction formats show")
    text.append(f"   statistically significant differences (p < 0.05).")

    temp_comparisons_01_10 = len(test_df[test_df['p_01_vs_10'].notna()])
    text.append(f"\n3. Temperature 0.1 vs 1.0: {sig_01_10}/{temp_comparisons_01_10} auction formats show")
    text.append(f"   statistically significant differences (p < 0.05).\n")

    # Detailed findings by auction
    text.append("Auction-Specific Results:\n")
    for _, row in test_df.iterrows():
        auction = row['auction']
        text.append(f"\n{auction}:")

        if pd.notna(row['smad_01']) and pd.notna(row['smad_05']) and pd.notna(row['smad_10']):
            text.append(f"  SMAD: T=0.1: {row['smad_01']:.2f}%, T=0.5: {row['smad_05']:.2f}%, T=1.0: {row['smad_10']:.2f}%")

            # Determine which is best
            if row['smad_01'] < row['smad_05'] and row['smad_01'] < row['smad_10']:
                best = "0.1"
            elif row['smad_10'] < row['smad_05'] and row['smad_10'] < row['smad_01']:
                best = "1.0"
            else:
                best = "0.5"

            text.append(f"  Best performance: Temperature {best}")

            # Significance
            sig_findings = []
            if pd.notna(row['p_01_vs_05']) and row['p_01_vs_05'] < 0.05:
                sig_findings.append(f"T=0.1 vs T=0.5 (p={row['p_01_vs_05']:.4f})")
            if pd.notna(row['p_05_vs_10']) and row['p_05_vs_10'] < 0.05:
                sig_findings.append(f"T=0.5 vs T=1.0 (p={row['p_05_vs_10']:.4f})")
            if pd.notna(row['p_01_vs_10']) and row['p_01_vs_10'] < 0.05:
                sig_findings.append(f"T=0.1 vs T=1.0 (p={row['p_01_vs_10']:.4f})")

            if sig_findings:
                text.append(f"  Significant differences: {'; '.join(sig_findings)}")
            else:
                text.append(f"  No significant differences found")
        elif pd.notna(row['smad_05']) and pd.notna(row['smad_10']):
            text.append(f"  SMAD: T=0.5: {row['smad_05']:.2f}%, T=1.0: {row['smad_10']:.2f}%")
            text.append(f"  (Temperature 0.1 data not available)")

    text.append("\n" + "="*80)
    text.append("INTERPRETATION")
    text.append("="*80 + "\n")

    if overall_10 < overall_05 < overall_01:
        text.append("Higher temperature (T=1.0) consistently produces better performance (lower SMAD),")
        text.append("suggesting that increased output variability helps GPT-4o explore more effective")
        text.append("bidding strategies across different auction mechanisms.")
    elif overall_01 < overall_05 < overall_10:
        text.append("Lower temperature (T=0.1) produces better performance (lower SMAD), suggesting")
        text.append("that more deterministic outputs help GPT-4o follow optimal bidding strategies")
        text.append("more consistently.")
    else:
        text.append("The relationship between temperature and performance varies across auction formats,")
        text.append("suggesting that optimal temperature settings may be auction-specific.")

    return "\n".join(text)


def main():
    """Main execution function."""
    print("="*80)
    print("APPENDIX 2: TEMPERATURE COMPARISON ANALYSIS")
    print("="*80)

    # Process all models and auctions
    results_df = process_all_models()

    # Save results to CSV
    output_csv = Path('./appendix2_temperature_results.csv')
    results_df.to_csv(output_csv, index=False)
    print(f"\n\nResults saved to: {output_csv}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY BY MODEL")
    print("="*80)
    summary = results_df.groupby('model')['smad'].agg(['mean', 'std', 'min', 'max'])
    print(summary.to_string())

    # Perform statistical tests
    test_df = perform_statistical_tests(results_df)

    # Generate and print text description
    description = generate_text_description(test_df)
    print(description)

    # Generate LaTeX table
    latex_table = generate_latex_table(test_df)

    # Save LaTeX table to file
    latex_output = Path('./appendix2_temperature_latex.tex')
    with open(latex_output, 'w') as f:
        f.write(latex_table)
    print(f"\nLaTeX table saved to: {latex_output}")

    # Also print LaTeX table
    print("\n" + "="*80)
    print("LATEX TABLE")
    print("="*80)
    print(latex_table)

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

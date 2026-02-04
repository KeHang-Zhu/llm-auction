import pandas as pd
import numpy as np
import json
from pathlib import Path

def calculate_cv_deviation(auction_path, auction_type='first_price'):
    """
    Calculate CV auction deviation using theoretical profit benchmarks.

    For First-Price CV: π* ≈ 2ε/(n+1)
    For Second-Price CV: π* ≈ ε/(n+1)

    where ε_i = signal_i - common_value
    """
    auction_dir = Path(auction_path)

    # Find all JSON result files
    json_files = list(auction_dir.glob('raw_data/result_*.json'))

    if not json_files:
        print(f"No JSON files found in {auction_dir}/raw_data/")
        return None

    print(f"Found {len(json_files)} JSON files")

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

            all_deviations.append({
                'actual_profit': actual_profit,
                'theoretical_profit': theoretical_profit,
                'deviation': deviation,
                'epsilon': epsilon,
                'winner_signal': winner_signal,
                'common_value': common_value
            })

    # Calculate summary statistics
    deviations_array = np.array([d['deviation'] for d in all_deviations])
    theoretical_profits = np.array([d['theoretical_profit'] for d in all_deviations])

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

    # Calculate mean theoretical profit for informational purposes (not used for scaling)
    mean_theoretical = np.abs(theoretical_profits).mean()

    return {
        'smad': smad,
        'se': se_smad,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'n_observations': len(all_deviations),
        'mean_theoretical_profit': mean_theoretical,
        'mean_actual_profit': np.mean([d['actual_profit'] for d in all_deviations]),
        'all_deviations': all_deviations
    }

# Calculate for both CV auctions
base_dir = Path('/Users/kehangzh/Desktop/llm-auction/experiment_logs/V10')

print("="*80)
print("RECALCULATING COMMON VALUE AUCTION DEVIATIONS")
print("="*80)

# First-Price CV
print("\n\nFirst-Price Common Value:")
print("-" * 60)
fp_cv_path = base_dir / 'common_value_first' / 'run_2026-01-12_22-28-21-388751'
fp_cv_results = calculate_cv_deviation(fp_cv_path, auction_type='first_price')

if fp_cv_results:
    print(f"Number of observations: {fp_cv_results['n_observations']}")
    print(f"Mean theoretical profit: ${fp_cv_results['mean_theoretical_profit']:.2f}")
    print(f"Mean actual profit: ${fp_cv_results['mean_actual_profit']:.2f}")
    print(f"SMAD: {fp_cv_results['smad']:.2f}%")
    print(f"95% CI: [{fp_cv_results['ci_lower']:.2f}%, {fp_cv_results['ci_upper']:.2f}%]")

# Second-Price CV
print("\n\nSecond-Price Common Value:")
print("-" * 60)
sp_cv_path = base_dir / 'common_value_second' / 'run_2026-01-12_21-59-13-727950'
sp_cv_results = calculate_cv_deviation(sp_cv_path, auction_type='second_price')

if sp_cv_results:
    print(f"Number of observations: {sp_cv_results['n_observations']}")
    print(f"Mean theoretical profit: ${sp_cv_results['mean_theoretical_profit']:.2f}")
    print(f"Mean actual profit: ${sp_cv_results['mean_actual_profit']:.2f}")
    print(f"SMAD: {sp_cv_results['smad']:.2f}%")
    print(f"95% CI: [{sp_cv_results['ci_lower']:.2f}%, {sp_cv_results['ci_upper']:.2f}%]")

print("\n" + "="*80)
print("COMPARISON WITH PREVIOUS RESULTS")
print("="*80)

# Load previous results
prev_results = pd.read_csv('plots/theoretical_deviation_results.csv')
prev_fp_cv = prev_results[prev_results['auction'] == 'First-Price CV'].iloc[0]
prev_sp_cv = prev_results[prev_results['auction'] == 'Second-Price CV'].iloc[0]

print("\nFirst-Price CV:")
print(f"  Previous SMAD: {prev_fp_cv['smad']:.2f}% [{prev_fp_cv['ci_lower']:.2f}, {prev_fp_cv['ci_upper']:.2f}]")
if fp_cv_results:
    print(f"  New SMAD:      {fp_cv_results['smad']:.2f}% [{fp_cv_results['ci_lower']:.2f}, {fp_cv_results['ci_upper']:.2f}]")
    print(f"  Change:        {fp_cv_results['smad'] - prev_fp_cv['smad']:.2f}%")

print("\nSecond-Price CV:")
print(f"  Previous SMAD: {prev_sp_cv['smad']:.2f}% [{prev_sp_cv['ci_lower']:.2f}, {prev_sp_cv['ci_upper']:.2f}]")
if sp_cv_results:
    print(f"  New SMAD:      {sp_cv_results['smad']:.2f}% [{sp_cv_results['ci_lower']:.2f}, {sp_cv_results['ci_upper']:.2f}]")
    print(f"  Change:        {sp_cv_results['smad'] - prev_sp_cv['smad']:.2f}%")

# Update the results CSV
if fp_cv_results and sp_cv_results:
    print("\n" + "="*80)
    print("UPDATING RESULTS")
    print("="*80)

    # Update the dataframe
    prev_results.loc[prev_results['auction'] == 'First-Price CV', ['smad', 'se', 'ci_lower', 'ci_upper', 'n']] = [
        fp_cv_results['smad'],
        fp_cv_results['se'],
        fp_cv_results['ci_lower'],
        fp_cv_results['ci_upper'],
        fp_cv_results['n_observations']
    ]

    prev_results.loc[prev_results['auction'] == 'Second-Price CV', ['smad', 'se', 'ci_lower', 'ci_upper', 'n']] = [
        sp_cv_results['smad'],
        sp_cv_results['se'],
        sp_cv_results['ci_lower'],
        sp_cv_results['ci_upper'],
        sp_cv_results['n_observations']
    ]

    # Save updated results
    prev_results.to_csv('plots/theoretical_deviation_results_updated.csv', index=False)
    print("Updated results saved to: plots/theoretical_deviation_results_updated.csv")

    print("\nUpdated Results Summary:")
    print(prev_results[['auction', 'smad', 'ci_lower', 'ci_upper', 'n']].to_string(index=False))

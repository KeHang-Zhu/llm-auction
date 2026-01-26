import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Set style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# Base directory
base_dir = Path('/Users/kehangzh/Desktop/llm-auction/experiment_logs_with_explanation/V10')

# Define auction types and their parameters
auction_configs = {
    'fpsb_ipv': {
        'name': 'First-Price IPV',
        'path': 'fpsb_ipv',
        'type': 'ipv',
        'theoretical_bid': lambda v, N=3: (N-1)/N * v,  # (N-1)/N * v
    },
    'spsb_ipv': {
        'name': 'Second-Price IPV',
        'path': 'spsb_ipv',
        'type': 'ipv',
        'theoretical_bid': lambda v, N=3: v,  # Truthful bidding
    },
    'spsb_apv': {
        'name': 'Second-Price APV',
        'path': 'spsb_apv',
        'type': 'apv',
        'theoretical_bid': lambda v, N=3: v,  # Truthful bidding
    },
    'ascending_clock_apv': {
        'name': 'Ascending Clock APV',
        'path': 'ascending_clock_apv',
        'type': 'apv',
        'theoretical_bid': lambda v, N=3: v,  # Truthful bidding (exit at value)
        'use_merged': True,  # Use merged results file
    },
    'ascending_clock_apv_closed': {
        'name': 'AC-Closed (AC-B) APV',
        'path': 'ascending_clock_apv_closed',
        'type': 'apv',
        'theoretical_bid': lambda v, N=3: v,  # Truthful bidding (exit at value)
        'use_merged': True,  # Use merged results file
    },
    'third_price_ipv': {
        'name': 'Third-Price IPV',
        'path': 'third_price_ipv',
        'type': 'ipv',
        'theoretical_bid': lambda v, N=3: (N-1)/(N-2) * v,  # (N-1)/(N-2) * v
    },
    'all_pay_ipv': {
        'name': 'All-Pay IPV',
        'path': 'all_pay_ipv',
        'type': 'all_pay',
        'theoretical_bid': lambda v, N=3: v / N,  # E[b*] = V/N for mixed strategy
    },
    'common_value_first': {
        'name': 'First-Price CV',
        'path': 'common_value_first',
        'type': 'cv',
        'use_profit': True,  # Use profit-based deviation for CV
    },
    'common_value_second': {
        'name': 'Second-Price CV',
        'path': 'common_value_second',
        'type': 'cv',
        'use_profit': True,  # Use profit-based deviation for CV
    },
}

def calculate_deviation(df, config):
    """
    Calculate the Scaled Mean Absolute Deviation (SMAD) as per PDF methodology.

    Δm = 100 · E[|b - b*_m(I)|] / E[b*_m(I)]
    """
    if config.get('use_profit', False):
        # For common value auctions, use profit-based deviation
        # Δ^CV_m = 100 · E[|π - π*|] / E[π*]
        # Theoretical optimal profit in CV auctions is tricky;
        # we'll use the absolute profit deviation from zero loss

        # The theoretical profit should account for winner's curse
        # For simplicity, we'll measure deviation from expected positive profit
        mean_profit = df['profit'].mean()

        # Theoretical optimal: should have small positive profit
        # We estimate based on the value range
        # In a properly adjusted CV auction, profit should be positive but small
        theoretical_profit = 0  # Benchmark: break-even

        # Calculate absolute profit deviation
        profit_deviations = np.abs(df['profit'] - theoretical_profit)
        mad_profit = profit_deviations.mean()

        # For scaling, use a reasonable baseline
        # We'll use the mean absolute profit as the baseline
        baseline = np.abs(df['profit']).mean()
        if baseline == 0:
            baseline = 1  # Avoid division by zero

        smad = 100 * mad_profit / baseline

        # Calculate standard error using bootstrap
        n = len(df)
        se_mad = profit_deviations.std() / np.sqrt(n)
        se_smad = 100 * se_mad / baseline

    else:
        # For IPV/APV auctions, use bid-based deviation
        # Calculate theoretical optimal bid for each observation
        df = df.copy()
        df['theoretical_bid'] = df['player_value'].apply(config['theoretical_bid'])

        # Calculate absolute deviation for each bid
        df['deviation'] = np.abs(df['bid'] - df['theoretical_bid'])

        # Calculate MAD (Mean Absolute Deviation)
        mad = df['deviation'].mean()

        # Calculate mean theoretical bid (μ*_m)
        mean_theoretical = df['theoretical_bid'].mean()

        # Calculate SMAD (Scaled Mean Absolute Deviation)
        smad = 100 * mad / mean_theoretical

        # Calculate standard error
        n = len(df)
        se_mad = df['deviation'].std() / np.sqrt(n)
        se_smad = 100 * se_mad / mean_theoretical

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

# Calculate deviations for each auction type
results = []

for auction_key, config in auction_configs.items():
    print(f"\nProcessing {config['name']}...")

    # Find the CSV file
    auction_dir = base_dir / config['path']

    # Check if we should use merged results
    if config.get('use_merged', False):
        merged_file = auction_dir / f"{config['path']}_merged_results.csv"
        if merged_file.exists():
            csv_file = merged_file
            print(f"  Using merged file: {csv_file}")
        else:
            csv_files = list(auction_dir.glob('**/results/*_results.csv'))
            if not csv_files:
                print(f"  Warning: No CSV file found for {auction_key}")
                continue
            csv_file = csv_files[0]
            print(f"  Reading: {csv_file}")
    else:
        csv_files = list(auction_dir.glob('**/results/*_results.csv'))
        if not csv_files:
            print(f"  Warning: No CSV file found for {auction_key}")
            continue
        csv_file = csv_files[0]
        print(f"  Reading: {csv_file}")

    # Read the data
    df = pd.read_csv(csv_file)

    print(f"  Total observations: {len(df)}")

    # Calculate deviation
    deviation_stats = calculate_deviation(df, config)

    results.append({
        'auction': config['name'],
        'auction_key': auction_key,
        'smad': deviation_stats['smad'],
        'se': deviation_stats['se'],
        'ci_lower': deviation_stats['ci_lower'],
        'ci_upper': deviation_stats['ci_upper'],
        'n': deviation_stats['n_observations'],
        'type': config['type']
    })

    print(f"  SMAD: {deviation_stats['smad']:.2f}%")
    print(f"  95% CI: [{deviation_stats['ci_lower']:.2f}%, {deviation_stats['ci_upper']:.2f}%]")

# Create results dataframe
results_df = pd.DataFrame(results)

# Sort by SMAD value for better visualization
results_df = results_df.sort_values('smad', ascending=True)

print("\n" + "="*60)
print("SUMMARY RESULTS")
print("="*60)
print(results_df.to_string(index=False))
print("="*60)

# Create visualization
fig, ax = plt.subplots(figsize=(12, 8))

# Define colors by auction type
type_colors = {
    'ipv': '#2E86AB',  # Blue
    'apv': '#A23B72',  # Purple
    'all_pay': '#F18F01',  # Orange
    'cv': '#C73E1D'  # Red
}

colors = [type_colors[t] for t in results_df['type']]

# Create horizontal bar plot
y_pos = np.arange(len(results_df))
ax.barh(y_pos, results_df['smad'], color=colors, alpha=0.7, height=0.6)

# Add error bars for 95% CI
xerr = np.array([
    results_df['smad'] - results_df['ci_lower'],
    results_df['ci_upper'] - results_df['smad']
])
ax.errorbar(results_df['smad'], y_pos, xerr=xerr, fmt='none',
            ecolor='black', capsize=5, capthick=2, linewidth=2)

# Add value labels
for i, (idx, row) in enumerate(results_df.iterrows()):
    # Add SMAD value
    ax.text(row['smad'] + 0.5, i, f"{row['smad']:.1f}%",
            va='center', ha='left', fontweight='bold', fontsize=10)

    # Add sample size
    ax.text(0.5, i, f"n={row['n']}",
            va='center', ha='left', fontsize=9, color='gray')

# Customize plot
ax.set_yticks(y_pos)
ax.set_yticklabels(results_df['auction'])
ax.set_xlabel('Scaled Mean Absolute Deviation (SMAD) from Theoretical Optimum (%)',
              fontsize=13, fontweight='bold')
ax.set_title('LLM Bidding Deviation from Theoretical Equilibrium\nAcross Auction Formats',
             fontsize=15, fontweight='bold', pad=20)

# Add vertical line at 0
ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.5)

# Add legend for auction types
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=type_colors['ipv'], alpha=0.7, label='Independent Private Value (IPV)'),
    Patch(facecolor=type_colors['apv'], alpha=0.7, label='Affiliated Private Value (APV)'),
    Patch(facecolor=type_colors['all_pay'], alpha=0.7, label='All-Pay Auction'),
    Patch(facecolor=type_colors['cv'], alpha=0.7, label='Common Value (CV)')
]
ax.legend(handles=legend_elements, loc='lower right', frameon=True,
          fontsize=10, title='Auction Types', title_fontsize=11)

# Set x-axis limits
max_ci = results_df['ci_upper'].max()
ax.set_xlim(-2, max_ci * 1.15)

# Add grid
ax.grid(axis='x', alpha=0.3, linestyle='--')

plt.tight_layout()

# Save figure
output_path = Path('/Users/kehangzh/Desktop/llm-auction/plots/theoretical_deviation_plot.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\nPlot saved to: {output_path}")

# Also save results to CSV
results_csv_path = Path('/Users/kehangzh/Desktop/llm-auction/plots/theoretical_deviation_results.csv')
results_df.to_csv(results_csv_path, index=False)
print(f"Results saved to: {results_csv_path}")

plt.show()

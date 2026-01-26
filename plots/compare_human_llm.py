import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 10

# Read human data
human_df = pd.read_csv('plots/Auction_human_data.csv')

# Read LLM data (use updated results with corrected CV calculations)
llm_df = pd.read_csv('plots/theoretical_deviation_results_updated.csv')

# Parse human data
def parse_ci_string(ci_str):
    """Parse CI string like '[29.4, 127.4]' or 'MC, no CI'"""
    if pd.isna(ci_str) or 'no CI' in str(ci_str):
        return None, None

    # Extract numbers from [lower, upper] format
    match = re.search(r'\[([0-9.]+),\s*([0-9.]+)\]', str(ci_str))
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

# Process human data
human_data = []
for _, row in human_df.iterrows():
    if pd.isna(row['Auction format']):
        continue

    auction_format = row['Auction format'].strip()
    smad = row['%Scaled MAD']
    ci_lower, ci_upper = parse_ci_string(row['95%CI'])

    # Map human format names to standard names
    format_mapping = {
        'First-Price IPV': 'First-Price IPV',
        'Second-Price IPV': 'Second-Price IPV',
        'Third-Price IPV': 'Third-Price IPV',
        'All-Pay IPV': 'All-Pay IPV',
        'AC-B (Breitmoser2022)': 'AC-Closed (AC-B) APV',
        'SPSB (Li 2017)': 'Second-Price APV',
        'Ascending Clock (LI 2017)': 'Ascending Clock APV',
        'First-Price Common Value': 'First-Price CV',
        'Second-Price Common Value (English proxy)': 'Second-Price CV',
    }

    standard_name = format_mapping.get(auction_format, auction_format)

    human_data.append({
        'auction': standard_name,
        'source': 'Human',
        'smad': smad,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'has_ci': ci_lower is not None
    })

human_comparison_df = pd.DataFrame(human_data)

# Process LLM data
llm_comparison_df = llm_df[['auction', 'smad', 'ci_lower', 'ci_upper']].copy()
llm_comparison_df['source'] = 'LLM (GPT-4o)'
llm_comparison_df['has_ci'] = True

# Combine data
combined_df = pd.concat([
    human_comparison_df,
    llm_comparison_df
], ignore_index=True)

# Find matching auctions
matched_auctions = set(human_comparison_df['auction']) & set(llm_comparison_df['auction'])
combined_df = combined_df[combined_df['auction'].isin(matched_auctions)]

# Sort by auction type and human performance
auction_order = combined_df[combined_df['source'] == 'Human'].sort_values('smad')['auction'].tolist()

print("Matched Auctions for Comparison:")
print("="*80)
for auction in auction_order:
    human_row = combined_df[(combined_df['auction'] == auction) & (combined_df['source'] == 'Human')].iloc[0]
    llm_row = combined_df[(combined_df['auction'] == auction) & (combined_df['source'] == 'LLM (GPT-4o)')].iloc[0]

    print(f"\n{auction}:")
    if human_row['has_ci']:
        print(f"  Human:      {human_row['smad']:.2f}% [{human_row['ci_lower']:.2f}, {human_row['ci_upper']:.2f}]")
    else:
        print(f"  Human:      {human_row['smad']:.2f}% (no CI)")
    print(f"  LLM:        {llm_row['smad']:.2f}% [{llm_row['ci_lower']:.2f}, {llm_row['ci_upper']:.2f}]")
    print(f"  Difference: {llm_row['smad'] - human_row['smad']:.2f}% ({'worse' if llm_row['smad'] > human_row['smad'] else 'better'})")

print("\n" + "="*80)

# Create comparison plot - HORIZONTAL layout
fig, ax = plt.subplots(figsize=(12, 10))

# Set up y positions (now auctions on y-axis)
n_auctions = len(auction_order)
y = np.arange(n_auctions)
height = 0.35  # bar height instead of width

# Colors
human_color = '#2E86AB'  # Blue
llm_color = '#F18F01'    # Orange

# Plot bars for each source (horizontal bars)
for i, auction in enumerate(auction_order):
    auction_data = combined_df[combined_df['auction'] == auction]

    for j, source in enumerate(['Human', 'LLM (GPT-4o)']):
        source_data = auction_data[auction_data['source'] == source]
        if len(source_data) == 0:
            continue

        row = source_data.iloc[0]
        y_pos = i + (j - 0.5) * height

        color = human_color if source == 'Human' else llm_color

        # Plot horizontal bar
        ax.barh(y_pos, row['smad'], height, color=color, alpha=0.7,
                label=source if i == 0 else "")

        # Add error bars if CI exists
        if row['has_ci']:
            xerr_lower = row['smad'] - row['ci_lower']
            xerr_upper = row['ci_upper'] - row['smad']
            ax.errorbar(row['smad'], y_pos,
                       xerr=[[xerr_lower], [xerr_upper]],
                       fmt='none', ecolor='black', capsize=4, capthick=1.5, linewidth=1.5)
        else:
            # Add a marker to indicate no CI
            ax.plot(row['smad'], y_pos, 'k*', markersize=10)

# Customize plot
ax.set_ylabel('Auction Format', fontsize=13, fontweight='bold')
ax.set_xlabel('Scaled Mean Absolute Deviation (SMAD) from Theoretical Optimum (%)',
              fontsize=13, fontweight='bold')
ax.set_title('Human vs LLM Bidding Behavior: Deviation from Theoretical Equilibrium',
             fontsize=15, fontweight='bold', pad=20)

# Set y-axis
ax.set_yticks(y)
ax.set_yticklabels(auction_order)

# Add legend
ax.legend(loc='lower right', frameon=True, fontsize=11)

# Add vertical line at 0
ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.5)

# Add grid
ax.grid(axis='x', alpha=0.3, linestyle='--')

# Add note about missing CIs
ax.text(0.98, 0.02, '* indicates no confidence interval available',
        transform=ax.transAxes, fontsize=9,
        verticalalignment='bottom', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()

# Save figure
output_path = Path('plots/human_llm_comparison.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\nPlot saved to: {output_path}")

# Create summary statistics table
summary_data = []
for auction in auction_order:
    human_row = combined_df[(combined_df['auction'] == auction) & (combined_df['source'] == 'Human')].iloc[0]
    llm_row = combined_df[(combined_df['auction'] == auction) & (combined_df['source'] == 'LLM (GPT-4o)')].iloc[0]

    summary_data.append({
        'Auction': auction,
        'Human_SMAD': human_row['smad'],
        'Human_CI': f"[{human_row['ci_lower']:.1f}, {human_row['ci_upper']:.1f}]" if human_row['has_ci'] else "N/A",
        'LLM_SMAD': llm_row['smad'],
        'LLM_CI': f"[{llm_row['ci_lower']:.1f}, {llm_row['ci_upper']:.1f}]",
        'Difference': llm_row['smad'] - human_row['smad'],
        'Relative_Increase': ((llm_row['smad'] - human_row['smad']) / human_row['smad'] * 100) if human_row['smad'] > 0 else np.nan
    })

summary_df = pd.DataFrame(summary_data)
summary_csv_path = Path('plots/human_llm_comparison_summary.csv')
summary_df.to_csv(summary_csv_path, index=False)
print(f"Summary table saved to: {summary_csv_path}")

plt.show()

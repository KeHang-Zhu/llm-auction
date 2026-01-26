import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.size'] = 11

# Read the updated results with corrected CV calculations
results_df = pd.read_csv('plots/theoretical_deviation_results_updated.csv')

# Sort by SMAD value
results_df = results_df.sort_values('smad', ascending=True)

print("\n" + "="*60)
print("RESULTS WITH CORRECTED CV CALCULATIONS")
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
    ax.text(row['smad'] + 5, i, f"{row['smad']:.1f}%",
            va='center', ha='left', fontweight='bold', fontsize=10)

    # Add sample size
    ax.text(5, i, f"n={row['n']}",
            va='center', ha='left', fontsize=9, color='gray')

# Customize plot
ax.set_yticks(y_pos)
ax.set_yticklabels(results_df['auction'])
ax.set_xlabel('Scaled Mean Absolute Deviation (SMAD) from Theoretical Optimum (%)',
              fontsize=13, fontweight='bold')
ax.set_title('LLM Bidding Deviation from Theoretical Equilibrium\nAcross Auction Formats (with Corrected CV Calculations)',
             fontsize=15, fontweight='bold', pad=20)

# Add vertical line at 0
ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.5)

# Add legend for auction types
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=type_colors['ipv'], alpha=0.7, label='Independent Private Value (IPV)'),
    Patch(facecolor=type_colors['apv'], alpha=0.7, label='Affiliated Private Value (APV)'),
    Patch(facecolor=type_colors['all_pay'], alpha=0.7, label='All-Pay Auction'),
    Patch(facecolor=type_colors['cv'], alpha=0.7, label='Common Value (CV) - Corrected')
]
ax.legend(handles=legend_elements, loc='lower right', frameon=True,
          fontsize=10, title='Auction Types', title_fontsize=11)

# Set x-axis limits
max_ci = results_df['ci_upper'].max()
ax.set_xlim(-2, max_ci * 1.15)

# Add grid
ax.grid(axis='x', alpha=0.3, linestyle='--')

# Add note about CV correction
ax.text(0.02, 0.98,
        'CV calculations use theoretical profit benchmarks:\n' +
        'FP-CV: π* = 2ε/(n+1), SP-CV: π* = ε/(n+1)',
        transform=ax.transAxes, fontsize=9, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()

# Save figure
output_path = Path('plots/theoretical_deviation_corrected.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\nPlot saved to: {output_path}")

plt.show()

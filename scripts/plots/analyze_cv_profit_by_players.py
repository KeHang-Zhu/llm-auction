"""
Analysis of Common Value Auction Winner's Profit by Number of Bidders
Tests whether winner's profit > 0 and how it changes with number of players
"""

import pandas as pd
import numpy as np
from scipy import stats
import os

# Define paths to all common value first-price auction experiments
base_path = "/Users/kehangzh/Desktop/llm-auction/experiment_logs/V10"
experiments = {
    # 3: f"{base_path}/common_value_first/run_2026-01-12_22-28-21-388751/results/common_value_first_results.csv",
    4: f"{base_path}/common_value_first_4player/run_2026-02-03_23-53-01-685040/results/common_value_first_results.csv",
    5: f"{base_path}/common_value_first_5player/run_2026-02-03_23-53-01-685169/results/common_value_first_results.csv",
    6: f"{base_path}/common_value_first_6player/run_2026-02-03_23-53-01-684852/results/common_value_first_results.csv",
    7: f"{base_path}/common_value_first_7player/run_2026-02-03_23-58-57-381398/results/common_value_first_results.csv",
}

# Load and process data
results = []
all_winner_profits = {}

print("=" * 80)
print("Common Value FPSB Auction: Winner's Profit Analysis by Number of Bidders")
print("=" * 80)

for n_players, filepath in experiments.items():
    if not os.path.exists(filepath):
        print(f"\nWarning: File not found for {n_players} players: {filepath}")
        continue

    df = pd.read_csv(filepath)

    # Filter for winners only
    winners = df[df['is_winner'] == True]
    winner_profits = winners['profit'].values

    # Store for later analysis
    all_winner_profits[n_players] = winner_profits

    # Calculate statistics
    n_auctions = len(winner_profits)
    mean_profit = np.mean(winner_profits)
    std_profit = np.std(winner_profits, ddof=1)
    median_profit = np.median(winner_profits)

    # Count positive/negative profits
    n_positive = np.sum(winner_profits > 0)
    n_negative = np.sum(winner_profits < 0)
    n_zero = np.sum(winner_profits == 0)
    pct_positive = (n_positive / n_auctions) * 100
    pct_negative = (n_negative / n_auctions) * 100

    # One-sample t-test: H0: mean profit = 0, Ha: mean profit > 0
    t_stat, p_value_two_sided = stats.ttest_1samp(winner_profits, 0)
    # One-sided p-value for testing if mean > 0
    p_value_greater = p_value_two_sided / 2 if t_stat > 0 else 1 - p_value_two_sided / 2

    # Wilcoxon signed-rank test (non-parametric alternative)
    # Tests if median differs from 0
    try:
        wilcoxon_stat, wilcoxon_p = stats.wilcoxon(winner_profits, alternative='greater')
    except ValueError:
        # Handle case where all values are zero
        wilcoxon_stat, wilcoxon_p = np.nan, np.nan

    results.append({
        'n_players': n_players,
        'n_auctions': n_auctions,
        'mean_profit': mean_profit,
        'std_profit': std_profit,
        'median_profit': median_profit,
        'pct_positive': pct_positive,
        'pct_negative': pct_negative,
        't_stat': t_stat,
        'p_value_greater_0': p_value_greater,
        'wilcoxon_p_greater_0': wilcoxon_p
    })

# Create summary table
summary_df = pd.DataFrame(results)
summary_df = summary_df.sort_values('n_players')

print("\n" + "=" * 80)
print("SUMMARY TABLE: Winner's Profit Statistics")
print("=" * 80)
print(summary_df.to_string(index=False, float_format=lambda x: f'{x:.4f}'))

# Create formatted table for display
print("\n" + "=" * 80)
print("FORMATTED RESULTS TABLE")
print("=" * 80)
print(f"{'Players':<10} {'N':<8} {'Mean':<12} {'Std':<12} {'Median':<12} {'% Pos':<10} {'% Neg':<10} {'t-stat':<10} {'p (>0)':<12}")
print("-" * 96)
for _, row in summary_df.iterrows():
    sig = "***" if row['p_value_greater_0'] < 0.001 else ("**" if row['p_value_greater_0'] < 0.01 else ("*" if row['p_value_greater_0'] < 0.05 else ""))
    print(f"{int(row['n_players']):<10} {int(row['n_auctions']):<8} {row['mean_profit']:<12.3f} {row['std_profit']:<12.3f} {row['median_profit']:<12.3f} {row['pct_positive']:<10.1f} {row['pct_negative']:<10.1f} {row['t_stat']:<10.3f} {row['p_value_greater_0']:<10.4f} {sig}")

# Statistical Tests
print("\n" + "=" * 80)
print("STATISTICAL TESTS")
print("=" * 80)

# Test 1: For each group, test if profit > 0
print("\n1. One-sample t-tests: H0: mean profit = 0, Ha: mean profit > 0")
print("-" * 60)
for n_players, profits in sorted(all_winner_profits.items()):
    t_stat, p_two = stats.ttest_1samp(profits, 0)
    p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2
    sig = "***" if p_one < 0.001 else ("**" if p_one < 0.01 else ("*" if p_one < 0.05 else "ns"))
    conclusion = "REJECT H0 (profit > 0)" if p_one < 0.05 and t_stat > 0 else "FAIL TO REJECT H0"
    print(f"  {n_players} players: t = {t_stat:.3f}, p = {p_one:.4f} {sig} -> {conclusion}")

# Test 1b: For each group, test if profit < 0 (winner's curse test)
print("\n1b. One-sample t-tests: H0: mean profit = 0, Ha: mean profit < 0 (Winner's Curse)")
print("-" * 60)
for n_players, profits in sorted(all_winner_profits.items()):
    t_stat, p_two = stats.ttest_1samp(profits, 0)
    p_one = p_two / 2 if t_stat < 0 else 1 - p_two / 2
    sig = "***" if p_one < 0.001 else ("**" if p_one < 0.01 else ("*" if p_one < 0.05 else "ns"))
    conclusion = "WINNER'S CURSE CONFIRMED" if p_one < 0.05 and t_stat < 0 else "No significant curse"
    print(f"  {n_players} players: t = {t_stat:.3f}, p = {p_one:.4f} {sig} -> {conclusion}")

# Test 2: ANOVA to test if profit differs by number of players
print("\n2. One-way ANOVA: Does mean profit differ by number of players?")
print("-" * 60)
groups = [all_winner_profits[n] for n in sorted(all_winner_profits.keys())]
f_stat, anova_p = stats.f_oneway(*groups)
print(f"  F-statistic: {f_stat:.3f}")
print(f"  p-value: {anova_p:.6f}")
if anova_p < 0.05:
    print("  -> Significant difference in profit across different numbers of bidders")
else:
    print("  -> No significant difference in profit across different numbers of bidders")

# Test 3: Linear trend test (correlation between n_players and profit)
print("\n3. Correlation test: Is there a linear relationship between # bidders and profit?")
print("-" * 60)
# Create arrays for correlation
all_n_players = []
all_profits = []
for n, profits in sorted(all_winner_profits.items()):
    all_n_players.extend([n] * len(profits))
    all_profits.extend(profits)

corr, corr_p = stats.pearsonr(all_n_players, all_profits)
print(f"  Pearson correlation: r = {corr:.4f}")
print(f"  p-value: {corr_p:.6f}")
if corr_p < 0.05:
    direction = "negative" if corr < 0 else "positive"
    print(f"  -> Significant {direction} correlation: profit {'decreases' if corr < 0 else 'increases'} with more bidders")
else:
    print("  -> No significant linear relationship between # bidders and profit")

# Test 4: Spearman correlation (non-parametric)
spearman_corr, spearman_p = stats.spearmanr(all_n_players, all_profits)
print(f"\n  Spearman correlation (non-parametric): rho = {spearman_corr:.4f}, p = {spearman_p:.6f}")

# Test 5: Jonckheere-Terpstra trend test (alternative: ordered trend)
print("\n4. Trend analysis: Mean profit by number of bidders")
print("-" * 60)
for n in sorted(all_winner_profits.keys()):
    mean = np.mean(all_winner_profits[n])
    print(f"  {n} players: mean = {mean:.3f}")

# Linear regression for trend
from scipy.stats import linregress
x = np.array(all_n_players)
y = np.array(all_profits)
slope, intercept, r_value, p_value, std_err = linregress(x, y)
print(f"\n  Linear regression: profit = {intercept:.3f} + {slope:.3f} * n_players")
print(f"  R-squared: {r_value**2:.4f}")
print(f"  Slope p-value: {p_value:.6f}")
if p_value < 0.05:
    print(f"  -> Significant trend: profit changes by {slope:.3f} per additional bidder")

# Test 6: Pairwise comparisons (post-hoc)
print("\n5. Pairwise t-tests between consecutive player counts")
print("-" * 60)
n_players_list = sorted(all_winner_profits.keys())
for i in range(len(n_players_list) - 1):
    n1 = n_players_list[i]
    n2 = n_players_list[i + 1]
    t_stat, p_val = stats.ttest_ind(all_winner_profits[n1], all_winner_profits[n2])
    sig = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else "ns"))
    print(f"  {n1} vs {n2} players: t = {t_stat:.3f}, p = {p_val:.4f} {sig}")

# Save summary to CSV
output_path = "/Users/kehangzh/Desktop/llm-auction/plots/cv_profit_by_players_summary.csv"
summary_df.to_csv(output_path, index=False)
print(f"\n\nSummary saved to: {output_path}")

# Overall conclusion
print("\n" + "=" * 80)
print("CONCLUSIONS")
print("=" * 80)
print("\n1. Is winner's profit > 0?")
for n in sorted(all_winner_profits.keys()):
    mean = np.mean(all_winner_profits[n])
    if mean > 0:
        t_stat, p_two = stats.ttest_1samp(all_winner_profits[n], 0)
        p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2
        if p_one < 0.05:
            print(f"   {n} players: Mean profit = {mean:.3f} > 0 (statistically significant)")
        else:
            print(f"   {n} players: Mean profit = {mean:.3f} > 0 (not statistically significant)")
    else:
        print(f"   {n} players: Mean profit = {mean:.3f} <= 0 (winner's curse evident)")

print(f"\n2. Does profit change with number of bidders?")
if anova_p < 0.05:
    print(f"   YES - ANOVA shows significant difference (F={f_stat:.3f}, p={anova_p:.6f})")
else:
    print(f"   No significant difference by ANOVA (F={f_stat:.3f}, p={anova_p:.6f})")

if corr_p < 0.05:
    print(f"   YES - Correlation shows {'decrease' if corr < 0 else 'increase'} in profit with more bidders")
    print(f"         (r={corr:.4f}, p={corr_p:.6f})")
else:
    print(f"   No significant linear trend (r={corr:.4f}, p={corr_p:.6f})")

# Create visualization
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))

# Prepare data for boxplot
plot_data = [all_winner_profits[n] for n in sorted(all_winner_profits.keys())]
positions = sorted(all_winner_profits.keys())

bp = ax.boxplot(plot_data, positions=positions, widths=0.6, patch_artist=True)

# Color the boxes
for patch in bp['boxes']:
    patch.set_facecolor('#3274A1')
    patch.set_alpha(0.7)

# Add zero line
ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, label='Zero Profit')

# Add mean markers
means = [np.mean(all_winner_profits[n]) for n in positions]
ax.scatter(positions, means, color='orange', marker='D', s=100, zorder=5, label='Mean')

# Labels and title
ax.set_xlabel('Number of Bidders', fontsize=12)
ax.set_ylabel("Winner's Profit ($)", fontsize=12)
ax.set_title("Distribution of Winner's Profit in Common Value FPSB Auctions\n(Winner's Curse Analysis, 4-7 Players)", fontsize=14)
ax.legend(loc='upper right')

# Add text annotation for winner's curse
ax.annotate("Winner's Curse:\nAll means below zero", xy=(6.5, 5), fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('/Users/kehangzh/Desktop/llm-auction/plots/cv_profit_by_players.png', dpi=150)
print(f"\nPlot saved to: /Users/kehangzh/Desktop/llm-auction/plots/cv_profit_by_players.png")

print("\n" + "=" * 80)

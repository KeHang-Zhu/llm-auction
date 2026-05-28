import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from scipy.stats import sem

# Read the data
fpsb_df = pd.read_csv('../robustness_logs/fpsb_ipv_15_rounds/run_2026-01-11_21-38-07-616091/results/fpsb_ipv_results.csv')
spsb_df = pd.read_csv('../robustness_logs/spsb_ipv_15_round/run_2026-01-11_20-51-34-820810/results/spsb_ipv_results.csv')

# Calculate MAD for FPSB (optimal bid = 2/3 * value)
fpsb_df['optimal_bid'] = (2/3) * fpsb_df['player_value']
fpsb_df['absolute_deviation'] = np.abs(fpsb_df['bid'] - fpsb_df['optimal_bid'])

# Calculate MAD for SPSB (optimal bid = value)
spsb_df['optimal_bid'] = spsb_df['player_value']
spsb_df['absolute_deviation'] = np.abs(spsb_df['bid'] - spsb_df['optimal_bid'])

# Scale by factor 25 to get SMAD
scaling_factor = 25

# Calculate SMAD with confidence intervals for each round
def calculate_smad_with_ci(df, rounds):
    """Calculate SMAD mean and 95% CI for each round"""
    means = []
    lower_cis = []
    upper_cis = []

    for round_num in rounds:
        round_data = df[df['round'] == round_num]['absolute_deviation'] / scaling_factor
        mean_val = round_data.mean()
        se = sem(round_data)
        ci = se * stats.t.ppf((1 + 0.95) / 2, len(round_data) - 1)  # 95% CI

        means.append(mean_val)
        lower_cis.append(mean_val - ci)
        upper_cis.append(mean_val + ci)

    return np.array(means), np.array(lower_cis), np.array(upper_cis)

rounds = sorted(fpsb_df['round'].unique())
fpsb_smad, fpsb_lower, fpsb_upper = calculate_smad_with_ci(fpsb_df, rounds)
spsb_smad, spsb_lower, spsb_upper = calculate_smad_with_ci(spsb_df, rounds)

# Create the plot with confidence intervals
plt.figure(figsize=(10, 6))

# Plot FPSB
plt.plot(rounds, fpsb_smad, marker='o', label='FPSB', linewidth=2, markersize=6, color='#1f77b4')
plt.fill_between(rounds, fpsb_lower, fpsb_upper, alpha=0.2, color='#1f77b4')

# Plot SPSB
plt.plot(rounds, spsb_smad, marker='s', label='SPSB', linewidth=2, markersize=6, color='#ff7f0e')
plt.fill_between(rounds, spsb_lower, spsb_upper, alpha=0.2, color='#ff7f0e')

plt.xlabel('Round', fontsize=12)
plt.ylabel('SMAD', fontsize=12)
plt.title('Scaled Mean Absolute Deviation (SMAD) Across Rounds with 95% CI', fontsize=14)
plt.legend(fontsize=11)
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Save the plot
plt.savefig('./smad_rounds.png', dpi=300, bbox_inches='tight')
plt.savefig('./smad_rounds.pdf', bbox_inches='tight')
print("Plot saved to plots/smad_rounds.png and plots/smad_rounds.pdf")

# ===== Statistical Tests =====
print("\n" + "="*60)
print("STATISTICAL ANALYSIS")
print("="*60)

# Test 1: First 5 rounds vs Last 5 rounds
def test_first_vs_last(df, name):
    """Compare first 5 rounds vs last 5 rounds"""
    first_5 = df[df['round'].isin(range(0, 5))]['absolute_deviation'] / scaling_factor
    last_5 = df[df['round'].isin(range(10, 15))]['absolute_deviation'] / scaling_factor

    # T-test
    t_stat, t_pval = stats.ttest_ind(first_5, last_5)

    # Mann-Whitney U test (non-parametric alternative)
    u_stat, u_pval = stats.mannwhitneyu(first_5, last_5, alternative='two-sided')

    print(f"\n{name}: First 5 rounds vs Last 5 rounds")
    print(f"  First 5 rounds - Mean: {first_5.mean():.4f}, Std: {first_5.std():.4f}, N: {len(first_5)}")
    print(f"  Last 5 rounds  - Mean: {last_5.mean():.4f}, Std: {last_5.std():.4f}, N: {len(last_5)}")
    print(f"  Difference: {first_5.mean() - last_5.mean():.4f}")
    print(f"  T-test: t={t_stat:.3f}, p={t_pval:.4f} {'***' if t_pval < 0.001 else '**' if t_pval < 0.01 else '*' if t_pval < 0.05 else 'ns'}")
    print(f"  Mann-Whitney U test: U={u_stat:.1f}, p={u_pval:.4f} {'***' if u_pval < 0.001 else '**' if u_pval < 0.01 else '*' if u_pval < 0.05 else 'ns'}")

    return first_5.mean(), last_5.mean(), t_pval, u_pval

fpsb_first_mean, fpsb_last_mean, fpsb_t_pval, fpsb_u_pval = test_first_vs_last(fpsb_df, "FPSB")
spsb_first_mean, spsb_last_mean, spsb_t_pval, spsb_u_pval = test_first_vs_last(spsb_df, "SPSB")

# Test 2: Linear trend across all rounds
def test_trend(df, name):
    """Test for linear trend across all rounds using regression"""
    round_nums = df['round'].values
    smad_values = (df['absolute_deviation'] / scaling_factor).values

    # Linear regression: SMAD ~ round
    slope, intercept, r_value, p_value, std_err = stats.linregress(round_nums, smad_values)

    print(f"\n{name}: Linear trend test (all rounds)")
    print(f"  Slope: {slope:.6f} (change in SMAD per round)")
    print(f"  R-squared: {r_value**2:.4f}")
    print(f"  P-value: {p_value:.4f} {'***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'ns'}")

    if p_value < 0.05:
        if slope > 0:
            print(f"  → Significant INCREASING trend")
        else:
            print(f"  → Significant DECREASING trend")
    else:
        print(f"  → No significant linear trend")

    return slope, p_value

fpsb_slope, fpsb_trend_p = test_trend(fpsb_df, "FPSB")
spsb_slope, spsb_trend_p = test_trend(spsb_df, "SPSB")

# Test 3: Spearman correlation (non-parametric trend test)
def test_spearman_trend(rounds_list, smad_values, name):
    """Test for monotonic trend using Spearman correlation"""
    corr, p_value = stats.spearmanr(rounds_list, smad_values)

    print(f"\n{name}: Spearman correlation test")
    print(f"  Correlation: {corr:.4f}")
    print(f"  P-value: {p_value:.4f} {'***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'ns'}")

    if p_value < 0.05:
        if corr > 0:
            print(f"  → Significant POSITIVE correlation (increasing trend)")
        else:
            print(f"  → Significant NEGATIVE correlation (decreasing trend)")
    else:
        print(f"  → No significant monotonic trend")

    return corr, p_value

fpsb_corr, fpsb_corr_p = test_spearman_trend(rounds, fpsb_smad, "FPSB")
spsb_corr, spsb_corr_p = test_spearman_trend(rounds, spsb_smad, "SPSB")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("\nFPSB:")
print(f"  Overall mean SMAD: {fpsb_smad.mean():.4f}")
print(f"  First 5 vs Last 5: {'Significant change' if fpsb_t_pval < 0.05 else 'No significant change'} (p={fpsb_t_pval:.4f})")
print(f"  Linear trend: {'Significant' if fpsb_trend_p < 0.05 else 'Not significant'} (p={fpsb_trend_p:.4f})")

print("\nSPSB:")
print(f"  Overall mean SMAD: {spsb_smad.mean():.4f}")
print(f"  First 5 vs Last 5: {'Significant change' if spsb_t_pval < 0.05 else 'No significant change'} (p={spsb_t_pval:.4f})")
print(f"  Linear trend: {'Significant' if spsb_trend_p < 0.05 else 'Not significant'} (p={spsb_trend_p:.4f})")

print("\n" + "="*60)

plt.show()

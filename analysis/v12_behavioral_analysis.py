"""
Analyze V12 Behavioral Interventions for SPSB Auctions.

Tests Shengwu Li's three axes of mechanism complexity + loss aversion.
Generates regression analysis and vertical comparison plots.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf


# Paths
EXPERIMENT_DIR = Path("experiment_logs/V12")
OUTPUT_DIR = Path("results/v12_interventions")

# Define intervention groups
AXIS_1_INTERVENTIONS = {
    "Baseline": "axis1_contingent_baseline",
    "Enumerate": "axis1_contingent_enumerate",
    "Dominated": "axis1_contingent_dominated",
    "Worst-case": "axis1_contingent_worstcase",
}

AXIS_2_INTERVENTIONS = {
    "Baseline": "axis2_forward_baseline",
    "Backward Induct": "axis2_forward_backward_induct",
    "One-step": "axis2_forward_onestep",
    "Decision Tree": "axis2_forward_tree",
}

AXIS_3_INTERVENTIONS = {
    "Baseline": "axis3_beliefs_baseline",
    "First-order": "axis3_beliefs_firstorder",
    "Second-order": "axis3_beliefs_secondorder",
    "Common Knowledge": "axis3_beliefs_common_knowledge",
}

LOSS_AVERSION_INTERVENTIONS = {
    "Baseline": "loss_aversion_baseline",
    "Gain Frame": "loss_aversion_gain_frame",
    "Loss Frame": "loss_aversion_loss_frame",
    "Mixed Frame": "loss_aversion_mixed_frame",
    "Endowment": "loss_aversion_endowment",
    "WTA/WTP": "loss_aversion_WTA_WTP",
}

ALL_GROUPS = {
    "Axis 1: Contingent Reasoning": AXIS_1_INTERVENTIONS,
    "Axis 2: Forward Planning": AXIS_2_INTERVENTIONS,
    "Axis 3: Higher-Order Beliefs": AXIS_3_INTERVENTIONS,
    "Loss Aversion": LOSS_AVERSION_INTERVENTIONS,
}


def load_experiment_data(exp_dir: Path, exp_name: str) -> pd.DataFrame:
    """Load experiment data from all runs."""
    dfs = []
    exp_path = exp_dir / exp_name

    if not exp_path.exists():
        print(f"  Warning: {exp_path} does not exist")
        return pd.DataFrame()

    for csv_file in exp_path.rglob("*_results.csv"):
        if "merged" not in csv_file.name:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception as e:
                print(f"  Error loading {csv_file}: {e}")

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def calculate_bid_shading(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate bid shading metrics for each observation.

    Bid shading = (Value - Bid) / Value
    Positive = underbidding (bid < value)
    Negative = overbidding (bid > value)

    For SPSB: optimal is bid = value, so shading should be 0.
    """
    df = df.copy()

    # Convert to numeric
    df['player_value'] = pd.to_numeric(df['player_value'], errors='coerce')
    df['bid'] = pd.to_numeric(df['bid'], errors='coerce')

    # Remove invalid rows
    df = df.dropna(subset=['player_value', 'bid'])
    df = df[df['player_value'] > 0]  # Avoid division by zero

    # Calculate metrics
    df['bid_shading'] = (df['player_value'] - df['bid']) / df['player_value']
    df['bid_ratio'] = df['bid'] / df['player_value']
    df['absolute_deviation'] = np.abs(df['bid'] - df['player_value'])
    df['deviation'] = df['bid'] - df['player_value']

    return df


def load_all_interventions() -> Dict[str, Dict[str, pd.DataFrame]]:
    """Load all intervention data grouped by axis."""
    all_data = {}

    for group_name, interventions in ALL_GROUPS.items():
        print(f"\n📊 Loading {group_name}...")
        group_data = {}

        for display_name, exp_name in interventions.items():
            print(f"  {display_name}...", end=" ")
            df = load_experiment_data(EXPERIMENT_DIR, exp_name)

            if not df.empty:
                df = calculate_bid_shading(df)
                df['intervention'] = display_name
                df['axis'] = group_name
                group_data[display_name] = df
                print(f"✓ {len(df)} observations")
            else:
                print("⚠️ No data")

        all_data[group_name] = group_data

    return all_data


def run_regression_analysis(all_data: Dict[str, Dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """
    Run regression analysis comparing interventions within each axis.

    Model: bid_shading ~ intervention + value + C(intervention)
    """
    results = []

    for group_name, group_data in all_data.items():
        if not group_data:
            continue

        print(f"\n{'='*70}")
        print(f"REGRESSION ANALYSIS: {group_name}")
        print('='*70)

        # Combine all interventions in this group
        combined_df = pd.concat(group_data.values(), ignore_index=True)

        if len(combined_df) < 10:
            print("  Insufficient data for regression")
            continue

        # Get baseline name (first intervention)
        baseline_name = list(group_data.keys())[0]

        # Summary statistics by intervention
        print(f"\nSummary Statistics (Bid Shading = (Value - Bid) / Value):")
        print("-" * 60)
        summary = combined_df.groupby('intervention')['bid_shading'].agg([
            'count', 'mean', 'std', 'median'
        ]).round(4)
        print(summary.to_string())

        # T-tests comparing each intervention to baseline
        print(f"\nT-tests vs Baseline ({baseline_name}):")
        print("-" * 60)

        baseline_data = group_data.get(baseline_name)
        if baseline_data is not None and len(baseline_data) > 0:
            baseline_shading = baseline_data['bid_shading'].values

            for int_name, int_df in group_data.items():
                if int_name == baseline_name:
                    continue

                int_shading = int_df['bid_shading'].values

                if len(int_shading) > 0:
                    t_stat, p_value = stats.ttest_ind(baseline_shading, int_shading)
                    diff = np.mean(int_shading) - np.mean(baseline_shading)

                    sig = ""
                    if p_value < 0.01:
                        sig = "***"
                    elif p_value < 0.05:
                        sig = "**"
                    elif p_value < 0.10:
                        sig = "*"

                    print(f"  {int_name:20s}: diff={diff:+.4f}, t={t_stat:6.2f}, p={p_value:.4f} {sig}")

                    results.append({
                        'Axis': group_name,
                        'Intervention': int_name,
                        'Baseline': baseline_name,
                        'N': len(int_shading),
                        'Mean_Shading': np.mean(int_shading),
                        'Diff_from_Baseline': diff,
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'significant': sig
                    })

        # OLS regression with intervention dummies
        print(f"\nOLS Regression: bid_shading ~ C(intervention)")
        print("-" * 60)

        try:
            # Set baseline as reference category
            combined_df['intervention'] = pd.Categorical(
                combined_df['intervention'],
                categories=[baseline_name] + [k for k in group_data.keys() if k != baseline_name]
            )

            model = smf.ols('bid_shading ~ C(intervention) + player_value', data=combined_df).fit()
            print(model.summary().tables[1].as_text())
        except Exception as e:
            print(f"  Regression error: {e}")

    return pd.DataFrame(results)


def plot_vertical_comparison(group_name: str,
                              group_data: Dict[str, pd.DataFrame],
                              output_path: Path):
    """Create vertical stacked distribution plots for one axis."""

    if not group_data:
        print(f"  No data for {group_name}")
        return

    # Number of interventions
    n_rows = len(group_data)

    # Create figure
    fig, axes = plt.subplots(n_rows, 1, figsize=(10, 2.5 * n_rows), sharex=True)

    if n_rows == 1:
        axes = [axes]

    # Define bins for bid ratio (bid/value)
    bins = np.linspace(0, 2, 21)  # 0 to 2 in steps of 0.1

    # Colors
    colors = plt.cm.Set2(np.linspace(0, 1, n_rows))

    for idx, (label, df) in enumerate(group_data.items()):
        ax = axes[idx]

        # Get bid ratio data
        data = df['bid_ratio'].values
        data = data[(data >= 0) & (data <= 2)]  # Clip to reasonable range

        if len(data) == 0:
            continue

        # Calculate weights for percentage
        weights = 100.0 * np.ones(len(data)) / len(data)

        # Histogram
        ax.hist(data, bins=bins, weights=weights, alpha=0.7,
                color=colors[idx], edgecolor='black', linewidth=0.5)

        # Mean line
        mean_val = np.mean(data)
        ax.axvline(mean_val, color='red', linestyle='-', linewidth=2,
                   label=f'Mean={mean_val:.2f}')

        # Optimal line (bid = value, ratio = 1)
        ax.axvline(1.0, color='green', linestyle='--', linewidth=2,
                   alpha=0.7, label='Optimal (b=v)')

        # Labels
        ax.set_ylabel('Density (%)', fontsize=10)
        if idx == n_rows - 1:
            ax.set_xlabel('Bid / Value Ratio', fontsize=12, fontweight='bold')

        # Title on left
        ax.text(0.02, 0.95, label,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='left',
                fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))

        # Stats box on right
        stats_text = (f'N={len(data)}\n'
                      f'μ={mean_val:.3f}\n'
                      f'σ={np.std(data):.3f}')
        ax.text(0.98, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                fontsize=9, family='monospace',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))

        # Grid
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xlim(0, 2)
        ax.set_ylim(0, None)

    # Title
    short_name = group_name.replace("Axis ", "").replace(": ", " - ")
    fig.suptitle(f'{short_name}\nBid/Value Distribution by Intervention',
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"  ✓ Saved: {output_path}")

    plt.close()


def plot_summary_comparison(all_data: Dict[str, Dict[str, pd.DataFrame]],
                            output_path: Path):
    """Create summary plot comparing all axes."""

    # Collect summary statistics
    summary_data = []

    for group_name, group_data in all_data.items():
        for int_name, df in group_data.items():
            if len(df) > 0:
                summary_data.append({
                    'Axis': group_name.split(':')[0].strip() if ':' in group_name else group_name,
                    'Intervention': int_name,
                    'Mean_Ratio': df['bid_ratio'].mean(),
                    'Std_Ratio': df['bid_ratio'].std(),
                    'Mean_Shading': df['bid_shading'].mean(),
                    'N': len(df)
                })

    if not summary_data:
        print("No data for summary plot")
        return

    summary_df = pd.DataFrame(summary_data)

    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(14, 8))

    axes = summary_df['Axis'].unique()
    x = np.arange(len(axes))
    width = 0.15

    # Get all unique interventions
    all_interventions = []
    for group_data in all_data.values():
        all_interventions.extend(group_data.keys())
    unique_interventions = list(dict.fromkeys(all_interventions))[:6]  # Max 6

    colors = plt.cm.Set2(np.linspace(0, 1, len(unique_interventions)))

    for i, intervention in enumerate(unique_interventions):
        means = []
        stds = []
        for axis in axes:
            subset = summary_df[(summary_df['Axis'] == axis) &
                                (summary_df['Intervention'] == intervention)]
            if len(subset) > 0:
                means.append(subset['Mean_Ratio'].values[0])
                stds.append(subset['Std_Ratio'].values[0])
            else:
                means.append(np.nan)
                stds.append(np.nan)

        offset = (i - len(unique_interventions)/2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, label=intervention,
                      color=colors[i], edgecolor='black', linewidth=0.5)

    # Optimal line
    ax.axhline(1.0, color='green', linestyle='--', linewidth=2,
               label='Optimal (bid=value)', alpha=0.7)

    ax.set_ylabel('Mean Bid/Value Ratio', fontsize=12, fontweight='bold')
    ax.set_xlabel('Behavioral Axis', fontsize=12, fontweight='bold')
    ax.set_title('V12 Behavioral Interventions: Summary Comparison\n(SPSB Auction - Optimal bid = value)',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(axes, fontsize=10)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 1.5)

    plt.tight_layout()

    # Save
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"✓ Saved summary: {output_path}")

    plt.close()


def print_key_findings(all_data: Dict[str, Dict[str, pd.DataFrame]]):
    """Print key findings from the analysis."""

    print("\n" + "="*70)
    print("KEY FINDINGS")
    print("="*70)

    print("\n📌 SPSB Optimal Strategy: Bid = Value (bid_ratio = 1.0)")
    print("   Deviations indicate failure to understand dominant strategy.\n")

    for group_name, group_data in all_data.items():
        print(f"\n{group_name}:")
        print("-" * 50)

        if not group_data:
            print("  No data")
            continue

        # Find best and worst performing interventions
        means = {name: df['bid_ratio'].mean() for name, df in group_data.items() if len(df) > 0}

        if means:
            best = min(means.items(), key=lambda x: abs(x[1] - 1.0))
            worst = max(means.items(), key=lambda x: abs(x[1] - 1.0))

            print(f"  Closest to optimal: {best[0]} (ratio={best[1]:.3f})")
            print(f"  Furthest from optimal: {worst[0]} (ratio={worst[1]:.3f})")

            # Check if baseline is best/worst
            baseline = list(group_data.keys())[0]
            if baseline in means:
                baseline_ratio = means[baseline]
                print(f"  Baseline ({baseline}): ratio={baseline_ratio:.3f}")

                # Count improvements over baseline
                improvements = sum(1 for name, ratio in means.items()
                                   if name != baseline and abs(ratio - 1.0) < abs(baseline_ratio - 1.0))
                print(f"  Interventions closer to optimal than baseline: {improvements}/{len(means)-1}")


def main():
    """Main execution."""
    print("="*70)
    print("V12 BEHAVIORAL INTERVENTIONS ANALYSIS")
    print("Testing Shengwu Li's Mechanism Complexity Axes + Loss Aversion")
    print("="*70)

    # Load all data
    all_data = load_all_interventions()

    # Run regression analysis
    print("\n" + "="*70)
    print("STATISTICAL ANALYSIS")
    print("="*70)
    regression_results = run_regression_analysis(all_data)

    # Save regression results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not regression_results.empty:
        regression_results.to_csv(OUTPUT_DIR / "regression_results.csv", index=False)
        print(f"\n✓ Saved regression results to {OUTPUT_DIR / 'regression_results.csv'}")

    # Generate plots for each axis
    print("\n" + "="*70)
    print("GENERATING PLOTS")
    print("="*70)

    axis_files = {
        "Axis 1: Contingent Reasoning": "axis_1_comparison.png",
        "Axis 2: Forward Planning": "axis_2_comparison.png",
        "Axis 3: Higher-Order Beliefs": "axis_3_comparison.png",
        "Loss Aversion": "loss_aversion_comparison.png",
    }

    for group_name, group_data in all_data.items():
        print(f"\n📊 Plotting {group_name}...")
        output_file = axis_files.get(group_name, f"{group_name.lower().replace(' ', '_')}.png")
        plot_vertical_comparison(group_name, group_data, OUTPUT_DIR / output_file)

    # Summary comparison plot
    print(f"\n📊 Generating summary comparison...")
    plot_summary_comparison(all_data, OUTPUT_DIR / "v12_summary_comparison.png")

    # Print key findings
    print_key_findings(all_data)

    print("\n" + "="*70)
    print("✓ ANALYSIS COMPLETE!")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()

"""
Claude Sonnet Intervention Comparison: FPSB vs TPSB

Compares bidding behavior across all interventions for Claude Sonnet,
showing FP and TP side-by-side.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
EXPERIMENT_DIR = Path("experiment_logs_cutoff/V12")
OUTPUT_DIR = Path("results/v12_interventions/claude_comparison")

# All interventions grouped by axis
ALL_INTERVENTIONS = {
    "Contingent Reasoning": {
        "Baseline": ("axis1_contingent_baseline_first", "axis1_contingent_baseline_third"),
        "List Cases": ("axis1_contingent_enumerate_first", "axis1_contingent_enumerate_third"),
        "Dominated Bid": ("axis1_contingent_dominated_first", "axis1_contingent_dominated_third"),
        "Worst Case": ("axis1_contingent_worstcase_first", "axis1_contingent_worstcase_third"),
        "Nash Deviation": ("intervention_nash_deviation_first", "intervention_nash_deviation_third"),
    },
    "Forward Planning": {
        "Two-Stage OSP": ("axis2_forward_baseline_first", "axis2_forward_baseline_third"),
        "Backward Induct": ("axis2_forward_backward_induct_first", "axis2_forward_backward_induct_third"),
        "One-Step Look": ("axis2_forward_onestep_first", "axis2_forward_onestep_third"),
        "Decision Tree": ("axis2_forward_tree_first", "axis2_forward_tree_third"),
        "Proxy/Clock": ("intervention_proxy_breitmoser_first", "intervention_proxy_breitmoser_third"),
        "Menu Frame": ("intervention_menu_first", "intervention_menu_third"),
    },
    "Higher-Order Beliefs": {
        "Rational Others": ("axis3_beliefs_baseline_first", "axis3_beliefs_baseline_third"),
        "First-Order": ("axis3_beliefs_firstorder_first", "axis3_beliefs_firstorder_third"),
        "Second-Order": ("axis3_beliefs_secondorder_first", "axis3_beliefs_secondorder_third"),
        "Common Know": ("axis3_beliefs_common_knowledge_first", "axis3_beliefs_common_knowledge_third"),
    },
    "Prospect Theory": {
        "LA: Baseline": ("loss_aversion_baseline_first", "loss_aversion_baseline_third"),
        "LA: Gain Frame": ("loss_aversion_gain_frame_first", "loss_aversion_gain_frame_third"),
        "LA: Loss Frame": ("loss_aversion_loss_frame_first", "loss_aversion_loss_frame_third"),
        "LA: Mixed Frame": ("loss_aversion_mixed_frame_first", "loss_aversion_mixed_frame_third"),
        "LA: Endowment": ("loss_aversion_endowment_first", "loss_aversion_endowment_third"),
        "LA: WTA vs WTP": ("loss_aversion_WTA_WTP_first", "loss_aversion_WTA_WTP_third"),
        "Risk Averse": ("intervention_risk_averse_first", "intervention_risk_averse_third"),
        "Risk Neutral": ("intervention_risk_neutral_first", "intervention_risk_neutral_third"),
        "Risk Seeking": ("intervention_risk_seeking_first", "intervention_risk_seeking_third"),
    },
    "Strategy Revelation": {
        "Correct Strategy": ("intervention_NE_strat_reveal_first", "intervention_NE_strat_reveal_third"),
        "Wrong Strategy": ("intervention_wrong_strat_reveal_first", "intervention_wrong_strat_reveal_third"),
    },
}

# Optimal ratios
OPTIMAL_FP = 2/3
OPTIMAL_TP = 2.0


def load_experiment_data(exp_name: str) -> pd.DataFrame:
    """Load experiment data from all runs."""
    if exp_name is None:
        return pd.DataFrame()

    exp_path = EXPERIMENT_DIR / exp_name
    if not exp_path.exists():
        return pd.DataFrame()

    dfs = []
    for csv_file in exp_path.rglob("*_results.csv"):
        if "merged" not in csv_file.name:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception:
                pass

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df['player_value'] = pd.to_numeric(df['player_value'], errors='coerce')
        df['bid'] = pd.to_numeric(df['bid'], errors='coerce')
        df = df.dropna(subset=['player_value', 'bid'])
        df = df[df['player_value'] > 0]
        return df
    return pd.DataFrame()


def compute_metrics(df: pd.DataFrame, optimal_ratio: float) -> dict:
    """Compute bidding metrics."""
    if df.empty:
        return {'n': 0, 'mean_ratio': np.nan, 'std_ratio': np.nan,
                'smad': np.nan, 'dist_from_optimal': np.nan}

    values = df['player_value'].values
    bids = df['bid'].values

    ratios = bids / values
    mean_ratio = np.mean(ratios)
    std_ratio = np.std(ratios)

    # SMAD
    optimal_bids = values * optimal_ratio
    smad = 100 * np.mean(np.abs(bids - optimal_bids)) / np.mean(optimal_bids)

    return {
        'n': len(df),
        'mean_ratio': mean_ratio,
        'std_ratio': std_ratio,
        'smad': smad,
        'dist_from_optimal': abs(mean_ratio - optimal_ratio)
    }


def plot_claude_fp_tp_comparison():
    """Create comprehensive FP vs TP comparison plot for Claude."""

    # Collect all data
    all_results = []

    for axis_name, interventions in ALL_INTERVENTIONS.items():
        for int_name, (fp_exp, tp_exp) in interventions.items():
            df_fp = load_experiment_data(fp_exp)
            df_tp = load_experiment_data(tp_exp)

            metrics_fp = compute_metrics(df_fp, OPTIMAL_FP)
            metrics_tp = compute_metrics(df_tp, OPTIMAL_TP)

            all_results.append({
                'Axis': axis_name,
                'Intervention': int_name,
                'FP_N': metrics_fp['n'],
                'FP_Ratio': metrics_fp['mean_ratio'],
                'FP_Std': metrics_fp['std_ratio'],
                'FP_SMAD': metrics_fp['smad'],
                'FP_Dist': metrics_fp['dist_from_optimal'],
                'TP_N': metrics_tp['n'],
                'TP_Ratio': metrics_tp['mean_ratio'],
                'TP_Std': metrics_tp['std_ratio'],
                'TP_SMAD': metrics_tp['smad'],
                'TP_Dist': metrics_tp['dist_from_optimal'],
            })

    results_df = pd.DataFrame(all_results)

    # Filter to interventions with data
    results_df = results_df[results_df['FP_N'] > 0]

    if results_df.empty:
        print("No data found!")
        return None

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))

    # Colors for each axis
    axis_colors = {
        'Contingent Reasoning': '#1f77b4',
        'Forward Planning': '#ff7f0e',
        'Higher-Order Beliefs': '#2ca02c',
        'Prospect Theory': '#d62728',
        'Strategy Revelation': '#9467bd',
    }

    # Plot 1: Bar chart of bid ratios
    n_interventions = len(results_df)
    x = np.arange(n_interventions)
    width = 0.35

    # Get colors for each bar based on axis
    bar_colors = [axis_colors.get(row['Axis'], 'gray') for _, row in results_df.iterrows()]

    bars1 = ax1.bar(x - width/2, results_df['FP_Ratio'], width,
                    label='First-Price', color='#1f77b4', alpha=0.8)
    bars2 = ax1.bar(x + width/2, results_df['TP_Ratio'], width,
                    label='Third-Price', color='#d62728', alpha=0.8)

    # Add optimal lines
    ax1.axhline(y=OPTIMAL_FP, color='#1f77b4', linestyle='--', linewidth=2,
                label=f'FP Optimal ({OPTIMAL_FP:.2f})')
    ax1.axhline(y=OPTIMAL_TP, color='#d62728', linestyle='--', linewidth=2,
                label=f'TP Optimal ({OPTIMAL_TP:.2f})')
    ax1.axhline(y=1.0, color='black', linestyle=':', linewidth=1, alpha=0.5,
                label='bid = value')

    ax1.set_ylabel('Mean Bid/Value Ratio', fontsize=11)
    ax1.set_title('Claude Sonnet: Bid Ratios by Intervention', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(results_df['Intervention'], rotation=45, ha='right', fontsize=9)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_ylim(0, 2.5)
    ax1.grid(True, alpha=0.3, axis='y')

    # Add axis separators
    current_axis = None
    for i, (_, row) in enumerate(results_df.iterrows()):
        if row['Axis'] != current_axis:
            if current_axis is not None:
                ax1.axvline(x=i-0.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
            current_axis = row['Axis']

    # Plot 2: SMAD comparison
    bars3 = ax2.bar(x - width/2, results_df['FP_SMAD'], width,
                    label='First-Price SMAD', color='#1f77b4', alpha=0.8)
    bars4 = ax2.bar(x + width/2, results_df['TP_SMAD'], width,
                    label='Third-Price SMAD', color='#d62728', alpha=0.8)

    ax2.set_ylabel('SMAD (%)', fontsize=11)
    ax2.set_title('Claude Sonnet: SMAD by Intervention', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(results_df['Intervention'], rotation=45, ha='right', fontsize=9)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add axis separators
    current_axis = None
    for i, (_, row) in enumerate(results_df.iterrows()):
        if row['Axis'] != current_axis:
            if current_axis is not None:
                ax2.axvline(x=i-0.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
            current_axis = row['Axis']

    plt.suptitle('Claude Sonnet: First-Price vs Third-Price Auction Interventions',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_DIR / 'claude_fp_tp_comparison_bars.png', dpi=150, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'claude_fp_tp_comparison_bars.pdf', bbox_inches='tight')
    print(f"Saved bar plot to {OUTPUT_DIR / 'claude_fp_tp_comparison_bars.png'}")
    plt.close()

    return results_df


def plot_claude_scatter_grid():
    """Create scatter plot grid showing bid vs value for each intervention."""

    # Count interventions
    n_total = sum(len(ints) for ints in ALL_INTERVENTIONS.values())

    # Create grid
    n_cols = 2  # FP and TP
    n_rows = n_total

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 2.5 * n_rows))

    row_idx = 0
    current_axis = None

    for axis_name, interventions in ALL_INTERVENTIONS.items():
        for int_name, (fp_exp, tp_exp) in interventions.items():
            df_fp = load_experiment_data(fp_exp)
            df_tp = load_experiment_data(tp_exp)

            # Plot FP
            ax_fp = axes[row_idx, 0]
            if not df_fp.empty:
                values = df_fp['player_value'].values
                bids = df_fp['bid'].values

                ax_fp.scatter(values, bids, alpha=0.4, s=20, c='#1f77b4', edgecolors='none')

                x_line = np.linspace(0, max(values.max(), 50), 100)
                ax_fp.plot(x_line, x_line * OPTIMAL_FP, 'g--', lw=2, label='Optimal (2/3·v)')
                ax_fp.plot(x_line, x_line, 'k:', lw=1, alpha=0.5)

                mean_ratio = np.mean(bids / values)
                ax_fp.plot(x_line, x_line * mean_ratio, 'r-', lw=1.5, alpha=0.7)

                metrics = compute_metrics(df_fp, OPTIMAL_FP)
                stats = f'N={metrics["n"]}, μ={metrics["mean_ratio"]:.2f}, SMAD={metrics["smad"]:.1f}%'
                ax_fp.text(0.02, 0.98, stats, transform=ax_fp.transAxes, fontsize=8,
                          va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

                ax_fp.set_xlim(0, 55)
                ax_fp.set_ylim(0, 55)
            else:
                ax_fp.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax_fp.transAxes)

            ax_fp.set_ylabel(int_name, fontsize=9, fontweight='bold')
            ax_fp.grid(True, alpha=0.2)

            # Add axis label on first intervention of each axis
            if axis_name != current_axis:
                current_axis = axis_name
                ax_fp.text(-0.2, 0.5, axis_name, transform=ax_fp.transAxes,
                          fontsize=10, fontweight='bold', ha='right', va='center', rotation=90)

            # Plot TP
            ax_tp = axes[row_idx, 1]
            if not df_tp.empty:
                values = df_tp['player_value'].values
                bids = df_tp['bid'].values

                ax_tp.scatter(values, bids, alpha=0.4, s=20, c='#d62728', edgecolors='none')

                x_line = np.linspace(0, max(values.max(), 50), 100)
                ax_tp.plot(x_line, x_line * OPTIMAL_TP, 'g--', lw=2, label='Optimal (2·v)')
                ax_tp.plot(x_line, x_line, 'k:', lw=1, alpha=0.5)

                mean_ratio = np.mean(bids / values)
                ax_tp.plot(x_line, x_line * mean_ratio, 'r-', lw=1.5, alpha=0.7)

                metrics = compute_metrics(df_tp, OPTIMAL_TP)
                stats = f'N={metrics["n"]}, μ={metrics["mean_ratio"]:.2f}, SMAD={metrics["smad"]:.1f}%'
                ax_tp.text(0.02, 0.98, stats, transform=ax_tp.transAxes, fontsize=8,
                          va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

                ax_tp.set_xlim(0, 55)
                ax_tp.set_ylim(0, 120)
            else:
                ax_tp.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax_tp.transAxes)

            ax_tp.grid(True, alpha=0.2)

            row_idx += 1

    # Column headers
    axes[0, 0].set_title('First-Price (optimal: 2/3·v)', fontsize=12, fontweight='bold')
    axes[0, 1].set_title('Third-Price (optimal: 2·v)', fontsize=12, fontweight='bold')

    # X-axis labels only on bottom row
    axes[-1, 0].set_xlabel('Value', fontsize=10)
    axes[-1, 1].set_xlabel('Value', fontsize=10)

    fig.suptitle('Claude Sonnet: Bid vs Value Across All Interventions',
                 fontsize=14, fontweight='bold', y=1.01)

    plt.tight_layout(rect=[0.05, 0, 1, 0.99])

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_DIR / 'claude_fp_tp_scatter_grid.png', dpi=150, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'claude_fp_tp_scatter_grid.pdf', bbox_inches='tight')
    print(f"Saved scatter grid to {OUTPUT_DIR / 'claude_fp_tp_scatter_grid.png'}")
    plt.close()


def create_summary_table():
    """Create and save summary CSV."""

    all_results = []

    for axis_name, interventions in ALL_INTERVENTIONS.items():
        for int_name, (fp_exp, tp_exp) in interventions.items():
            df_fp = load_experiment_data(fp_exp)
            df_tp = load_experiment_data(tp_exp)

            metrics_fp = compute_metrics(df_fp, OPTIMAL_FP)
            metrics_tp = compute_metrics(df_tp, OPTIMAL_TP)

            all_results.append({
                'Axis': axis_name,
                'Intervention': int_name,
                'Auction': 'FPSB',
                'N': metrics_fp['n'],
                'Mean_Ratio': metrics_fp['mean_ratio'],
                'Std_Ratio': metrics_fp['std_ratio'],
                'Optimal_Ratio': OPTIMAL_FP,
                'Distance_from_Optimal': metrics_fp['dist_from_optimal'],
                'SMAD': metrics_fp['smad'],
            })
            all_results.append({
                'Axis': axis_name,
                'Intervention': int_name,
                'Auction': 'TPSB',
                'N': metrics_tp['n'],
                'Mean_Ratio': metrics_tp['mean_ratio'],
                'Std_Ratio': metrics_tp['std_ratio'],
                'Optimal_Ratio': OPTIMAL_TP,
                'Distance_from_Optimal': metrics_tp['dist_from_optimal'],
                'SMAD': metrics_tp['smad'],
            })

    results_df = pd.DataFrame(all_results)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_DIR / 'claude_intervention_summary.csv', index=False)
    print(f"Saved summary to {OUTPUT_DIR / 'claude_intervention_summary.csv'}")

    return results_df


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')

    print("="*70)
    print("CLAUDE SONNET INTERVENTION COMPARISON: FP vs TP")
    print("="*70)

    # Create bar comparison plot
    print("\nGenerating bar comparison plot...")
    results_df = plot_claude_fp_tp_comparison()

    if results_df is not None:
        # Create scatter grid
        print("\nGenerating scatter grid plot...")
        plot_claude_scatter_grid()

        # Create summary table
        print("\nGenerating summary table...")
        summary_df = create_summary_table()

        # Print summary
        print("\n" + "="*70)
        print("SUMMARY: Claude Sonnet Bid Ratios")
        print("="*70)
        print(f"\n{'Intervention':<20} {'FP Ratio':<12} {'FP SMAD':<12} {'TP Ratio':<12} {'TP SMAD':<12}")
        print("-"*70)

        for _, row in results_df.iterrows():
            print(f"{row['Intervention']:<20} {row['FP_Ratio']:.3f}        {row['FP_SMAD']:.1f}%        {row['TP_Ratio']:.3f}        {row['TP_SMAD']:.1f}%")

    print("\n" + "="*70)
    print("COMPLETE!")
    print(f"Results saved to: {OUTPUT_DIR}")
    print("="*70)

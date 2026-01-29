"""
Claude Sonnet Combined Scatter Plot: FPSB vs SPSB

Shows both auction types on the same scatter plot for each intervention,
color-coded by cognitive axis.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
EXPERIMENT_DIR = Path("experiment_logs_cutoff/V12")
OUTPUT_DIR = Path("results/v12_interventions/claude_comparison")

# All interventions with (SPSB, FPSB) experiment names
ALL_INTERVENTIONS = {
    "Contingent Reasoning": {
        "Baseline": ("axis1_contingent_baseline", "axis1_contingent_baseline_first"),
        "List Cases": ("axis1_contingent_enumerate", "axis1_contingent_enumerate_first"),
        "Dominated Bid": ("axis1_contingent_dominated", "axis1_contingent_dominated_first"),
        "Worst Case": ("axis1_contingent_worstcase", "axis1_contingent_worstcase_first"),
        "Nash Deviation": (None, "intervention_nash_deviation_first"),
    },
    "Forward Planning": {
        "Two-Stage OSP": ("axis2_forward_baseline", "axis2_forward_baseline_first"),
        "Backward Induct": ("axis2_forward_backward_induct", "axis2_forward_backward_induct_first"),
        "One-Step Look": ("axis2_forward_onestep", "axis2_forward_onestep_first"),
        "Decision Tree": ("axis2_forward_tree", "axis2_forward_tree_first"),
        "Proxy/Clock": (None, "intervention_proxy_breitmoser_first"),
        "Menu Frame": (None, "intervention_menu_first"),
    },
    "Higher-Order Beliefs": {
        "Rational Others": ("axis3_beliefs_baseline", "axis3_beliefs_baseline_first"),
        "First-Order": ("axis3_beliefs_firstorder", "axis3_beliefs_firstorder_first"),
        "Second-Order": ("axis3_beliefs_secondorder", "axis3_beliefs_secondorder_first"),
        "Common Know": ("axis3_beliefs_common_knowledge", "axis3_beliefs_common_knowledge_first"),
    },
    "Prospect Theory": {
        "LA: Baseline": ("loss_aversion_baseline", "loss_aversion_baseline_first"),
        "LA: Gain Frame": ("loss_aversion_gain_frame", "loss_aversion_gain_frame_first"),
        "LA: Loss Frame": ("loss_aversion_loss_frame", "loss_aversion_loss_frame_first"),
        "LA: Mixed Frame": ("loss_aversion_mixed_frame", "loss_aversion_mixed_frame_first"),
        "LA: Endowment": ("loss_aversion_endowment", "loss_aversion_endowment_first"),
        "LA: WTA vs WTP": ("loss_aversion_WTA_WTP", "loss_aversion_WTA_WTP_first"),
        "Risk Averse": (None, "intervention_risk_averse_first"),
        "Risk Neutral": (None, "intervention_risk_neutral_first"),
        "Risk Seeking": (None, "intervention_risk_seeking_first"),
    },
    "Strategy Revelation": {
        "Correct Strategy": (None, "intervention_NE_strat_reveal_first"),
        "Wrong Strategy": (None, "intervention_wrong_strat_reveal_first"),
    },
}

# Optimal ratios
OPTIMAL = {
    'SPSB': 1.0,
    'FPSB': 2/3,
}

# Colors for auction types (used in regression lines)
AUCTION_COLORS = {
    'FPSB': '#1f77b4',  # Blue
    'SPSB': '#d62728',  # Red
}

# Colors for cognitive axes
AXIS_COLORS = {
    'Contingent Reasoning': '#1f77b4',   # Blue
    'Forward Planning': '#ff7f0e',        # Orange
    'Higher-Order Beliefs': '#2ca02c',    # Green
    'Prospect Theory': '#9467bd',         # Purple
    'Strategy Revelation': '#8c564b',     # Brown
}


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
        return {'n': 0, 'mean_ratio': np.nan, 'smad': np.nan}

    values = df['player_value'].values
    bids = df['bid'].values
    ratios = bids / values

    optimal_bids = values * optimal_ratio
    smad = 100 * np.mean(np.abs(bids - optimal_bids)) / np.mean(optimal_bids)

    return {
        'n': len(df),
        'mean_ratio': np.mean(ratios),
        'smad': smad,
    }


def plot_combined_scatter():
    """Create combined scatter plot with SPSB and FPSB, color-coded by axis."""

    # Count interventions
    all_ints = []
    for axis_name, interventions in ALL_INTERVENTIONS.items():
        for int_name, exps in interventions.items():
            all_ints.append((axis_name, int_name, exps))

    n_total = len(all_ints)
    n_cols = 5
    n_rows = (n_total + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
    axes = axes.flatten()

    for idx, (axis_name, int_name, (sp_exp, fp_exp)) in enumerate(all_ints):
        ax = axes[idx]
        axis_color = AXIS_COLORS[axis_name]

        df_sp = load_experiment_data(sp_exp)
        df_fp = load_experiment_data(fp_exp)

        max_val = 50
        x_line = np.linspace(0, max_val, 100)

        legend_entries = []

        # FPSB (axis color, circles)
        if not df_fp.empty:
            values_fp = df_fp['player_value'].values
            bids_fp = df_fp['bid'].values
            ax.scatter(values_fp, bids_fp, alpha=0.4, s=15, c=axis_color,
                      edgecolors='none', marker='o')
            metrics_fp = compute_metrics(df_fp, OPTIMAL['FPSB'])
            legend_entries.append(f"FP: μ={metrics_fp['mean_ratio']:.2f}")
            # Regression line for FPSB (solid)
            ax.plot(x_line, x_line * metrics_fp['mean_ratio'], '-', color=axis_color,
                    lw=2, alpha=0.8)

        # SPSB (axis color but lighter/different marker)
        if not df_sp.empty:
            values_sp = df_sp['player_value'].values
            bids_sp = df_sp['bid'].values
            ax.scatter(values_sp, bids_sp, alpha=0.3, s=15, c=axis_color,
                      edgecolors='none', marker='s')
            metrics_sp = compute_metrics(df_sp, OPTIMAL['SPSB'])
            legend_entries.append(f"SP: μ={metrics_sp['mean_ratio']:.2f}")
            # Regression line for SPSB (dashed)
            ax.plot(x_line, x_line * metrics_sp['mean_ratio'], '--', color=axis_color,
                    lw=2, alpha=0.8)

        # Identity line (y = x)
        ax.plot(x_line, x_line, 'k-', lw=1, alpha=0.5)

        ax.set_xlim(0, 55)
        ax.set_ylim(0, 55)
        ax.set_title(f"{int_name}", fontsize=10, fontweight='bold', color=axis_color)
        ax.set_xlabel('Value', fontsize=8)
        ax.set_ylabel('Bid', fontsize=8)
        ax.grid(True, alpha=0.2)

        # Add colored border to show axis
        for spine in ax.spines.values():
            spine.set_edgecolor(axis_color)
            spine.set_linewidth(2)

        # Stats text
        if legend_entries:
            stats_text = '\n'.join(legend_entries)
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=7,
                   va='top', ha='left',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Hide unused axes
    for idx in range(n_total, len(axes)):
        axes[idx].set_visible(False)

    # Create legend for axes and markers
    from matplotlib.lines import Line2D
    legend_elements = []
    for axis_name, color in AXIS_COLORS.items():
        legend_elements.append(
            Line2D([0], [0], marker='s', color='w', markerfacecolor=color,
                   markersize=10, label=axis_name)
        )
    legend_elements.extend([
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
               markersize=8, label='FPSB (circles)'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='gray',
               markersize=8, label='SPSB (squares)'),
        Line2D([0], [0], linestyle='-', color='gray', lw=2, label='FP mean'),
        Line2D([0], [0], linestyle='--', color='gray', lw=2, label='SP mean'),
        Line2D([0], [0], linestyle='-', color='black', alpha=0.5, label='y = x'),
    ])
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.99, 0.99),
               fontsize=9)

    fig.suptitle('Claude Sonnet: Bid vs Value by Intervention\n(circles=FPSB, squares=SPSB; solid=FP mean, dashed=SP mean)',
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_DIR / 'claude_fp_sp_scatter.png', dpi=150, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'claude_fp_sp_scatter.pdf', bbox_inches='tight')
    print(f"Saved to {OUTPUT_DIR / 'claude_fp_sp_scatter.png'}")
    plt.close()


def plot_aggregated_by_axis():
    """Create one scatter plot per cognitive axis, aggregating all interventions."""

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    axis_results = []

    for idx, (axis_name, interventions) in enumerate(ALL_INTERVENTIONS.items()):
        ax = axes[idx]
        axis_color = AXIS_COLORS[axis_name]

        # Collect all data for this axis
        all_fp_values, all_fp_bids = [], []
        all_sp_values, all_sp_bids = [], []

        for int_name, (sp_exp, fp_exp) in interventions.items():
            df_fp = load_experiment_data(fp_exp)
            df_sp = load_experiment_data(sp_exp)

            if not df_fp.empty:
                all_fp_values.extend(df_fp['player_value'].values)
                all_fp_bids.extend(df_fp['bid'].values)
            if not df_sp.empty:
                all_sp_values.extend(df_sp['player_value'].values)
                all_sp_bids.extend(df_sp['bid'].values)

        all_fp_values = np.array(all_fp_values)
        all_fp_bids = np.array(all_fp_bids)
        all_sp_values = np.array(all_sp_values)
        all_sp_bids = np.array(all_sp_bids)

        max_val = 50
        x_line = np.linspace(0, max_val, 100)

        # Plot FPSB (circles)
        if len(all_fp_values) > 0:
            ax.scatter(all_fp_values, all_fp_bids, alpha=0.3, s=10, c=AUCTION_COLORS['FPSB'],
                      edgecolors='none', marker='o', label='FPSB')
            fp_ratio = np.mean(all_fp_bids / all_fp_values)
            ax.plot(x_line, x_line * fp_ratio, '-', color=AUCTION_COLORS['FPSB'], lw=2.5, alpha=0.9)
            fp_smad = 100 * np.mean(np.abs(all_fp_bids - all_fp_values * OPTIMAL['FPSB'])) / np.mean(all_fp_values * OPTIMAL['FPSB'])
        else:
            fp_ratio, fp_smad = np.nan, np.nan

        # Plot SPSB (squares)
        if len(all_sp_values) > 0:
            ax.scatter(all_sp_values, all_sp_bids, alpha=0.3, s=10, c=AUCTION_COLORS['SPSB'],
                      edgecolors='none', marker='s', label='SPSB')
            sp_ratio = np.mean(all_sp_bids / all_sp_values)
            ax.plot(x_line, x_line * sp_ratio, '--', color=AUCTION_COLORS['SPSB'], lw=2.5, alpha=0.9)
            sp_smad = 100 * np.mean(np.abs(all_sp_bids - all_sp_values * OPTIMAL['SPSB'])) / np.mean(all_sp_values * OPTIMAL['SPSB'])
        else:
            sp_ratio, sp_smad = np.nan, np.nan

        # Identity line
        ax.plot(x_line, x_line, 'k-', lw=1.5, alpha=0.5)

        ax.set_xlim(0, 55)
        ax.set_ylim(0, 55)
        ax.set_title(axis_name, fontsize=12, fontweight='bold', color=axis_color)
        ax.set_xlabel('Value', fontsize=10)
        ax.set_ylabel('Bid', fontsize=10)
        ax.grid(True, alpha=0.2)

        # Colored border
        for spine in ax.spines.values():
            spine.set_edgecolor(axis_color)
            spine.set_linewidth(3)

        # Stats
        stats_text = f"FP: n={len(all_fp_values)}, μ={fp_ratio:.2f}\nSP: n={len(all_sp_values)}, μ={sp_ratio:.2f}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
               va='top', ha='left',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

        axis_results.append({
            'Axis': axis_name,
            'FP_N': len(all_fp_values),
            'FP_Ratio': fp_ratio,
            'FP_SMAD': fp_smad,
            'SP_N': len(all_sp_values),
            'SP_Ratio': sp_ratio,
            'SP_SMAD': sp_smad,
        })

    # Hide last subplot
    axes[-1].set_visible(False)

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=AUCTION_COLORS['FPSB'],
               markersize=10, label='FPSB (opt=0.67)'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor=AUCTION_COLORS['SPSB'],
               markersize=10, label='SPSB (opt=1.0)'),
        Line2D([0], [0], linestyle='-', color=AUCTION_COLORS['FPSB'], lw=2, label='FP mean'),
        Line2D([0], [0], linestyle='--', color=AUCTION_COLORS['SPSB'], lw=2, label='SP mean'),
        Line2D([0], [0], linestyle='-', color='black', alpha=0.5, lw=1.5, label='y = x'),
    ]
    fig.legend(handles=legend_elements, loc='lower right', bbox_to_anchor=(0.95, 0.15),
               fontsize=10)

    fig.suptitle('Claude Sonnet: Aggregated by Cognitive Axis\n(FPSB=blue circles, SPSB=red squares)',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()

    # Save
    plt.savefig(OUTPUT_DIR / 'claude_aggregated_by_axis.png', dpi=150, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'claude_aggregated_by_axis.pdf', bbox_inches='tight')
    print(f"Saved to {OUTPUT_DIR / 'claude_aggregated_by_axis.png'}")
    plt.close()

    return pd.DataFrame(axis_results)


def create_summary():
    """Create summary table with SPSB and FPSB."""

    all_results = []

    for axis_name, interventions in ALL_INTERVENTIONS.items():
        for int_name, (sp_exp, fp_exp) in interventions.items():
            for auction, exp, opt in [('SPSB', sp_exp, OPTIMAL['SPSB']),
                                       ('FPSB', fp_exp, OPTIMAL['FPSB'])]:
                df = load_experiment_data(exp)
                metrics = compute_metrics(df, opt)

                all_results.append({
                    'Axis': axis_name,
                    'Intervention': int_name,
                    'Auction': auction,
                    'N': metrics['n'],
                    'Mean_Ratio': metrics['mean_ratio'],
                    'Optimal': opt,
                    'SMAD': metrics['smad'],
                })

    results_df = pd.DataFrame(all_results)
    results_df.to_csv(OUTPUT_DIR / 'claude_fp_sp_summary.csv', index=False)
    print(f"Saved summary to {OUTPUT_DIR / 'claude_fp_sp_summary.csv'}")

    return results_df


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')

    print("="*70)
    print("CLAUDE SCATTER: FPSB vs SPSB")
    print("="*70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Master combined plot
    print("\nGenerating scatter plot...")
    plot_combined_scatter()

    # Aggregated by axis plot
    print("\nGenerating aggregated by axis plot...")
    axis_results = plot_aggregated_by_axis()

    # Summary table
    print("\nGenerating summary...")
    summary_df = create_summary()

    # Find interesting patterns
    print("\n" + "="*70)
    print("KEY FINDINGS BY INTERVENTION")
    print("="*70)

    fp_data = summary_df[summary_df['Auction'] == 'FPSB'].dropna()
    sp_data = summary_df[summary_df['Auction'] == 'SPSB'].dropna()

    if not fp_data.empty:
        fp_data = fp_data.copy()
        fp_data['dist'] = abs(fp_data['Mean_Ratio'] - 0.667)
        best_fp = fp_data.nsmallest(5, 'dist')
        worst_fp = fp_data.nlargest(5, 'dist')

        print("\nFPSB (optimal = 0.67):")
        print("  Best interventions:")
        for _, row in best_fp.iterrows():
            print(f"    {row['Intervention']}: {row['Mean_Ratio']:.3f}")
        print("  Worst interventions:")
        for _, row in worst_fp.iterrows():
            print(f"    {row['Intervention']}: {row['Mean_Ratio']:.3f}")

    if not sp_data.empty:
        sp_data = sp_data.copy()
        sp_data['dist'] = abs(sp_data['Mean_Ratio'] - 1.0)
        best_sp = sp_data.nsmallest(5, 'dist')
        worst_sp = sp_data.nlargest(5, 'dist')

        print("\nSPSB (optimal = 1.0):")
        print("  Best interventions:")
        for _, row in best_sp.iterrows():
            print(f"    {row['Intervention']}: {row['Mean_Ratio']:.3f}")
        print("  Worst interventions:")
        for _, row in worst_sp.iterrows():
            print(f"    {row['Intervention']}: {row['Mean_Ratio']:.3f}")

    print("\n" + "="*70)
    print("KEY FINDINGS BY COGNITIVE AXIS")
    print("="*70)
    print("\nAggregated results (which axis helps most?):\n")
    print(f"{'Axis':<25} {'FP Ratio':<12} {'FP SMAD':<12} {'SP Ratio':<12} {'SP SMAD':<12}")
    print("-"*75)
    for _, row in axis_results.iterrows():
        print(f"{row['Axis']:<25} {row['FP_Ratio']:.3f}        {row['FP_SMAD']:.1f}%        {row['SP_Ratio']:.3f}        {row['SP_SMAD']:.1f}%")

    # Find best/worst axis
    axis_results['FP_dist'] = abs(axis_results['FP_Ratio'] - 0.667)
    axis_results['SP_dist'] = abs(axis_results['SP_Ratio'] - 1.0)

    best_fp_axis = axis_results.loc[axis_results['FP_dist'].idxmin()]
    worst_fp_axis = axis_results.loc[axis_results['FP_dist'].idxmax()]
    best_sp_axis = axis_results.loc[axis_results['SP_dist'].idxmin()]
    worst_sp_axis = axis_results.loc[axis_results['SP_dist'].idxmax()]

    print(f"\nFPSB: Best axis = {best_fp_axis['Axis']} ({best_fp_axis['FP_Ratio']:.3f})")
    print(f"FPSB: Worst axis = {worst_fp_axis['Axis']} ({worst_fp_axis['FP_Ratio']:.3f})")
    print(f"SPSB: Best axis = {best_sp_axis['Axis']} ({best_sp_axis['SP_Ratio']:.3f})")
    print(f"SPSB: Worst axis = {worst_sp_axis['Axis']} ({worst_sp_axis['SP_Ratio']:.3f})")

    print(f"\nPlots saved to: {OUTPUT_DIR}")
    print("="*70)

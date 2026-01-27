"""
Generate Bid vs Value plots for V12 Behavioral Interventions.

Compares FPSB vs TPSB side-by-side for each intervention,
grouped by cognitive axis.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# Paths
EXPERIMENT_DIR = Path("experiment_logs/V12")
OUTPUT_DIR = Path("results/v12_interventions/bid_vs_value")

# Categorize ALL interventions into cognitive axes
# Format: {display_name: (spsb_exp_name, fpsb_exp_name, tpsb_exp_name)}

AXIS_1_CONTINGENT = {
    "Baseline": ("axis1_contingent_baseline", "axis1_contingent_baseline_first", "axis1_contingent_baseline_third"),
    "List Cases": ("axis1_contingent_enumerate", "axis1_contingent_enumerate_first", "axis1_contingent_enumerate_third"),
    "Dominated Bid": ("axis1_contingent_dominated", "axis1_contingent_dominated_first", "axis1_contingent_dominated_third"),
    "Worst Case": ("axis1_contingent_worstcase", "axis1_contingent_worstcase_first", "axis1_contingent_worstcase_third"),
    "Nash Deviation": (None, "intervention_nash_deviation_first", "intervention_nash_deviation_third"),
}

AXIS_2_FORWARD = {
    "Two-Stage OSP": ("axis2_forward_baseline", "axis2_forward_baseline_first", "axis2_forward_baseline_third"),
    "Backward Induct": ("axis2_forward_backward_induct", "axis2_forward_backward_induct_first", "axis2_forward_backward_induct_third"),
    "One-Step Look": ("axis2_forward_onestep", "axis2_forward_onestep_first", "axis2_forward_onestep_third"),
    "Decision Tree": ("axis2_forward_tree", "axis2_forward_tree_first", "axis2_forward_tree_third"),
    "Proxy/Clock": (None, "intervention_proxy_breitmoser_first", "intervention_proxy_breitmoser_third"),
    "Menu Frame": (None, "intervention_menu_first", "intervention_menu_third"),
}

AXIS_3_BELIEFS = {
    "Rational Others": ("axis3_beliefs_baseline", "axis3_beliefs_baseline_first", "axis3_beliefs_baseline_third"),
    "First-Order": ("axis3_beliefs_firstorder", "axis3_beliefs_firstorder_first", "axis3_beliefs_firstorder_third"),
    "Second-Order": ("axis3_beliefs_secondorder", "axis3_beliefs_secondorder_first", "axis3_beliefs_secondorder_third"),
    "Common Know": ("axis3_beliefs_common_knowledge", "axis3_beliefs_common_knowledge_first", "axis3_beliefs_common_knowledge_third"),
}

PROSPECT_THEORY = {
    "LA: Baseline": ("loss_aversion_baseline", "loss_aversion_baseline_first", "loss_aversion_baseline_third"),
    "LA: Gain Frame": ("loss_aversion_gain_frame", "loss_aversion_gain_frame_first", "loss_aversion_gain_frame_third"),
    "LA: Loss Frame": ("loss_aversion_loss_frame", "loss_aversion_loss_frame_first", "loss_aversion_loss_frame_third"),
    "LA: Mixed Frame": ("loss_aversion_mixed_frame", "loss_aversion_mixed_frame_first", "loss_aversion_mixed_frame_third"),
    "LA: Endowment": ("loss_aversion_endowment", "loss_aversion_endowment_first", "loss_aversion_endowment_third"),
    "LA: WTA vs WTP": ("loss_aversion_WTA_WTP", "loss_aversion_WTA_WTP_first", "loss_aversion_WTA_WTP_third"),
    "Risk Averse": (None, "intervention_risk_averse_first", "intervention_risk_averse_third"),
    "Risk Neutral": (None, "intervention_risk_neutral_first", "intervention_risk_neutral_third"),
    "Risk Seeking": (None, "intervention_risk_seeking_first", "intervention_risk_seeking_third"),
}

STRATEGY_REVEAL = {
    "Correct Strategy": (None, "intervention_NE_strat_reveal_first", "intervention_NE_strat_reveal_third"),
    "Wrong Strategy": (None, "intervention_wrong_strat_reveal_first", "intervention_wrong_strat_reveal_third"),
}

ALL_AXES = {
    "Contingent Reasoning": AXIS_1_CONTINGENT,
    "Forward Planning": AXIS_2_FORWARD,
    "Higher-Order Beliefs": AXIS_3_BELIEFS,
    "Prospect Theory": PROSPECT_THEORY,
    "Strategy Revelation": STRATEGY_REVEAL,
}

# Optimal bid functions
def optimal_fpsb(value, n_bidders=3):
    """First price: bid = (n-1)/n * value"""
    return value * (n_bidders - 1) / n_bidders

def optimal_tpsb(value, n_bidders=3):
    """Third price: bid above value. Approximate as 2*value for 3 bidders."""
    # This is a simplification - actual equilibrium is more complex
    return value * 2

def optimal_spsb(value):
    """Second price: bid = value"""
    return value


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


def plot_bid_vs_value(ax, df: pd.DataFrame, auction_type: str, title: str, color: str):
    """Plot bid vs value scatter with optimal line."""
    if df.empty:
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes, fontsize=12)
        ax.set_title(title, fontsize=10, fontweight='bold')
        return

    values = df['player_value'].values
    bids = df['bid'].values

    # Scatter plot
    ax.scatter(values, bids, alpha=0.3, s=15, c=color, edgecolors='none')

    # Optimal line
    x_line = np.linspace(0, max(values.max(), 25), 100)
    if auction_type == 'fpsb':
        y_optimal = optimal_fpsb(x_line)
        opt_label = 'Optimal (2/3·v)'
    elif auction_type == 'tpsb':
        y_optimal = optimal_tpsb(x_line)
        opt_label = 'Optimal (2·v)'
    else:  # spsb
        y_optimal = optimal_spsb(x_line)
        opt_label = 'Optimal (v)'

    ax.plot(x_line, y_optimal, 'g--', linewidth=2, alpha=0.8, label=opt_label)

    # Identity line (bid = value)
    ax.plot(x_line, x_line, 'k:', linewidth=1, alpha=0.5, label='bid = value')

    # Mean bid line
    mean_ratio = bids.mean() / values.mean() if values.mean() > 0 else 0
    y_mean = x_line * mean_ratio
    ax.plot(x_line, y_mean, 'r-', linewidth=1.5, alpha=0.7, label=f'Mean ({mean_ratio:.2f}·v)')

    # Labels
    ax.set_xlabel('Value', fontsize=9)
    ax.set_ylabel('Bid', fontsize=9)
    ax.set_title(title, fontsize=10, fontweight='bold')

    # Limits
    max_val = max(values.max(), bids.max(), 25)
    ax.set_xlim(0, max_val * 1.05)
    ax.set_ylim(0, max_val * 1.5 if auction_type == 'tpsb' else max_val * 1.05)

    ax.grid(True, alpha=0.2)

    # Stats box
    n = len(df)
    mean_bid = bids.mean()
    mean_val = values.mean()
    stats_text = f'N={n}\nμ(b/v)={mean_ratio:.2f}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=8,
            verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3',
            facecolor='white', alpha=0.8))


def plot_axis_comparison(axis_name: str, interventions: Dict, output_path: Path):
    """Create bid vs value plots for all interventions in an axis, FPSB vs TPSB side by side."""

    n_interventions = len(interventions)
    fig, axes = plt.subplots(n_interventions, 2, figsize=(12, 3 * n_interventions))

    if n_interventions == 1:
        axes = axes.reshape(1, -1)

    colors = {'fpsb': '#1f77b4', 'tpsb': '#d62728'}

    for idx, (name, (spsb_exp, fpsb_exp, tpsb_exp)) in enumerate(interventions.items()):
        # Load data
        df_fpsb = load_experiment_data(fpsb_exp)
        df_tpsb = load_experiment_data(tpsb_exp)

        # Plot FPSB
        plot_bid_vs_value(axes[idx, 0], df_fpsb, 'fpsb', f'{name} - FPSB', colors['fpsb'])

        # Plot TPSB
        plot_bid_vs_value(axes[idx, 1], df_tpsb, 'tpsb', f'{name} - TPSB', colors['tpsb'])

    # Add column headers
    axes[0, 0].text(0.5, 1.15, 'First-Price Sealed Bid', transform=axes[0, 0].transAxes,
                    fontsize=12, fontweight='bold', ha='center')
    axes[0, 1].text(0.5, 1.15, 'Third-Price Sealed Bid', transform=axes[0, 1].transAxes,
                    fontsize=12, fontweight='bold', ha='center')

    # Overall title
    fig.suptitle(f'{axis_name}: Bid vs Value Comparison', fontsize=14, fontweight='bold', y=1.02)

    # Legend
    legend_elements = [
        Line2D([0], [0], color='g', linestyle='--', linewidth=2, label='Optimal'),
        Line2D([0], [0], color='k', linestyle=':', linewidth=1, label='bid = value'),
        Line2D([0], [0], color='r', linestyle='-', linewidth=1.5, label='Mean'),
    ]
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.99, 0.99), fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.98])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"  ✓ Saved: {output_path}")

    plt.close()


def plot_master_comparison(output_path: Path):
    """Create a master plot with all interventions, grouped by axis."""

    # Collect all interventions in order
    all_interventions = []
    for axis_name, interventions in ALL_AXES.items():
        for name, exp_names in interventions.items():
            all_interventions.append((axis_name, name, exp_names))

    n_total = len(all_interventions)
    fig, axes = plt.subplots(n_total, 2, figsize=(14, 2.2 * n_total))

    colors = {'fpsb': '#1f77b4', 'tpsb': '#d62728'}

    current_axis = None
    for idx, (axis_name, name, (spsb_exp, fpsb_exp, tpsb_exp)) in enumerate(all_interventions):
        # Load data
        df_fpsb = load_experiment_data(fpsb_exp)
        df_tpsb = load_experiment_data(tpsb_exp)

        # Add axis separator
        if axis_name != current_axis:
            current_axis = axis_name
            # Add axis label on left
            axes[idx, 0].text(-0.15, 0.5, axis_name, transform=axes[idx, 0].transAxes,
                             fontsize=10, fontweight='bold', ha='right', va='center',
                             rotation=90)

        # Plot FPSB
        plot_bid_vs_value(axes[idx, 0], df_fpsb, 'fpsb', f'{name}', colors['fpsb'])

        # Plot TPSB
        plot_bid_vs_value(axes[idx, 1], df_tpsb, 'tpsb', f'{name}', colors['tpsb'])

    # Column headers
    fig.text(0.3, 0.995, 'First-Price Sealed Bid (optimal: 2/3·v)', fontsize=12, fontweight='bold', ha='center')
    fig.text(0.75, 0.995, 'Third-Price Sealed Bid (optimal: 2·v)', fontsize=12, fontweight='bold', ha='center')

    # Overall title
    fig.suptitle('V12 Behavioral Interventions: Bid vs Value\nFPSB vs TPSB Comparison',
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout(rect=[0.05, 0, 1, 0.99])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"✓ Saved master plot: {output_path}")

    plt.close()


def create_summary_stats(output_path: Path):
    """Create summary statistics CSV."""
    rows = []

    for axis_name, interventions in ALL_AXES.items():
        for name, (spsb_exp, fpsb_exp, tpsb_exp) in interventions.items():
            for auction_type, exp_name in [('FPSB', fpsb_exp), ('TPSB', tpsb_exp)]:
                df = load_experiment_data(exp_name)
                if not df.empty:
                    values = df['player_value'].values
                    bids = df['bid'].values
                    bid_ratio = bids / values
                    bid_ratio = bid_ratio[np.isfinite(bid_ratio)]

                    # Calculate optimal ratio
                    if auction_type == 'FPSB':
                        optimal_ratio = 2/3
                    else:
                        optimal_ratio = 2.0

                    rows.append({
                        'Axis': axis_name,
                        'Intervention': name,
                        'Auction': auction_type,
                        'N': len(df),
                        'Mean_Bid_Ratio': bid_ratio.mean(),
                        'Std_Bid_Ratio': bid_ratio.std(),
                        'Optimal_Ratio': optimal_ratio,
                        'Distance_from_Optimal': abs(bid_ratio.mean() - optimal_ratio),
                    })

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_path, index=False)
    print(f"✓ Saved summary: {output_path}")
    return summary_df


def main():
    """Main execution."""
    print("="*70)
    print("V12 BID VS VALUE PLOTS - FPSB vs TPSB")
    print("="*70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate per-axis plots
    print("\n📊 Generating per-axis plots...")
    axis_files = {
        "Contingent Reasoning": "axis1_contingent_bid_vs_value.png",
        "Forward Planning": "axis2_forward_bid_vs_value.png",
        "Higher-Order Beliefs": "axis3_beliefs_bid_vs_value.png",
        "Prospect Theory": "prospect_theory_bid_vs_value.png",
        "Strategy Revelation": "strategy_reveal_bid_vs_value.png",
    }

    for axis_name, interventions in ALL_AXES.items():
        print(f"\n  {axis_name}...")
        output_file = axis_files.get(axis_name)
        if output_file:
            plot_axis_comparison(axis_name, interventions, OUTPUT_DIR / output_file)

    # Generate master plot
    print("\n📊 Generating master comparison plot...")
    plot_master_comparison(OUTPUT_DIR / "v12_master_bid_vs_value.png")

    # Generate summary stats
    print("\n📋 Generating summary statistics...")
    summary_df = create_summary_stats(OUTPUT_DIR / "bid_vs_value_summary.csv")

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY: Mean Bid/Value Ratios")
    print("="*70)
    print(f"\n{'Intervention':<25} {'FPSB (opt=0.67)':<18} {'TPSB (opt=2.0)':<18}")
    print("-"*60)

    for axis_name, interventions in ALL_AXES.items():
        print(f"\n{axis_name}:")
        for name in interventions.keys():
            fpsb_row = summary_df[(summary_df['Intervention'] == name) & (summary_df['Auction'] == 'FPSB')]
            tpsb_row = summary_df[(summary_df['Intervention'] == name) & (summary_df['Auction'] == 'TPSB')]

            fpsb_val = f"{fpsb_row['Mean_Bid_Ratio'].values[0]:.3f}" if len(fpsb_row) > 0 else "N/A"
            tpsb_val = f"{tpsb_row['Mean_Bid_Ratio'].values[0]:.3f}" if len(tpsb_row) > 0 else "N/A"

            print(f"  {name:<23} {fpsb_val:<18} {tpsb_val:<18}")

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()

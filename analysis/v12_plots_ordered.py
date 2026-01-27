"""
Generate ordered vertical comparison plots for V12 Behavioral Interventions.

Orders interventions within each axis by effectiveness (closeness to optimal bid_ratio = 1.0).
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D


# Paths
EXPERIMENT_DIR = Path("experiment_logs/V12")
OUTPUT_DIR = Path("results/v12_interventions")

# Single unified baseline - standard SPSB with no modifications
# (axis1_contingent_baseline and loss_aversion_baseline are identical)
BASELINE_EXPERIMENT = "axis1_contingent_baseline"
BASELINE_LABEL = "SPSB Baseline"

# Define intervention groups with short 2-3 word labels
# Former "baselines" that were actually different prompts are now interventions
AXIS_1_INTERVENTIONS = {
    "List Cases": "axis1_contingent_enumerate",        # Enumerate all opponent scenarios
    "Dominated Bid": "axis1_contingent_dominated",     # Point out dominated strategies
    "Worst Case": "axis1_contingent_worstcase",        # Focus on worst-case outcome
}

AXIS_2_INTERVENTIONS = {
    "Two-Stage OSP": "axis2_forward_baseline",         # Was "baseline" - actually OSP mechanism
    "Backward Induct": "axis2_forward_backward_induct", # Explicit backward induction
    "One-Step Look": "axis2_forward_onestep",          # Look one step ahead only
    "Decision Tree": "axis2_forward_tree",             # Full decision tree visualization
}

AXIS_3_INTERVENTIONS = {
    "Rational Others": "axis3_beliefs_baseline",       # Was "baseline" - states others are rational
    "First-Order": "axis3_beliefs_firstorder",         # What others will do
    "Second-Order": "axis3_beliefs_secondorder",       # What others think you'll do
    "Common Know": "axis3_beliefs_common_knowledge",   # Common knowledge of rationality
}

LOSS_AVERSION_INTERVENTIONS = {
    "Gain Frame": "loss_aversion_gain_frame",          # Frame as potential gain
    "Loss Frame": "loss_aversion_loss_frame",          # Frame as potential loss
    "Mixed Frame": "loss_aversion_mixed_frame",        # Both gain and loss
    "Endowment": "loss_aversion_endowment",            # You already own it
    "WTA vs WTP": "loss_aversion_WTA_WTP",             # Willingness to accept/pay
}

ALL_GROUPS = {
    "Contingent Reasoning": AXIS_1_INTERVENTIONS,
    "Forward Planning": AXIS_2_INTERVENTIONS,
    "Higher-Order Beliefs": AXIS_3_INTERVENTIONS,
    "Loss Aversion": LOSS_AVERSION_INTERVENTIONS,
}

# Theoretical predictions for annotations
AXIS_DESCRIPTIONS = {
    "Contingent Reasoning": "Case-by-case reasoning about others' moves",
    "Forward Planning": "Backward induction through decision nodes",
    "Higher-Order Beliefs": "Reasoning about what others believe",
    "Loss Aversion": "Reference-dependent preferences (Prospect Theory)",
}


def load_experiment_data(exp_dir: Path, exp_name: str) -> pd.DataFrame:
    """Load experiment data from all runs."""
    dfs = []
    exp_path = exp_dir / exp_name

    if not exp_path.exists():
        return pd.DataFrame()

    for csv_file in exp_path.rglob("*_results.csv"):
        if "merged" not in csv_file.name:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception:
                pass

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate bid shading metrics."""
    df = df.copy()
    df['player_value'] = pd.to_numeric(df['player_value'], errors='coerce')
    df['bid'] = pd.to_numeric(df['bid'], errors='coerce')
    df = df.dropna(subset=['player_value', 'bid'])
    df = df[df['player_value'] > 0]

    df['bid_ratio'] = df['bid'] / df['player_value']
    df['bid_shading'] = (df['player_value'] - df['bid']) / df['player_value']

    return df


def load_all_interventions() -> Tuple[pd.DataFrame, Dict[str, Dict[str, pd.DataFrame]]]:
    """Load unified baseline and all intervention data grouped by axis.

    Returns:
        baseline_df: DataFrame with unified SPSB baseline data
        all_data: Dict of axis_name -> {intervention_name: DataFrame}
    """
    # Load unified baseline
    baseline_df = load_experiment_data(EXPERIMENT_DIR, BASELINE_EXPERIMENT)
    if not baseline_df.empty:
        baseline_df = calculate_metrics(baseline_df)
        baseline_df['intervention'] = BASELINE_LABEL
    print(f"  Loaded baseline: {len(baseline_df)} observations")

    # Load all interventions
    all_data = {}
    for group_name, interventions in ALL_GROUPS.items():
        group_data = {}
        for display_name, exp_name in interventions.items():
            df = load_experiment_data(EXPERIMENT_DIR, exp_name)
            if not df.empty:
                df = calculate_metrics(df)
                df['intervention'] = display_name
                group_data[display_name] = df
        all_data[group_name] = group_data
        print(f"  Loaded {group_name}: {len(group_data)} interventions")

    return baseline_df, all_data


def order_by_effectiveness(group_data: Dict[str, pd.DataFrame], baseline_first: bool = True) -> List[Tuple[str, pd.DataFrame, float, bool]]:
    """
    Order interventions by effectiveness (closeness to optimal bid_ratio = 1.0).
    Returns list of (name, df, mean_ratio, is_baseline) tuples.

    If baseline_first=True, puts baseline at top, then other interventions ordered by effectiveness.
    """
    effectiveness = []
    baseline_entry = None

    for name, df in group_data.items():
        if len(df) > 0:
            mean_ratio = df['bid_ratio'].mean()
            distance_from_optimal = abs(mean_ratio - 1.0)
            is_baseline = "baseline" in name.lower()
            entry = (name, df, mean_ratio, distance_from_optimal, is_baseline)

            if is_baseline and baseline_first:
                baseline_entry = entry
            else:
                effectiveness.append(entry)

    # Sort non-baseline by distance from optimal (ascending = best first)
    effectiveness.sort(key=lambda x: x[3])

    # Put baseline first if requested
    if baseline_first and baseline_entry:
        effectiveness.insert(0, baseline_entry)

    return [(name, df, mean_ratio, is_baseline) for name, df, mean_ratio, _, is_baseline in effectiveness]


def plot_axis_vertical(group_name: str,
                       group_data: Dict[str, pd.DataFrame],
                       baseline_df: pd.DataFrame,
                       output_path: Path):
    """Create vertical stacked distribution plot for one axis, ordered by effectiveness.

    Simple histogram style: bid density around value with vertical line at mean.
    Unified baseline shown at top for comparison.
    """

    if not group_data:
        print(f"  No data for {group_name}")
        return

    # Order by effectiveness (no baseline_first since we handle it separately)
    ordered_data = order_by_effectiveness(group_data, baseline_first=False)

    # Add baseline at top
    if not baseline_df.empty:
        baseline_mean = baseline_df['bid_ratio'].mean()
        ordered_data.insert(0, (BASELINE_LABEL, baseline_df, baseline_mean, True))

    n_rows = len(ordered_data)

    if n_rows == 0:
        return

    # Create figure
    fig, axes = plt.subplots(n_rows, 1, figsize=(10, 2.5 * n_rows), sharex=True)
    if n_rows == 1:
        axes = [axes]

    # Bins for bid ratio (centered around 1.0 = optimal)
    bins = np.linspace(0, 2, 21)  # Coarser bins for cleaner look

    # Color scheme: gray for baseline, then gradient from green (best) to red (worst)
    # Use explicit hex colors to avoid alpha issues
    n_interventions = n_rows - 1  # Exclude baseline from color gradient
    if n_interventions > 0:
        color_vals = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, n_interventions))
        intervention_colors = ['#%02x%02x%02x' % (int(c[0]*255), int(c[1]*255), int(c[2]*255)) for c in color_vals]
    else:
        intervention_colors = []

    baseline_color = '#888888'  # Gray for baseline
    intervention_idx = 0

    for idx, (label, df, mean_ratio, is_baseline) in enumerate(ordered_data):
        ax = axes[idx]

        data = df['bid_ratio'].values
        data = data[(data >= 0) & (data <= 2)]

        if len(data) == 0:
            continue

        # Calculate weights for percentage density
        weights = 100.0 * np.ones(len(data)) / len(data)

        # Choose color: gray for baseline, gradient for others
        if is_baseline:
            bar_color = baseline_color
        else:
            bar_color = intervention_colors[intervention_idx] if intervention_idx < len(intervention_colors) else '#888888'
            intervention_idx += 1

        # Histogram - filled with color
        ax.hist(data, bins=bins, weights=weights, alpha=0.7,
                color=bar_color, edgecolor=bar_color, linewidth=0.8)

        # Mean line (black, solid)
        ax.axvline(mean_ratio, color='black', linestyle='-', linewidth=2, alpha=0.8)

        # Optimal line (bid = value, ratio = 1.0) - gray dashed
        ax.axvline(1.0, color='gray', linestyle='--', linewidth=1, alpha=0.4)

        # Y-axis label
        ax.set_ylabel('Density (%)', fontsize=11, fontweight='bold')

        # Title on left
        if is_baseline:
            title_text = f"Baseline (No Intervention)"
        else:
            rank_label = f"#{intervention_idx}"  # Rank among interventions only
            title_text = f"{rank_label}: {label}"

        ax.text(0.02, 0.95, title_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='left',
                fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4',
                         facecolor='lightyellow' if is_baseline else 'white',
                         edgecolor='orange' if is_baseline else 'gray',
                         alpha=0.9, linewidth=1))

        # Stats box on right - simpler
        stats_text = f'μ={mean_ratio:.3f}\nσ={np.std(data):.3f}'
        ax.text(0.98, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                fontsize=9, family='monospace',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                         edgecolor='gray', alpha=0.9, linewidth=0.5))

        # Grid
        ax.grid(True, alpha=0.15, axis='y')
        ax.set_axisbelow(True)
        ax.set_xlim(0, 2)
        ax.set_ylim(0, None)

    # X-axis label on bottom
    axes[-1].set_xlabel('Bid / Value Ratio (Optimal = 1.0)', fontsize=12, fontweight='bold')

    # Overall title
    axis_desc = AXIS_DESCRIPTIONS.get(group_name, "")
    fig.suptitle(f'{group_name}\n{axis_desc}\n(Ordered by effectiveness)',
                 fontsize=13, fontweight='bold', y=1.02)

    # Legend
    legend_elements = [
        Line2D([0], [0], color='black', linewidth=2, label='Mean'),
        Line2D([0], [0], color='gray', linestyle='--', linewidth=1, alpha=0.6, label='Optimal (b=v)'),
    ]
    fig.legend(handles=legend_elements, loc='upper right',
               bbox_to_anchor=(0.98, 0.99), fontsize=10, framealpha=0.95, edgecolor='gray')

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"  ✓ Saved: {output_path}")

    plt.close()


def plot_master_comparison(all_data: Dict[str, Dict[str, pd.DataFrame]],
                           baseline_df: pd.DataFrame,
                           output_path: Path):
    """
    Create a master plot showing all axes stacked vertically,
    with interventions within each axis ordered by effectiveness.

    Simple histogram style: bid density with vertical line at mean.
    Unified baseline shown at top of each axis.
    """

    # Collect all ordered data
    all_ordered = []
    for group_name in ALL_GROUPS.keys():
        group_data = all_data.get(group_name, {})

        # Add baseline first for each axis
        if not baseline_df.empty:
            baseline_mean = baseline_df['bid_ratio'].mean()
            all_ordered.append((group_name, BASELINE_LABEL, baseline_df, baseline_mean, True))

        if group_data:
            ordered = order_by_effectiveness(group_data, baseline_first=False)
            for name, df, mean_ratio, is_baseline in ordered:
                all_ordered.append((group_name, name, df, mean_ratio, False))

    n_rows = len(all_ordered)
    if n_rows == 0:
        print("No data for master plot")
        return

    # Create figure
    fig, axes = plt.subplots(n_rows, 1, figsize=(10, 2.0 * n_rows), sharex=True)
    if n_rows == 1:
        axes = [axes]

    bins = np.linspace(0, 2, 21)  # Coarser bins for cleaner look

    # Color by axis
    axis_colors = {
        "Contingent Reasoning": '#1f77b4',      # Blue
        "Forward Planning": '#ff7f0e',           # Orange
        "Higher-Order Beliefs": '#2ca02c',       # Green
        "Loss Aversion": '#d62728',              # Red
    }

    current_axis = None
    intervention_idx_in_axis = 0

    for idx, (group_name, label, df, mean_ratio, is_baseline) in enumerate(all_ordered):
        ax = axes[idx]

        # Track axis changes
        if group_name != current_axis:
            current_axis = group_name
            intervention_idx_in_axis = 0

        data = df['bid_ratio'].values
        data = data[(data >= 0) & (data <= 2)]

        if len(data) == 0:
            continue

        weights = 100.0 * np.ones(len(data)) / len(data)

        # Gray for baseline, axis color for interventions
        base_color = axis_colors.get(group_name, 'gray')
        color = '#888888' if is_baseline else base_color

        ax.hist(data, bins=bins, weights=weights, alpha=0.7,
                color=color, edgecolor=color, linewidth=0.8)

        # Mean line (black)
        ax.axvline(mean_ratio, color='black', linestyle='-', linewidth=2, alpha=0.8)

        # Optimal line (gray dashed)
        ax.axvline(1.0, color='gray', linestyle='--', linewidth=1, alpha=0.4)

        # Labels
        ax.set_ylabel('Density (%)', fontsize=10, fontweight='bold')

        # Short axis label
        short_axis = group_name.split(':')[0].replace('Axis ', 'A') if ':' in group_name else group_name[:4]

        if is_baseline:
            title_text = f"{short_axis}: Baseline"
        else:
            intervention_idx_in_axis += 1
            title_text = f"{short_axis} #{intervention_idx_in_axis}: {label}"

        ax.text(0.02, 0.95, title_text,
                transform=ax.transAxes,
                verticalalignment='top',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4',
                         facecolor='lightyellow' if is_baseline else 'white',
                         edgecolor='orange' if is_baseline else base_color,
                         alpha=0.9, linewidth=1))

        # Stats
        stats_text = f'μ={mean_ratio:.3f}\nσ={np.std(data):.3f}'
        ax.text(0.98, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                fontsize=9, family='monospace',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                         edgecolor='gray', alpha=0.9, linewidth=0.5))

        ax.grid(True, alpha=0.15, axis='y')
        ax.set_axisbelow(True)
        ax.set_xlim(0, 2)
        ax.set_ylim(0, None)

    axes[-1].set_xlabel('Bid / Value Ratio (Optimal = 1.0)', fontsize=12, fontweight='bold')

    # Title
    fig.suptitle('V12 Behavioral Interventions: All Axes\n(Ordered by effectiveness within each axis)',
                 fontsize=14, fontweight='bold', y=1.01)

    # Legend for axes
    legend_elements = [
        Rectangle((0, 0), 1, 1, fc='#888888', alpha=0.7, label='Baseline'),
        Rectangle((0, 0), 1, 1, fc=axis_colors["Contingent Reasoning"],
                  alpha=0.7, label='Contingtic'),
        Rectangle((0, 0), 1, 1, fc=axis_colors["Forward Planning"],
                  alpha=0.7, label='Forward'),
        Rectangle((0, 0), 1, 1, fc=axis_colors["Higher-Order Beliefs"],
                  alpha=0.7, label='Beliefs'),
        Rectangle((0, 0), 1, 1, fc=axis_colors["Loss Aversion"],
                  alpha=0.7, label='Loss Aversion'),
        Line2D([0], [0], color='black', linewidth=2, label='Mean'),
    ]
    fig.legend(handles=legend_elements, loc='upper right',
               bbox_to_anchor=(0.99, 0.995), fontsize=9, framealpha=0.95, edgecolor='gray', ncol=2)

    plt.tight_layout(rect=[0, 0, 1, 0.98])

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"✓ Saved master plot: {output_path}")

    plt.close()


def create_summary_table(all_data: Dict[str, Dict[str, pd.DataFrame]],
                         baseline_df: pd.DataFrame) -> pd.DataFrame:
    """Create summary table of all interventions ordered by effectiveness."""
    rows = []

    # Add baseline info once
    if not baseline_df.empty:
        baseline_mean = baseline_df['bid_ratio'].mean()
        rows.append({
            'Axis': 'All',
            'Rank': 'Baseline',
            'Intervention': BASELINE_LABEL,
            'Is_Baseline': True,
            'N': len(baseline_df),
            'Mean_Bid_Ratio': baseline_mean,
            'Std_Bid_Ratio': baseline_df['bid_ratio'].std(),
            'Distance_from_Optimal': abs(baseline_mean - 1.0),
            'Mean_Bid_Shading': baseline_df['bid_shading'].mean(),
        })

    for group_name, group_data in all_data.items():
        ordered = order_by_effectiveness(group_data, baseline_first=False)
        intervention_rank = 0
        for name, df, mean_ratio, is_baseline in ordered:
            intervention_rank += 1
            rows.append({
                'Axis': group_name,
                'Rank': str(intervention_rank),
                'Intervention': name,
                'Is_Baseline': False,
                'N': len(df),
                'Mean_Bid_Ratio': mean_ratio,
                'Std_Bid_Ratio': df['bid_ratio'].std(),
                'Distance_from_Optimal': abs(mean_ratio - 1.0),
                'Mean_Bid_Shading': df['bid_shading'].mean(),
            })

    return pd.DataFrame(rows)


def main():
    """Main execution."""
    print("="*70)
    print("V12 BEHAVIORAL INTERVENTIONS - ORDERED PLOTS")
    print("="*70)

    # Load all data
    print("\n📊 Loading data...")
    baseline_df, all_data = load_all_interventions()

    # Create summary table
    print("\n📋 Creating summary table...")
    summary_df = create_summary_table(all_data, baseline_df)
    summary_df.to_csv(OUTPUT_DIR / "intervention_rankings.csv", index=False)
    print(f"  ✓ Saved: {OUTPUT_DIR / 'intervention_rankings.csv'}")

    # Print summary
    print("\n" + "="*70)
    print("INTERVENTION RANKINGS (Unified baseline, then by effectiveness)")
    print("="*70)

    # Print baseline first
    baseline_row = summary_df[summary_df['Is_Baseline'] == True].iloc[0]
    print(f"\n[BASELINE]: {baseline_row['Intervention']:20s} ratio={baseline_row['Mean_Bid_Ratio']:.3f} (|μ-1|={baseline_row['Distance_from_Optimal']:.3f})")

    for group_name in ALL_GROUPS.keys():
        group_summary = summary_df[summary_df['Axis'] == group_name]
        print(f"\n{group_name}:")
        print("-" * 50)
        for _, row in group_summary.iterrows():
            print(f"  #{row['Rank']}: {row['Intervention']:20s} ratio={row['Mean_Bid_Ratio']:.3f} (|μ-1|={row['Distance_from_Optimal']:.3f})")

    # Generate individual axis plots
    print("\n" + "="*70)
    print("GENERATING ORDERED PLOTS")
    print("="*70)

    axis_files = {
        "Contingent Reasoning": "axis_1_ordered.png",
        "Forward Planning": "axis_2_ordered.png",
        "Higher-Order Beliefs": "axis_3_ordered.png",
        "Loss Aversion": "loss_aversion_ordered.png",
    }

    for group_name, group_data in all_data.items():
        print(f"\n📊 Plotting {group_name}...")
        output_file = axis_files.get(group_name)
        if output_file:
            plot_axis_vertical(group_name, group_data, baseline_df, OUTPUT_DIR / output_file)

    # Generate master comparison plot
    print(f"\n📊 Generating master comparison plot...")
    plot_master_comparison(all_data, baseline_df, OUTPUT_DIR / "v12_master_ordered.png")

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()

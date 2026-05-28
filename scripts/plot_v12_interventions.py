"""
Generate vertical distribution plots for V12 behavioral intervention experiments.

Compares baseline vs treatments within each axis:
- Axis 1: Contingent Reasoning
- Axis 2: Forward Planning
- Axis 3: Higher-Order Beliefs
- Loss Aversion

Shows distributions of (bid - value) / value (bid shading ratio) for each experiment.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import sys


# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Paths (relative to project root)
EXPERIMENT_DIR = PROJECT_ROOT / "experiment_logs" / "V12"
OUTPUT_DIR = PROJECT_ROOT / "results" / "v12_interventions"

# V12 Intervention Experiments organized by axis
AXIS1_EXPERIMENTS = {
    "Baseline": "axis1_contingent_baseline",
    "Enumerate": "axis1_contingent_enumerate",
    "Dominated": "axis1_contingent_dominated",
    "Worst Case": "axis1_contingent_worstcase",
}

AXIS2_EXPERIMENTS = {
    "Baseline": "axis2_forward_baseline",
    "Backward Induct": "axis2_forward_backward_induct",
    "One Step": "axis2_forward_onestep",
    "Tree": "axis2_forward_tree",
}

AXIS3_EXPERIMENTS = {
    "Baseline": "axis3_beliefs_baseline",
    "First-Order": "axis3_beliefs_firstorder",
    "Second-Order": "axis3_beliefs_secondorder",
    "Common Knowledge": "axis3_beliefs_common_knowledge",
}

LOSS_AVERSION_EXPERIMENTS = {
    "Baseline": "loss_aversion_baseline",
    "Gain Frame": "loss_aversion_gain_frame",
    "Loss Frame": "loss_aversion_loss_frame",
    "Mixed Frame": "loss_aversion_mixed_frame",
    "Endowment": "loss_aversion_endowment",
    "WTA/WTP": "loss_aversion_WTA_WTP",
}

# Color schemes
AXIS_COLORS = {
    "Axis 1": "#4472C4",  # Blue
    "Axis 2": "#ED7D31",  # Orange
    "Axis 3": "#A5A5A5",  # Gray
    "Loss Aversion": "#70AD47",  # Green
}


def load_experiment_data(exp_dir: Path, exp_name: str) -> pd.DataFrame:
    """Load experiment data from merged file or individual runs."""
    # Try merged file first
    merged_file = exp_dir / exp_name / f"{exp_name}_merged_results.csv"
    if merged_file.exists():
        print(f"    Loading merged file: {merged_file.name}")
        return pd.read_csv(merged_file)

    # Try looking for run directories
    exp_path = exp_dir / exp_name
    if not exp_path.exists():
        print(f"    ⚠️  Directory not found: {exp_path}")
        return pd.DataFrame()

    # Collect all CSV files from run directories
    dfs = []
    run_dirs = sorted([d for d in exp_path.iterdir() if d.is_dir() and d.name.startswith("run_")])

    for run_dir in run_dirs:
        # Look for results CSV files in results/ subdirectory
        results_dir = run_dir / "results"
        if results_dir.exists():
            for csv_file in results_dir.glob("*_results.csv"):
                if "merged" not in csv_file.name:
                    dfs.append(pd.read_csv(csv_file))

        # Also check in run directory root (backward compatibility)
        for csv_file in run_dir.glob("*_results.csv"):
            if "merged" not in csv_file.name and csv_file.parent == run_dir:
                dfs.append(pd.read_csv(csv_file))

    if dfs:
        print(f"    Loaded {len(dfs)} result files from {len(run_dirs)} runs")
        return pd.concat(dfs, ignore_index=True)
    else:
        print(f"    ⚠️  No result files found in {exp_path}")
        return pd.DataFrame()


def calculate_bid_shading(df: pd.DataFrame) -> np.ndarray:
    """
    Calculate (value - bid) / value for each agent.
    Positive values = underbidding (bid shading)
    Negative values = overbidding
    """
    shadings = []

    for _, row in df.iterrows():
        try:
            value = float(row['player_value'])
            bid = float(row['bid'])

            # Skip if value is 0 (division by zero)
            if value == 0:
                continue

            # Calculate bid shading: (value - bid) / value
            # Positive = shading (bidding below value)
            # Negative = overbidding
            shading = (value - bid) / 25
            shadings.append(shading)

        except (KeyError, ValueError, TypeError):
            continue

    return np.array(shadings)


def load_axis_data(experiments: Dict[str, str]) -> Dict[str, np.ndarray]:
    """Load data for all experiments in an axis."""
    axis_data = {}

    for display_name, exp_name in experiments.items():
        print(f"  Loading {display_name}...")
        df = load_experiment_data(EXPERIMENT_DIR, exp_name)

        if not df.empty:
            shadings = calculate_bid_shading(df)
            if len(shadings) > 0:
                axis_data[display_name] = shadings
                print(f"    ✓ {len(shadings)} bids")
            else:
                print(f"    ⚠️  No valid data")
        else:
            print(f"    ⚠️  No data found")

    return axis_data


def plot_axis_comparison(axis_data: Dict[str, np.ndarray],
                         axis_name: str,
                         output_path: Path):
    """Create vertical stacked distribution plots for one axis."""

    if not axis_data:
        print(f"❌ No data to plot for {axis_name}!")
        return

    # Define row order (baseline first)
    row_order = ["Baseline"] + [k for k in axis_data.keys() if k != "Baseline"]

    # Collect data
    plot_data = []
    plot_labels = []

    for row_name in row_order:
        data = axis_data.get(row_name)
        if data is not None and len(data) > 0:
            plot_data.append(data)
            plot_labels.append(row_name)

    if not plot_data:
        print(f"❌ No valid data to plot for {axis_name}!")
        return

    # Create figure - vertical layout
    n_rows = len(plot_data)
    fig, axes = plt.subplots(n_rows, 1, figsize=(12, 2.5 * n_rows), sharex=True)

    if n_rows == 1:
        axes = [axes]

    # Define bins
    bins = np.linspace(-0.5, 0.5, 21)  # 20 bins from -50% to +50%

    # Color
    color = AXIS_COLORS.get(axis_name, "#4472C4")

    for idx, (label, data) in enumerate(zip(plot_labels, plot_data)):
        ax = axes[idx]

        # Calculate weights to get percentage density
        weights = 100.0 * np.ones(len(data)) / len(data)

        # Histogram
        ax.hist(data, bins=bins, weights=weights, alpha=0.7, color=color,
               edgecolor=color, linewidth=0.8)

        # Mean line (black)
        mean_val = np.mean(data)
        ax.axvline(mean_val, color='black', linestyle='-', linewidth=2, alpha=0.8)

        # Zero line (ideal = no shading)
        ax.axvline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.6, label='Truthful')

        # Labels
        ax.set_ylabel('Density (%)', fontsize=11, fontweight='bold')
        if idx == n_rows - 1:  # Only label x-axis on bottom plot
            ax.set_xlabel('Bid Shading: (Value - Bid) / 25', fontsize=12, fontweight='bold')

        # Title on the left side
        is_baseline = (label == "Baseline")
        title_text = f"{'★ ' if is_baseline else ''}{label}"
        ax.text(0.02, 0.95, title_text,
               transform=ax.transAxes,
               verticalalignment='top',
               horizontalalignment='left',
               fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.4',
                        facecolor='yellow' if is_baseline else 'white',
                        edgecolor='black' if is_baseline else 'gray',
                        alpha=0.9, linewidth=1.5 if is_baseline else 1))

        # Statistics box on the right
        mean_val = np.mean(data)
        median_val = np.median(data)
        std_val = np.std(data)

        # Calculate % within ±5% of truthful
        truthful_pct = 100 * np.sum(np.abs(data) <= 0.05) / len(data)

        stats_text = (f'μ={mean_val:+.3f}\n'
                     f'σ={std_val:.3f}\n'
                     f'med={median_val:+.3f}\n'
                     f'|·|≤5%: {truthful_pct:.1f}%')

        ax.text(0.98, 0.95, stats_text,
               transform=ax.transAxes,
               verticalalignment='top',
               horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                        edgecolor='gray', alpha=0.95, linewidth=0.5),
               fontsize=9, family='monospace')

        # Grid
        ax.grid(True, alpha=0.2, axis='y')
        ax.set_axisbelow(True)

        # Limits
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(0, max(70, weights.max() * 1.2))  # Adaptive y-limit

    # Overall title
    fig.suptitle(f'{axis_name}: Bid Shading Comparison',
                fontsize=16, fontweight='bold', y=0.995)

    # Legend
    from matplotlib.patches import Rectangle
    from matplotlib.lines import Line2D
    legend_elements = [
        Rectangle((0, 0), 1, 1, fc=color, ec=color,
                 alpha=0.7, linewidth=0.8, label='Distribution'),
        Line2D([0], [0], color='black', linewidth=2, label='Mean'),
        Line2D([0], [0], color='red', linewidth=1.5, linestyle='--', label='Truthful (0)'),
    ]
    fig.legend(handles=legend_elements, loc='upper right',
              bbox_to_anchor=(0.98, 0.99), framealpha=0.95,
              fontsize=10, edgecolor='gray', ncol=1)

    plt.tight_layout(rect=[0, 0, 1, 0.99])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')

    print(f"\n✓ Saved: {output_path}")
    print(f"✓ Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def print_axis_statistics(axis_data: Dict[str, np.ndarray], axis_name: str):
    """Print summary statistics for an axis."""
    print(f"\n{'='*70}")
    print(f"{axis_name} - SUMMARY STATISTICS")
    print('='*70)

    # Print baseline first
    if "Baseline" in axis_data:
        data = axis_data["Baseline"]
        print(f"\n★ Baseline:")
        print(f"  N:              {len(data):6d}")
        print(f"  Mean:           {np.mean(data):+7.4f}")
        print(f"  Std:            {np.std(data):7.4f}")
        print(f"  Median:         {np.median(data):+7.4f}")
        print(f"  Min:            {np.min(data):+7.4f}")
        print(f"  Max:            {np.max(data):+7.4f}")
        truthful_pct = 100 * np.sum(np.abs(data) <= 0.05) / len(data)
        print(f"  Truthful (±5%): {truthful_pct:6.2f}%")

    # Print treatments
    for name in sorted(axis_data.keys()):
        if name == "Baseline":
            continue

        data = axis_data[name]
        print(f"\n{name}:")
        print(f"  N:              {len(data):6d}")
        print(f"  Mean:           {np.mean(data):+7.4f}")
        print(f"  Std:            {np.std(data):7.4f}")
        print(f"  Median:         {np.median(data):+7.4f}")
        print(f"  Min:            {np.min(data):+7.4f}")
        print(f"  Max:            {np.max(data):+7.4f}")
        truthful_pct = 100 * np.sum(np.abs(data) <= 0.05) / len(data)
        print(f"  Truthful (±5%): {truthful_pct:6.2f}%")

        # Compare to baseline
        if "Baseline" in axis_data:
            baseline_mean = np.mean(axis_data["Baseline"])
            diff = np.mean(data) - baseline_mean
            print(f"  Δ from baseline: {diff:+.4f}")


def main():
    """Main execution."""
    print("="*70)
    print("V12 BEHAVIORAL INTERVENTIONS - DISTRIBUTION COMPARISON")
    print("="*70 + "\n")

    # Process each axis
    axes = [
        ("Axis 1", AXIS1_EXPERIMENTS),
        ("Axis 2", AXIS2_EXPERIMENTS),
        ("Axis 3", AXIS3_EXPERIMENTS),
        ("Loss Aversion", LOSS_AVERSION_EXPERIMENTS),
    ]

    for axis_name, experiments in axes:
        print(f"\n{'='*70}")
        print(f"📊 Processing {axis_name}: {len(experiments)} experiments")
        print('='*70)

        # Load data
        axis_data = load_axis_data(experiments)

        if not axis_data:
            print(f"⚠️  No data found for {axis_name}, skipping...")
            continue

        # Print statistics
        print_axis_statistics(axis_data, axis_name)

        # Generate plot
        print(f"\n📊 Generating plot for {axis_name}...")
        output_filename = axis_name.lower().replace(" ", "_") + "_comparison.png"
        output_path = OUTPUT_DIR / output_filename
        plot_axis_comparison(axis_data, axis_name, output_path)

    print("\n" + "="*70)
    print("✓ COMPLETE!")
    print(f"✓ All plots saved to: {OUTPUT_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()

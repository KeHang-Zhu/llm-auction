"""
Generate summary comparison plot showing baseline vs best treatment for each axis.

Creates a single figure with all 4 axes (Axis 1, 2, 3, and Loss Aversion),
comparing baseline performance to the best-performing treatment.
"""

from pathlib import Path
from typing import Dict, List, Tuple
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

# V12 Experiments - organize by axis
ALL_EXPERIMENTS = {
    "Axis 1: Contingent Reasoning": {
        "Baseline": "axis1_contingent_baseline",
        "Enumerate": "axis1_contingent_enumerate",
        "Dominated": "axis1_contingent_dominated",
        "Worst Case": "axis1_contingent_worstcase",
    },
    "Axis 2: Forward Planning": {
        "Baseline": "axis2_forward_baseline",
        "Backward Induct": "axis2_forward_backward_induct",
        "One Step": "axis2_forward_onestep",
        "Tree": "axis2_forward_tree",
    },
    "Axis 3: Higher-Order Beliefs": {
        "Baseline": "axis3_beliefs_baseline",
        "First-Order": "axis3_beliefs_firstorder",
        "Second-Order": "axis3_beliefs_secondorder",
        "Common Knowledge": "axis3_beliefs_common_knowledge",
    },
    "Loss Aversion": {
        "Baseline": "loss_aversion_baseline",
        "Gain Frame": "loss_aversion_gain_frame",
        "Loss Frame": "loss_aversion_loss_frame",
        "Mixed Frame": "loss_aversion_mixed_frame",
        "Endowment": "loss_aversion_endowment",
        "WTA/WTP": "loss_aversion_WTA_WTP",
    },
}


def load_experiment_data(exp_dir: Path, exp_name: str) -> pd.DataFrame:
    """Load experiment data from merged file or individual runs."""
    merged_file = exp_dir / exp_name / f"{exp_name}_merged_results.csv"
    if merged_file.exists():
        return pd.read_csv(merged_file)

    exp_path = exp_dir / exp_name
    if not exp_path.exists():
        return pd.DataFrame()

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

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def calculate_bid_shading(df: pd.DataFrame) -> np.ndarray:
    """Calculate (value - bid) / value for each agent."""
    shadings = []

    for _, row in df.iterrows():
        try:
            value = float(row['player_value'])
            bid = float(row['bid'])

            if value == 0:
                continue

            shading = (value - bid) / 25
            shadings.append(shading)

        except (KeyError, ValueError, TypeError):
            continue

    return np.array(shadings)


def load_axis_data(experiments: Dict[str, str]) -> Dict[str, np.ndarray]:
    """Load data for all experiments in an axis."""
    axis_data = {}

    for display_name, exp_name in experiments.items():
        df = load_experiment_data(EXPERIMENT_DIR, exp_name)

        if not df.empty:
            shadings = calculate_bid_shading(df)
            if len(shadings) > 0:
                axis_data[display_name] = shadings

    return axis_data


def find_best_treatment(axis_data: Dict[str, np.ndarray]) -> Tuple[str, np.ndarray]:
    """
    Find the treatment with mean closest to 0 (most truthful).
    Excludes baseline from consideration.
    """
    best_name = None
    best_data = None
    best_distance = float('inf')

    for name, data in axis_data.items():
        if name == "Baseline":
            continue

        mean_val = np.mean(data)
        distance = abs(mean_val)

        if distance < best_distance:
            best_distance = distance
            best_name = name
            best_data = data

    return best_name, best_data


def plot_summary_comparison(all_data: Dict[str, Dict[str, np.ndarray]], output_path: Path):
    """Create summary plot comparing baseline vs best treatment for each axis."""

    # Create 2x2 grid
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # Define bins
    bins = np.linspace(-0.5, 0.5, 21)

    # Colors
    baseline_color = "#4472C4"  # Blue
    treatment_color = "#ED7D31"  # Orange

    axis_names = list(all_data.keys())

    for idx, axis_name in enumerate(axis_names):
        ax = axes[idx]
        axis_data = all_data[axis_name]

        if not axis_data or "Baseline" not in axis_data:
            ax.text(0.5, 0.5, f"No data for\n{axis_name}",
                   transform=ax.transAxes, ha='center', va='center',
                   fontsize=14, color='gray')
            ax.set_xlim(-0.5, 0.5)
            ax.set_ylim(0, 70)
            continue

        # Get baseline
        baseline_data = axis_data["Baseline"]

        # Find best treatment
        best_name, best_data = find_best_treatment(axis_data)

        if best_data is None:
            # Only baseline exists
            weights_baseline = 100.0 * np.ones(len(baseline_data)) / len(baseline_data)
            ax.hist(baseline_data, bins=bins, weights=weights_baseline,
                   alpha=0.7, color=baseline_color, edgecolor=baseline_color,
                   linewidth=0.8, label='Baseline')

            mean_baseline = np.mean(baseline_data)
            ax.axvline(mean_baseline, color=baseline_color, linestyle='-',
                      linewidth=2, alpha=0.8)

        else:
            # Plot both baseline and best treatment
            weights_baseline = 100.0 * np.ones(len(baseline_data)) / len(baseline_data)
            weights_best = 100.0 * np.ones(len(best_data)) / len(best_data)

            # Baseline (filled)
            ax.hist(baseline_data, bins=bins, weights=weights_baseline,
                   alpha=0.5, color=baseline_color, edgecolor=baseline_color,
                   linewidth=1.2, label='Baseline')

            # Best treatment (filled with different color)
            ax.hist(best_data, bins=bins, weights=weights_best,
                   alpha=0.5, color=treatment_color, edgecolor=treatment_color,
                   linewidth=1.2, label=best_name)

            # Mean lines
            mean_baseline = np.mean(baseline_data)
            mean_best = np.mean(best_data)

            ax.axvline(mean_baseline, color=baseline_color, linestyle='-',
                      linewidth=2.5, alpha=0.8)
            ax.axvline(mean_best, color=treatment_color, linestyle='-',
                      linewidth=2.5, alpha=0.8)

        # Zero line (truthful bidding)
        ax.axvline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.6)

        # Labels
        ax.set_xlabel('Bid Shading: (Value - Bid) / 25', fontsize=11, fontweight='bold')
        ax.set_ylabel('Density (%)', fontsize=11, fontweight='bold')

        # Title
        ax.set_title(axis_name, fontsize=13, fontweight='bold', pad=10)

        # Statistics box
        if best_data is not None:
            mean_baseline = np.mean(baseline_data)
            mean_best = np.mean(best_data)
            improvement = mean_baseline - mean_best  # Positive = treatment improved

            stats_text = (
                f'Baseline:  μ={mean_baseline:+.3f}\n'
                f'{best_name}: μ={mean_best:+.3f}\n'
                f'Δ: {improvement:+.3f}'
            )
        else:
            mean_baseline = np.mean(baseline_data)
            stats_text = f'Baseline: μ={mean_baseline:+.3f}'

        ax.text(0.98, 0.97, stats_text,
               transform=ax.transAxes,
               verticalalignment='top',
               horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.6', facecolor='white',
                        edgecolor='gray', alpha=0.95, linewidth=1),
               fontsize=9, family='monospace')

        # Grid
        ax.grid(True, alpha=0.2, axis='y')
        ax.set_axisbelow(True)

        # Limits
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(0, 70)

        # Legend
        ax.legend(loc='upper left', fontsize=9, framealpha=0.95)

    # Overall title
    fig.suptitle('V12 Interventions: Summary Comparison (Baseline vs Best Treatment)',
                fontsize=18, fontweight='bold', y=0.995)

    plt.tight_layout(rect=[0, 0, 1, 0.99])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')

    print(f"\n✓ Saved: {output_path}")
    print(f"✓ Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def print_summary_statistics(all_data: Dict[str, Dict[str, np.ndarray]]):
    """Print comprehensive summary statistics."""
    print("\n" + "="*80)
    print("V12 INTERVENTIONS - SUMMARY STATISTICS")
    print("="*80)

    for axis_name, axis_data in all_data.items():
        print(f"\n{'='*80}")
        print(f"{axis_name}")
        print('='*80)

        if not axis_data or "Baseline" not in axis_data:
            print("  ⚠️  No data available")
            continue

        # Baseline
        baseline_data = axis_data["Baseline"]
        baseline_mean = np.mean(baseline_data)
        baseline_truthful = 100 * np.sum(np.abs(baseline_data) <= 0.05) / len(baseline_data)

        print(f"\n  Baseline:")
        print(f"    N:              {len(baseline_data):6d}")
        print(f"    Mean:           {baseline_mean:+7.4f}")
        print(f"    Std:            {np.std(baseline_data):7.4f}")
        print(f"    Truthful (±5%): {baseline_truthful:6.2f}%")

        # Find and report best treatment
        best_name, best_data = find_best_treatment(axis_data)

        if best_data is not None:
            best_mean = np.mean(best_data)
            best_truthful = 100 * np.sum(np.abs(best_data) <= 0.05) / len(best_data)
            improvement = baseline_mean - best_mean

            print(f"\n  ★ Best Treatment: {best_name}")
            print(f"    N:              {len(best_data):6d}")
            print(f"    Mean:           {best_mean:+7.4f}")
            print(f"    Std:            {np.std(best_data):7.4f}")
            print(f"    Truthful (±5%): {best_truthful:6.2f}%")
            print(f"    Improvement:    {improvement:+7.4f}")
            print(f"    Truthful Δ:     {best_truthful - baseline_truthful:+6.2f}%")

        # Report all treatments
        print(f"\n  All Treatments (sorted by mean):")
        treatments = [(name, data) for name, data in axis_data.items() if name != "Baseline"]
        treatments.sort(key=lambda x: abs(np.mean(x[1])))

        for name, data in treatments:
            mean_val = np.mean(data)
            improvement = baseline_mean - mean_val
            print(f"    {name:20s}: μ={mean_val:+.4f}  Δ={improvement:+.4f}")


def main():
    """Main execution."""
    print("="*80)
    print("V12 BEHAVIORAL INTERVENTIONS - SUMMARY ANALYSIS")
    print("="*80 + "\n")

    # Load all data
    all_data = {}

    for axis_name, experiments in ALL_EXPERIMENTS.items():
        print(f"📊 Loading {axis_name}...")
        axis_data = load_axis_data(experiments)

        if axis_data:
            all_data[axis_name] = axis_data
            print(f"  ✓ Loaded {len(axis_data)} experiments")
        else:
            print(f"  ⚠️  No data found")

    if not all_data:
        print("\n❌ No data available for any axis!")
        return

    # Print statistics
    print_summary_statistics(all_data)

    # Generate summary plot
    print("\n" + "="*80)
    print("📊 Generating summary comparison plot...")
    output_path = OUTPUT_DIR / "v12_summary_comparison.png"
    plot_summary_comparison(all_data, output_path)

    print("\n" + "="*80)
    print("✓ COMPLETE!")
    print(f"✓ Results saved to: {OUTPUT_DIR}")
    print("="*80)


if __name__ == "__main__":
    main()

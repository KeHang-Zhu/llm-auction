"""
Publication-ready plots for LLM DA (Deferred Acceptance) intervention experiments.
Metric: Kendall tau distance (count of discordant pairs from truthful ranking)

Each intervention plot shows:
- Rows: One per model
- Columns: One per intervention
- Gray histogram: direct_baseline distribution
- Colored histogram: Intervention distribution
- Vertical lines at means
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# ============================================================================
# STYLE CONFIGURATION (same as auctions)
# ============================================================================

plt.style.use('seaborn-v0_8-whitegrid')

plt.rcParams.update({
    'figure.facecolor': 'white',
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.15,

    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,

    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'axes.edgecolor': '#555555',
    'axes.labelcolor': '#333333',

    'grid.alpha': 0.4,
    'grid.linewidth': 0.5,
    'axes.grid': True,
    'axes.axisbelow': True,
})

OUTPUT_DIR = Path(__file__).parent / 'da'

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

MODEL_NAMES = {
    'claude': 'Claude 3.5 Haiku',
    'gemini': 'Gemini 2.0 Flash',
    'gpt4o': 'GPT-4o',
    'gemma': 'Gemma 3 27B',
    'others': 'GPT-4o',  # others folder contains mislabeled GPT-4o data
}

MODEL_COLORS = {
    'Claude 3.5 Haiku': '#4363d8',    # Blue
    'Gemini 2.0 Flash': '#e6194B',    # Red
    'GPT-4o': '#f58231',              # Orange
    'Gemma 3 27B': '#3cb44b',         # Green
}

# Darker versions for outlines
MODEL_COLORS_DARK = {
    'Claude 3.5 Haiku': '#2a3d8a',    # Darker blue
    'Gemini 2.0 Flash': '#a11232',    # Darker red
    'GPT-4o': '#c46820',              # Darker orange
    'Gemma 3 27B': '#297a33',         # Darker green
}

# Order by baseline error severity (best to worst)
MODEL_ORDER = ['Claude 3.5 Haiku', 'Gemini 2.0 Flash', 'GPT-4o', 'Gemma 3 27B']

BASELINE_COLOR = '#888888'  # Gray for direct_baseline

# ============================================================================
# KENDALL TAU COMPUTATION
# ============================================================================

def get_true_ranking(values):
    """
    Convert values dict to true ranking (sorted by value, descending).

    Args:
        values: dict of {school: value}

    Returns:
        list of schools in true preference order (best first)
    """
    return sorted(values.keys(), key=lambda x: values[x], reverse=True)


def kendall_tau_distance(true_ranking, submitted_ranking):
    """
    Count discordant pairs between two rankings.

    Args:
        true_ranking: list of items in true preference order (best first)
        submitted_ranking: list of items in submitted order

    Returns:
        tuple: (discordant_count, n_pairs)
    """
    # Only compare items that appear in both
    common = set(true_ranking) & set(submitted_ranking)
    n = len(common)

    if n < 2:
        return 0, 0  # No pairs to compare

    # Get positions in each ranking (only for common items)
    true_pos = {item: i for i, item in enumerate(true_ranking) if item in common}
    sub_pos = {item: i for i, item in enumerate(submitted_ranking) if item in common}

    # Count discordant pairs
    items = list(common)
    discordant = 0
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            a, b = items[i], items[j]
            # Check if relative order differs
            true_order = true_pos[a] < true_pos[b]
            sub_order = sub_pos[a] < sub_pos[b]
            if true_order != sub_order:
                discordant += 1

    n_pairs = n * (n - 1) // 2
    return discordant, n_pairs


def normalized_kendall_tau(true_ranking, submitted_ranking):
    """
    Compute normalized Kendall tau (fraction of pairs that are discordant).

    Returns:
        float: 0.0 = identical rankings, 1.0 = completely reversed
    """
    discordant, n_pairs = kendall_tau_distance(true_ranking, submitted_ranking)
    if n_pairs == 0:
        return 0.0
    return discordant / n_pairs


# ============================================================================
# DATA LOADING
# ============================================================================

def load_da_data():
    """
    Load all DA experiment results from JSON files.

    Returns:
        DataFrame with columns: model, experiment, student, kendall_tau,
                               kendall_tau_normalized, n_pairs, is_truthful,
                               mechanism_type
    """
    da_dir = Path(__file__).parent.parent / 'experiment_logs' / 'da'

    rows = []

    for model_dir in da_dir.iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name
        if model_name not in MODEL_NAMES:
            continue

        model_short = MODEL_NAMES[model_name]

        for exp_dir in model_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            exp_name = exp_dir.name
            raw_data_dir = exp_dir / 'raw_data'

            if not raw_data_dir.exists():
                continue

            for json_file in raw_data_dir.glob('*.json'):
                try:
                    with open(json_file) as f:
                        data = json.load(f)

                    mechanism_type = data.get('mechanism_type', 'direct')
                    values = data.get('values', {})
                    truthfulness = data.get('truthfulness', {})

                    # Get submitted rankings based on mechanism type
                    if mechanism_type == 'osp':
                        rankings = data.get('osp_choices', {})
                    else:
                        rankings = data.get('rankings', {})

                    # Process each student
                    for student, student_values in values.items():
                        true_ranking = get_true_ranking(student_values)
                        submitted = rankings.get(student, [])

                        if not submitted:
                            continue

                        # For OSP, truncate true ranking to revealed length
                        if mechanism_type == 'osp':
                            # Get the subset of true ranking for revealed items
                            revealed_items = set(submitted)
                            true_ranking_truncated = [s for s in true_ranking if s in revealed_items]
                        else:
                            true_ranking_truncated = true_ranking

                        discordant, n_pairs = kendall_tau_distance(true_ranking_truncated, submitted)
                        normalized = discordant / n_pairs if n_pairs > 0 else 0.0

                        rows.append({
                            'model': model_name,
                            'model_short': model_short,
                            'experiment': exp_name,
                            'student': student,
                            'kendall_tau': discordant,
                            'kendall_tau_normalized': normalized,
                            'n_pairs': n_pairs,
                            'is_truthful': truthfulness.get(student, None),
                            'mechanism_type': mechanism_type,
                            'revealed_length': len(submitted)
                        })

                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
                    continue

    df = pd.DataFrame(rows)
    return df


def get_reference_data(df):
    """Get direct_baseline data for reference distributions."""
    refs = {}

    baseline_data = df[df['experiment'] == 'direct_baseline']
    if not baseline_data.empty:
        refs['baseline'] = baseline_data
        refs['baseline_by_model'] = {
            model: baseline_data[baseline_data['model_short'] == model]['kendall_tau_normalized'].values
            for model in MODEL_ORDER if model in baseline_data['model_short'].values
        }

    return refs


# ============================================================================
# HISTOGRAM DISTRIBUTION PLOTS
# ============================================================================

def plot_intervention_histograms(df, experiments, title, filename, xlabel_map, refs):
    """
    Create a grid of histograms showing Kendall tau distributions.

    Layout:
    - Rows: Models
    - Columns: Interventions
    - Each cell: direct_baseline (gray) vs Intervention (colored)
    """
    models = [m for m in MODEL_ORDER if m in df['model_short'].unique()]
    exps = [e for e in experiments if e in df['experiment'].unique()]

    if not models or not exps:
        print(f"Skipping {filename}: no data for models={models}, exps={exps}")
        return

    n_models = len(models)
    n_exps = len(exps)

    fig, axes = plt.subplots(n_models, n_exps, figsize=(3.0 * n_exps, 2.6 * n_models),
                             squeeze=False)

    # X-axis: normalized Kendall tau (0 to 1)
    bins = np.linspace(0, 1, 21)  # 0%, 5%, 10%, ..., 100%

    # First pass: compute histograms to find global y-max for this figure
    y_max = 0
    for model in models:
        for exp in exps:
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['kendall_tau_normalized'].values
            baseline_data = refs.get('baseline_by_model', {}).get(model, np.array([]))

            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                counts, _ = np.histogram(int_data, bins=bins, weights=int_weights)
                y_max = max(y_max, counts.max())

            if len(baseline_data) > 0:
                baseline_weights = np.ones_like(baseline_data) * 100 / len(baseline_data)
                counts, _ = np.histogram(baseline_data, bins=bins, weights=baseline_weights)
                y_max = max(y_max, counts.max())

    # Add padding to y_max
    y_max = y_max * 1.1

    for row_idx, model in enumerate(models):
        for col_idx, exp in enumerate(exps):
            ax = axes[row_idx, col_idx]

            # Get intervention data
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['kendall_tau_normalized'].values

            # Get baseline for this model
            baseline_data = refs.get('baseline_by_model', {}).get(model, np.array([]))

            # Plot intervention FIRST (colored, behind, with darker outline)
            baseline_mean = None
            int_mean = None

            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                ax.hist(int_data, bins=bins, alpha=0.6, color=MODEL_COLORS[model],
                       edgecolor=MODEL_COLORS_DARK[model], linewidth=0.6, weights=int_weights)

                # Add mean line for intervention (dashed)
                int_mean = np.mean(int_data)
                ax.axvline(int_mean, color=MODEL_COLORS[model], linestyle='--',
                          linewidth=2, alpha=0.9)

            # Plot baseline SECOND (gray, in front, with black outline)
            if len(baseline_data) > 0:
                baseline_weights = np.ones_like(baseline_data) * 100 / len(baseline_data)
                ax.hist(baseline_data, bins=bins, alpha=0.5, color=BASELINE_COLOR,
                       edgecolor='#333333', linewidth=0.6, weights=baseline_weights)

                # Add mean line for baseline
                baseline_mean = np.mean(baseline_data)
                ax.axvline(baseline_mean, color=BASELINE_COLOR, linestyle='--',
                          linewidth=1.5, alpha=0.8)

            # Styling - use shared y_max for this figure
            ax.set_xlim(0, 1)
            ax.set_ylim(0, y_max)

            # Column titles (intervention names) - only on top row
            if row_idx == 0:
                ax.set_title(xlabel_map.get(exp, exp).replace('_', ' '),
                           fontweight='bold', fontsize=11, pad=8)

            # Row labels (model names) - only on left column
            if col_idx == 0:
                ax.set_ylabel(f'{model}\n% of obs', fontweight='bold', fontsize=10,
                            color=MODEL_COLORS[model])
            else:
                ax.set_ylabel('')

            # Show y-tick labels (percentage)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))

            # X-axis: show as percentage
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.0f}%'))

            # X-axis label only on bottom row
            if row_idx == n_models - 1:
                ax.set_xlabel('Kendall τ (% pairs wrong)', fontsize=9)

            # Add stats annotation (both means) or "No data" if missing
            if len(int_data) > 0 and int_mean is not None:
                # Show both baseline and intervention means
                annotation_lines = []

                if baseline_mean is not None:
                    annotation_lines.append((f'μ={baseline_mean*100:.0f}%', BASELINE_COLOR))

                annotation_lines.append((f'μ={int_mean*100:.0f}%', MODEL_COLORS[model]))

                # Draw annotations stacked vertically
                for i, (text, color) in enumerate(annotation_lines):
                    ax.text(0.97, 0.95 - i*0.12, text,
                           transform=ax.transAxes, fontsize=9, fontweight='bold',
                           ha='right', va='top', color=color,
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                    alpha=0.85, edgecolor='none'))
            else:
                ax.text(0.5, 0.5, 'No data',
                       transform=ax.transAxes, fontsize=10,
                       ha='center', va='center', color='#999999',
                       style='italic')

    # Add legend at bottom
    legend_elements = [
        mpatches.Patch(facecolor=BASELINE_COLOR, alpha=0.35, edgecolor='#333333',
                      linewidth=0.6, label='Direct Baseline'),
        mpatches.Patch(facecolor='#666666', alpha=0.7, label='Intervention'),
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=2,
                  label='Intervention Mean'),
        plt.Line2D([0], [0], color=BASELINE_COLOR, linestyle='--', linewidth=1.5,
                  label='Baseline Mean'),
    ]

    fig.legend(handles=legend_elements, loc='lower center', ncol=4,
              frameon=True, framealpha=0.95, edgecolor='#cccccc',
              bbox_to_anchor=(0.5, -0.02), fontsize=9)

    # Main title
    fig.suptitle(title, fontweight='bold', fontsize=14, y=1.02)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)

    output_path = OUTPUT_DIR / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✓ Saved: {filename}")


def plot_da_vs_osp(df, refs):
    """
    Special comparison plot: Direct DA baseline vs OSP baseline.
    """
    models = [m for m in MODEL_ORDER if m in df['model_short'].unique()]

    # Check if we have both experiments
    has_direct = 'direct_baseline' in df['experiment'].values
    has_osp = 'osp_baseline' in df['experiment'].values

    if not has_direct or not has_osp:
        print("Skipping DA vs OSP plot: missing data")
        return

    n_models = len(models)

    fig, axes = plt.subplots(n_models, 2, figsize=(6.0, 2.6 * n_models), squeeze=False)

    bins = np.linspace(0, 1, 21)

    for row_idx, model in enumerate(models):
        for col_idx, (exp, exp_label) in enumerate([
            ('direct_baseline', 'Direct DA'),
            ('osp_baseline', 'OSP (Iterative)')
        ]):
            ax = axes[row_idx, col_idx]

            data = df[(df['experiment'] == exp) &
                     (df['model_short'] == model)]['kendall_tau_normalized'].values

            if len(data) > 0:
                weights = np.ones_like(data) * 100 / len(data)
                ax.hist(data, bins=bins, alpha=0.7, color=MODEL_COLORS[model],
                       edgecolor='white', linewidth=0.5, weights=weights)

                mean_val = np.mean(data)
                ax.axvline(mean_val, color=MODEL_COLORS[model], linestyle='--',
                          linewidth=2, alpha=0.9)

                # Annotation
                if mean_val > 0.3:
                    text_color = '#c44e52'
                elif mean_val > 0.1:
                    text_color = '#d4a700'
                else:
                    text_color = '#2d8a2d'

                ax.text(0.97, 0.95, f'μ={mean_val*100:.0f}%',
                       transform=ax.transAxes, fontsize=9, fontweight='bold',
                       ha='right', va='top', color=text_color,
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                alpha=0.85, edgecolor='none'))

            ax.set_xlim(0, 1)
            ax.set_ylim(bottom=0)

            if row_idx == 0:
                ax.set_title(exp_label, fontweight='bold', fontsize=11, pad=8)

            if col_idx == 0:
                ax.set_ylabel(f'{model}\n% of obs', fontweight='bold', fontsize=10,
                            color=MODEL_COLORS[model])
            else:
                ax.set_ylabel('')

            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.0f}%'))

            if row_idx == n_models - 1:
                ax.set_xlabel('Kendall τ (% pairs wrong)', fontsize=9)

    fig.suptitle('Direct DA vs OSP (Iterative DA)', fontweight='bold', fontsize=14, y=1.02)

    plt.tight_layout()

    output_path = OUTPUT_DIR / 'da_vs_osp.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✓ Saved: da_vs_osp.png")


def plot_all_interventions_combined(df, refs):
    """
    Create a single summary plot with all DA interventions, color-coded by axis.

    Layout:
    - Rows: Models
    - Columns: All interventions (grouped by axis via color)
    - Each cell: Direct baseline (gray) vs Intervention (axis-colored)
    """
    models = [m for m in MODEL_ORDER if m in df['model_short'].unique()]

    # Define axis colors
    AXIS_COLORS = {
        'Axis 1': '#e6194B',   # Red - Contingent Reasoning
        'Axis 2': '#3cb44b',   # Green - Forward Planning
        'Axis 3': '#4363d8',   # Blue - Beliefs
    }

    AXIS_COLORS_DARK = {
        'Axis 1': '#a11232',
        'Axis 2': '#297a33',
        'Axis 3': '#2a3d8a',
    }

    # All interventions in order with axis assignment
    interventions = [
        # Axis 1: Contingent Reasoning
        ('axis1_onestep', '1-step', 'Axis 1'),
        ('axis1_tree', 'Tree', 'Axis 1'),
        ('axis1_backward_induct', 'Backward', 'Axis 1'),
        ('axis1_worstcase', 'Worst', 'Axis 1'),
        ('axis1_enumerate_gpt4o', 'Enum', 'Axis 1'),
        ('axis1_dominanted', 'Dom', 'Axis 1'),
        # Axis 2: Forward Planning
        ('axis2_0step', '0-step', 'Axis 2'),
        ('axis2_1step', '1-step', 'Axis 2'),
        ('axis2_2step', '2-step', 'Axis 2'),
        ('axis2_fullsim', 'Full', 'Axis 2'),
        # Axis 3: Beliefs
        ('axis3_firstorder', '1st', 'Axis 3'),
        ('axis3_secondorder', '2nd', 'Axis 3'),
        ('axis3_common_knowledge', 'CK', 'Axis 3'),
    ]

    # Filter to interventions that exist in data
    interventions = [(exp, label, axis) for exp, label, axis in interventions
                     if exp in df['experiment'].unique()]

    if not interventions:
        print("No intervention data found for combined plot")
        return

    n_models = len(models)
    n_exps = len(interventions)

    fig, axes = plt.subplots(n_models, n_exps, figsize=(1.5 * n_exps, 2.4 * n_models),
                             squeeze=False)

    # X-axis: normalized Kendall tau (0 to 1)
    bins = np.linspace(0, 1, 15)

    # First pass: compute y_max
    y_max = 0
    for model in models:
        baseline_data = refs.get('baseline_by_model', {}).get(model, np.array([]))
        if len(baseline_data) > 0:
            baseline_weights = np.ones_like(baseline_data) * 100 / len(baseline_data)
            counts, _ = np.histogram(baseline_data, bins=bins, weights=baseline_weights)
            y_max = max(y_max, counts.max())

        for exp, _, _ in interventions:
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['kendall_tau_normalized'].values
            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                counts, _ = np.histogram(int_data, bins=bins, weights=int_weights)
                y_max = max(y_max, counts.max())

    y_max = y_max * 1.1

    for row_idx, model in enumerate(models):
        for col_idx, (exp, label, axis) in enumerate(interventions):
            ax = axes[row_idx, col_idx]

            color = AXIS_COLORS[axis]
            color_dark = AXIS_COLORS_DARK[axis]

            # Get intervention data
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['kendall_tau_normalized'].values

            # Get baseline for this model
            baseline_data = refs.get('baseline_by_model', {}).get(model, np.array([]))

            baseline_mean = None
            int_mean = None

            # Plot intervention FIRST (colored, behind)
            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                ax.hist(int_data, bins=bins, alpha=0.6, color=color,
                       edgecolor=color_dark, linewidth=0.5, weights=int_weights)
                int_mean = np.mean(int_data)
                ax.axvline(int_mean, color=color, linestyle='--',
                          linewidth=1.5, alpha=0.9)

            # Plot baseline SECOND (gray, in front)
            if len(baseline_data) > 0:
                baseline_weights = np.ones_like(baseline_data) * 100 / len(baseline_data)
                ax.hist(baseline_data, bins=bins, alpha=0.4, color=BASELINE_COLOR,
                       edgecolor='#333333', linewidth=0.5, weights=baseline_weights)
                baseline_mean = np.mean(baseline_data)
                ax.axvline(baseline_mean, color=BASELINE_COLOR, linestyle='--',
                          linewidth=1.2, alpha=0.7)

            # Styling
            ax.set_xlim(0, 1)
            ax.set_ylim(0, y_max)

            # Column titles - only on top row
            if row_idx == 0:
                ax.set_title(label, fontweight='bold', fontsize=8, pad=3, color=color)

            # Row labels - only on left column
            if col_idx == 0:
                ax.set_ylabel(f'{model}\n% obs', fontweight='bold', fontsize=8,
                            color=MODEL_COLORS[model])
            else:
                ax.set_ylabel('')
                ax.set_yticklabels([])

            # Y-axis formatting
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}'))

            # X-axis label only on bottom row
            if row_idx == n_models - 1:
                ax.set_xlabel('τ', fontsize=7)
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.0f}%'))
            else:
                ax.set_xticklabels([])

            # Compact annotation
            if int_mean is not None:
                ax.text(0.95, 0.92, f'{int_mean*100:.0f}%',
                       transform=ax.transAxes, fontsize=6, fontweight='bold',
                       ha='right', va='top', color=color,
                       bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                                alpha=0.8, edgecolor='none'))

    # Add legend at bottom
    legend_elements = [
        mpatches.Patch(facecolor=BASELINE_COLOR, alpha=0.4, edgecolor='#333333',
                      linewidth=0.5, label='Direct Baseline'),
        mpatches.Patch(facecolor=AXIS_COLORS['Axis 1'], alpha=0.6,
                      label='Ax1: Contingent'),
        mpatches.Patch(facecolor=AXIS_COLORS['Axis 2'], alpha=0.6,
                      label='Ax2: Forward'),
        mpatches.Patch(facecolor=AXIS_COLORS['Axis 3'], alpha=0.6,
                      label='Ax3: Beliefs'),
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=1.5,
                  label='Mean'),
    ]

    fig.legend(handles=legend_elements, loc='lower center', ncol=5,
              frameon=True, framealpha=0.95, edgecolor='#cccccc',
              bbox_to_anchor=(0.5, -0.02), fontsize=8)

    fig.suptitle('All Cognitive Interventions (DA)',
                fontweight='bold', fontsize=12, y=1.01)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12, top=0.92, hspace=0.15, wspace=0.08)

    output_path = OUTPUT_DIR / 'da_all_interventions_combined.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✓ Saved: da_all_interventions_combined.png")


def print_findings(df, refs):
    """Print key findings."""
    print("\n" + "═"*65)
    print("KEY FINDINGS")
    print("═"*65)

    if 'baseline' in refs:
        baseline_mean = refs['baseline']['kendall_tau_normalized'].mean()
        print(f"\nDirect Baseline mean Kendall τ: {baseline_mean*100:.1f}%")

    # Truthfulness rates by experiment
    print("\nTruthfulness rates by experiment:")
    truth_rates = df.groupby('experiment')['is_truthful'].mean().sort_values()
    for exp, rate in truth_rates.items():
        print(f"  {exp}: {rate*100:.1f}%")

    # Compare Direct vs OSP
    direct_data = df[df['experiment'] == 'direct_baseline']
    osp_data = df[df['experiment'] == 'osp_baseline']

    if not direct_data.empty and not osp_data.empty:
        print("\nDirect vs OSP comparison:")
        print(f"  Direct Baseline - mean τ: {direct_data['kendall_tau_normalized'].mean()*100:.1f}%, "
              f"truthful: {direct_data['is_truthful'].mean()*100:.1f}%")
        print(f"  OSP Baseline - mean τ: {osp_data['kendall_tau_normalized'].mean()*100:.1f}%, "
              f"truthful: {osp_data['is_truthful'].mean()*100:.1f}%")


def main():
    print("Loading DA data...")
    df = load_da_data()
    print(f"Loaded {len(df):,} observations\n")

    if df.empty:
        print("No data found!")
        return

    refs = get_reference_data(df)

    if 'baseline' in refs:
        print(f"Direct Baseline mean Kendall τ: {refs['baseline']['kendall_tau_normalized'].mean()*100:.1f}%")

    # Check data availability
    print("\nData availability:")
    for model in MODEL_ORDER:
        model_exps = df[df['model_short'] == model]['experiment'].unique()
        print(f"  {model}: {len(model_exps)} experiments")

    print("\nExperiments found:")
    for exp in sorted(df['experiment'].unique()):
        count = len(df[df['experiment'] == exp])
        print(f"  {exp}: {count} observations")

    print("\nGenerating plots...\n")

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 1: Reasoning Depth
    # ─────────────────────────────────────────────────────────────────────────
    axis1_exps = ['axis1_onestep', 'axis1_tree', 'axis1_backward_induct',
                  'axis1_worstcase', 'axis1_enumerate_gpt4o', 'axis1_dominanted']
    axis1_labels = {
        'axis1_onestep': 'One-step',
        'axis1_tree': 'Tree',
        'axis1_backward_induct': 'Backward Ind.',
        'axis1_worstcase': 'Worst-case',
        'axis1_enumerate_gpt4o': 'Enumerate',
        'axis1_dominanted': 'Dominated'
    }
    plot_intervention_histograms(df, axis1_exps, 'Contingent Reasoning',
                                 'da_axis1_reasoning.png', axis1_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 2: Forward Lookahead
    # ─────────────────────────────────────────────────────────────────────────
    axis2_exps = ['axis2_0step', 'axis2_1step', 'axis2_2step', 'axis2_fullsim']
    axis2_labels = {
        'axis2_0step': '0-step',
        'axis2_1step': '1-step',
        'axis2_2step': '2-step',
        'axis2_fullsim': 'Full Sim'
    }
    plot_intervention_histograms(df, axis2_exps, 'Forward Planning (Lookahead)',
                                 'da_axis2_forward.png', axis2_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 2: Monotonicity variants
    # ─────────────────────────────────────────────────────────────────────────
    axis2_mono_exps = ['axis2_monotonic_options', 'axis2_monotonic_outcome',
                       'axis2_monotonic_safety']
    axis2_mono_labels = {
        'axis2_monotonic_options': 'Options',
        'axis2_monotonic_outcome': 'Outcome',
        'axis2_monotonic_safety': 'Safety'
    }
    plot_intervention_histograms(df, axis2_mono_exps, 'Forward Planning (Monotonicity)',
                                 'da_axis2_monotonic.png', axis2_mono_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 3: Beliefs
    # ─────────────────────────────────────────────────────────────────────────
    axis3_exps = ['axis3_firstorder', 'axis3_secondorder', 'axis3_common_knowledge']
    axis3_labels = {
        'axis3_firstorder': 'First-order',
        'axis3_secondorder': 'Second-order',
        'axis3_common_knowledge': 'Common Know.'
    }
    plot_intervention_histograms(df, axis3_exps, 'Beliefs',
                                 'da_axis3_beliefs.png', axis3_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # Loss Aversion
    # ─────────────────────────────────────────────────────────────────────────
    loss_exps = ['loss_aversion_gain_frame', 'loss_aversion_loss_frame',
                 'loss_aversion_mixed_frame', 'loss_aversion_endowment',
                 'loss_aversion_WTA_WTP']
    loss_labels = {
        'loss_aversion_gain_frame': 'Gain',
        'loss_aversion_loss_frame': 'Loss',
        'loss_aversion_mixed_frame': 'Mixed',
        'loss_aversion_endowment': 'Endowment',
        'loss_aversion_WTA_WTP': 'WTA/WTP'
    }
    plot_intervention_histograms(df, loss_exps, 'Loss Aversion Interventions',
                                 'da_loss_aversion.png', loss_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # Risk Preferences
    # ─────────────────────────────────────────────────────────────────────────
    risk_exps = ['intervention_risk_averse', 'intervention_risk_neutral',
                 'intervention_risk_seeking']
    risk_labels = {
        'intervention_risk_averse': 'Risk Averse',
        'intervention_risk_neutral': 'Risk Neutral',
        'intervention_risk_seeking': 'Risk Seeking'
    }
    plot_intervention_histograms(df, risk_exps, 'Risk Preference Interventions',
                                 'da_risk_preferences.png', risk_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # Direct variants
    # ─────────────────────────────────────────────────────────────────────────
    direct_exps = ['direct_null', 'direct_menu_mechanics', 'direct_menu_property',
                   'direct_textbook_sp']
    direct_labels = {
        'direct_null': 'Null',
        'direct_menu_mechanics': 'Menu Mech.',
        'direct_menu_property': 'Menu Prop.',
        'direct_textbook_sp': 'Textbook SP'
    }
    plot_intervention_histograms(df, direct_exps, 'Direct Mechanism Variants',
                                 'da_direct_variants.png', direct_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # DA vs OSP comparison
    # ─────────────────────────────────────────────────────────────────────────
    plot_da_vs_osp(df, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # ALL INTERVENTIONS COMBINED (single summary plot)
    # ─────────────────────────────────────────────────────────────────────────
    plot_all_interventions_combined(df, refs)

    print_findings(df, refs)

    print("\n" + "═"*65)
    print(f"All DA plots saved to: {OUTPUT_DIR}")
    print("═"*65)


if __name__ == '__main__':
    main()

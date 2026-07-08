"""
Publication-ready plots for LLM auction intervention experiments.
Metric: bid - value (signed deviation, shows over/under-bidding)

Each intervention plot shows:
- Rows: One per model
- Columns: One per intervention (excluding axis baselines - SPSB is the baseline)
- Gray histogram: SPSB baseline distribution
- Colored histogram: Intervention distribution
- Vertical lines at means
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# ============================================================================
# STYLE CONFIGURATION
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

OUTPUT_DIR = Path(__file__).parent / 'auctions'

# Value midpoint for high/low type classification
VALUE_MIDPOINT = 25  # Midpoint of 0-49 value range

# ============================================================================
# COLOR UTILITIES
# ============================================================================

def lighten_color(hex_color, factor=0.4):
    """Lighten a hex color by mixing with white."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f'#{r:02x}{g:02x}{b:02x}'

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

MODEL_NAMES = {
    'claude-3-5-haiku-20241022': 'Claude 3.5 Haiku',
    'gemini-2.0-flash': 'Gemini 2.0 Flash',
    'google/gemma-3-27b-it': 'Gemma 3 27B',
    'gpt-4o': 'GPT-4o'
}

# Clean, professional palette
MODEL_COLORS = {
    'Claude 3.5 Haiku': '#4363d8',    # Blue
    'Gemini 2.0 Flash': '#e6194B',    # Red
    'Gemma 3 27B': '#3cb44b',         # Green
    'GPT-4o': '#f58231'               # Orange
}

# Darker versions for outlines (darken by ~30%)
MODEL_COLORS_DARK = {
    'Claude 3.5 Haiku': '#2a3d8a',    # Darker blue
    'Gemini 2.0 Flash': '#a11232',    # Darker red
    'Gemma 3 27B': '#297a33',         # Darker green
    'GPT-4o': '#c46820'               # Darker orange
}

# Order by baseline error severity (best to worst): Claude, Gemini, GPT-4o, Gemma
MODEL_ORDER = ['Claude 3.5 Haiku', 'Gemini 2.0 Flash', 'GPT-4o', 'Gemma 3 27B']

SPSB_COLOR = '#888888'  # Gray for SPSB baseline

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data():
    """Load the combined experimental results (most recent file)."""
    results_dir = Path(__file__).parent.parent / 'results'
    # Find the most recent combined results file
    combined_files = sorted(results_dir.glob('all_experiments_combined_*.csv'))
    if not combined_files:
        raise FileNotFoundError("No combined results files found")
    data_path = combined_files[-1]  # Most recent
    print(f"Using: {data_path.name}")
    df = pd.read_csv(data_path)
    df['model_short'] = df['model'].map(MODEL_NAMES)
    df['deviation'] = df['bid'] - df['player_value']  # Signed deviation
    df['value_type'] = np.where(df['player_value'] >= VALUE_MIDPOINT, 'high', 'low')
    return df


def get_reference_data(df):
    """Get SPSB and AC data for reference distributions."""
    refs = {}

    spsb_data = df[df['experiment'].isin(['spsb_apv', 'spsb'])]
    if not spsb_data.empty:
        refs['spsb'] = spsb_data
        refs['spsb_by_model'] = {
            model: spsb_data[spsb_data['model_short'] == model]['deviation'].values
            for model in MODEL_ORDER if model in spsb_data['model_short'].values
        }
        refs['spsb_by_model_type'] = {
            model: {
                'high': spsb_data[(spsb_data['model_short'] == model) &
                                  (spsb_data['value_type'] == 'high')]['deviation'].values,
                'low': spsb_data[(spsb_data['model_short'] == model) &
                                 (spsb_data['value_type'] == 'low')]['deviation'].values
            }
            for model in MODEL_ORDER if model in spsb_data['model_short'].values
        }

    ac_data = df[df['experiment'].isin(['ascending_clock_apv', 'ascending_clock_closed'])]
    if not ac_data.empty:
        refs['ac'] = ac_data
        refs['ac_by_model'] = {
            model: ac_data[ac_data['model_short'] == model]['deviation'].values
            for model in MODEL_ORDER if model in ac_data['model_short'].values
        }

    return refs


# ============================================================================
# HISTOGRAM DISTRIBUTION PLOTS
# ============================================================================

def plot_intervention_histograms(df, experiments, title, filename, xlabel_map, refs):
    """
    Create a grid of histograms showing bid - value distributions.

    Layout:
    - Rows: Models
    - Columns: Interventions
    - Each cell: SPSB (gray) vs Intervention (colored) overlaid histograms
    """
    models = [m for m in MODEL_ORDER if m in df['model_short'].unique()]
    exps = [e for e in experiments if e in df['experiment'].unique()]

    n_models = len(models)
    n_exps = len(exps)

    fig, axes = plt.subplots(n_models, n_exps, figsize=(3.0 * n_exps, 2.6 * n_models),
                             squeeze=False)

    # Determine common x-axis range (symmetric around 0)
    all_devs = df[df['experiment'].isin(experiments)]['deviation']
    if 'spsb' in refs:
        all_devs = pd.concat([all_devs, refs['spsb']['deviation']])

    x_limit = min(np.percentile(np.abs(all_devs.dropna()), 98), 25)
    bins = np.linspace(-x_limit, x_limit, 30)

    # First pass: compute histograms to find global y-max for this figure
    y_max = 0
    for model in models:
        spsb_data = refs.get('spsb_by_model', {}).get(model, np.array([]))
        if len(spsb_data) > 0:
            spsb_weights = np.ones_like(spsb_data) * 100 / len(spsb_data)
            counts, _ = np.histogram(spsb_data, bins=bins, weights=spsb_weights)
            y_max = max(y_max, counts.max())

        for exp in exps:
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['deviation'].values
            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                counts, _ = np.histogram(int_data, bins=bins, weights=int_weights)
                y_max = max(y_max, counts.max())

    # Add padding to y_max
    y_max = y_max * 1.1

    for row_idx, model in enumerate(models):
        for col_idx, exp in enumerate(exps):
            ax = axes[row_idx, col_idx]

            # Get intervention data
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['deviation'].values

            # Get SPSB baseline for this model
            spsb_data = refs.get('spsb_by_model', {}).get(model, np.array([]))

            spsb_mean = None
            int_mean = None

            # Plot intervention FIRST (colored, behind)
            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                ax.hist(int_data, bins=bins, alpha=0.6, color=MODEL_COLORS[model],
                       edgecolor=MODEL_COLORS_DARK[model], linewidth=0.6, weights=int_weights)
                int_mean = np.mean(int_data)
                ax.axvline(int_mean, color=MODEL_COLORS[model], linestyle='--',
                          linewidth=2, alpha=0.9)

            # Plot SPSB baseline SECOND (gray, in front)
            if len(spsb_data) > 0:
                spsb_weights = np.ones_like(spsb_data) * 100 / len(spsb_data)
                ax.hist(spsb_data, bins=bins, alpha=0.5, color=SPSB_COLOR,
                       edgecolor='#333333', linewidth=0.6, weights=spsb_weights)
                spsb_mean = np.mean(spsb_data)
                ax.axvline(spsb_mean, color=SPSB_COLOR, linestyle='--',
                          linewidth=1.5, alpha=0.8)

            # Styling
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(0, y_max)

            # Column titles (intervention names) - only on top row
            if row_idx == 0:
                ax.set_title(xlabel_map.get(exp, exp).replace('\n', ' '),
                           fontweight='bold', fontsize=11, pad=8)

            # Row labels (model names) - only on left column
            if col_idx == 0:
                ax.set_ylabel(f'{model}\n% of obs', fontweight='bold', fontsize=10,
                            color=MODEL_COLORS[model])
            else:
                ax.set_ylabel('')

            # Show y-tick labels (percentage)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))

            # X-axis label only on bottom row
            if row_idx == n_models - 1:
                ax.set_xlabel('bid − value', fontsize=9)

            # Add stats annotation (both means)
            if int_mean is not None:
                annotation_lines = []
                if spsb_mean is not None:
                    annotation_lines.append((f'μ={spsb_mean:+.1f}', SPSB_COLOR))
                annotation_lines.append((f'μ={int_mean:+.1f}', MODEL_COLORS[model]))

                # Draw annotations stacked vertically
                for i, (text, color) in enumerate(annotation_lines):
                    ax.text(0.97, 0.95 - i*0.12, text,
                           transform=ax.transAxes, fontsize=9, fontweight='bold',
                           ha='right', va='top', color=color,
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                    alpha=0.85, edgecolor='none'))
            else:
                # No data for this model/experiment
                ax.text(0.5, 0.5, 'No data',
                       transform=ax.transAxes, fontsize=10,
                       ha='center', va='center', color='#999999',
                       style='italic')

    # Add legend at bottom
    legend_elements = [
        mpatches.Patch(facecolor=SPSB_COLOR, alpha=0.5, edgecolor='#333333', linewidth=0.6, label='SPSB Baseline'),
        mpatches.Patch(facecolor='#666666', alpha=0.6, label='Intervention'),
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=2, label='Mean'),
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


def plot_high_low_type_summary(df, refs):
    """
    Create a summary plot showing high types are responsible for most underbidding.

    Layout:
    - 2 rows: Baseline (SPSB), Best Intervention (Tree)
    - 4 columns: Models
    - Each cell: overlaid histograms for high type (hatched) and low type (solid)
    """
    models = [m for m in MODEL_ORDER if m in df['model_short'].unique()]
    experiments = [('spsb', 'SPSB Baseline'), ('axis2_forward_tree', 'Tree Intervention')]

    fig, axes = plt.subplots(2, len(models), figsize=(3.5 * len(models), 5),
                             squeeze=False)

    # Determine common x-axis range
    all_devs = df[df['experiment'].isin(['spsb', 'axis2_forward_tree'])]['deviation']
    x_limit = min(np.percentile(np.abs(all_devs.dropna()), 98), 25)
    bins = np.linspace(-x_limit, x_limit, 25)

    # First pass: find global y-max
    y_max = 0
    for model in models:
        for exp, _ in experiments:
            for vtype in ['high', 'low']:
                data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model) &
                         (df['value_type'] == vtype)]['deviation'].values
                if len(data) > 0:
                    weights = np.ones_like(data) * 100 / len(data)
                    counts, _ = np.histogram(data, bins=bins, weights=weights)
                    y_max = max(y_max, counts.max())
    y_max = y_max * 1.15

    for row_idx, (exp, exp_label) in enumerate(experiments):
        for col_idx, model in enumerate(models):
            ax = axes[row_idx, col_idx]

            # Get data split by type
            high_data = df[(df['experiment'] == exp) &
                          (df['model_short'] == model) &
                          (df['value_type'] == 'high')]['deviation'].values
            low_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model) &
                         (df['value_type'] == 'low')]['deviation'].values

            color_light = lighten_color(MODEL_COLORS[model], factor=0.4)
            color_dark = MODEL_COLORS_DARK[model]

            mean_high = None
            mean_low = None

            # Plot LOW types FIRST (solid, lighter, behind)
            if len(low_data) > 0:
                low_weights = np.ones_like(low_data) * 100 / len(low_data)
                ax.hist(low_data, bins=bins, alpha=0.6, color=color_light,
                       edgecolor=MODEL_COLORS[model], linewidth=0.6, weights=low_weights,
                       label='Low Type')
                mean_low = np.mean(low_data)
                ax.axvline(mean_low, color=color_light, linestyle='--', linewidth=1.5, alpha=0.8)

            # Plot HIGH types SECOND (hatched, darker, in front)
            if len(high_data) > 0:
                high_weights = np.ones_like(high_data) * 100 / len(high_data)
                ax.hist(high_data, bins=bins, alpha=0.7, color=color_dark,
                       edgecolor='black', linewidth=0.6, weights=high_weights,
                       hatch='//', label='High Type')
                mean_high = np.mean(high_data)
                ax.axvline(mean_high, color=color_dark, linestyle='--', linewidth=2, alpha=0.9)

            # Styling
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(0, y_max)

            # Column titles (model names) - only on top row
            if row_idx == 0:
                ax.set_title(model, fontweight='bold', fontsize=11, color=MODEL_COLORS[model])

            # Row labels - only on left column
            if col_idx == 0:
                ax.set_ylabel(f'{exp_label}\n% of obs', fontweight='bold', fontsize=10)
            else:
                ax.set_ylabel('')

            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))

            # X-axis label only on bottom row
            if row_idx == 1:
                ax.set_xlabel('bid − value', fontsize=9)

            # Add annotation with means
            annotation_lines = []
            if mean_high is not None:
                annotation_lines.append((f'high={mean_high:+.1f}', color_dark))
            if mean_low is not None:
                annotation_lines.append((f'low={mean_low:+.1f}', color_light))

            for i, (text, color) in enumerate(annotation_lines):
                ax.text(0.97, 0.95 - i*0.12, text,
                       transform=ax.transAxes, fontsize=8, fontweight='bold',
                       ha='right', va='top', color=color,
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                alpha=0.85, edgecolor='none'))

    # Add legend at bottom
    legend_elements = [
        mpatches.Patch(facecolor='#aaaaaa', alpha=0.6, edgecolor='#666666',
                      linewidth=0.6, label=f'Low Type (v<{VALUE_MIDPOINT})'),
        mpatches.Patch(facecolor='#555555', alpha=0.7, edgecolor='black',
                      linewidth=0.6, hatch='//', label=f'High Type (v≥{VALUE_MIDPOINT})'),
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=1.5, label='Mean'),
    ]

    fig.legend(handles=legend_elements, loc='lower center', ncol=3,
              frameon=True, framealpha=0.95, edgecolor='#cccccc',
              bbox_to_anchor=(0.5, -0.02), fontsize=9)

    fig.suptitle('High Types Drive Underbidding (Tree Intervention Fixes It)',
                fontweight='bold', fontsize=13, y=1.02)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)

    output_path = OUTPUT_DIR / 'high_low_type_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✓ Saved: high_low_type_summary.png")


def plot_all_interventions_combined(df, refs):
    """
    Create a single summary plot with all interventions, color-coded by axis.

    Layout:
    - Rows: Models
    - Columns: All interventions (grouped by axis via color)
    - Each cell: SPSB (gray) vs Intervention (axis-colored) overlaid histograms
    """
    models = [m for m in MODEL_ORDER if m in df['model_short'].unique()]

    # Define all interventions grouped by axis with colors
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
        ('axis1_contingent_dominated', 'Dominated', 'Axis 1'),
        ('axis1_contingent_enumerate', 'Enumerate', 'Axis 1'),
        ('axis1_contingent_worstcase', 'Worst-case', 'Axis 1'),
        # Axis 2: Forward Planning
        ('axis2_forward_onestep', 'One-step', 'Axis 2'),
        ('axis2_forward_tree', 'Tree', 'Axis 2'),
        ('axis2_forward_backward_induct', 'Backward', 'Axis 2'),
        # Axis 3: Beliefs
        ('axis3_beliefs_firstorder', '1st-order', 'Axis 3'),
        ('axis3_beliefs_secondorder', '2nd-order', 'Axis 3'),
        ('axis3_beliefs_common_knowledge', 'CK', 'Axis 3'),
    ]

    # Filter to interventions that exist in data
    interventions = [(exp, label, axis) for exp, label, axis in interventions
                     if exp in df['experiment'].unique()]

    n_models = len(models)
    n_exps = len(interventions)

    fig, axes = plt.subplots(n_models, n_exps, figsize=(1.8 * n_exps, 2.4 * n_models),
                             squeeze=False)

    # Determine common x-axis range
    all_devs = df[df['experiment'].isin([e for e, _, _ in interventions])]['deviation']
    if 'spsb' in refs:
        all_devs = pd.concat([all_devs, refs['spsb']['deviation']])

    x_limit = min(np.percentile(np.abs(all_devs.dropna()), 98), 25)
    bins = np.linspace(-x_limit, x_limit, 25)

    # First pass: compute y_max
    y_max = 0
    for model in models:
        spsb_data = refs.get('spsb_by_model', {}).get(model, np.array([]))
        if len(spsb_data) > 0:
            spsb_weights = np.ones_like(spsb_data) * 100 / len(spsb_data)
            counts, _ = np.histogram(spsb_data, bins=bins, weights=spsb_weights)
            y_max = max(y_max, counts.max())

        for exp, _, _ in interventions:
            int_data = df[(df['experiment'] == exp) &
                         (df['model_short'] == model)]['deviation'].values
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
                         (df['model_short'] == model)]['deviation'].values

            # Get SPSB baseline for this model
            spsb_data = refs.get('spsb_by_model', {}).get(model, np.array([]))

            spsb_mean = None
            int_mean = None

            # Plot intervention FIRST (colored, behind)
            if len(int_data) > 0:
                int_weights = np.ones_like(int_data) * 100 / len(int_data)
                ax.hist(int_data, bins=bins, alpha=0.6, color=color,
                       edgecolor=color_dark, linewidth=0.5, weights=int_weights)
                int_mean = np.mean(int_data)
                ax.axvline(int_mean, color=color, linestyle='--',
                          linewidth=1.5, alpha=0.9)

            # Plot SPSB baseline SECOND (gray, in front)
            if len(spsb_data) > 0:
                spsb_weights = np.ones_like(spsb_data) * 100 / len(spsb_data)
                ax.hist(spsb_data, bins=bins, alpha=0.4, color=SPSB_COLOR,
                       edgecolor='#333333', linewidth=0.5, weights=spsb_weights)
                spsb_mean = np.mean(spsb_data)
                ax.axvline(spsb_mean, color=SPSB_COLOR, linestyle='--',
                          linewidth=1.2, alpha=0.7)

            # Styling
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(0, y_max)

            # Column titles - only on top row
            if row_idx == 0:
                ax.set_title(label, fontweight='bold', fontsize=9, pad=4, color=color)

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
                ax.set_xlabel('bid−val', fontsize=7)
            else:
                ax.set_xticklabels([])

            # Compact annotation
            if int_mean is not None:
                ax.text(0.95, 0.92, f'{int_mean:+.1f}',
                       transform=ax.transAxes, fontsize=7, fontweight='bold',
                       ha='right', va='top', color=color,
                       bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                alpha=0.8, edgecolor='none'))

    # Add axis group labels at top
    # Calculate column spans for each axis
    axis_spans = {}
    for col_idx, (_, _, axis) in enumerate(interventions):
        if axis not in axis_spans:
            axis_spans[axis] = [col_idx, col_idx]
        else:
            axis_spans[axis][1] = col_idx

    for axis, (start, end) in axis_spans.items():
        mid = (start + end) / 2
        fig.text((mid + 0.5) / n_exps * 0.85 + 0.08, 0.98,
                axis.replace('Axis ', 'Ax'),
                ha='center', va='bottom', fontsize=10, fontweight='bold',
                color=AXIS_COLORS[axis])

    # Add legend at bottom
    legend_elements = [
        mpatches.Patch(facecolor=SPSB_COLOR, alpha=0.4, edgecolor='#333333',
                      linewidth=0.5, label='SPSB Baseline'),
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
              bbox_to_anchor=(0.5, -0.01), fontsize=8)

    fig.suptitle('All Cognitive Interventions (Auctions)',
                fontweight='bold', fontsize=12, y=1.01)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.1, top=0.92, hspace=0.15, wspace=0.08)

    output_path = OUTPUT_DIR / 'all_interventions_combined.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✓ Saved: all_interventions_combined.png")


def print_findings(df, refs):
    """Print key findings."""
    print("\n" + "═"*65)
    print("KEY FINDINGS")
    print("═"*65)

    if 'spsb' in refs:
        spsb_mean = refs['spsb']['deviation'].mean()
        print(f"\nSPSB Baseline mean(bid - value): {spsb_mean:+.2f}")

    groups = {
        'Axis 1 (Contingent)': ['axis1_contingent_dominated',
                                'axis1_contingent_enumerate', 'axis1_contingent_worstcase'],
        'Axis 2 (Forward)': ['axis2_forward_onestep',
                             'axis2_forward_tree', 'axis2_forward_backward_induct'],
        'Axis 3 (Beliefs)': ['axis3_beliefs_firstorder',
                             'axis3_beliefs_secondorder', 'axis3_beliefs_common_knowledge'],
        'Loss Aversion': ['loss_aversion_gain_frame',
                          'loss_aversion_loss_frame', 'loss_aversion_mixed_frame',
                          'loss_aversion_endowment', 'loss_aversion_WTA_WTP'],
        'Risk Preferences': ['risk_averse', 'risk_neutrality', 'risk_seeking'],
    }

    for group_name, exps in groups.items():
        print(f"\n{group_name}:")
        subset = df[df['experiment'].isin(exps)]

        for exp in exps:
            exp_data = subset[subset['experiment'] == exp]['deviation']
            if len(exp_data) > 0:
                exp_name = exp.split('_')[-1]
                print(f"  {exp_name}: mean = {exp_data.mean():+.2f}")


def main():
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df):,} observations\n")

    refs = get_reference_data(df)

    if 'spsb' in refs:
        print(f"SPSB Baseline mean(bid - value): {refs['spsb']['deviation'].mean():+.2f}")

    # Check for missing data
    print("\nData availability:")
    for model in MODEL_ORDER:
        model_exps = df[df['model_short'] == model]['experiment'].unique()
        print(f"  {model}: {len(model_exps)} experiments")

    print("\nGenerating plots...\n")

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 1: Contingent Reasoning (no baseline - SPSB is the baseline)
    # ─────────────────────────────────────────────────────────────────────────
    axis1_exps = ['axis1_contingent_dominated',
                  'axis1_contingent_enumerate', 'axis1_contingent_worstcase']
    axis1_labels = {
        'axis1_contingent_dominated': 'Dominated',
        'axis1_contingent_enumerate': 'Enumerate',
        'axis1_contingent_worstcase': 'Worst-case'
    }
    plot_intervention_histograms(df, axis1_exps, 'Contingent Reasoning',
                                 'axis1_contingent_reasoning.png', axis1_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 2: Forward Reasoning
    # ─────────────────────────────────────────────────────────────────────────
    axis2_exps = ['axis2_forward_onestep',
                  'axis2_forward_tree', 'axis2_forward_backward_induct']
    axis2_labels = {
        'axis2_forward_onestep': 'One-step',
        'axis2_forward_tree': 'Game Tree',
        'axis2_forward_backward_induct': 'Backward Ind.'
    }
    plot_intervention_histograms(df, axis2_exps, 'Forward Planning',
                                 'axis2_forward_reasoning.png', axis2_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # AXIS 3: Beliefs
    # ─────────────────────────────────────────────────────────────────────────
    axis3_exps = ['axis3_beliefs_firstorder',
                  'axis3_beliefs_secondorder', 'axis3_beliefs_common_knowledge']
    axis3_labels = {
        'axis3_beliefs_firstorder': 'First-order',
        'axis3_beliefs_secondorder': 'Second-order',
        'axis3_beliefs_common_knowledge': 'Common Know.'
    }
    plot_intervention_histograms(df, axis3_exps, 'Beliefs',
                                 'axis3_beliefs.png', axis3_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # Loss Aversion (no baseline)
    # ─────────────────────────────────────────────────────────────────────────
    loss_exps = ['loss_aversion_gain_frame',
                 'loss_aversion_loss_frame', 'loss_aversion_mixed_frame',
                 'loss_aversion_endowment', 'loss_aversion_WTA_WTP']
    loss_labels = {
        'loss_aversion_gain_frame': 'Gain',
        'loss_aversion_loss_frame': 'Loss',
        'loss_aversion_mixed_frame': 'Mixed',
        'loss_aversion_endowment': 'Endowment',
        'loss_aversion_WTA_WTP': 'WTA/WTP'
    }
    plot_intervention_histograms(df, loss_exps, 'Loss Aversion Interventions',
                                 'loss_aversion.png', loss_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # Risk Preferences
    # ─────────────────────────────────────────────────────────────────────────
    risk_exps = ['risk_averse', 'risk_neutrality', 'risk_seeking']
    risk_labels = {
        'risk_averse': 'Risk Averse',
        'risk_neutrality': 'Risk Neutral',
        'risk_seeking': 'Risk Seeking'
    }
    plot_intervention_histograms(df, risk_exps, 'Risk Preference Interventions',
                                 'risk_preferences.png', risk_labels, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # HIGH/LOW TYPE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    plot_high_low_type_summary(df, refs)

    # ─────────────────────────────────────────────────────────────────────────
    # ALL INTERVENTIONS COMBINED (single summary plot)
    # ─────────────────────────────────────────────────────────────────────────
    plot_all_interventions_combined(df, refs)

    print_findings(df, refs)

    print("\n" + "═"*65)
    print(f"All plots saved to: {OUTPUT_DIR}")
    print("═"*65)


if __name__ == '__main__':
    main()

"""
DA OSP (Yes/No Fixed) vs Direct Baseline - GPT-4o

Compares truthfulness rates between:
- Direct baseline DA (gray)
- OSP yes/no fixed format (colored)
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Style (matching existing plots)
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

OUTPUT_DIR = Path(__file__).parent
BASELINE_COLOR = '#888888'
OSP_COLOR = '#f58231'  # Orange for GPT-4o

DA_DIR = Path(__file__).parent.parent / 'experiment_logs' / 'da' / 'gpt4o'


def load_truthfulness_rates(experiment_name):
    """Load per-student truthfulness from all JSON files for an experiment."""
    raw_dir = DA_DIR / experiment_name / 'raw_data'
    per_student = []
    per_experiment = []

    for f in sorted(raw_dir.glob('*.json')):
        try:
            data = json.load(open(f))
            rate = data.get('truthfulness_rate', 0)
            per_experiment.append(rate)
            for student, truthful in data.get('truthfulness', {}).items():
                per_student.append(1 if truthful else 0)
        except Exception:
            continue

    return np.array(per_experiment), np.array(per_student)


def main():
    direct_exp, direct_student = load_truthfulness_rates('direct_baseline')
    osp_exp, osp_student = load_truthfulness_rates('osp_yesno_fixed')

    print(f"Direct baseline: {len(direct_exp)} experiments, "
          f"{len(direct_student)} students, "
          f"mean truthfulness = {direct_student.mean():.3f}")
    print(f"OSP yes/no fixed: {len(osp_exp)} experiments, "
          f"{len(osp_student)} students, "
          f"mean truthfulness = {osp_student.mean():.3f}")

    # Plot: histogram of per-experiment truthfulness rates
    fig, ax = plt.subplots(figsize=(6, 4))

    bins = np.array([0, 0.125, 0.375, 0.625, 0.875, 1.125])  # centers at 0, 0.25, 0.5, 0.75, 1.0

    # OSP first (colored, behind)
    osp_weights = np.ones_like(osp_exp) * 100 / len(osp_exp)
    ax.hist(osp_exp, bins=bins, alpha=0.6, color=OSP_COLOR,
            edgecolor='#b35a1a', linewidth=0.6, weights=osp_weights,
            label='OSP (Yes/No)')

    # Direct baseline second (gray, in front)
    direct_weights = np.ones_like(direct_exp) * 100 / len(direct_exp)
    ax.hist(direct_exp, bins=bins, alpha=0.5, color=BASELINE_COLOR,
            edgecolor='#333333', linewidth=0.6, weights=direct_weights,
            label='Direct Baseline')

    # Mean lines
    direct_mean = direct_exp.mean()
    osp_mean = osp_exp.mean()
    ax.axvline(direct_mean, color=BASELINE_COLOR, linestyle='--', linewidth=1.5, alpha=0.8)
    ax.axvline(osp_mean, color=OSP_COLOR, linestyle='--', linewidth=2, alpha=0.9)

    # Reference line at 1.0 (perfect truthfulness)
    ax.axvline(1.0, color='#2d8a2d', linestyle='-', linewidth=1.5, alpha=0.7)

    ax.set_xlabel('Truthfulness Rate (per experiment)', fontsize=11)
    ax.set_ylabel('% of experiments', fontsize=11)
    ax.set_title('DA: Direct Baseline vs OSP (Yes/No) — GPT-4o',
                 fontweight='bold', fontsize=13, pad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(['0', '0.25', '0.5', '0.75', '1.0'])

    # Annotations
    ax.text(0.03, 0.95, f'Direct μ={direct_mean:.2f}',
            transform=ax.transAxes, fontsize=10, fontweight='bold',
            ha='left', va='top', color=BASELINE_COLOR,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor='none'))
    ax.text(0.03, 0.82, f'OSP μ={osp_mean:.2f}',
            transform=ax.transAxes, fontsize=10, fontweight='bold',
            ha='left', va='top', color=OSP_COLOR,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor='none'))

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=BASELINE_COLOR, alpha=0.5, edgecolor='#333333',
                       linewidth=0.6, label='Direct Baseline'),
        mpatches.Patch(facecolor=OSP_COLOR, alpha=0.6, edgecolor='#b35a1a',
                       linewidth=0.6, label='OSP (Yes/No)'),
        plt.Line2D([0], [0], color='#2d8a2d', linestyle='-', linewidth=1.5,
                   label='Perfect Truthfulness'),
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=2,
                   label='Mean'),
    ]
    ax.legend(handles=legend_elements, loc='upper left',
              bbox_to_anchor=(0.0, 0.72), frameon=True, framealpha=0.95,
              edgecolor='#cccccc', fontsize=9)

    plt.tight_layout()

    output_path = OUTPUT_DIR / 'da' / 'da_osp_yesno_vs_direct.png'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"\nSaved: {output_path}")


if __name__ == '__main__':
    main()

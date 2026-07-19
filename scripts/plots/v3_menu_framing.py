#!/usr/bin/env python3
"""v3_menu_framing.pdf -- menu restatement + clock framing, four models.

Rebuild of the paper's Figure 5 (previously
writeup/figures/figure3_intervention_comparison.png) in the house style of the
other main-text figures (Engineering_simplicity/plots/fig1/fig2/fig4/fig5,
style spec: engineer_simplicity-main/plots/plot_osp_comparison.py).

Layout: 2 rows x 4 model columns.
    row 1  Menu restatement (B1)  -- intervention_menu
    row 2  Clock framing (B3)     -- intervention_proxy_breitmoser
    cols   Claude 3.5 Haiku, Gemini 2.0 Flash, GPT-4o, Gemma 3 27B

Gray overlay = the paper's CORRECTED pooled axis baseline for the same model:
axis1_contingent_baseline + axis3_beliefs_baseline ONLY. axis2_forward_baseline
is EXCLUDED -- its template was a mislabeled clock-framing treatment, see
results/merged_ranking/_axis2_baseline_provenance.md.

Data is bid-level:
  baselines from Engineering_simplicity .../results/all_experiments_combined_*.csv
  treatments parsed from the raw ES intervention logs
  (experiment_logs/<model>/<exp>/result_*.json) via the same parsing logic as
  analysis/build_auction_cells.py (imported, not duplicated).

Computed means are cross-checked against the paper's canonical values and the
script aborts on any mismatch > 0.05.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from build_auction_cells import (_rows_from_raw_json, ES, ES_CSV,  # noqa: E402
                                 ES_MODEL_DIRS)

OUT = ROOT / "writeup" / "figures" / "v3_menu_framing.pdf"

# ============================================================================
# STYLE CONFIGURATION (exactly as plots/plot_osp_comparison.py)
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

BASELINE_COLOR = '#888888'

MODEL_ORDER = ['Claude 3.5 Haiku', 'Gemini 2.0 Flash', 'GPT-4o', 'Gemma 3 27B']

MODEL_COLORS = {
    'Claude 3.5 Haiku': '#4363d8',    # Blue
    'Gemini 2.0 Flash': '#e6194B',    # Red
    'GPT-4o': '#f58231',              # Orange
    'Gemma 3 27B': '#3cb44b',         # Green
}

MODEL_COLORS_DARK = {
    'Claude 3.5 Haiku': '#2a3d8a',
    'Gemini 2.0 Flash': '#a11232',
    'GPT-4o': '#c46820',
    'Gemma 3 27B': '#297a33',
}

MODEL_IDS = {  # display name -> canonical model id (ES_MODEL_DIRS values)
    'Claude 3.5 Haiku': 'claude-3-5-haiku-20241022',
    'Gemini 2.0 Flash': 'gemini-2.0-flash',
    'GPT-4o': 'gpt-4o',
    'Gemma 3 27B': 'google/gemma-3-27b-it',
}

# ============================================================================
# DATA
# ============================================================================

# Corrected pooled axis baseline: axis2_forward_baseline EXCLUDED (mislabeled
# clock-framing treatment; see results/merged_ranking/_axis2_baseline_provenance.md).
BASELINES = ['axis1_contingent_baseline', 'axis3_beliefs_baseline']

TREATMENTS = [('intervention_menu', 'Menu Restatement (B1)'),
              ('intervention_proxy_breitmoser', 'Clock Framing (B3)')]

# Paper-canonical means, cross-checked below (abort on mismatch > 0.05).
EXPECTED_BASELINE = {'Claude 3.5 Haiku': +0.54, 'Gemini 2.0 Flash': -1.25,
                     'GPT-4o': -2.94, 'Gemma 3 27B': -6.53}
EXPECTED_MENU = {'Claude 3.5 Haiku': +1.37, 'Gemini 2.0 Flash': -1.13,
                 'GPT-4o': -4.10, 'Gemma 3 27B': -4.50}


def load_baselines() -> dict[str, np.ndarray]:
    """Corrected pooled baseline deviations (bid - value, $) per model."""
    df = pd.read_csv(ES_CSV)
    df = df[df['experiment'].isin(BASELINES)].copy()
    df['dev'] = pd.to_numeric(df['bid'], errors='coerce') - \
        pd.to_numeric(df['player_value'], errors='coerce')
    df = df.dropna(subset=['dev'])
    return {m: g['dev'].values for m, g in df.groupby('model')}


def load_treatment(mdir: str, model_id: str, exp: str) -> np.ndarray:
    """Treatment deviations parsed from the raw ES intervention logs."""
    exp_dir = ES / 'experiment_logs' / mdir / exp
    cfg = yaml.safe_load(open(ES / 'configs_auction' / f'interventions_{mdir}'
                              / f'{exp}.yaml'))
    frames = [
        _rows_from_raw_json(j, cfg, 'es_v12_raw', 'es_v12', model_id, exp)
        for j in sorted(exp_dir.glob('result_*.json'))]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    return (df['bid'] - df['player_value']).dropna().values


# ============================================================================
# PLOT
# ============================================================================

def pfmt(p: float) -> str:
    return 'p < 0.001' if p < 1e-3 else f'p = {p:.3f}'


def main():
    base = load_baselines()
    mdir_of = {v: k for k, v in ES_MODEL_DIRS.items()}

    # Geometry matches the v3 family (scripts/plots/v3_split_domain_figs.py,
    # 2-row case = v3_beliefs_auction.pdf): 5.8in wide, per-panel ticks,
    # no suptitle (the LaTeX caption titles the figure).
    fig, axes = plt.subplots(2, 4, figsize=(5.8, 3.3), squeeze=False)

    x_limit = 20
    bins = np.linspace(-x_limit, x_limit, 30)

    for row_idx, (exp, row_label) in enumerate(TREATMENTS):
        expected_t = EXPECTED_MENU if exp == 'intervention_menu' else None
        for col_idx, model in enumerate(MODEL_ORDER):
            ax = axes[row_idx, col_idx]
            color = MODEL_COLORS[model]
            color_dark = MODEL_COLORS_DARK[model]
            model_id = MODEL_IDS[model]

            treat_dev = load_treatment(mdir_of[model_id], model_id, exp)
            base_dev = base[model_id]

            # Treatment FIRST (colored, behind)
            treat_weights = np.ones_like(treat_dev) * 100 / len(treat_dev)
            ax.hist(treat_dev, bins=bins, alpha=0.6, color=color,
                    edgecolor=color_dark, linewidth=0.6, weights=treat_weights)
            treat_mean = np.mean(treat_dev)
            ax.axvline(treat_mean, color=color, linestyle='--', linewidth=2,
                       alpha=0.9)

            # Baseline SECOND (gray, in front)
            base_weights = np.ones_like(base_dev) * 100 / len(base_dev)
            ax.hist(base_dev, bins=bins, alpha=0.5, color=BASELINE_COLOR,
                    edgecolor='#333333', linewidth=0.6, weights=base_weights)
            base_mean = np.mean(base_dev)
            ax.axvline(base_mean, color=BASELINE_COLOR, linestyle='--',
                       linewidth=2, alpha=0.9)

            welch_p = stats.ttest_ind(treat_dev, base_dev,
                                      equal_var=False).pvalue

            # Cross-checks against the paper's canonical values
            assert abs(base_mean - EXPECTED_BASELINE[model]) <= 0.05, \
                (model, 'baseline', base_mean)
            if expected_t is not None:
                assert abs(treat_mean - expected_t[model]) <= 0.05, \
                    (model, exp, treat_mean)

            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(0, 100)
            ax.set_yticks([0, 20, 40, 60, 80, 100])
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))

            # Annotations: baseline mu (gray, top), treatment mu (colored),
            # Welch p vs the corrected baseline (smaller, lighter).
            box = dict(boxstyle='round,pad=0.2', facecolor='white',
                       alpha=0.9, edgecolor='none')
            ax.text(0.97, 0.95, f'μ = {base_mean:+.1f}',
                    transform=ax.transAxes, fontsize=9, fontweight='bold',
                    ha='right', va='top', color=BASELINE_COLOR, bbox=box)
            ax.text(0.97, 0.75, f'μ = {treat_mean:+.1f}',
                    transform=ax.transAxes, fontsize=9, fontweight='bold',
                    ha='right', va='top', color=color, bbox=box)
            ax.text(0.97, 0.56, pfmt(welch_p),
                    transform=ax.transAxes, fontsize=7, ha='right',
                    va='top', color='#999999',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                              alpha=0.85, edgecolor='none'))

            if row_idx == 0:
                ax.set_title(model, fontweight='bold', fontsize=10,
                             color=color, pad=6)
            if col_idx == 0:
                ax.set_ylabel(f'{row_label}\n(% of obs)', fontsize=9,
                              fontweight='bold')
            if row_idx == 1:
                ax.set_xlabel('bid − value ($)', fontsize=9)

            print(f"  {row_label} | {model}: baseline n={len(base_dev)}, "
                  f"μ={base_mean:+.2f} | treatment n={len(treat_dev)}, "
                  f"μ={treat_mean:+.2f} | Welch p={welch_p:.4f}")

    # ------------------------------------------------------------------------
    # LEGEND (multi-colored intervention patch, as in plot_osp_comparison.py)
    # ------------------------------------------------------------------------
    class MultiColorPatch:
        pass

    class MultiColorHandler:
        def __init__(self, colors):
            self.colors = colors

        def legend_artist(self, legend, orig_handle, fontsize, handlebox):
            x0, y0 = handlebox.xdescent, handlebox.ydescent
            width, height = handlebox.width, handlebox.height
            n = len(self.colors)
            patches = []
            for i, color in enumerate(self.colors):
                patch = mpatches.FancyBboxPatch(
                    (x0 + i * width / n, y0), width / n, height,
                    boxstyle='square,pad=0', facecolor=color, alpha=0.6,
                    edgecolor='none', transform=handlebox.get_transform())
                handlebox.add_artist(patch)
                patches.append(patch)
            return patches[0] if patches else None

    multi_patch = MultiColorPatch()
    handles = [
        mpatches.Patch(facecolor=BASELINE_COLOR, alpha=0.5,
                       edgecolor='#333333', linewidth=0.6),
        multi_patch,
        plt.Line2D([0], [0], color='#666666', linestyle='--', linewidth=2),
    ]
    labels = ['Baseline', 'Intervention', 'Mean']

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.30 / 3.3 * 2.2)
    fig.legend(handles, labels, loc='lower center', ncol=3,
               frameon=True, framealpha=0.95, edgecolor='#cccccc',
               bbox_to_anchor=(0.5, -0.03), fontsize=9,
               handler_map={MultiColorPatch: MultiColorHandler(
                   [MODEL_COLORS[m] for m in MODEL_ORDER])})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"\n✓ Saved: {OUT}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
build_cardinal_grid.py
======================
Evidence base for paper Section 7 (cardinal calibration):
"LLMs agree with human data ordinally; what does it take to make them agree
CARDINALLY? Is there a consistent tuning that works across mechanisms?"

For every (tuning knob, setting, model, mechanism) cell with existing data we
compute distance-to-human on three axes:
  1. Level:      SMAD (100 * E|b - b*(v)| / 24.5) vs canonical human SMAD
  2. Direction:  share of bids ABOVE value (tol 0.1 sealed / 0.5 clock) vs
                 the human overbid share from plots/auction_human.csv
  3. Shape:      Wasserstein-1 distance between scaled deviation-from-value
                 distributions, LLM vs synthetic human reconstruction
                 (results/v12_interventions/moment_matching/*_synthetic_bids.csv)

Conventions (documented for the Section-7 writer):
  * SMAD normalizer: 24.5 = E[b*] for truthful bidding with values Unif{0..49}.
    NOTE: legacy figure scripts (scripts/plots/appendix2_*.py,
    theoretical_deviation_results_updated.csv) used 25; numbers here are
    therefore ~2% larger than those legacy CSVs. The merged paper's
    intervention numbers (writeup/auction-v2-numbers.txt) already use 24.5.
  * b* per mechanism: FP(N=3): 2v/3; SP/SP-APV/AC/AC-B: v; TP(N=5): 4v/3;
    TP(N=3): 2v.  CV formats: profit-based deviation (|pi_win - pi*|/20,
    pi*_FP = 2eps/(N+1), pi*_SP = eps/(N+1)) exactly as
    scripts/plots/appendix2_temperature.py.
  * Direction classification is vs VALUE (not vs b*): under if b < v - tol,
    over if b > v + tol, equal otherwise. This matches the reading of the
    human Under/Equal/Over columns in plots/auction_human.csv (e.g. FPSB
    humans: 92.1% below value / 0.4% above value).
  * Clock formats: non-winners only (winner's recorded 'bid' is the closing
    price, not an intended exit).
  * Wasserstein-1 on d = (b - v)/E[v_scale] * 100 (percentage points of the
    truthful-bid scale); human synthetic reconstructions are on their source
    study's scale and are normalized by their own mean value.
  * Bootstrap CIs: percentile, 2000 reps, numpy seed 1299.

Baseline mapping for treatment-vs-baseline tests (column `baseline_id`):
  * temperature cells        -> same mechanism, gpt-4o T=0.5 anchor
                                (experiment_logs/V10).
  * risk-persona cells       -> same model's POOLED axis1/2/3 baselines
                                (axis*_baseline for SP from the combined ES
                                CSV; axis*_baseline_first/_third for FP/TP3
                                from recovered_logs V12). No risk-specific
                                baseline exists.
  * prospect-frame cells     -> the MORE SPECIFIC loss_aversion_baseline of
                                the same model & mechanism.
  * rule-explanation cells   -> explanation ON (= canonical V10 anchors);
                                OFF comes from the git tree
                                experiment_logs_without_explanation (commit
                                ce36a78b), results CSVs extracted to a local
                                cache directory (see WO_EXPL_DIR).
Tests: Welch t on |b - b*| (level) and two-proportion z on overbid-vs-value
share (direction).
"""

import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import wasserstein_distance

# ----------------------------------------------------------------------------
# Paths & constants
# ----------------------------------------------------------------------------
REPO = Path('/Users/kehangzh/Desktop/llm-auction')
V10 = REPO / 'experiment_logs/V10'
ROB = REPO / 'robustness_logs'
V12 = REPO / 'recovered_logs/experiment_logs_gpt_4o/V12'
COMBINED_CSV = (REPO / 'Engineering_simplicity/engineer_simplicity-main/results/'
                'all_experiments_combined_20260204_114522.csv')
MM_DIR = REPO / 'results/v12_interventions/moment_matching'
HUMAN_CSV = REPO / 'plots/auction_human.csv'
OUT_DIR = REPO / 'results/cardinal'
# Cache of `experiment_logs_without_explanation` (git commit ce36a78b),
# extracted with:
#   git ls-tree -r --name-only ce36a78b -- experiment_logs_without_explanation \
#     | grep -E "(results/.*_results\.csv|config\.yaml)$" \
#     | while read f; do git show "ce36a78b:$f" > <cache>/${f#experiment_logs_without_explanation/}; done
WO_EXPL_DIR = Path(os.environ.get(
    'WO_EXPL_DIR',
    '/private/tmp/claude-503/-Users-kehangzh-Desktop-llm-auction/'
    'e6af7b33-5c8d-4f65-ac39-dc081936377b/scratchpad/without_explanation'))

SEED = 1299
N_BOOT = 2000
NORM = 24.5          # E[b*] for truthful bidding, values Unif{0..49}
TOL_SEAL = 0.1       # = bid increment
TOL_CLOCK = 0.5      # = one clock cycle (matches scripts/plots/figure2_*.py)

# b*(v) per mechanism code
BSTAR = {
    'FP':     lambda v: 2.0 * v / 3.0,   # N=3 RNNE
    'SP':     lambda v: v,
    'TP5':    lambda v: 4.0 * v / 3.0,   # N=5 RNNE
    'TP3':    lambda v: 2.0 * v,         # N=3 RNNE
    'SP-APV': lambda v: v,
    'AC':     lambda v: v,               # exit at value
    'AC-B':   lambda v: v,
}
CLOCK_MECHS = {'AC', 'AC-B'}
CV_MECHS = {'CV-FP', 'CV-SP'}

# Canonical human targets: SMAD and direction shares (percent) from
# plots/auction_human.csv (validated at runtime below).
HUMAN = {
    'FP':     dict(smad=24.7639, under=92.1, equal=7.5, over=0.4,
                   src='Kagel-Levin 1993 FPSB (auction_human.csv)'),
    'SP':     dict(smad=5.646,  under=5.7,  equal=27.0, over=67.2,
                   src='SPSB IPV (auction_human.csv)'),
    'TP5':    dict(smad=7.6566, under=4.2,  equal=6.1,  over=89.8,
                   src='Kagel-Levin 1993 TPSB n=5 (auction_human.csv)'),
    # No human third-price N=3 exists; the KL93 n=5 numbers are the paper's
    # canonical target (deviation measured vs each environment's own RNNE).
    'TP3':    dict(smad=7.6566, under=4.2,  equal=6.1,  over=89.8,
                   src='Kagel-Levin 1993 TPSB n=5 (env mismatch: LLM N=3)'),
    'SP-APV': dict(smad=9.31,   under=10.0, equal=50.0, over=40.0,
                   src='Li 2017 SPSB (auction_human.csv)'),
    'AC':     dict(smad=3.54,   under=15.0, equal=67.0, over=18.0,
                   src='Li 2017 AC (auction_human.csv)'),
    'AC-B':   dict(smad=5.83,   under=16.0, equal=44.0, over=40.0,
                   src='Breitmoser 2022 AC-B (auction_human.csv)'),
    'CV-FP':  dict(smad=47.59,  under=None, equal=None, over=None,
                   src='First-Price CV (auction_human.csv, profit-based)'),
    'CV-SP':  dict(smad=18.23,  under=None, equal=None, over=None,
                   src='Second-Price CV (auction_human.csv, profit-based)'),
}

# Synthetic human reconstructions for Wasserstein-1 (value col, filter)
SYNTH_MAP = {
    'FP':     ('kagel_levin_1993_synthetic_bids.csv', 'value',
               lambda d: d[(d.auction_type == 'FPSB') & (d.n_bidders == 5)]),
    'SP':     ('gonczarowski_2022_synthetic_bids.csv', 'player_value',
               lambda d: d[d.treatment == 'Traditional']),
    'TP5':    ('kagel_levin_1993_synthetic_bids.csv', 'value',
               lambda d: d[(d.auction_type == 'TPSB') & (d.n_bidders == 5)]),
    'TP3':    ('kagel_levin_1993_synthetic_bids.csv', 'value',
               lambda d: d[(d.auction_type == 'TPSB') & (d.n_bidders == 5)]),
    'SP-APV': ('li_2017_osp_synthetic_bids.csv', 'player_value',
               lambda d: d[d.auction_type == '2P']),
    'AC':     ('li_2017_osp_synthetic_bids.csv', 'player_value',
               lambda d: d[d.auction_type == 'AC']),
    'AC-B':   ('breitmoser_2022_clock_synthetic_bids.csv', 'player_value',
               lambda d: d[d.auction_type == 'AC-DO']),  # clock, no dropout info
}

# ----------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------

def load_rundir(family_dir, merged_name=None):
    """Concatenate results/*_results.csv across run_* dirs (figure2 logic)."""
    family_dir = Path(family_dir)
    if merged_name:
        m = family_dir / merged_name
        if m.exists():
            return pd.read_csv(m)
    files = [f for f in glob.glob(str(family_dir / 'run_*/results/*_results.csv'))
             if 'merged' not in os.path.basename(f)]
    if not files:
        return None
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def load_cv_profit_devs(family_dir, price_order, n_agents=3):
    """Profit-based CV deviations (ports appendix2_temperature.py logic).

    Returns array of |actual_profit - theoretical_profit| for auction winners.
    pi*_FP = 2*eps/(N+1); pi*_SP = eps/(N+1); eps = winner_signal - common.
    """
    files = glob.glob(str(Path(family_dir) / 'run_*/raw_data/result_*.json'))
    devs = []
    for jf in files:
        with open(jf) as f:
            data = json.load(f)
        for rk, rd in data.items():
            if not rk.startswith('round_'):
                continue
            try:
                signals = rd['value']
                common = rd['common']
                profits = rd['profit']
                winner = rd['history']['winner']['winner']
                widx = None
                for idx, bi in enumerate(rd['history']['bidding history']):
                    if bi['agent'] == winner:
                        widx = idx
                        break
                if widx is None:
                    continue
                eps = signals[widx] - common
                pi_star = (2 * eps if price_order == 'first' else eps) / (n_agents + 1)
                devs.append(abs(profits[widx] - pi_star))
            except (KeyError, TypeError, IndexError):
                continue
    return np.array(devs) if devs else None


_synth_cache = {}

def load_synth(mech):
    if mech not in SYNTH_MAP:
        return None
    if mech in _synth_cache:
        return _synth_cache[mech]
    fname, vcol, filt = SYNTH_MAP[mech]
    df = filt(pd.read_csv(MM_DIR / fname))
    v = df[vcol].to_numpy(float)
    b = df['bid'].to_numpy(float)
    scaled_dev = 100.0 * (b - v) / v.mean()   # pp of that study's E[v] scale
    _synth_cache[mech] = (scaled_dev, f'{fname}:{len(df)} rows')
    return _synth_cache[mech]

# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------

def boot_ci(x, stat_fn, rng):
    idx = rng.integers(0, len(x), size=(N_BOOT, len(x)))
    reps = np.array([stat_fn(x[i]) for i in idx])
    return np.percentile(reps, [2.5, 97.5])


def cell_metrics(mech, values, bids, human, rng):
    """All metrics for a bid-level cell (non-CV)."""
    v = np.asarray(values, float)
    b = np.asarray(bids, float)
    n = len(b)
    bstar = BSTAR[mech](v)
    absdev = np.abs(b - bstar)
    smad = 100.0 * absdev.mean() / NORM
    lo, hi = boot_ci(absdev, lambda a: 100.0 * a.mean() / NORM, rng)
    tol = TOL_CLOCK if mech in CLOCK_MECHS else TOL_SEAL
    dv = b - v
    over = 100.0 * (dv > tol).mean()
    under = 100.0 * (dv < -tol).mean()
    equal = 100.0 - over - under
    n_dev = (np.abs(dv) > tol).sum()
    over_among_dev = (100.0 * (dv > tol).sum() / n_dev) if n_dev else np.nan
    over_vs_eq = 100.0 * ((b - bstar) > tol).mean()
    out = dict(
        n_bids=n, mean_dev_vs_value=dv.mean(), llm_smad=smad,
        llm_smad_lo=lo, llm_smad_hi=hi,
        llm_under_share=under, llm_equal_share=equal, llm_over_share=over,
        llm_over_among_deviators=over_among_dev,
        llm_over_vs_eq_share=over_vs_eq,
    )
    out['human_smad'] = human['smad']
    out['delta_smad'] = smad - human['smad']
    out['abs_delta_smad'] = abs(out['delta_smad'])
    if human['over'] is not None:
        out['human_over_share'] = human['over']
        out['dir_gap'] = abs(over - human['over'])
    else:
        out['human_over_share'] = np.nan
        out['dir_gap'] = np.nan
    synth = load_synth(mech)
    if synth is not None:
        sd_h, src = synth
        sd_l = 100.0 * dv / NORM
        out['wasserstein_pp'] = wasserstein_distance(sd_l, sd_h)
        out['synth_source'] = src
    else:
        out['wasserstein_pp'] = np.nan
        out['synth_source'] = 'NA'
    return out


def cv_cell_metrics(mech, devs, human, rng):
    smad = 100.0 * devs.mean() / 20.0     # fixed CV scaling (legacy convention)
    lo, hi = boot_ci(devs, lambda a: 100.0 * a.mean() / 20.0, rng)
    return dict(
        n_bids=len(devs), mean_dev_vs_value=np.nan, llm_smad=smad,
        llm_smad_lo=lo, llm_smad_hi=hi,
        llm_under_share=np.nan, llm_equal_share=np.nan, llm_over_share=np.nan,
        llm_over_among_deviators=np.nan, llm_over_vs_eq_share=np.nan,
        human_smad=human['smad'], delta_smad=smad - human['smad'],
        abs_delta_smad=abs(smad - human['smad']),
        human_over_share=np.nan, dir_gap=np.nan,
        wasserstein_pp=np.nan, synth_source='NA (CV: profit-based metric)',
    )


def welch_test(absdev_a, absdev_b):
    if absdev_a is None or absdev_b is None or len(absdev_a) < 2 or len(absdev_b) < 2:
        return np.nan
    return stats.ttest_ind(absdev_a, absdev_b, equal_var=False).pvalue


def two_prop_test(k1, n1, k2, n2):
    if min(n1, n2) == 0:
        return np.nan
    p = (k1 + k2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (k1 / n1 - k2 / n2) / se
    return 2 * (1 - stats.norm.cdf(abs(z)))

# ----------------------------------------------------------------------------
# Cell registry
# ----------------------------------------------------------------------------
# Each cell: id, knob, setting, model, mechanism + a loader spec.
# kind='rundir'  -> (dir, merged_name or None)
# kind='combined'-> experiment name(s) in the combined ES CSV for that model
# kind='cv'      -> (dir, 'first'/'second')

COMBINED_MODELS = {
    'gpt-4o': 'gpt-4o',
    'claude-3-5-haiku': 'claude-3-5-haiku-20241022',
    'gemini-2.0-flash': 'gemini-2.0-flash',
    'gemma-3-27b': 'google/gemma-3-27b-it',
}
AXIS_BASELINES_SP = ['axis1_contingent_baseline', 'axis2_forward_baseline',
                     'axis3_beliefs_baseline']

CELLS = []

def add(cid, knob, setting, model, mech, kind, spec, baseline_id, note=''):
    CELLS.append(dict(cell_id=cid, knob=knob, setting=setting, model=model,
                      mechanism=mech, kind=kind, spec=spec,
                      baseline_id=baseline_id, note=note))

# --- knob 0/1: anchors + temperature (gpt-4o) --------------------------------
TEMP_FAMS = {
    'FP': 'fpsb_ipv', 'SP': 'spsb_ipv', 'TP5': 'third_price_ipv',
    'TP3': 'third_price_ipv_3player', 'SP-APV': 'spsb_apv',
    'AC': 'ascending_clock_apv', 'AC-B': 'ascending_clock_apv_closed',
}
for mech, fam in TEMP_FAMS.items():
    merged = f'{fam}_merged_results.csv' if mech in CLOCK_MECHS else None
    add(f'gpt-4o|{mech}|T0.5', 'temperature', 'T=0.5 (anchor)', 'gpt-4o', mech,
        'rundir', (V10 / fam, merged), baseline_id=f'gpt-4o|{mech}|T0.5',
        note='canonical V10 anchor (= rule-explanation ON)')
    for tkey, tset in [('temp01', 'T=0.1'), ('temp10', 'T=1.0')]:
        # robustness dirs: <base>_gpt4o_<tkey>[_3player]
        rob_dir = (ROB / f'third_price_ipv_gpt4o_{tkey}_3player'
                   if mech == 'TP3' else ROB / f'{fam}_gpt4o_{tkey}')
        add(f'gpt-4o|{mech}|{tset}', 'temperature', tset, 'gpt-4o', mech,
            'rundir', (rob_dir, None),
            baseline_id=f'gpt-4o|{mech}|T0.5')
for mech, fam, po in [('CV-FP', 'common_value_first', 'first'),
                      ('CV-SP', 'common_value_second', 'second')]:
    add(f'gpt-4o|{mech}|T0.5', 'temperature', 'T=0.5 (anchor)', 'gpt-4o', mech,
        'cv', (V10 / fam, po), baseline_id=f'gpt-4o|{mech}|T0.5',
        note='profit-based CV metric')
    for tkey, tset in [('temp01', 'T=0.1'), ('temp10', 'T=1.0')]:
        add(f'gpt-4o|{mech}|{tset}', 'temperature', tset, 'gpt-4o', mech,
            'cv', (ROB / f'{fam}_gpt4o_{tkey}', po),
            baseline_id=f'gpt-4o|{mech}|T0.5', note='profit-based CV metric')

# --- knob 2: risk personas ----------------------------------------------------
# SP cells for all 4 models via combined CSV; baseline = pooled axis baselines.
for mkey, mname in COMBINED_MODELS.items():
    add(f'{mkey}|SP|axis_baseline_pooled', 'risk_persona',
        'baseline (axis-pooled)', mkey, 'SP', 'combined',
        (mname, AXIS_BASELINES_SP),
        baseline_id=f'{mkey}|SP|axis_baseline_pooled',
        note='pooled axis1/2/3 baselines (canonical intervention baseline)')
    for exp, setting in [('risk_averse', 'risk-averse'),
                         ('risk_neutrality', 'risk-neutral'),
                         ('risk_seeking', 'risk-seeking')]:
        add(f'{mkey}|SP|{exp}', 'risk_persona', setting, mkey, 'SP',
            'combined', (mname, [exp]),
            baseline_id=f'{mkey}|SP|axis_baseline_pooled')
# FP / TP3 gpt-4o via recovered V12 run dirs.
for mech, suf in [('FP', 'first'), ('TP3', 'third')]:
    add(f'gpt-4o|{mech}|axis_baseline_pooled', 'risk_persona',
        'baseline (axis-pooled)', 'gpt-4o', mech, 'rundir_multi',
        [V12 / f'axis{i}_{a}_baseline_{suf}' for i, a in
         [(1, 'contingent'), (2, 'forward'), (3, 'beliefs')]],
        baseline_id=f'gpt-4o|{mech}|axis_baseline_pooled',
        note='pooled axis1/2/3 baselines, recovered V12 (unconstrained-bid gen)')
    for exp, setting in [('intervention_risk_averse', 'risk-averse'),
                         ('intervention_risk_neutral', 'risk-neutral'),
                         ('intervention_risk_seeking', 'risk-seeking')]:
        add(f'gpt-4o|{mech}|{exp}', 'risk_persona', setting, 'gpt-4o', mech,
            'rundir', (V12 / f'{exp}_{suf}', None),
            baseline_id=f'gpt-4o|{mech}|axis_baseline_pooled')

# --- knob 3: prospect frames ---------------------------------------------------
FRAMES = [('loss_aversion_loss_frame', 'loss frame'),
          ('loss_aversion_gain_frame', 'gain frame'),
          ('loss_aversion_mixed_frame', 'mixed frame'),
          ('loss_aversion_endowment', 'endowment'),
          ('loss_aversion_WTA_WTP', 'WTA-WTP')]
for mkey, mname in COMBINED_MODELS.items():
    add(f'{mkey}|SP|loss_aversion_baseline', 'prospect_frame',
        'baseline (loss-aversion)', mkey, 'SP', 'combined',
        (mname, ['loss_aversion_baseline']),
        baseline_id=f'{mkey}|SP|loss_aversion_baseline',
        note='frame-specific baseline (more specific than axis baselines)')
    for exp, setting in FRAMES:
        add(f'{mkey}|SP|{exp}', 'prospect_frame', setting, mkey, 'SP',
            'combined', (mname, [exp]),
            baseline_id=f'{mkey}|SP|loss_aversion_baseline')
for mech, suf in [('FP', 'first'), ('TP3', 'third')]:
    add(f'gpt-4o|{mech}|loss_aversion_baseline', 'prospect_frame',
        'baseline (loss-aversion)', 'gpt-4o', mech, 'rundir',
        (V12 / f'loss_aversion_baseline_{suf}', None),
        baseline_id=f'gpt-4o|{mech}|loss_aversion_baseline')
    for exp, setting in FRAMES:
        add(f'gpt-4o|{mech}|{exp}', 'prospect_frame', setting, 'gpt-4o', mech,
            'rundir', (V12 / f'{exp}_{suf}', None),
            baseline_id=f'gpt-4o|{mech}|loss_aversion_baseline')

# --- knob 4: rule explanation ---------------------------------------------------
# ON = canonical V10 anchors (identical to recovered_logs/..._with_explanation);
# OFF = git tree experiment_logs_without_explanation (ce36a78b), sealed formats
# only. AC/AC-B runs are byte-identical across the trees -> no contrast (NA).
# CV: OFF has no raw_data JSONs in git -> NA.
WO_FAMS = {'FP': 'fpsb_ipv', 'SP': 'spsb_ipv', 'TP3': 'third_price_ipv',
           'SP-APV': 'spsb_apv'}
for mech, fam in WO_FAMS.items():
    on_dir = (REPO / 'recovered_logs/experiment_logs_with_explanation/V10' / fam
              if mech == 'TP3' else V10 / fam)
    on_note = ('explanation-ON TP is the Jan-12 N=3 run from '
               'recovered_logs/..._with_explanation (current V10 third_price is a newer N=5 run)'
               if mech == 'TP3' else '= V10 anchor')
    add(f'gpt-4o|{mech}|expl_on', 'rule_explanation', 'explanation ON',
        'gpt-4o', mech, 'rundir', (on_dir, None),
        baseline_id=f'gpt-4o|{mech}|expl_on', note=on_note)
    add(f'gpt-4o|{mech}|expl_off', 'rule_explanation', 'explanation OFF',
        'gpt-4o', mech, 'rundir', (WO_EXPL_DIR / 'V10' / fam, None),
        baseline_id=f'gpt-4o|{mech}|expl_on',
        note='git-recovered experiment_logs_without_explanation (ce36a78b)')

# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------

def validate_human_targets():
    h = pd.read_csv(HUMAN_CSV)
    h.columns = [c.strip() for c in h.columns]
    m = dict(zip(h['Auction'].str.strip(), h['SMAD']))
    checks = [('First-Price IPV', 'FP'), ('Second-Price IPV', 'SP'),
              ('Third-Price IPV', 'TP5'), ('SPSB (Li 2017)', 'SP-APV'),
              ('Ascending Clock (Li 2017)', 'AC'),
              ('AC-B (Breitmoser2022)', 'AC-B'),
              ('First-Price Common Value', 'CV-FP'),
              ('Second-Price Common Value', 'CV-SP')]
    for name, mech in checks:
        assert abs(m[name] - HUMAN[mech]['smad']) < 1e-6, \
            f'human SMAD mismatch for {mech}: {m[name]} vs {HUMAN[mech]["smad"]}'
    print('Human targets validated against plots/auction_human.csv')


def main():
    validate_human_targets()
    combined = pd.read_csv(COMBINED_CSV)
    rows = []
    raw_store = {}   # cell_id -> dict(absdev=..., k_over=..., n=...)

    for cell in CELLS:
        rng = np.random.default_rng(SEED)   # per-cell seed: fully reproducible
        mech = cell['mechanism']
        human = HUMAN[mech]
        note = cell['note']
        df = None
        if cell['kind'] == 'rundir':
            d, merged = cell['spec']
            df = load_rundir(d, merged)
        elif cell['kind'] == 'rundir_multi':
            parts = [load_rundir(d) for d in cell['spec']]
            parts = [p for p in parts if p is not None]
            df = pd.concat(parts, ignore_index=True) if parts else None
        elif cell['kind'] == 'combined':
            mname, exps = cell['spec']
            df = combined[(combined.model == mname)
                          & (combined.experiment.isin(exps))]
            if len(df) == 0:
                df = None
        elif cell['kind'] == 'cv':
            d, po = cell['spec']
            devs = load_cv_profit_devs(d, po)
            if devs is None or len(devs) == 0:
                rows.append({**base_cols(cell), 'n_bids': 0,
                             'status': 'NA: no result JSONs found',
                             'human_smad': human['smad']})
                continue
            met = cv_cell_metrics(mech, devs, human, rng)
            raw_store[cell['cell_id']] = dict(absdev=devs, k_over=None, n=len(devs))
            rows.append({**base_cols(cell), **met, 'status': 'ok'})
            continue

        if df is None or len(df) == 0:
            rows.append({**base_cols(cell), 'n_bids': 0,
                         'status': 'NA: no data found', 'human_smad': human['smad']})
            continue
        if mech in CLOCK_MECHS:
            df = df[~df['is_winner']]
            if len(df) == 0:
                rows.append({**base_cols(cell), 'n_bids': 0,
                             'status': 'NA: no non-winner exits',
                             'human_smad': human['smad']})
                continue
        # sanity: verify model/temperature columns where present
        if 'model' in df.columns:
            mods = set(df['model'].unique())
            assert len(mods) == 1, f'{cell["cell_id"]}: mixed models {mods}'
        v = df['player_value'].to_numpy(float)
        b = df['bid'].to_numpy(float)
        met = cell_metrics(mech, v, b, human, rng)
        tol = TOL_CLOCK if mech in CLOCK_MECHS else TOL_SEAL
        raw_store[cell['cell_id']] = dict(
            absdev=np.abs(b - BSTAR[mech](v)),
            k_over=int(((b - v) > tol).sum()), n=len(b))
        rows.append({**base_cols(cell), **met, 'status': 'ok'})

    grid = pd.DataFrame(rows)

    # treatment-vs-baseline tests
    pvals_lvl, pvals_dir, d_smad_base = [], [], []
    for _, r in grid.iterrows():
        bid_ = r['baseline_id']
        if (r['status'] != 'ok' or bid_ == r['cell_id']
                or bid_ not in raw_store or r['cell_id'] not in raw_store):
            pvals_lvl.append(np.nan); pvals_dir.append(np.nan)
            d_smad_base.append(np.nan)
            continue
        a, base = raw_store[r['cell_id']], raw_store[bid_]
        pvals_lvl.append(welch_test(a['absdev'], base['absdev']))
        if a['k_over'] is None or base['k_over'] is None:
            pvals_dir.append(np.nan)
        else:
            pvals_dir.append(two_prop_test(a['k_over'], a['n'],
                                           base['k_over'], base['n']))
        brow = grid[grid.cell_id == bid_].iloc[0]
        d_smad_base.append(r['llm_smad'] - brow['llm_smad'])
    grid['smad_minus_baseline'] = d_smad_base
    grid['p_level_vs_baseline'] = pvals_lvl
    grid['p_dir_vs_baseline'] = pvals_dir

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / 'cardinal_grid.csv'
    grid.to_csv(out, index=False, float_format='%.4f')
    print(f'wrote {out} ({len(grid)} rows)')

    # ------------------------------------------------------------------
    # Ranking: which setting best closes each gap, per mechanism (gpt-4o)
    # ------------------------------------------------------------------
    g4 = grid[(grid.model == 'gpt-4o') & (grid.status == 'ok')].copy()
    core = ['FP', 'SP', 'TP3']   # mechanisms where EVERY knob has data
    print('\n===== per-mechanism ranking, gpt-4o (all mechanisms) =====')
    for metric in ['abs_delta_smad', 'dir_gap', 'wasserstein_pp']:
        print(f'\n--- {metric} (lower = closer to humans) ---')
        for mech in ['FP', 'SP', 'TP5', 'TP3', 'SP-APV', 'AC', 'AC-B',
                     'CV-FP', 'CV-SP']:
            sub = g4[(g4.mechanism == mech) & g4[metric].notna()]
            if len(sub) == 0:
                continue
            sub = sub.sort_values(metric)
            top = sub.iloc[0]
            print(f'{mech:7s} best: {top.knob}/{top.setting:24s} '
                  f'{metric}={top[metric]:7.2f} (llm_smad={top.llm_smad:6.2f}, '
                  f'human={top.human_smad:5.2f}, n={int(top.n_bids)})')

    print('\n===== worst-case-rank analysis on core mechanisms (FP, SP, TP3) =====')
    sub = g4[g4.mechanism.isin(core)].copy()
    sub['setting_id'] = sub.knob + '/' + sub.setting
    for metric in ['abs_delta_smad', 'dir_gap']:
        piv = sub.pivot_table(index='setting_id', columns='mechanism',
                              values=metric)
        piv = piv.dropna()   # settings with data on all three core mechanisms
        ranks = piv.rank(axis=0)
        piv['worst_rank'] = ranks.max(axis=1)
        piv['mean_rank'] = ranks.mean(axis=1)
        piv = piv.sort_values(['worst_rank', 'mean_rank'])
        print(f'\n--- {metric}: value per mechanism + ranks '
              f'(1 = closest to human; {len(piv)} settings) ---')
        print(piv.round(2).to_string())
        piv.round(4).to_csv(OUT_DIR / f'rank_core_{metric}.csv')
    print(f'\nAlso wrote {OUT_DIR}/rank_core_*.csv')


def base_cols(cell):
    return dict(cell_id=cell['cell_id'], knob=cell['knob'],
                setting=cell['setting'], model=cell['model'],
                mechanism=cell['mechanism'],
                baseline_id=cell['baseline_id'], note=cell['note'],
                source=str(cell['spec']))


if __name__ == '__main__':
    main()

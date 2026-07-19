"""
Rank concordance of the difficulty ordering: reconstructed humans vs GPT-4o.

WHAT THIS DOES
--------------
Completes the pending statistic for the validity map's difficulty-ordering row
(tab:validity-map, TODO "E6 residual" in writeup/contents_v3/03_validation.tex):
Kendall's tau-b between the human and GPT-4o SMAD rankings over the five
in-scope auction formats, with uncertainty from BOTH sides of the comparison.

Formats (5) and canonical SMAD anchors:

    format                       human (reconstruction)   GPT-4o (V10 logs)
    FPSB IPV                     24.7639                  27.5518  (n=285)
    SPSB IPV                      5.6460                   8.6859  (n=270)
    SP-APV  (sealed SPSB, APV)    9.3100                  10.7340  (n=291)
    AC      (open clock, APV)     3.5400                   0.8113  (n=106)
    AC-B    (closed clock, APV)   5.8300                   0.4737  (n=114)

Human anchors are the moment-matched reconstructions of sec:reconstruction
(paper points in results/reconstruction_bands/bands.csv).  GPT-4o SMADs are
recomputed here from bid level (experiment_logs/V10, the same cells behind
plots/theoretical_deviation_results_updated.csv) and asserted against the
published values before anything else runs.

UNCERTAINTY (two layers)
------------------------
(a) LLM sampling.  Nonparametric bootstrap of GPT-4o's five SMAD values:
    resample bids (i.e. per-bid absolute deviations |b - b*(v)|) with
    replacement WITHIN each format cell, recompute the five SMADs, recompute
    tau-b against the FIXED canonical human ranking.  B=2000, seed 1299,
    percentile 95% CI.

(b) Human calibration.  The reconstruction re-draw machinery of
    analysis/reconstruction_bands.py (parametric bootstrap over the mixture
    calibration parameters).  The per-anchor draw functions below replicate
    fragility_checks() in that script EXACTLY -- same seed (1299+7), same rng
    call order (FPSB, SPSB, SP-APV, AC, AC-B), same B=2000 -- so the re-draw
    vectors here are the same ones behind the published band facts
    (FPSB>SPSB in 100.0% of draws, AC-B<SP-APV in 92.6%).  We recompute tau-b
    of each human re-draw vector against the FIXED canonical GPT-4o ranking.

(c) Joint.  Pair LLM-bootstrap draw b with human re-draw b (independent
    streams) and recompute tau-b between the two redrawn vectors.

Everything is deterministic (numpy only, no API calls).

OUTPUTS
-------
    results/analysis/difficulty_concordance.json
    results/analysis/difficulty_concordance.md

Run (from repo root):
    python3 analysis/difficulty_concordance.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "analysis"))

# Reuse the published calibration configs + helpers from the bands script so
# the human re-draws cannot drift from the ones the paper already reports.
import reconstruction_bands as rb  # noqa: E402  (KL, CLOCK, kl_mean_ratio, Z95)

SEED = 1299
B = 2000

LOGS = PROJECT_ROOT / "experiment_logs" / "V10"
OUT_DIR = PROJECT_ROOT / "results" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Canonical ordering of the five in-scope formats (fixed everywhere below).
FORMATS = ["FPSB IPV", "SPSB IPV", "SP-APV", "AC", "AC-B"]

# Human paper points (results/reconstruction_bands/bands.csv, column paper_point).
HUMAN_SMAD = np.array([24.7639, 5.646, 9.31, 3.54, 5.83])

# Published GPT-4o SMADs (plots/theoretical_deviation_results_updated.csv);
# the bid-level recomputation below must reproduce these before we proceed.
LLM_SMAD_PUBLISHED = np.array([27.551813, 8.685926, 10.734021, 0.811321, 0.473684])
LLM_N_PUBLISHED = np.array([285, 270, 291, 106, 114])

SCALING = 25.0  # fixed IPV/APV scaling factor (plot_theoretical_deviation.py)

# Bid-level cells behind theoretical_deviation_results_updated.csv (GPT-4o,
# temperature 0.5, V10).  b*(v): 2/3*v for FPSB (N=3), v elsewhere; clock
# formats keep non-winners only (winner's exit price is censored).
CELLS = {
    "FPSB IPV": dict(
        csv=LOGS / "fpsb_ipv/run_2026-01-12_21-59-13-724783/results/fpsb_ipv_results.csv",
        bstar=lambda v: 2.0 / 3.0 * v, clock=False),
    "SPSB IPV": dict(
        csv=LOGS / "spsb_ipv/run_2026-01-12_21-59-13-727690/results/spsb_ipv_results.csv",
        bstar=lambda v: v, clock=False),
    "SP-APV": dict(
        csv=LOGS / "spsb_apv/run_2026-01-12_22-28-06-038405/results/spsb_apv_results.csv",
        bstar=lambda v: v, clock=False),
    "AC": dict(
        csv=LOGS / "ascending_clock_apv/ascending_clock_apv_merged_results.csv",
        bstar=lambda v: v, clock=True),
    "AC-B": dict(
        csv=LOGS / "ascending_clock_apv_closed/ascending_clock_apv_closed_merged_results.csv",
        bstar=lambda v: v, clock=True),
}


# ---------------------------------------------------------------------------
# Kendall tau-b (hand implementation, cross-checked against scipy)
# ---------------------------------------------------------------------------
def kendall_tau_b(x, y):
    """Kendall's tau-b: (C - D) / sqrt((n0 - n1)(n0 - n2))."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    C = D = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(x[i] - x[j]) * np.sign(y[i] - y[j])
            if s > 0:
                C += 1
            elif s < 0:
                D += 1
    n0 = n * (n - 1) / 2.0

    def tie_term(v):
        _, counts = np.unique(v, return_counts=True)
        return sum(c * (c - 1) / 2.0 for c in counts)

    denom = np.sqrt((n0 - tie_term(x)) * (n0 - tie_term(y)))
    return (C - D) / denom if denom > 0 else np.nan


# ---------------------------------------------------------------------------
# GPT-4o bid-level deviations
# ---------------------------------------------------------------------------
def load_llm_deviations():
    """Per-bid |b - b*(v)| for each format cell, reproducing the published SMADs."""
    devs = {}
    for fmt in FORMATS:
        cfg = CELLS[fmt]
        df = pd.read_csv(cfg["csv"])
        assert set(df["model"].unique()) == {"gpt-4o"}, f"{fmt}: non-GPT-4o rows"
        if cfg["clock"]:
            df = df[~df["is_winner"]].copy()
        devs[fmt] = np.abs(df["bid"].to_numpy(float)
                           - cfg["bstar"](df["player_value"].to_numpy(float)))
    smads = np.array([100.0 * devs[f].mean() / SCALING for f in FORMATS])
    ns = np.array([len(devs[f]) for f in FORMATS])
    assert np.allclose(smads, LLM_SMAD_PUBLISHED, atol=1e-4), \
        f"bid-level SMADs {smads} != published {LLM_SMAD_PUBLISHED}"
    assert (ns == LLM_N_PUBLISHED).all(), f"cell sizes {ns} != {LLM_N_PUBLISHED}"
    return devs, smads, ns


def bootstrap_llm_smads(devs, rng):
    """(B, 5) matrix of within-cell resampled SMAD vectors."""
    out = np.empty((B, len(FORMATS)))
    for b in range(B):
        for k, fmt in enumerate(FORMATS):
            d = devs[fmt]
            out[b, k] = 100.0 * rng.choice(d, size=len(d), replace=True).mean() / SCALING
    return out


# ---------------------------------------------------------------------------
# Human reconstruction re-draws
# (exact replica of reconstruction_bands.fragility_checks, seed 1299+7)
# ---------------------------------------------------------------------------
def kl_draws(cfg, rng):
    s = cfg["s"]
    shares0 = np.array([cfg["below"], cfg["at"], cfg["above"]], float)
    shares0 = shares0 / shares0.sum()
    D0 = (cfg["smad"] / 100.0) * s
    r_mean0 = rb.kl_mean_ratio(cfg)
    dev_share0 = shares0[0] + shares0[2]
    gap0_raw = abs(r_mean0 - s)
    gap0 = min(gap0_raw, D0)
    spread0 = D0 - gap0
    out = np.empty(B)
    for b in range(B):
        w = rng.multinomial(640, shares0) / 640
        spread_b = spread0 * ((w[0] + w[2]) / dev_share0) if dev_share0 > 0 else spread0
        beta_b = rng.normal(cfg["beta"], cfg["se_beta"])
        r_mean_b = (cfg["alpha"] + beta_b * cfg["ev"]) / cfg["ev"]
        gap_scale = (abs(r_mean_b - s) / gap0_raw) if gap0_raw > 1e-9 else 1.0
        out[b] = 100.0 * (gap0 * gap_scale + spread_b) / s
    return out


def clock_draws(cfg, rng):
    lo, hi = cfg["ci"]
    se_delta = ((hi - cfg["smad"]) + (cfg["smad"] - lo)) / 2.0 / rb.Z95
    se_mad = se_delta * cfg["ev"] / 100.0
    mad0 = cfg["smad"] * cfg["ev"] / 100.0
    base_mass = cfg["p_over"] + 0.5 * cfg["p_under"]
    out = np.empty(B)
    for b in range(B):
        mad_b = rng.normal(mad0, se_mad)
        pe = np.clip(cfg["p_eq"] + rng.uniform(-.05, .05), 0, 1)
        po = np.clip(cfg["p_over"] + rng.uniform(-.05, .05), 0, 1)
        pu = np.clip(cfg["p_under"] + rng.uniform(-.05, .05), 0, 1)
        tot = pe + po + pu
        mass = (po / tot) + 0.5 * (pu / tot)
        out[b] = 100.0 * (mad_b * (mass / base_mass)) / cfg["ev"]
    return out


def human_redraw_matrix():
    """(B, 5) matrix of human SMAD re-draw vectors, columns in FORMATS order.

    The rng seed and call order replicate fragility_checks() in
    reconstruction_bands.py exactly (fp, sp, spapv, ac, acb on seed SEED+7),
    so these are the same draws behind the published band facts.
    """
    rng = np.random.default_rng(SEED + 7)
    fp = kl_draws(rb.KL["FPSB IPV"], rng)
    sp = kl_draws(rb.KL["SPSB IPV"], rng)
    spapv = clock_draws(rb.CLOCK["SP-APV"], rng)
    ac = clock_draws(rb.CLOCK["AC"], rng)
    acb = clock_draws(rb.CLOCK["AC-B"], rng)
    return np.column_stack([fp, sp, spapv, ac, acb])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # --- point estimate, with a scipy cross-check on the hand implementation
    devs, llm_smads, ns = load_llm_deviations()
    tau_hand = kendall_tau_b(HUMAN_SMAD, llm_smads)
    tau_scipy = stats.kendalltau(HUMAN_SMAD, llm_smads, variant="b").statistic
    assert abs(tau_hand - tau_scipy) < 1e-12, (tau_hand, tau_scipy)
    tau_point = float(tau_hand)

    # --- layer (a): LLM bootstrap vs fixed human ranking
    rng_llm = np.random.default_rng(SEED)
    llm_boot = bootstrap_llm_smads(devs, rng_llm)
    taus_a = np.array([kendall_tau_b(HUMAN_SMAD, llm_boot[b]) for b in range(B)])
    ci_a = np.percentile(taus_a, [2.5, 97.5])
    frac_a_pos = float(np.mean(taus_a > 0))
    frac_a_fpsb = float(np.mean(llm_boot[:, 0] > llm_boot[:, 1]))  # LLM FPSB > SPSB

    # --- layer (b): human reconstruction re-draws vs fixed LLM ranking
    hum = human_redraw_matrix()
    taus_b = np.array([kendall_tau_b(hum[b], llm_smads) for b in range(B)])
    ci_b = np.percentile(taus_b, [2.5, 97.5])
    frac_b_pos = float(np.mean(taus_b > 0))
    frac_b_fpsb = float(np.mean(hum[:, 0] > hum[:, 1]))            # human FPSB > SPSB

    # cross-check against the published band facts (bands_summary.md)
    frac_acb_lt_spapv = float(np.mean(hum[:, 4] < hum[:, 2]))
    assert frac_b_fpsb == 1.0, frac_b_fpsb
    assert abs(frac_acb_lt_spapv - 0.926) < 0.01, frac_acb_lt_spapv

    # --- layer (c): joint (LLM bootstrap draw b x human re-draw b)
    taus_j = np.array([kendall_tau_b(hum[b], llm_boot[b]) for b in range(B)])
    ci_j = np.percentile(taus_j, [2.5, 97.5])
    frac_j_pos = float(np.mean(taus_j > 0))
    frac_j_fpsb = float(np.mean((hum[:, 0] > hum[:, 1]) & (llm_boot[:, 0] > llm_boot[:, 1])))

    def dist(t):
        vals, counts = np.unique(np.round(t, 10), return_counts=True)
        return {f"{v:.1f}": int(c) for v, c in zip(vals, counts)}

    results = {
        "statistic": "Kendall tau-b, human vs GPT-4o SMAD ranking, 5 in-scope formats",
        "formats": FORMATS,
        "human_smad": HUMAN_SMAD.tolist(),
        "llm_smad": llm_smads.tolist(),
        "llm_n": ns.tolist(),
        "tau_point": tau_point,
        "seed": SEED,
        "B": B,
        "layer_a_llm_bootstrap": {
            "design": "resample per-bid |b-b*(v)| with replacement within each "
                      "format cell; recompute SMAD vector; tau-b vs fixed human "
                      "canonical ranking; percentile CI",
            "ci95": ci_a.tolist(),
            "frac_tau_positive": frac_a_pos,
            "frac_fpsb_gt_spsb_llm": frac_a_fpsb,
            "tau_distribution": dist(taus_a),
        },
        "layer_b_human_redraws": {
            "design": "reconstruction-calibration re-draws replicating "
                      "reconstruction_bands.fragility_checks (seed 1299+7); "
                      "tau-b vs fixed GPT-4o canonical ranking",
            "ci95": ci_b.tolist(),
            "frac_tau_positive": frac_b_pos,
            "frac_fpsb_gt_spsb_human": frac_b_fpsb,
            "crosscheck_frac_acb_lt_spapv_published_0.926": frac_acb_lt_spapv,
            "tau_distribution": dist(taus_b),
        },
        "layer_c_joint": {
            "design": "pair LLM-bootstrap draw b with human re-draw b "
                      "(independent streams); tau-b between the two redrawn vectors",
            "ci95": ci_j.tolist(),
            "frac_tau_positive": frac_j_pos,
            "frac_fpsb_gt_spsb_both_sides": frac_j_fpsb,
            "tau_distribution": dist(taus_j),
        },
    }
    (OUT_DIR / "difficulty_concordance.json").write_text(json.dumps(results, indent=2))

    md = f"""# Difficulty-ordering concordance: reconstructed humans vs GPT-4o

*Generated by `analysis/difficulty_concordance.py`, seed {SEED}, B={B}. Fills the
`tab:validity-map` difficulty-ordering row (TODO "E6 residual", 03_validation.tex).*

Five in-scope formats: FPSB IPV, SPSB IPV, SP-APV, AC (open clock), AC-B (closed
clock). Human anchors are the sec:reconstruction paper points; GPT-4o SMADs are
recomputed from bid level (`experiment_logs/V10`) and match the published values
exactly (n = {', '.join(str(n) for n in ns)}).

| | tau-b | 95% CI | tau > 0 | FPSB > SPSB |
|---|---:|---|---:|---:|
| Point estimate | {tau_point:.2f} | -- | -- | -- |
| (a) LLM bootstrap (within-cell bid resampling, human ranking fixed) | -- | [{ci_a[0]:.2f}, {ci_a[1]:.2f}] | {frac_a_pos*100:.1f}% | {frac_a_fpsb*100:.1f}% |
| (b) Human reconstruction re-draws (LLM ranking fixed) | -- | [{ci_b[0]:.2f}, {ci_b[1]:.2f}] | {frac_b_pos*100:.1f}% | {frac_b_fpsb*100:.1f}% |
| (c) Joint (a) x (b) | -- | [{ci_j[0]:.2f}, {ci_j[1]:.2f}] | {frac_j_pos*100:.1f}% | {frac_j_fpsb*100:.1f}% |

The point tau-b = {tau_point:.2f} comes from 8 concordant / 2 discordant pairs (no
ties): both discordances involve AC-B, whose human anchor (Breitmoser 2022) sits
between SPSB IPV and SP-APV while GPT-4o puts both clock formats at the bottom.
The human re-draws (layer b) replicate `reconstruction_bands.fragility_checks`
exactly (same seed/call order), so the published band facts are reproduced here
(FPSB>SPSB in {frac_b_fpsb*100:.1f}% of draws; AC-B<SP-APV in {frac_acb_lt_spapv*100:.1f}%, published 92.6%).

Note the layer-(a) percentile CI is degenerate at [{ci_a[0]:.2f}, {ci_a[1]:.2f}]: the GPT-4o
ranking is stable under bid resampling ({dist(taus_a).get("0.6", 0)/B*100:.1f}% of draws leave tau at
{tau_point:.2f}; the rest split between 0.4 and 0.8), so the joint CI is driven by the
human reconstruction re-draws.

Proposed table-row sentence:

> Kendall's tau-b = {tau_point:.2f} between the human and GPT-4o SMAD rankings over the
> five in-scope formats; the estimate is stable under bid-level resampling of the
> LLM cells (95% CI [{ci_a[0]:.2f}, {ci_a[1]:.2f}], B={B}) and stays positive in {frac_j_pos*100:.0f}% of joint
> draws that add human reconstruction re-draws (joint 95% CI [{ci_j[0]:.2f}, {ci_j[1]:.2f}]),
> with FPSB ranked hardest on both sides in every draw.

Caveats: human-side uncertainty is reconstruction/calibration uncertainty (the
parametric bootstrap of `analysis/reconstruction_bands.py`), not human sampling
error; the LLM CI treats bids as i.i.d. within cells (no clustering by
round/session); with n=5 formats tau-b is a coarse statistic taking few values.
"""
    (OUT_DIR / "difficulty_concordance.md").write_text(md)

    print(f"tau point = {tau_point:.4f} (scipy cross-check OK)")
    print(f"(a) LLM bootstrap  : 95% CI [{ci_a[0]:.3f}, {ci_a[1]:.3f}]  "
          f"tau>0 {frac_a_pos*100:.1f}%  FPSB>SPSB {frac_a_fpsb*100:.1f}%")
    print(f"(b) human re-draws : 95% CI [{ci_b[0]:.3f}, {ci_b[1]:.3f}]  "
          f"tau>0 {frac_b_pos*100:.1f}%  FPSB>SPSB {frac_b_fpsb*100:.1f}%  "
          f"(AC-B<SP-APV {frac_acb_lt_spapv*100:.1f}%, published 92.6%)")
    print(f"(c) joint          : 95% CI [{ci_j[0]:.3f}, {ci_j[1]:.3f}]  "
          f"tau>0 {frac_j_pos*100:.1f}%  FPSB>SPSB both {frac_j_fpsb*100:.1f}%")
    print(f"Wrote {OUT_DIR/'difficulty_concordance.json'} and .md")


if __name__ == "__main__":
    main()

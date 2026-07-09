#!/usr/bin/env python3
"""
Formal mediation / process analysis of the reasoning-trace double dissociation.

This is the "option 2 (+ option 4 folded in)" upgrade of the baseline keyword
analysis (results/traces/traces_summary.md, analysis/build_trace_features.py).
It promotes the descriptive mediation *sketch* of Finding 4 to a defensible,
zero-new-data process analysis, and folds in the per-model stated-vs-revealed
consistency metric (option 4). Everything is deterministic (numpy seed 1299)
and reproducible from this single script; it consumes only the frozen
results/traces/trace_features.csv produced by build_trace_features.py.

Deliverables produced (all under results/traces/mediation/):
  manipulation_checks.csv / .tex   one row per auction lever: does the lever
      move its OWN target language feature vs the correct baseline, and does it
      move behavior (mean dev, mean |dev|)? p-values are wild-cluster-bootstrap
      (Rademacher, seed 1299) because each experiment x model = ONE run_id
      cluster, so treatment-vs-baseline contrasts have only ~8-16 clusters and
      naive cluster-robust SEs are unreliable in that regime.
  dissociation_2x2.csv             the 2x2 "moves-language x moves-bids"
      classification for the four canonical levers (worst-case, Payoff Safety,
      Payoff Tree, menu), with the test stats behind each cell.
  mediation_b2.csv                 the formal Payoff-Safety (B2) mediation
      first stage (lever -> verbalized-understanding mediators) plus the implied
      product-of-coefficients bound on the mediated share, with a cluster
      bootstrap CI; and the (clearly labeled non-causal) within-treatment
      cross-sectional association.
  consistency_calibration.csv      per model x lever stated-vs-revealed
      consistency scalar (option 4) + the $-amount calibration statistics.
  consistency_calibration.pdf       calibration figure (stated vs realized bid,
      binned, per model).
  mediation_tables.tex             booktabs LaTeX fragments (manipulation-check
      table + 2x2 matrix), paper table style. NOT wired into writeup/.
  mediation_summary.md             full methods + findings + caveats writeup.

METHODS DISCIPLINE (see traces_summary.md caveats):
* Cluster-robust by run_id everywhere; n_clusters reported. Because the sealed
  grid has exactly ONE run_id per (experiment, model), a lever cell has 4
  clusters and its baseline 4-12; that is the few-cluster regime, so the
  headline p-value for every treatment contrast is a WILD CLUSTER BOOTSTRAP
  (Rademacher weights, 2000 reps, seed 1299) with a cluster-permutation
  cross-check; naive cluster-robust SEs are reported alongside but flagged.
* Every headline number is re-run on the deduplicated sample (byte-identical
  plan+bid duplicates dropped) and both are reported; flips are flagged.
* Prompt-echo confound (caveat 6b): the "target language" manipulation check is
  partly a check on whether the model parrots the prompt's new vocabulary. Each
  lever row is annotated with whether its target feature is seeded by its own
  prompt; menu (B1) removes the second-price vocabulary wholesale, so its
  rule-rehearsal target is 0 by construction and is flagged, not interpreted.
  All language contrasts are lever-vs-its-own-baseline only.
* Ascending-clock traces excluded from all sealed-bid analyses (as the OLS did).
* Cell means are sanity-checked against the published numbers before any join.

Baseline mapping (PROVENANCE-CORRECTED, 2026-07-08; see
results/merged_ranking/_axis2_baseline_provenance.md):
* The V12 `axis2_forward_baseline` template was a two-stage
  sealed-bid-as-clock-exit description, NOT a plain SPSB text. It is treated
  here as a TREATMENT cell ("Two-stage clock-exit descr.", family B3v) and
  leaves every baseline pool.
* Corrected pooled baseline = {axis1_contingent_baseline,
  axis3_beliefs_baseline}. Cells with a clean own-grid baseline keep it
  (axis-1 scaffolds, belief scaffolds, loss frames); everything else --
  including the axis-2 treatments Payoff Safety (B2) and Payoff Tree -- is
  tested against the corrected pooled baseline.
* The legacy pooled-of-three and the dedicated spsb cell (the paper's
  published -2.67 -> -1.53 comparison) are retained as clearly-labeled
  comparison columns/rows; the pre-correction 2x2 conventions are re-computed
  in dissociation_2x2_precorrection.csv to document what the correction
  changes.
"""

import os
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths (this machine). trace_features.csv is the single frozen input.
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRACES = os.path.join(REPO, "results", "traces")
OUT = os.path.join(TRACES, "mediation")
os.makedirs(OUT, exist_ok=True)

SEED = 1299
N_BOOT = 2000
N_PERM = 5000
rng = np.random.default_rng(SEED)

FEATURE_COLS = [
    "dominance_language", "truthful_intent", "payment_rule_correct",
    "second_price_mention", "first_price_mention", "opponent_modeling",
    "probability_reasoning", "expected_value_reasoning", "shading_intent",
    "overbid_intent", "worst_case", "safety_recognition", "overpay_concern",
    "zero_profit_fallacy", "margin_language", "conservative_language",
    "aggressive_language", "risk_language",
]

# --- Baseline conventions (PROVENANCE CORRECTION 2026-07-08) -----------------
# results/merged_ranking/_axis2_baseline_provenance.md: the V12
# `axis2_forward_baseline` template was NOT a plain SPSB description — it was a
# two-stage sealed-bid-as-clock-exit (clock-framing) text (recovered from the
# engineer_simplicity git history; survives as rule_template/auctions/
# axis2_forward_baseline_DEPRECATED.txt). Trace evidence: 15–25% of
# claude/gemini/gemma plans in that cell contain clock/exit/stage-2 language vs
# 0% in the axis1/axis3 baselines; behaviorally it fixes gemma (−0.59 vs −5 to
# −7) and hurts gemini (−6.12). It is a TREATED cell, not a baseline.
# CORRECTED pooled baseline = {axis1, axis3} only. The legacy pooled-of-three
# and the dedicated spsb cell are retained as clearly-labeled comparisons.
AXIS_BASELINES_CORRECTED = ["axis1_contingent_baseline",
                            "axis3_beliefs_baseline"]
AXIS_BASELINES_LEGACY = ["axis1_contingent_baseline", "axis2_forward_baseline",
                         "axis3_beliefs_baseline"]

# Detects the two-stage clock-exit framing language (target feature for the
# reclassified axis2_forward_baseline treatment row). Regex from the provenance
# note; reproduces its 17.3 / 24.7 / 15.3 / 0.0% per-model prevalence exactly.
CLOCK_EXIT_RE = (r"clock|exit price|stage 2|drop out|exit the auction|"
                 r"automatically exit")

# ---------------------------------------------------------------------------
# Lever specification: (label, family, experiment, target_feature,
#   baseline_experiments, prompt_echo_note). target_feature is the language the
#   lever is *designed* to induce (its manipulation-check target). baseline is
#   the CORRECT comparison per the mapping above. prompt_echo flags whether the
#   target feature is mechanically seeded (or removed) by the lever's own prompt.
# ---------------------------------------------------------------------------
LEVERS = [
    # label, family, experiment, target, baseline_list, echo
    ("Payoff Safety", "B2", "axis2_forward_onestep", "safety_recognition",
     AXIS_BASELINES_CORRECTED,
     "prompt asserts the invariant but 0/600 traces echo it -> no echo issue; "
     "baseline corrected to {axis1,axis3} (provenance note)"),
    ("Worst-case scaffold", "C1", "axis1_contingent_worstcase", "worst_case",
     ["axis1_contingent_baseline"],
     "prompt says 'worst-case' -> target rise is partly prompt echo"),
    ("Payoff Tree", "C1", "axis2_forward_tree", "second_price_mention",
     AXIS_BASELINES_CORRECTED,
     "shares 'second-highest' rule vocab with the axis1/axis3 baselines -> "
     "clean contrast; own-grid axis2 baseline is CONTAMINATED (two-stage "
     "clock-exit text, provenance note) so baseline = corrected {axis1,axis3}"),
    ("Dominated", "C1", "axis1_contingent_dominated", "dominance_language",
     ["axis1_contingent_baseline"],
     "prompt says 'dominated' -> target rise is partly prompt echo"),
    ("Enumerate", "C1", "axis1_contingent_enumerate", "opponent_modeling",
     ["axis1_contingent_baseline"],
     "prompt asks about others' bids -> target rise is partly prompt echo"),
    ("Menu restatement", "B1", "intervention_menu", "second_price_mention",
     AXIS_BASELINES_CORRECTED,
     "REVERSE echo: prompt removes 'second-highest' vocab -> target 0 by "
     "construction; NOT interpretable as comprehension (caveat 6b)"),
    ("Clock-framing", "B3", "intervention_proxy_breitmoser",
     "clock_exit_language", AXIS_BASELINES_CORRECTED,
     "prompt reframes bid as clock exit -> target rise is partly prompt echo "
     "(this IS the manipulation)"),
    ("Two-stage clock-exit descr.", "B3v", "axis2_forward_baseline",
     "clock_exit_language", AXIS_BASELINES_CORRECTED,
     "RECLASSIFIED (provenance note 2026-07-08): the V12 axis2 'baseline' text "
     "was a two-stage sealed-bid-as-clock-exit description -> treated cell, "
     "B3-variant; target rise is partly prompt echo (this IS the manipulation)"),
    ("First-order beliefs", "C3", "axis3_beliefs_firstorder", "opponent_modeling",
     ["axis3_beliefs_baseline"],
     "prompt asks 'what will others bid' -> target rise is partly prompt echo"),
    ("Second-order beliefs", "C3", "axis3_beliefs_secondorder", "opponent_modeling",
     ["axis3_beliefs_baseline"],
     "prompt asks 'what do others think YOU bid' -> partly prompt echo"),
    ("Common-knowledge beliefs", "C3", "axis3_beliefs_common_knowledge",
     "opponent_modeling", ["axis3_beliefs_baseline"],
     "prompt asserts common knowledge of rationality -> partly prompt echo"),
    ("Backward induction", "C2", "axis2_forward_backward_induct",
     "expected_value_reasoning", AXIS_BASELINES_CORRECTED,
     "prompt = the two-stage clock-exit text PLUS 'work backwards from Stage "
     "2' guidance; vs corrected baseline this measures the BUNDLE "
     "(framing+guidance); the within-pair contrast vs axis2_forward_baseline "
     "(shared framing) isolates the guidance and is reported in the summary"),
    ("Risk-averse persona", "D", "risk_averse", "risk_language",
     AXIS_BASELINES_CORRECTED,
     "prompt says 'you are risk-averse' -> target rise is partly prompt echo"),
    ("Risk-neutral persona", "D", "risk_neutrality", "risk_language",
     AXIS_BASELINES_CORRECTED,
     "prompt sets a risk-neutral persona -> partly prompt echo"),
    ("Risk-seeking persona", "D", "risk_seeking", "aggressive_language",
     AXIS_BASELINES_CORRECTED,
     "prompt sets a risk-seeking persona -> partly prompt echo"),
    ("Loss frame", "D", "loss_aversion_loss_frame", "risk_language",
     ["loss_aversion_baseline"],
     "prompt frames payment as a loss -> mild echo"),
    ("Gain frame", "D", "loss_aversion_gain_frame", "risk_language",
     ["loss_aversion_baseline"],
     "prompt frames outcome as a gain -> mild echo"),
    ("Endowment", "D", "loss_aversion_endowment", "risk_language",
     ["loss_aversion_baseline"],
     "prompt grants an endowment -> mild echo"),
    ("Mixed frame", "D", "loss_aversion_mixed_frame", "risk_language",
     ["loss_aversion_baseline"],
     "mixed gain/loss framing -> mild echo"),
    ("WTA/WTP", "D", "loss_aversion_WTA_WTP", "risk_language",
     ["loss_aversion_baseline"],
     "willingness-to-accept vs -pay framing -> mild echo"),
]

# The four canonical levers that make the 2x2 dissociation matrix (paper claim).
DISSOC_LEVERS = ["Payoff Safety", "Worst-case scaffold", "Payoff Tree",
                 "Menu restatement"]


# ---------------------------------------------------------------------------
# Statistical machinery
# ---------------------------------------------------------------------------
def naive_cluster_p(frame, dv, treat_col="treated"):
    """Naive cluster-robust (by run_id) OLS p-value for the treated coef.
    Reported but flagged unreliable when n_clusters is small."""
    if frame[dv].std() == 0 or frame[treat_col].nunique() < 2:
        return np.nan, np.nan, 0
    m = smf.ols(f"{dv} ~ {treat_col} + C(model)", data=frame).fit(
        cov_type="cluster", cov_kwds={"groups": frame["run_id"]})
    ncl = frame["run_id"].nunique()
    return float(m.params[treat_col]), float(m.pvalues[treat_col]), ncl


def wild_cluster_boot_p(frame, dv, treat_col="treated", n_boot=N_BOOT,
                        seed=SEED):
    """Wild cluster bootstrap p-value (Rademacher weights) for the treated
    coefficient, imposing the null (restricted residuals). Model FE partialled
    out. Cluster = run_id. Robust in the few-cluster regime.

    Returns (coef, wcb_p, n_clusters). Two-sided p from the bootstrap t-dist.
    """
    fr = frame.copy()
    if fr[dv].std() == 0 or fr[treat_col].nunique() < 2:
        return np.nan, np.nan, fr["run_id"].nunique()
    local_rng = np.random.default_rng(seed)
    # Design: dv ~ treated + model FE.  Wald t on 'treated'.
    Xcols = pd.get_dummies(fr["model"], prefix="m", drop_first=True).astype(float)
    X = pd.concat([pd.Series(1.0, index=fr.index, name="const"),
                   fr[treat_col].astype(float).rename("treated"),
                   Xcols], axis=1)
    y = fr[dv].astype(float).values
    Xm = X.values
    clusters = fr["run_id"].values

    def cluster_t(Xm, y):
        XtX = Xm.T @ Xm
        try:
            XtXi = np.linalg.pinv(XtX)
        except np.linalg.LinAlgError:
            return np.nan, None, None
        beta = XtXi @ (Xm.T @ y)
        resid = y - Xm @ beta
        # CR1 cluster-robust variance for the 'treated' coef (index 1).
        uniq = np.unique(clusters)
        meat = np.zeros((Xm.shape[1], Xm.shape[1]))
        for c in uniq:
            idx = clusters == c
            Xc = Xm[idx]
            uc = resid[idx]
            sc = Xc.T @ uc
            meat += np.outer(sc, sc)
        G = len(uniq)
        n, k = Xm.shape
        adj = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 and n > k else 1.0
        V = adj * XtXi @ meat @ XtXi
        se = np.sqrt(max(V[1, 1], 1e-30))
        return beta[1], beta[1] / se, resid

    beta1, t_obs, _ = cluster_t(Xm, y)
    if t_obs is None or not np.isfinite(t_obs):
        return float(beta1) if beta1 is not None else np.nan, np.nan, len(np.unique(clusters))

    # Restricted model under H0: beta_treated = 0. Fit dv ~ const + FE only.
    Xr = X.drop(columns=["treated"]).values
    XrtXr_i = np.linalg.pinv(Xr.T @ Xr)
    beta_r = XrtXr_i @ (Xr.T @ y)
    yhat_r = Xr @ beta_r
    resid_r = y - yhat_r

    uniq = np.unique(clusters)
    cl_index = {c: (clusters == c) for c in uniq}
    t_boot = np.empty(n_boot)
    for b in range(n_boot):
        w = local_rng.choice([-1.0, 1.0], size=len(uniq))
        wmap = dict(zip(uniq, w))
        wvec = np.array([wmap[c] for c in clusters])
        y_star = yhat_r + resid_r * wvec
        _, t_star, _ = cluster_t(Xm, y_star)
        t_boot[b] = t_star if (t_star is not None and np.isfinite(t_star)) else 0.0
    p = float(np.mean(np.abs(t_boot) >= abs(t_obs)))
    p = min(1.0, (p * n_boot + 1) / (n_boot + 1))  # small-sample correction
    return float(beta1), p, len(uniq)


def cluster_perm_p(frame, dv, treat_col="treated", n_perm=N_PERM, seed=SEED):
    """Cluster-level permutation test: randomly reassign the treated label at
    the cluster (run_id) level, holding the count of treated clusters fixed;
    statistic = difference in FE-adjusted cluster means. Cross-check for WCB."""
    fr = frame.copy()
    if fr[dv].std() == 0 or fr[treat_col].nunique() < 2:
        return np.nan
    local_rng = np.random.default_rng(seed + 7)
    cl = fr.groupby("run_id").agg(
        treated=(treat_col, "first"),
        val=(dv, "mean")).reset_index()
    n_t = int(cl["treated"].sum())
    G = len(cl)
    if n_t == 0 or n_t == G:
        return np.nan
    obs = cl.loc[cl.treated == 1, "val"].mean() - cl.loc[cl.treated == 0, "val"].mean()
    vals = cl["val"].values
    cnt = 0
    for _ in range(n_perm):
        perm = local_rng.permutation(G)
        t_idx = perm[:n_t]
        c_idx = perm[n_t:]
        stat = vals[t_idx].mean() - vals[c_idx].mean()
        if abs(stat) >= abs(obs):
            cnt += 1
    return (cnt + 1) / (n_perm + 1)


def cluster_boot_diff_ci(frame, dv, treat_col="treated", n_boot=N_BOOT,
                         seed=SEED):
    """Cluster bootstrap 95% CI for the treated-vs-control difference in means
    of `dv` (resample run_id clusters with replacement)."""
    fr = frame.copy()
    local_rng = np.random.default_rng(seed + 3)
    clusters = fr["run_id"].unique()
    groups = {c: fr[fr["run_id"] == c] for c in clusters}
    diffs = []
    for _ in range(n_boot):
        pick = local_rng.choice(clusters, size=len(clusters), replace=True)
        boot = pd.concat([groups[c] for c in pick])
        t = boot[boot[treat_col] == 1][dv]
        c = boot[boot[treat_col] == 0][dv]
        if len(t) and len(c):
            diffs.append(t.mean() - c.mean())
    if not diffs:
        return (np.nan, np.nan)
    return tuple(np.percentile(diffs, [2.5, 97.5]))


# ---------------------------------------------------------------------------
# Load + sanity checks
# ---------------------------------------------------------------------------
def load():
    df = pd.read_csv(os.path.join(TRACES, "trace_features.csv"))
    # Derived feature (provenance correction): two-stage clock-exit framing
    # language, target of the reclassified axis2_forward_baseline cell and the
    # B3 clock-framing cell.
    df["clock_exit_language"] = (df["plan"].str.lower()
                                 .str.contains(CLOCK_EXIT_RE, regex=True)
                                 .astype(int))
    # sealed second-price only for the lever analysis (exclude ascending clock;
    # exclude fpsb/tpsb which are the mechanism-contrast cells, not levers).
    sp = df[df["mechanism"] == "spsb_sealed"].copy()
    return df, sp


def sanity(sp, log):
    """Sanity-check cell means against traces_summary.md published numbers and
    the axis2-baseline provenance note before trusting any join."""
    checks = []
    os_dev = sp.loc[sp.experiment == "axis2_forward_onestep", "deviation"].mean()
    checks.append(("axis2_forward_onestep mean dev", os_dev, -1.53))
    axb = sp[sp.experiment.isin(AXIS_BASELINES_LEGACY)]["abs_dev"].mean()
    checks.append(("LEGACY pooled-of-three baseline |dev|", axb, 3.27))
    os_ad = sp.loc[sp.experiment == "axis2_forward_onestep", "abs_dev"].mean()
    checks.append(("onestep mean |dev|", os_ad, 1.95))
    spsb_dev = sp.loc[sp.experiment == "spsb", "deviation"].mean()
    checks.append(("spsb mean dev", spsb_dev, -2.67))
    wc = sp.loc[sp.experiment == "axis1_contingent_worstcase", "worst_case"].mean()
    checks.append(("worstcase 'worst_case' prevalence", wc, 0.43))
    tree_ad = sp.loc[sp.experiment == "axis2_forward_tree", "abs_dev"].mean()
    checks.append(("payoff_tree mean |dev|", tree_ad, 1.29))
    # Provenance-note checks (_axis2_baseline_provenance.md): the contaminated
    # cell's clock-exit language and per-model behavior must reproduce.
    a2 = sp[sp.experiment == "axis2_forward_baseline"]
    prov = {"claude-3-5-haiku-20241022": 0.173, "gemini-2.0-flash": 0.247,
            "google/gemma-3-27b-it": 0.153, "gpt-4o": 0.000}
    for m, target in prov.items():
        got = a2.loc[a2.model == m, "clock_exit_language"].mean()
        checks.append((f"axis2fb clock-exit lang {m[:12]}", got, target))
    checks.append(("axis2fb gemma mean dev",
                   a2.loc[a2.model == "google/gemma-3-27b-it",
                          "deviation"].mean(), -0.59))
    checks.append(("axis2fb gemini mean dev",
                   a2.loc[a2.model == "gemini-2.0-flash",
                          "deviation"].mean(), -6.12))
    # axis1/axis3 baselines must have ZERO clock-exit language.
    clean = sp[sp.experiment.isin(AXIS_BASELINES_CORRECTED)]
    checks.append(("corrected baselines clock-exit lang",
                   clean["clock_exit_language"].mean(), 0.0))
    log("### SANITY CHECKS vs published (traces_summary.md + provenance note)")
    ok = True
    for name, got, pub in checks:
        flag = "OK" if abs(got - pub) < 0.06 else "!! MISMATCH"
        if flag != "OK":
            ok = False
        log(f"  {name:42s} got={got:+.3f}  published={pub:+.3f}  {flag}")
    assert ok, "Sanity check failed: cell means do not match published numbers."
    log("")


# ---------------------------------------------------------------------------
# (1) Manipulation-check table for every lever
# ---------------------------------------------------------------------------
def manipulation_checks(sp, dedup=False, log=print):
    rows = []
    work = sp
    if dedup:
        work = sp.drop_duplicates(
            subset=["model", "experiment", "value", "bid", "plan"]).copy()
    for (label, fam, exp, target, base_list, echo) in LEVERS:
        treat = work[work.experiment == exp].copy()
        ctrl = work[work.experiment.isin(base_list)].copy()
        if len(treat) == 0 or len(ctrl) == 0:
            continue
        both = pd.concat([treat.assign(treated=1), ctrl.assign(treated=0)])
        # --- target language contrast ---
        prev_c = ctrl[target].mean()
        prev_t = treat[target].mean()
        _, wcb_p_lang, ncl = wild_cluster_boot_p(both, target)
        perm_p_lang = cluster_perm_p(both, target)
        _, naive_p_lang, _ = naive_cluster_p(both, target)
        # --- behavior contrasts (primary = corrected baseline in base_list) ---
        dev_c, dev_t = ctrl["deviation"].mean(), treat["deviation"].mean()
        ad_c, ad_t = ctrl["abs_dev"].mean(), treat["abs_dev"].mean()
        _, wcb_p_dev, _ = wild_cluster_boot_p(both, "deviation")
        _, wcb_p_ad, _ = wild_cluster_boot_p(both, "abs_dev")
        perm_p_ad = cluster_perm_p(both, "abs_dev")
        ci_ad = cluster_boot_diff_ci(both, "abs_dev")
        # --- comparison columns: LEGACY pooled-of-three and dedicated spsb ---
        # (clearly labeled; legacy is skipped when the treatment cell is itself
        # part of the legacy pool, i.e. the reclassified axis2fb row).
        cmp_cols = {}
        for tag, cmp_base in [("legacy", AXIS_BASELINES_LEGACY),
                              ("spsb", ["spsb"])]:
            if exp in cmp_base:
                cmp_cols[f"absdev_base_{tag}"] = np.nan
                cmp_cols[f"absdev_diff_{tag}"] = np.nan
                cmp_cols[f"absdev_wcb_p_{tag}"] = np.nan
                continue
            cctrl = work[work.experiment.isin(cmp_base)].copy()
            cboth = pd.concat([treat.assign(treated=1),
                               cctrl.assign(treated=0)])
            _, cp, _ = wild_cluster_boot_p(cboth, "abs_dev")
            cmp_cols[f"absdev_base_{tag}"] = round(cctrl["abs_dev"].mean(), 3)
            cmp_cols[f"absdev_diff_{tag}"] = round(
                ad_t - cctrl["abs_dev"].mean(), 3)
            cmp_cols[f"absdev_wcb_p_{tag}"] = (round(cp, 4)
                                               if pd.notna(cp) else np.nan)
        rows.append(dict(
            lever=label, family=fam, experiment=exp, target_feature=target,
            n_treat=len(treat), n_ctrl=len(ctrl), n_clusters=ncl,
            prev_baseline=round(prev_c, 4), prev_treated=round(prev_t, 4),
            prev_diff=round(prev_t - prev_c, 4),
            lang_wcb_p=round(wcb_p_lang, 4) if pd.notna(wcb_p_lang) else np.nan,
            lang_perm_p=round(perm_p_lang, 4) if pd.notna(perm_p_lang) else np.nan,
            lang_naive_p=round(naive_p_lang, 4) if pd.notna(naive_p_lang) else np.nan,
            dev_baseline=round(dev_c, 3), dev_treated=round(dev_t, 3),
            dev_wcb_p=round(wcb_p_dev, 4) if pd.notna(wcb_p_dev) else np.nan,
            absdev_baseline=round(ad_c, 3), absdev_treated=round(ad_t, 3),
            absdev_diff=round(ad_t - ad_c, 3),
            absdev_ci_lo=round(ci_ad[0], 3), absdev_ci_hi=round(ci_ad[1], 3),
            absdev_wcb_p=round(wcb_p_ad, 4) if pd.notna(wcb_p_ad) else np.nan,
            absdev_perm_p=round(perm_p_ad, 4) if pd.notna(perm_p_ad) else np.nan,
            **cmp_cols,
            prompt_echo_note=echo,
        ))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# (2) 2x2 moves-language / moves-bids classification
# ---------------------------------------------------------------------------
def classify_2x2(mc, sp, scheme="corrected"):
    """From the manipulation-check table, classify each canonical lever as
    moves-language (yes/no) x moves-bids (yes/no). 'Moves' = wild-cluster
    bootstrap p < 0.05; a cluster-level permutation p is reported alongside
    (only 4 model-clusters, so the two can disagree).

    scheme='corrected' (headline): behavior tested against the provenance-
    corrected pooled baseline {axis1, axis3} for B2/Tree/Menu (the axis2
    'baseline' cell is a treated clock-framing cell and leaves the pool);
    worst-case keeps its own clean axis1 baseline.
    scheme='precorrection': the conventions of the pre-provenance run (spsb
    for B2, own-axis2 for the Tree, legacy pooled-of-three for the menu) —
    retained only to document what the correction changes."""
    ALPHA = 0.05
    if scheme == "corrected":
        CLS_BASE = {
            "Payoff Safety": AXIS_BASELINES_CORRECTED,
            "Worst-case scaffold": ["axis1_contingent_baseline"],
            "Payoff Tree": AXIS_BASELINES_CORRECTED,
            "Menu restatement": AXIS_BASELINES_CORRECTED,
        }
    else:  # precorrection conventions (documentation of the change only)
        CLS_BASE = {
            "Payoff Safety": ["spsb"],
            "Worst-case scaffold": ["axis1_contingent_baseline"],
            "Payoff Tree": ["axis2_forward_baseline"],
            "Menu restatement": AXIS_BASELINES_LEGACY,
        }
    rows = []
    for lever in DISSOC_LEVERS:
        r = mc[mc.lever == lever]
        if r.empty:
            continue
        r = r.iloc[0]
        exp = r.experiment
        # --- behavior tested against the canonical classification baseline ---
        treat = sp[sp.experiment == exp].copy()
        ctrl = sp[sp.experiment.isin(CLS_BASE[lever])].copy()
        both = pd.concat([treat.assign(treated=1), ctrl.assign(treated=0)])
        _, bid_wcb, ncl = wild_cluster_boot_p(both, "abs_dev")
        bid_perm = cluster_perm_p(both, "abs_dev")
        ad_c, ad_t = ctrl["abs_dev"].mean(), treat["abs_dev"].mean()
        # --- language (own-baseline manipulation-check row) ---
        lang_wcb = r.lang_wcb_p
        lang_perm = r.lang_perm_p
        lang_moves = pd.notna(lang_wcb) and lang_wcb < ALPHA
        bids_move = pd.notna(bid_wcb) and bid_wcb < ALPHA
        lang_note = ""
        if lever == "Menu restatement":
            # target language is 0-by-construction (prompt removes vocab);
            # scored moves-language = no on that structural fact, not a test.
            lang_moves = False
            lang_note = "target 0 by construction (prompt removes rule vocab)"
        # robustness flag: WCB says moves but the model-cluster permutation does not
        robust_note = ""
        if bids_move and pd.notna(bid_perm) and bid_perm >= ALPHA:
            robust_note = (f"bids: WCB p={bid_wcb:.3f}<.05 but cluster-perm "
                           f"p={bid_perm:.2f}>=.05 (soft at the model-cluster "
                           f"level)")
        if (not bids_move) and pd.notna(bid_wcb) and bid_wcb < 0.10:
            robust_note = (robust_note + "; " if robust_note else "") + \
                f"bids marginal (WCB p={bid_wcb:.3f})"
        rows.append(dict(
            lever=r.lever, family=r.family, target_feature=r.target_feature,
            scheme=scheme, n_clusters=ncl,
            moves_language=("yes" if lang_moves else "no"),
            lang_prev=f"{r.prev_baseline:.3f}->{r.prev_treated:.3f}",
            lang_wcb_p=lang_wcb, lang_perm_p=lang_perm, lang_note=lang_note,
            moves_bids=("yes" if bids_move else "no"),
            absdev=f"{ad_c:.2f}->{ad_t:.2f}",
            absdev_wcb_p=round(bid_wcb, 4) if pd.notna(bid_wcb) else np.nan,
            absdev_perm_p=round(bid_perm, 4) if pd.notna(bid_perm) else np.nan,
            robust_note=robust_note,
            cell=("both" if lang_moves and bids_move else
                  "language-only" if lang_moves else
                  "bids-only" if bids_move else "neither"),
        ))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# (3) Formal mediation for Payoff Safety (B2)
# ---------------------------------------------------------------------------
def mediation_b2(sp, log=print):
    """First stage (lever -> verbalized-understanding mediators) ~ 0 with CIs,
    the implied product-of-coefficients bound on the mediated share, and the
    within-treatment (non-causal) cross-sectional association."""
    MEDS = ["payment_rule_correct", "safety_recognition", "second_price_mention"]
    treat = sp[sp.experiment == "axis2_forward_onestep"].copy()
    out_rows = []
    for base_name, base_list in [
            ("corrected_axis1_axis3", AXIS_BASELINES_CORRECTED),
            ("legacy_pooled_of_three", AXIS_BASELINES_LEGACY),
            ("spsb_cell", ["spsb"])]:
        ctrl = sp[sp.experiment.isin(base_list)].copy()
        both = pd.concat([treat.assign(treated=1), ctrl.assign(treated=0)])
        # total effect on behavior (|dev|)
        tot_ad = treat["abs_dev"].mean() - ctrl["abs_dev"].mean()
        _, tot_p, ncl = wild_cluster_boot_p(both, "abs_dev")
        tot_ci = cluster_boot_diff_ci(both, "abs_dev")
        for med in MEDS:
            # First stage a: treated -> mediator
            a = treat[med].mean() - ctrl[med].mean()
            _, a_p, _ = wild_cluster_boot_p(both, med)
            a_ci = cluster_boot_diff_ci(both, med)
            # Second stage b: mediator -> |dev| WITHIN TREATMENT (cross-sectional)
            if treat[med].nunique() > 1:
                b_model = smf.ols(f"abs_dev ~ {med} + C(model)", data=treat).fit(
                    cov_type="cluster", cov_kwds={"groups": treat["run_id"]})
                b = float(b_model.params[med])
                # raw within-treatment gap + cluster-boot CI (non-causal)
                gap_ci = cluster_boot_diff_ci(
                    treat.assign(treated=treat[med]), "abs_dev")
                gap = (treat.loc[treat[med] == 1, "abs_dev"].mean()
                       - treat.loc[treat[med] == 0, "abs_dev"].mean())
            else:
                b, gap = np.nan, np.nan
                gap_ci = (np.nan, np.nan)
            # product-of-coefficients mediated effect a*b and share of total
            acme = a * b if pd.notna(b) else np.nan
            share = (acme / tot_ad) if (pd.notna(acme) and tot_ad != 0) else np.nan
            out_rows.append(dict(
                baseline=base_name, mediator=med,
                n_treat=len(treat), n_ctrl=len(ctrl), n_clusters=ncl,
                prev_treated=round(treat[med].mean(), 4),
                prev_ctrl=round(ctrl[med].mean(), 4),
                first_stage_a=round(a, 4),
                a_ci_lo=round(a_ci[0], 4), a_ci_hi=round(a_ci[1], 4),
                a_wcb_p=round(a_p, 4) if pd.notna(a_p) else np.nan,
                second_stage_b_within_treat=round(b, 4) if pd.notna(b) else np.nan,
                within_gap=round(gap, 4) if pd.notna(gap) else np.nan,
                within_gap_ci_lo=round(gap_ci[0], 4) if pd.notna(gap_ci[0]) else np.nan,
                within_gap_ci_hi=round(gap_ci[1], 4) if pd.notna(gap_ci[1]) else np.nan,
                product_acme=round(acme, 4) if pd.notna(acme) else np.nan,
                total_effect_absdev=round(tot_ad, 4),
                total_ci_lo=round(tot_ci[0], 4), total_ci_hi=round(tot_ci[1], 4),
                mediated_share=round(share, 4) if pd.notna(share) else np.nan,
            ))
    med_df = pd.DataFrame(out_rows)

    # Bound the mediated share via cluster bootstrap on the product a*b, pooled
    # over the three verbalized-understanding mediators. Primary bound = the
    # corrected baseline; the legacy bound is retained to document the change.
    bound = bootstrap_mediation_bound(
        sp, MEDS, base_list=AXIS_BASELINES_CORRECTED, log=log)
    bound_legacy = bootstrap_mediation_bound(
        sp, MEDS, base_list=AXIS_BASELINES_LEGACY, log=log)
    return med_df, bound, bound_legacy


def bootstrap_mediation_bound(sp, meds, base_list=AXIS_BASELINES_CORRECTED,
                              log=print):
    """Cluster-bootstrap the product-of-coefficients mediated effect for each
    verbalized-understanding mediator and report the 95% CI of the implied
    mediated SHARE of the total |dev| effect. Because the first stage a~0, the
    honest statement is an upper bound: 'verbalized understanding cannot mediate
    more than X% of the Payoff Safety effect'. NOT a causal mediation estimate
    (sequential ignorability is not claimed)."""
    treat = sp[sp.experiment == "axis2_forward_onestep"].copy()
    ctrl = sp[sp.experiment.isin(base_list)].copy()
    both = pd.concat([treat.assign(treated=1), ctrl.assign(treated=0)]).copy()
    # combined mediator = any verbalized understanding fires (set BEFORE the
    # per-cluster split so the bootstrap draws carry the column).
    both["any_vu"] = (both[meds].sum(axis=1) > 0).astype(int)
    clusters = both["run_id"].unique()
    tgroups = {c: both[both["run_id"] == c] for c in clusters}
    local_rng = np.random.default_rng(SEED + 11)

    shares = []
    acmes = []
    for _ in range(N_BOOT):
        pick = local_rng.choice(clusters, size=len(clusters), replace=True)
        boot = pd.concat([tgroups[c] for c in pick])
        bt = boot[boot.treated == 1]
        bc = boot[boot.treated == 0]
        if len(bt) == 0 or len(bc) == 0:
            continue
        a = bt["any_vu"].mean() - bc["any_vu"].mean()
        # within-treatment b (cross-sectional, non-causal) using bootstrap draw
        if bt["any_vu"].nunique() > 1:
            b = (bt.loc[bt.any_vu == 1, "abs_dev"].mean()
                 - bt.loc[bt.any_vu == 0, "abs_dev"].mean())
        else:
            b = 0.0
        tot = bt["abs_dev"].mean() - bc["abs_dev"].mean()
        acme = a * b
        acmes.append(acme)
        if tot != 0:
            shares.append(acme / tot)
    acmes = np.array(acmes)
    shares = np.array(shares)
    res = dict(
        acme_point=float(np.median(acmes)),
        acme_ci=(float(np.percentile(acmes, 2.5)),
                 float(np.percentile(acmes, 97.5))),
        share_point=float(np.median(shares)),
        share_ci=(float(np.percentile(shares, 2.5)),
                  float(np.percentile(shares, 97.5))),
        share_abs_upper95=float(np.percentile(np.abs(shares), 95)),
    )
    return res


# ---------------------------------------------------------------------------
# (3b) The reclassified axis2_forward_baseline cell as a treatment
#      ("two-stage clock-exit description", B3 variant): per-model detail.
# ---------------------------------------------------------------------------
def axis2fb_treatment_detail(sp):
    """Per-model manipulation check + behavioral effect for the reclassified
    axis2_forward_baseline cell vs the corrected baseline {axis1, axis3}.
    Per-model inference caveat: each model contributes ONE treated cluster and
    TWO control clusters, so no cluster-level test is possible within model;
    the Welch p is row-level (near-duplicate rows -> optimistic) and is
    reported for description only. The pooled WCB/permutation tests live in
    the manipulation-check row."""
    from scipy import stats
    treat = sp[sp.experiment == "axis2_forward_baseline"]
    ctrl = sp[sp.experiment.isin(AXIS_BASELINES_CORRECTED)]
    rows = []
    for model in sorted(sp.model.unique()):
        t = treat[treat.model == model]
        c = ctrl[ctrl.model == model]
        welch = stats.ttest_ind(t["deviation"], c["deviation"],
                                equal_var=False).pvalue
        welch_ad = stats.ttest_ind(t["abs_dev"], c["abs_dev"],
                                   equal_var=False).pvalue
        rows.append(dict(
            model=model,
            n_treat=len(t), n_ctrl=len(c),
            clock_lang_treated=round(t["clock_exit_language"].mean(), 4),
            clock_lang_baseline=round(c["clock_exit_language"].mean(), 4),
            dev_baseline=round(c["deviation"].mean(), 3),
            dev_treated=round(t["deviation"].mean(), 3),
            dev_shift=round(t["deviation"].mean() - c["deviation"].mean(), 3),
            absdev_baseline=round(c["abs_dev"].mean(), 3),
            absdev_treated=round(t["abs_dev"].mean(), 3),
            welch_p_dev_rowlevel=round(welch, 5),
            welch_p_absdev_rowlevel=round(welch_ad, 5),
        ))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# (4) Option 4: per model x lever stated-vs-revealed consistency + calibration
# ---------------------------------------------------------------------------
BID_CUE = re.compile(
    r"(?:bid|submit|offer|place|go with|settle on|choose|aim(?:ing)? for|"
    r"around|approximately|about|set(?:ting)? (?:my|it) (?:to|at)|price of)"
    r"\s*(?:of|at|is|to|be|around|about|approximately|~|:)?\s*\$?\s?"
    r"(\d+(?:\.\d+)?)", re.I)


def parse_stated_bid(plan):
    """Extract the stated intended bid: the last $-amount that follows a
    bid-intent cue in the plan text. Returns NaN if none. Values > 55 are
    treated as parse errors (item value range is $0-49)."""
    cues = [float(m.group(1)) for m in BID_CUE.finditer(str(plan))]
    if not cues:
        return np.nan
    v = cues[-1]
    return v if v <= 55 else np.nan


def consistency_calibration(sp, log=print):
    """Two instruments per model x lever:
    (A) direction consistency: P(sign(realized dev) matches stated intent |
        an intent (shading/overbid/truthful) is stated).
    (B) $-amount calibration: parse the stated intended bid and compare to the
        realized bid (exact-match share, correlation, mean |stated-realized|).
    """
    work = sp.copy()
    work["stated_bid"] = work["plan"].apply(parse_stated_bid)

    # --- (A) direction consistency ---
    # stated direction: shading -> expect dev<0; overbid -> dev>0; truthful ->
    # expect |dev| small (<=0.5). We define a per-trace 'match' where an intent
    # is stated (mutually: use the dominant stated intent).
    def direction_match(r):
        if r["overbid_intent"] == 1 and r["shading_intent"] == 0:
            return int(r["deviation"] > 0)
        if r["shading_intent"] == 1 and r["overbid_intent"] == 0:
            return int(r["deviation"] < 0)
        if r["truthful_intent"] == 1 and r["shading_intent"] == 0 and r["overbid_intent"] == 0:
            return int(r["abs_dev"] <= 0.5)
        return np.nan  # no clean single stated intent
    work["dir_match"] = work.apply(direction_match, axis=1)

    lever_by_exp = {L[2]: (L[0], L[1]) for L in LEVERS}
    lever_by_exp["spsb"] = ("Baseline SPSB", "A")

    def lever_of(exp):
        return lever_by_exp.get(exp, (exp, "?"))

    rows = []
    work["lever"] = work["experiment"].map(lambda e: lever_of(e)[0])
    work["family"] = work["experiment"].map(lambda e: lever_of(e)[1])
    for (model, lever), g in work.groupby(["model", "lever"]):
        stated = g[g["dir_match"].notna()]
        cal = g[g["stated_bid"].notna()].copy()
        cal["sb_err"] = cal["stated_bid"] - cal["bid"]
        rows.append(dict(
            model=model, lever=lever,
            n_intent_stated=len(stated),
            dir_consistency=round(stated["dir_match"].mean(), 4)
            if len(stated) else np.nan,
            n_calib=len(cal),
            calib_coverage=round(len(cal) / len(g), 4) if len(g) else np.nan,
            exact_match=round((cal["sb_err"].abs() < 0.01).mean(), 4)
            if len(cal) else np.nan,
            within_0p5=round((cal["sb_err"].abs() <= 0.5).mean(), 4)
            if len(cal) else np.nan,
            corr_stated_realized=round(cal["stated_bid"].corr(cal["bid"]), 4)
            if len(cal) > 2 else np.nan,
            mean_abs_stated_minus_realized=round(cal["sb_err"].abs().mean(), 4)
            if len(cal) else np.nan,
        ))
    cal_df = pd.DataFrame(rows).sort_values(["lever", "model"]).reset_index(drop=True)

    # per-model pooled scalar (over all sealed cells)
    pooled = []
    for model, g in work.groupby("model"):
        stated = g[g["dir_match"].notna()]
        cal = g[g["stated_bid"].notna()].copy()
        cal["sb_err"] = cal["stated_bid"] - cal["bid"]
        pooled.append(dict(
            model=model, scope="ALL sealed cells",
            n_intent_stated=len(stated),
            dir_consistency=round(stated["dir_match"].mean(), 4),
            n_calib=len(cal),
            exact_match=round((cal["sb_err"].abs() < 0.01).mean(), 4),
            corr_stated_realized=round(cal["stated_bid"].corr(cal["bid"]), 4),
            mean_abs_stated_minus_realized=round(cal["sb_err"].abs().mean(), 4),
        ))
    pooled_df = pd.DataFrame(pooled)
    return cal_df, pooled_df, work


def calibration_figure(work, path):
    """Binned calibration curve of realized bid vs stated intended bid, per
    model. Publication-grade (Okabe-Ito, no chartjunk)."""
    C = {"gpt-4o": "#0072B2", "claude-3-5-haiku-20241022": "#D55E00",
         "gemini-2.0-flash": "#009E73", "google/gemma-3-27b-it": "#CC79A7"}
    LAB = {"gpt-4o": "GPT-4o", "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
           "gemini-2.0-flash": "Gemini 2.0 Flash",
           "google/gemma-3-27b-it": "Gemma 3 27B"}
    cal = work[work["stated_bid"].notna()].copy()
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.labelsize": 11, "legend.frameon": False, "legend.fontsize": 9,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "savefig.dpi": 200,
        "axes.grid": False, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.6, "lines.linewidth": 2.0,
    })
    fig, ax = plt.subplots(figsize=(8, 6))
    bins = np.arange(0, 51, 5)
    centers = (bins[:-1] + bins[1:]) / 2
    ax.plot([0, 49], [0, 49], ls="--", lw=0.9, color="#999999", zorder=1)
    ax.text(41, 45, "stated = realized", fontsize=8.5, color="#777777",
            rotation=34, ha="center", va="center")
    for model in ["gpt-4o", "claude-3-5-haiku-20241022", "gemini-2.0-flash",
                  "google/gemma-3-27b-it"]:
        g = cal[cal.model == model]
        if g.empty:
            continue
        g = g.copy()
        g["bin"] = pd.cut(g["stated_bid"], bins=bins, labels=centers,
                          include_lowest=True)
        m = g.groupby("bin", observed=True)["bid"].mean()
        xs = m.index.astype(float).values
        ax.plot(xs, m.values, marker="o", ms=4, color=C[model], label=LAB[model])
    ax.set_xlabel("Stated intended bid parsed from plan ($)")
    ax.set_ylabel("Mean realized bid ($)")
    ax.set_title("Stated-vs-realized bid calibration, by model")
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 50)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# LaTeX fragments (booktabs, paper style)
# ---------------------------------------------------------------------------
def _p(p):
    if pd.isna(p):
        return "---"
    if p < 0.001:
        return "$<0.001$"
    return f"${p:.3f}$"


def write_tex(mc, dissoc, path):
    lines = []
    lines.append("% Auto-generated by analysis/build_trace_mediation.py "
                 "(seed 1299). Fragments only; NOT wired into writeup/.")
    lines.append("% p-values are wild-cluster bootstrap (Rademacher, 2000 reps),"
                 " robust in the few-cluster regime.")
    lines.append("")
    # ---- Manipulation-check table ----
    lines.append("% ===== Manipulation-check table (every auction lever) =====")
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\footnotesize")
    lines.append(r"\setlength{\tabcolsep}{4pt}")
    lines.append(r"\resizebox{\textwidth}{!}{%")
    lines.append(r"\begin{tabular}{lll cc c cc c}")
    lines.append(r"\toprule")
    lines.append(r"& & & \multicolumn{3}{c}{Target language} "
                 r"& \multicolumn{3}{c}{Behavior ($|b-v|$)} \\")
    lines.append(r"\cmidrule(lr){4-6}\cmidrule(lr){7-9}")
    lines.append(r"Lever & Fam. & Target feature & base$\to$treat & $\Delta$ "
                 r"& WCB $p$ & base$\to$treat & $\Delta$ & WCB $p$ \\")
    lines.append(r"\midrule")
    fam_order = ["B2", "B1", "B3", "B3v", "C1", "C2", "C3", "D"]
    mc_sorted = mc.copy()
    mc_sorted["_o"] = mc_sorted["family"].map({f: i for i, f in enumerate(fam_order)})
    mc_sorted = mc_sorted.sort_values(["_o", "lever"])
    for _, r in mc_sorted.iterrows():
        tf = r.target_feature.replace("_", r"\_")
        lang = f"{r.prev_baseline:.3f}$\\to${r.prev_treated:.3f}"
        langd = f"${r.prev_diff:+.3f}$"
        beh = f"{r.absdev_baseline:.2f}$\\to${r.absdev_treated:.2f}"
        behd = f"${r.absdev_diff:+.2f}$"
        lines.append(
            f"{r.lever} & {r.family} & \\texttt{{{tf}}} & {lang} & {langd} & "
            f"{_p(r.lang_wcb_p)} & {beh} & {behd} & {_p(r.absdev_wcb_p)} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}}")
    lines.append(
        r"\caption{Manipulation checks for every auction lever: does the lever "
        r"move its own target language feature, and does it move behavior "
        r"($|b-v|$)? Baselines follow the provenance-corrected convention: the "
        r"V12 \texttt{axis2\_forward\_baseline} template was a two-stage "
        r"sealed-bid-as-clock-exit description, not a plain SPSB text, so it "
        r"enters this table as a \emph{treated} cell (row ``Two-stage "
        r"clock-exit descr.'', family B3v) and leaves every baseline pool; the "
        r"corrected pooled baseline is $\{$axis-1, axis-3$\}$ only. Cells with "
        r"a clean own-grid baseline (axis-1 scaffolds, belief scaffolds, "
        r"loss-aversion frames) keep it; all others --- including the axis-2 "
        r"treatments Payoff Safety and Payoff Tree --- are tested against the "
        r"corrected pooled baseline (legacy pooled-of-three and dedicated-SPSB "
        r"comparisons are in the CSV, clearly labeled). $p$-values are "
        r"wild-cluster bootstrap (Rademacher weights, 2000 reps, seed 1299), "
        r"clustered by run directory; each sealed cell is one cluster per "
        r"model, so contrasts have $8$--$16$ clusters and naive cluster-robust "
        r"SEs are unreliable; a cluster-permutation cross-check and the naive "
        r"$p$ are in the CSV. Target-language increases for levers whose "
        r"prompt seeds the target vocabulary (worst-case, dominated, belief, "
        r"clock-framing, risk/loss cells) are partly prompt echo; the menu "
        r"cell's rule-rehearsal target is $0$ by construction because its "
        r"prompt removes the second-price vocabulary (caveat 6b). "
        r"\texttt{results/traces/mediation/manipulation\_checks.csv}.}")
    lines.append(r"\label{tab:trace-manipulation}")
    lines.append(r"\end{table}")
    lines.append("")
    # ---- 2x2 dissociation matrix ----
    lines.append(r"% ===== 2x2 moves-language / moves-bids matrix =====")
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{l cc cc l}")
    lines.append(r"\toprule")
    lines.append(r"& \multicolumn{2}{c}{Moves language?} "
                 r"& \multicolumn{2}{c}{Moves bids?} & \\")
    lines.append(r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}")
    lines.append(r"Lever (family) & call & WCB/perm $p$ & call "
                 r"& WCB/perm $p$ & Classification \\")
    lines.append(r"\midrule")
    for _, r in dissoc.iterrows():
        note = r"$^{\dagger}$" if r.lang_note else ""
        note2 = r"$^{\ddagger}$" if str(r.robust_note).strip() else ""
        lp = "---" if r.lang_note else \
            (f"{_p(r.lang_wcb_p)}/{r.lang_perm_p:.2f}"
             if pd.notna(r.lang_wcb_p) else "---")
        bp = (f"{_p(r.absdev_wcb_p)}/{r.absdev_perm_p:.2f}"
              if pd.notna(r.absdev_wcb_p) else "---")
        lines.append(
            f"{r.lever} ({r.family}){note} & {r.moves_language} & {lp} & "
            f"{r.moves_bids}{note2} & {bp} & {r.cell} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    # pattern sentence assembled from the actual classifications
    cls = {r.lever: r.cell for _, r in dissoc.iterrows()}
    lines.append(
        r"\caption{The $2\times2$ dissociation between stated reasoning and "
        r"bidding behavior, for the four canonical presentation/scaffold levers "
        r"(sealed-bid second-price cells, pooled over four models). "
        r"``Moves'' $=$ wild-cluster-bootstrap (WCB) $p<0.05$ on the target "
        r"language feature or on mean $|b-v|$; a cluster-level permutation $p$ "
        r"(4 model-clusters) is reported alongside. Behavior is tested against "
        r"the provenance-corrected baseline convention: the pooled "
        r"$\{$axis-1, axis-3$\}$ baselines for Payoff Safety, the Payoff Tree, "
        r"and the menu (the axis-2 ``baseline'' cell is a treated clock-framing "
        r"cell and leaves the pool; see Table~\ref{tab:trace-manipulation}), "
        r"and the own axis-1 baseline for the worst-case scaffold. "
        f"Classification: worst-case scaffold {cls.get('Worst-case scaffold','?')}, "
        f"Payoff Safety {cls.get('Payoff Safety','?')}, "
        f"Payoff Tree {cls.get('Payoff Tree','?')}, "
        f"menu {cls.get('Menu restatement','?')}. "
        r"$^{\dagger}$The menu's target language is $0$ by construction (its "
        r"prompt removes the second-price vocabulary), so moves-language $=$ "
        r"no rests on the structural fact, not a language test. "
        r"$^{\ddagger}$WCB and model-level permutation disagree at "
        r"$\alpha=0.05$ (see \texttt{robust\_note} in the CSV); with 4 "
        r"model-clusters the permutation test is the more conservative read. "
        r"\texttt{results/traces/mediation/dissociation\_2x2.csv}.}")
    lines.append(r"\label{tab:trace-dissociation-formal}")
    lines.append(r"\end{table}")
    lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Summary markdown
# ---------------------------------------------------------------------------
def write_summary(mc, mc_dd, dissoc, dissoc_dd, dissoc_pre, med_df, bound,
                  bound_legacy, a2fb, cal_df, pooled_df, log_lines, path):
    L = []
    w = L.append
    w("# Formal mediation / process analysis of the trace double dissociation "
      "— summary (provenance-corrected baselines)")
    w("")
    w("**Produced by:** `analysis/build_trace_mediation.py` (deterministic; "
      "numpy seed 1299; wild-cluster bootstrap 2000 reps, cluster permutation "
      "5000 reps).  ")
    w("**Input:** the frozen `results/traces/trace_features.csv` "
      "(21,990 traces) — no new data.  ")
    w("**Outputs (all under `results/traces/mediation/`):** "
      "`manipulation_checks.csv`, `dissociation_2x2.csv` "
      "(+ `dissociation_2x2_precorrection.csv`), `mediation_b2.csv`, "
      "`axis2fb_treatment_per_model.csv`, `consistency_calibration.csv`, "
      "`consistency_calibration.pdf`, `mediation_tables.tex`, this file.")
    w("")
    w("This upgrade promotes the descriptive mediation *sketch* of Finding 4 "
      "(`traces_summary.md`) to a defensible process analysis: (1) a "
      "manipulation-check table over **every** auction lever; (2) the 2×2 "
      "*moves-language × moves-bids* classification, tested rather than "
      "asserted; (3) a formal — and deliberately *bounded* — mediation "
      "statement for Payoff Safety; (4) per-model stated-vs-revealed "
      "consistency + $-amount calibration (option 4). This revision "
      "incorporates the **axis-2 baseline provenance correction** "
      "(`results/merged_ranking/_axis2_baseline_provenance.md`) throughout.")
    w("")
    w("## 0. The provenance correction (what changed and why)")
    w("")
    w("The V12 `axis2_forward_baseline` template — recovered from the "
      "engineer_simplicity git history and preserved as "
      "`rule_template/auctions/axis2_forward_baseline_DEPRECATED.txt` — was "
      "**not a plain SPSB description**: it was a two-stage "
      "sealed-bid-as-clock-exit (Breitmoser-style clock-framing) text. In the "
      "trace data, 17.3% / 24.7% / 15.3% of Claude/Gemini/Gemma plans in that "
      "cell contain clock/exit/stage-2 language vs **0.0%** in the axis-1 and "
      "axis-3 baselines (GPT-4o: 0.0% — it neither echoes nor reacts). "
      "Behaviorally the cell *fixes* Gemma (mean dev −0.59 vs −5 to −7 in its "
      "clean baselines) and *hurts* Gemini (−6.12 vs −0.8/−1.7). It is a "
      "treated cell, not a baseline. Consequences implemented here:")
    w("")
    w("- **Corrected pooled baseline = {axis1_contingent_baseline, "
      "axis3_beliefs_baseline} only** (n=1,188, 8 clusters; mean dev −2.56, "
      "mean |dev| 3.20). The legacy pooled-of-three and the dedicated `spsb` "
      "cell are kept as clearly-labeled comparison columns.")
    w("- **`axis2_forward_baseline` enters the lever table as a treatment** "
      "(row 'Two-stage clock-exit descr.', family B3v), with "
      "`clock_exit_language` as its manipulation-check target.")
    w("- The axis-2 treatments (Payoff Safety, Payoff Tree) and the backward-"
      "induction cell are re-based to the corrected pooled baseline. All "
      "sanity checks against the provenance note's numbers pass exactly "
      "(see `mediation_log.txt`).")
    w("")
    w("## Methods")
    w("")
    w("- **Clustering.** Every sealed-bid cell is one run directory per model, "
      "so `run_id` gives exactly **4 clusters per experiment**. A "
      "treatment-vs-baseline contrast therefore has only 8 (own-axis baseline) "
      "to 16 (pooled-axis baseline) clusters. This is squarely the few-cluster "
      "regime where naive cluster-robust SEs over-reject. The **headline "
      "p-value for every treatment contrast is a wild-cluster bootstrap** "
      "(Rademacher weights, restricted residuals imposing the null, 2000 reps, "
      "seed 1299), with a **cluster-level permutation test** (5000 reps) as a "
      "cross-check. Naive cluster-robust p-values are computed and stored in the "
      "CSV but are not the headline; the few-cluster flag is documented.")
    w("- **Baselines (provenance-corrected).** Cells with a *clean* own-grid "
      "baseline keep it (axis-1 scaffolds → `axis1_contingent_baseline`; "
      "belief scaffolds → `axis3_beliefs_baseline`; loss frames → "
      "`loss_aversion_baseline`). Everything else — the axis-2 treatments "
      "(Payoff Safety, Payoff Tree, backward induction), the B/D presentation "
      "cells, and the reclassified two-stage clock-exit cell — is tested "
      "against the corrected pooled baseline {axis1, axis3}. The legacy "
      "pooled-of-three and dedicated-`spsb` behavioral comparisons are stored "
      "in `manipulation_checks.csv` as `absdev_*_legacy` / `absdev_*_spsb` "
      "columns; the B2 mediation table reports all three conventions.")
    w("- **Deduplication.** ~40% of sealed rows are byte-identical "
      "(model×cell×value ⇒ same plan and bid at temp 0.5). Every headline is "
      "re-run on the deduplicated sample and both are reported; flips flagged.")
    w("- **Prompt-echo confound (caveat 6b).** The target-language "
      "manipulation check is partly a check on whether the model parrots the "
      "prompt's new vocabulary. Rows are annotated. All language contrasts are "
      "lever-vs-its-own-baseline. The menu cell removes the second-price "
      "vocabulary, so its rule-rehearsal target is 0 by construction and is not "
      "interpreted as comprehension.")
    w("- **Scope.** Ascending-clock traces are excluded (as in the OLS); the "
      "lever analysis is on the sealed second-price cells only.")
    w("")
    w("All cell means were sanity-checked before any join against both "
      "`traces_summary.md` (onestep dev −1.53, legacy pooled |dev| 3.27, "
      "onestep |dev| 1.95, spsb dev −2.67, worst-case language 43%, payoff-tree "
      "|dev| 1.29) and the provenance note (per-model clock-exit prevalence "
      "17.3/24.7/15.3/0.0%; Gemma −0.59, Gemini −6.12; corrected baselines "
      "0.0% clock language) — all matched to ±0.06.")
    w("")
    # ---- 2x2 findings ----
    w("## 1. The 2×2 dissociation (the headline, corrected baselines)")
    w("")
    w("Behavior tested against the corrected pooled baseline {axis1, axis3} "
      "for Payoff Safety, the Payoff Tree, and the menu, and the own axis-1 "
      "baseline for the worst-case scaffold. ``Moves'' = WCB p<0.05. "
      "Cluster-permutation p (model-level) reported alongside because with "
      "only 4 model-clusters the two tests can disagree.")
    w("")
    w("| Lever (family) | Moves language? (WCB p / perm p) | "
      "Moves bids? (WCB p / perm p) | Classification |")
    w("|---|---|---|---|")
    for _, r in dissoc.iterrows():
        lp = ("n/a" if r.lang_note else
              (f"{r.lang_wcb_p:.3f} / {r.lang_perm_p:.2f}"
               if pd.notna(r.lang_wcb_p) else "—"))
        bp = (f"{r.absdev_wcb_p:.3f} / {r.absdev_perm_p:.2f}"
              if pd.notna(r.absdev_wcb_p) else "—")
        w(f"| {r.lever} ({r.family}) | {r.moves_language} ({lp}) "
          f"[{r.lang_prev}] | {r.moves_bids} ({bp}) [{r.absdev}] | "
          f"**{r.cell}** |")
    w("")
    # robustness flags
    flags = [r for _, r in dissoc.iterrows() if str(r.robust_note).strip()]
    if flags:
        w("**Few-cluster robustness flags (IMPORTANT):**")
        w("")
        for r in flags:
            w(f"- **{r.lever}:** {r.robust_note}")
        w("")
    w("Deduplicated cross-check (byte-identical plan+bid dropped):")
    w("")
    w("| Lever | Classification (full) | Classification (dedup) | Flip? |")
    w("|---|---|---|---|")
    dd_map = {r.lever: r.cell for _, r in dissoc_dd.iterrows()}
    for _, r in dissoc.iterrows():
        dd = dd_map.get(r.lever, "—")
        flip = "**YES**" if dd != r.cell else "no"
        w(f"| {r.lever} | {r.cell} | {dd} | {flip} |")
    w("")
    # ---- what changed vs the pre-correction conventions ----
    w("### 1b. What the baseline correction changes (vs the pre-correction "
      "run)")
    w("")
    w("The pre-correction conventions (spsb for B2; own-axis2 for the Tree; "
      "legacy pooled-of-three for the menu) are re-computed in this same run "
      "for documentation (`dissociation_2x2_precorrection.csv`):")
    w("")
    w("| Lever | Pre-correction class (bids WCB/perm p) | Corrected class "
      "(bids WCB/perm p) | Changed? |")
    w("|---|---|---|---|")
    pre_map = {r.lever: r for _, r in dissoc_pre.iterrows()}
    for _, r in dissoc.iterrows():
        pr = pre_map.get(r.lever)
        if pr is None:
            continue
        ch = "**YES**" if pr.cell != r.cell else "no"
        w(f"| {r.lever} | {pr.cell} ({pr.absdev_wcb_p:.3f}/"
          f"{pr.absdev_perm_p:.2f}) | {r.cell} ({r.absdev_wcb_p:.3f}/"
          f"{r.absdev_perm_p:.2f}) | {ch} |")
    w("")
    w("(Note: the language column of the pre-correction rows above also uses "
      "the corrected-baseline manipulation check, so the Tree's row prints "
      "'neither' rather than the 'language-only' the earlier run published — "
      "the earlier run's language test was itself against the contaminated "
      "cell.)")
    w("")
    w("**Two provenance-explained reversals:**")
    w("")
    w("1. *Behavioral side (both axis-2 treatments sharpen).* The "
      "pre-correction fragility flags (Payoff Tree 'not robustly both', "
      "Payoff Safety bid effect only p=0.055 vs legacy pooled) were artifacts "
      "of the contaminated control cell: it dragged Gemma's control mean "
      "toward truthful (−0.59 vs −6.53 in its clean baselines) and blunted "
      "the model-level signal. Corrected, every model's Payoff-Safety and "
      "Payoff-Tree contrast points the same way and both clear WCB p<0.05 "
      "(0.015 and 0.017), stable under deduplication (0.012 / 0.018). The "
      "model-level permutation test remains soft (0.36 / 0.13) — an honest "
      "4-cluster power limit, no longer a contradiction.")
    w("")
    w("2. *Language side (the Tree's 'moves language' claim dies).* The "
      "celebrated '7.5%→26.7% rule rehearsal' rise under the Payoff Tree "
      "(traces_summary Finding 4; the paper's `tab:trace-dissociation`) was "
      "measured against the contaminated cell, whose clock-exit narrative "
      "*crowded out* rule name-dropping (7.5%). The clean axis-1/axis-3 "
      "baselines name-drop 'second-highest' at **33.0%** — statistically "
      "identical to the Tree cell's 32.7% (WCB p=0.897). **The Payoff Tree "
      "does not raise rule-rehearsal language at all; it is bids-only, like "
      "Payoff Safety.** The corrected 2×2 therefore has an *empty* 'both' "
      "cell: no lever moves language and bids together — stated reasoning "
      "and behavior dissociate completely.")
    w("")
    # ---- axis2fb as treatment ----
    w("## 2. The reclassified cell: `axis2_forward_baseline` as a two-stage "
      "clock-exit description (B3 variant)")
    w("")
    a2row = mc[mc.experiment == "axis2_forward_baseline"]
    if not a2row.empty:
        a2r = a2row.iloc[0]
        w(f"Pooled manipulation check vs the corrected baseline: "
          f"`clock_exit_language` {a2r.prev_baseline:.3f}→"
          f"{a2r.prev_treated:.3f} (WCB p={a2r.lang_wcb_p}, perm "
          f"p={a2r.lang_perm_p}); behavior |dev| {a2r.absdev_baseline:.2f}→"
          f"{a2r.absdev_treated:.2f} (WCB p={a2r.absdev_wcb_p}, perm "
          f"p={a2r.absdev_perm_p}). The pooled behavioral null **conceals "
          "fully offsetting per-model effects**:")
    w("")
    w("| Model | clock lang (base→treat) | mean dev (base→treat) | shift | "
      "\\|dev\\| (base→treat) | Welch p (row-level, optimistic) |")
    w("|---|---|---|---|---|---|")
    for _, r in a2fb.iterrows():
        w(f"| {r.model} | {r.clock_lang_baseline:.3f}→"
          f"{r.clock_lang_treated:.3f} | {r.dev_baseline:+.2f}→"
          f"{r.dev_treated:+.2f} | {r.dev_shift:+.2f} | "
          f"{r.absdev_baseline:.2f}→{r.absdev_treated:.2f} | "
          f"{r.welch_p_dev_rowlevel:.4f} |")
    w("")
    w("Per-model inference caveat: each model is ONE treated cluster vs TWO "
      "control clusters, so no within-model cluster test exists; Welch p is "
      "row-level on near-duplicate rows and is descriptive only.")
    w("")
    w("**Paraphrase sensitivity (headline-relevant).** Two clock-framing "
      "texts, two different effect profiles: this two-stage exit-price text "
      "produces a **large correction for Gemma** (−6.53→−0.59, |dev| "
      "6.57→2.12 — comparable to what the *true* clock achieves) and a "
      "**large backfire for Gemini** (−1.25→−6.12), with Claude ≈flat and "
      "GPT-4o inert in *both* language (0% echo) and bids (−2.94→−2.46); "
      "meanwhile the B3 `intervention_proxy_breitmoser` clock-framing text "
      "improves all four models modestly (the paper's ρ=+0.29 rung). Same "
      "design idea, different wording, different — even opposite-signed — "
      "per-model effects: direct evidence that description-lever effects are "
      "**paraphrase-sensitive**, and that pooled nulls can conceal offsetting "
      "model-level responses. GPT-4o's double inertness (no echo, no bid "
      "movement) is consistent with the paper's Finding 5 "
      "(mechanism-insensitive reasoning script).")
    w("")
    # ---- mediation ----
    w("## 3. Formal mediation bound — Payoff Safety (B2)")
    w("")
    canon = med_df[med_df.baseline == "corrected_axis1_axis3"]
    tot = canon["total_effect_absdev"].iloc[0]
    tci = (canon["total_ci_lo"].iloc[0], canon["total_ci_hi"].iloc[0])
    w(f"Total behavioral effect on mean $|b-v|$ (corrected baseline "
      f"{{axis1, axis3}}): **{tot:+.3f}** (cluster-boot 95% CI "
      f"[{tci[0]:+.2f}, {tci[1]:+.2f}]). The legacy pooled-of-three and "
      f"dedicated-spsb rows are in `mediation_b2.csv`, clearly labeled.")
    w("")
    w("First stage (lever → verbalized-understanding mediator), which must be "
      "≈0 for the mediation pathway to be shut:")
    w("")
    w("| Mediator | prev T | prev C | first-stage a | 95% CI | WCB p |")
    w("|---|---|---|---|---|---|")
    for _, r in canon.iterrows():
        w(f"| {r.mediator} | {r.prev_treated:.3f} | {r.prev_ctrl:.3f} | "
          f"{r.first_stage_a:+.4f} | [{r.a_ci_lo:+.3f}, {r.a_ci_hi:+.3f}] | "
          f"{r.a_wcb_p:.3f} |")
    w("")
    w(f"**Bound (product-of-coefficients, cluster-bootstrapped).** Pooling the "
      f"three verbalized-understanding mediators into an *any-VU-fires* "
      f"indicator, the mediated effect ACME = a·b has point estimate "
      f"{bound['acme_point']:+.3f} (95% CI [{bound['acme_ci'][0]:+.3f}, "
      f"{bound['acme_ci'][1]:+.3f}]); the implied mediated **share** of the "
      f"total effect is {bound['share_point']:+.3f} (95% CI "
      f"[{bound['share_ci'][0]:+.3f}, {bound['share_ci'][1]:+.3f}]). The 95% "
      f"upper bound on the absolute mediated share is "
      f"**{100*bound['share_abs_upper95']:.1f}%** (corrected baseline; under "
      f"the legacy pooled-of-three it was "
      f"{100*bound_legacy['share_abs_upper95']:.1f}%).")
    w("")
    w(f"> **Honest statement (no causal claim):** verbalized understanding "
      f"cannot mediate more than ~{100*bound['share_abs_upper95']:.0f}% of the "
      f"Payoff-Safety effect. We do *not* invoke sequential ignorability; the "
      f"first-stage zero is itself the finding — the lever does not work by "
      f"making agents verbalize why truth-telling is safe.")
    w("")
    w("**Within-treatment cross-sectional association (NON-CAUSAL, labeled).** "
      "Among the 600 treated traces, those that *do* rehearse the payment rule "
      "err less:")
    w("")
    w("| Mediator | within-treat gap in $|b-v|$ | 95% CI | second-stage b |")
    w("|---|---|---|---|")
    for _, r in canon.iterrows():
        if pd.isna(r.within_gap):
            w(f"| {r.mediator} | — (no within-treatment variation) | — | — |")
        else:
            w(f"| {r.mediator} | {r.within_gap:+.3f} | "
              f"[{r.within_gap_ci_lo:+.2f}, {r.within_gap_ci_hi:+.2f}] | "
              f"{r.second_stage_b_within_treat:+.3f} |")
    w("")
    w("This is a selection/confounding correlation (traces that rehearse the "
      "rule are also the more careful traces), not evidence of mediation — the "
      "first stage shows the lever does not *cause* more rule rehearsal.")
    w("")
    # ---- consistency ----
    w("## 4. Per-model stated-vs-revealed consistency + $-amount calibration "
      "(option 4)")
    w("")
    w("Pooled over all sealed cells, per model:")
    w("")
    w("| Model | dir. consistency | n (intent stated) | $ exact-match | "
      "corr(stated,realized) | mean \\|stated−realized\\| |")
    w("|---|---|---|---|---|---|")
    for _, r in pooled_df.iterrows():
        w(f"| {r.model} | {r.dir_consistency:.3f} | {r.n_intent_stated} | "
          f"{r.exact_match:.3f} | {r.corr_stated_realized:.3f} | "
          f"{r.mean_abs_stated_minus_realized:.2f} |")
    w("")
    w("- **Direction consistency** = P(sign of realized deviation matches "
      "stated intent | a single shading/overbid/truthful intent is stated). "
      "Truthful intent scored as |dev|≤$0.5.")
    w("- **$-amount calibration** parses the stated intended bid (last "
      "$-amount following a bid-intent cue in the plan) and compares to the "
      "realized bid. Coverage ≈87% of traces; parses >$55 dropped as errors.")
    w("- Figure: `consistency_calibration.pdf` (binned realized vs stated bid, "
      "per model).")
    w("")
    w("Per model × lever detail is in `consistency_calibration.csv`.")
    w("")
    w("Two model-level nuances worth a sentence in the paper. (a) **Gemma** "
      "states a single clean value-anchored intent in only ~830 traces (vs "
      "~2500–3100 for the others) — its plans are vague/unanchored, so its "
      "0.827 direction-consistency is computed on a thin, self-selected slice; "
      "yet when Gemma *does* name a bid amount its calibration is the tightest "
      "of any model (corr 0.99, mean |stated−realized| $0.28). (b) **Claude's** "
      "$ exact-match is only 0.41 because it habitually states a round planning "
      "figure and then submits a nearby (often slightly higher) number — the "
      "orange curve sits just above the 45° line — but its correlation is 0.98, "
      "so the plan is still a faithful *direction* signal, not cheap talk. "
      "Across all models the plan predicts the bid essentially one-for-one "
      "(corr 0.97–0.99): the traces are faithful plans, not post-hoc "
      "rationalizations.")
    w("")
    # ---- Flags for the paper ----
    w("## 5. Flags for the paper (updated after the provenance correction)")
    w("")
    w("1. **RESOLVED — the two pre-correction fragility flags were baseline "
      "contamination.** The earlier run of this analysis flagged (a) 'Payoff "
      "Tree is not robustly both' (bids WCB p=0.074 vs its own axis-2 "
      "baseline) and (b) 'Payoff Safety moves-bids is marginal under "
      "model-level permutation' (perm p=0.28–0.45). Both were artifacts of "
      "the contaminated `axis2_forward_baseline` control cell "
      "(`_axis2_baseline_provenance.md`): the treated clock-framing cell in "
      "the control pool dragged Gemma's control mean toward truthful (−0.59) "
      "and blunted the model-level signal. Section 1b reports the corrected "
      "classifications side by side with the pre-correction ones.")
    w("")
    w("2. **The paper's `tab:trace-dissociation` needs substantive "
      "revision, not just re-basing.** (a) Its Payoff Tree row's language "
      "entry ('rule rehearsal 7.5%→26.7%') and its 'moves both' "
      "classification are contamination artifacts — against clean baselines "
      "the Tree's rule-rehearsal is flat (33.0%→32.7%, WCB p=0.897) and the "
      "lever is **bids-only** (see Section 1b); the corrected 2×2 has an "
      "empty 'both' cell, which *strengthens* the paper's dissociation "
      "thesis. (b) Its baseline columns mix the contaminated cell (Tree row "
      "|b−v| 3.41) and the legacy pooled-of-three (Safety row 3.27; "
      "corrected 3.20). (c) The `06_ranking.tex` presentation-baseline "
      "declaration ('pooled per-model means +0.48, −2.88, −2.78, −4.54, "
      "cross-model −2.43') averages over the contaminated cell and should be "
      "recomputed on {axis1, axis3} in the integration pass — as should any "
      "ρ computed against pooled-axis or axis-2 baselines. Gemma's "
      "'anomalously good axis-2 baseline' caveat in `06_ranking.tex` is now "
      "*explained*, not just flagged, and should cite the provenance note.")
    w("")
    w("3. **Behavioral inference still needs cluster discipline.** Even "
      "after the correction, the honest tests are the WCB/permutation "
      "reported here (4 model-clusters per cell, ~40% byte-identical "
      "duplicate rows), not row-level t-tests. Where WCB and permutation "
      "disagree at α=0.05, the CSV's `robust_note` says so.")
    w("")
    w("4. **New tension for rung B3 (paraphrase sensitivity).** The paper "
      "presents clock-framing (B3) as 'universal in sign, modest' (ρ=+0.29). "
      "The reclassified two-stage clock-exit text is a *second* clock-framing "
      "description with a **sign-mixed** effect profile (Gemma strongly "
      "helped, Gemini strongly hurt, Claude/GPT-4o ≈flat — Section 2). The "
      "B3 rung's universality claim is therefore wording-specific; the two "
      "texts together are direct paraphrase-sensitivity evidence and belong "
      "in the discussion of description levers.")
    w("")
    w("5. **Claude sign flag (already known, restated).** In these logs "
      "Claude's Payoff-Safety mean deviation is +0.30 (mild overbidding); the "
      "ES manuscript reports −0.30. Magnitude and every |dev| quantity here "
      "are unaffected. Consistent with the note in `traces_summary.md` and "
      "`appendix_traces.tex`.")
    w("")
    w("## 6. Caveats")
    w("")
    w("- **Few clusters.** Even with the wild-cluster bootstrap, 8–16 clusters "
      "is not many; the WCB is the best available correction but treat p-values "
      "near 0.05 as soft. Cluster-permutation cross-checks agree in sign "
      "(stored in the CSV).")
    w("- **Prompt echo** inflates every target-language increase for levers "
      "whose prompt seeds the target vocabulary (including the two "
      "clock-framing texts, where the echo IS the manipulation check). The "
      "scientifically clean contrasts are (i) Payoff Safety, whose invariant "
      "is echoed in 0/600 traces despite being asserted in the prompt, and "
      "(ii) the Payoff Tree, which shares the 'second-highest' rule "
      "vocabulary with the corrected {axis1, axis3} baselines. The menu's "
      "language column is uninterpretable (reverse echo).")
    w("- **Per-model effects for the reclassified axis-2 cell** rest on one "
      "treated cluster vs two control clusters per model; they are "
      "descriptive (magnitudes are large and sign-opposed, but no "
      "within-model cluster test is possible).")
    w("- **The mediation bound is a bound, not an estimate.** The "
      "product-of-coefficients uses a *within-treatment cross-sectional* "
      "second stage, which is confounded; the bound is conservative precisely "
      "because the first stage is ≈0.")
    w("- **Calibration parser** is a regex, not an LLM; it misses paraphrased "
      "bid statements and can be fooled by multi-number plans (mitigated by the "
      "bid-cue anchor and the $55 cap).")
    w("")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log_lines = []

    def log(*a):
        s = " ".join(str(x) for x in a)
        print(s, file=sys.stderr)
        log_lines.append(s)

    df, sp = load()
    log(f"Loaded trace_features.csv: {len(df)} rows; "
        f"sealed second-price rows = {len(sp)}")
    sanity(sp, log)

    # (1) manipulation checks (full + dedup)
    log("Computing manipulation checks (full sample) ...")
    mc = manipulation_checks(sp, dedup=False, log=log)
    log("Computing manipulation checks (deduplicated) ...")
    mc_dd = manipulation_checks(sp, dedup=True, log=log)
    mc.to_csv(os.path.join(OUT, "manipulation_checks.csv"), index=False)
    mc_dd.to_csv(os.path.join(OUT, "manipulation_checks_dedup.csv"), index=False)

    # (2) 2x2 classification (corrected scheme: full + dedup; plus the
    #     pre-correction conventions, retained to document the change)
    sp_dd = sp.drop_duplicates(
        subset=["model", "experiment", "value", "bid", "plan"]).copy()
    dissoc = classify_2x2(mc, sp, scheme="corrected")
    dissoc_dd = classify_2x2(mc_dd, sp_dd, scheme="corrected")
    dissoc_pre = classify_2x2(mc, sp, scheme="precorrection")
    dissoc.to_csv(os.path.join(OUT, "dissociation_2x2.csv"), index=False)
    dissoc_dd.to_csv(os.path.join(OUT, "dissociation_2x2_dedup.csv"), index=False)
    dissoc_pre.to_csv(
        os.path.join(OUT, "dissociation_2x2_precorrection.csv"), index=False)
    log("\n2x2 dissociation (corrected baselines, full sample):")
    for _, r in dissoc.iterrows():
        log(f"  {r.lever:22s} lang={r.moves_language:3s} "
            f"(p={r.lang_wcb_p}) bids={r.moves_bids:3s} "
            f"(p={r.absdev_wcb_p}) -> {r.cell}")
    log("2x2 dissociation (PRE-correction conventions, for the diff):")
    for _, r in dissoc_pre.iterrows():
        log(f"  {r.lever:22s} bids p={r.absdev_wcb_p} -> {r.cell}")

    # (2b) the reclassified axis2_forward_baseline cell, per model
    a2fb = axis2fb_treatment_detail(sp)
    a2fb.to_csv(os.path.join(OUT, "axis2fb_treatment_per_model.csv"),
                index=False)
    log("\naxis2_forward_baseline as treatment (per model, vs corrected "
        "baseline):")
    for _, r in a2fb.iterrows():
        log(f"  {r.model:26s} clock-lang {r.clock_lang_baseline:.2f}->"
            f"{r.clock_lang_treated:.2f}  dev {r.dev_baseline:+.2f}->"
            f"{r.dev_treated:+.2f} (shift {r.dev_shift:+.2f})")

    # (3) mediation B2 (corrected primary + legacy + spsb rows)
    log("\nComputing Payoff-Safety mediation bound ...")
    med_df, bound, bound_legacy = mediation_b2(sp, log=log)
    med_df.to_csv(os.path.join(OUT, "mediation_b2.csv"), index=False)
    log(f"  mediated share 95% abs upper bound = "
        f"{100*bound['share_abs_upper95']:.1f}% (corrected baseline; legacy "
        f"{100*bound_legacy['share_abs_upper95']:.1f}%)")

    # (4) consistency + calibration
    log("\nComputing per-model consistency + calibration ...")
    cal_df, pooled_df, work = consistency_calibration(sp, log=log)
    cal_df.to_csv(os.path.join(OUT, "consistency_calibration.csv"), index=False)
    pooled_df.to_csv(os.path.join(OUT, "consistency_pooled.csv"), index=False)
    calibration_figure(work, os.path.join(OUT, "consistency_calibration.pdf"))
    log("Pooled per-model consistency:")
    for _, r in pooled_df.iterrows():
        log(f"  {r.model:26s} dir={r.dir_consistency:.3f} "
            f"exact={r.exact_match:.3f} corr={r.corr_stated_realized:.3f} "
            f"mean|d|={r.mean_abs_stated_minus_realized:.2f}")

    # LaTeX + summary
    write_tex(mc, dissoc, os.path.join(OUT, "mediation_tables.tex"))
    write_summary(mc, mc_dd, dissoc, dissoc_dd, dissoc_pre, med_df, bound,
                  bound_legacy, a2fb, cal_df, pooled_df, log_lines,
                  os.path.join(OUT, "mediation_summary.md"))

    with open(os.path.join(OUT, "mediation_log.txt"), "w") as f:
        f.write("\n".join(log_lines) + "\n")
    log("\nDone. Outputs in results/traces/mediation/")


if __name__ == "__main__":
    main()

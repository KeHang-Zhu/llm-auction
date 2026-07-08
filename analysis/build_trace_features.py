#!/usr/bin/env python3
"""
Reasoning-trace baseline analysis for the merged auction paper (auction-v2.tex).

Builds a transparent keyword/regex feature dictionary over the free-text 'plan'
reasoning traces emitted by every bidder in every auction round, then runs:

  (1) feature prevalence by model x lever family;
  (2) OLS: |deviation| ~ features + model FE + lever-family FE
      (cluster-robust by run directory);
  (3) signed deviation ~ stated intent (shading / overbid / truthful)
      -- sanity check that stated intents predict realized bids;
  (4) mediation sketch for the Payoff Safety lever
      (repo experiment `axis2_forward_onestep`; paper family B2):
      does the treatment raise safety/payment-rule verbalization, and does
      that verbalization predict smaller |deviation| within treatment?

Data sources
------------
A. Combined ES pipeline CSV (4 models x 23 sealed-bid SPSB experiments + one
   ascending-clock cell), one row per bidder-round, column `plan`:
     Engineering_simplicity/engineer_simplicity-main/results/
       all_experiments_combined_20260204_114522.csv
B. ES experiment_logs flat result JSONs for the two description cells missing
   from (A), all 4 models: intervention_menu (B1), intervention_proxy_breitmoser
   (B3 clock-framing; provenance caveat, see paper TODO plan R6).
C. Recovered GPT-4o V12 grid, `_first` (FPSB) and `_third` (TPSB) variants only
   (mechanism contrast; the un-suffixed V12 second-price cells duplicate (A)'s
   conditions under a different run and are deliberately excluded).

Baseline mapping (documented per task ground rules)
---------------------------------------------------
* Canonical sealed-bid SPSB baselines = pooled axis baselines
  {axis1_contingent_baseline, axis2_forward_baseline, axis3_beliefs_baseline}.
* The paper's published Payoff Safety comparison (06_ranking.tex, -2.67 ->
  -1.53) uses the `spsb` cell as baseline; we therefore report the mediation
  first stage against BOTH baselines.
* Payoff Safety (paper family B2) = repo experiment `axis2_forward_onestep`
  (verified: pooled mean dev -1.53; per-model -0.38/-1.88/-4.17 match
  06_ranking.tex; Claude +0.30 here vs -0.30 in the draft -- sign flagged).

Reproducibility: numpy seed 1299 for all bootstraps.

Outputs (all under results/traces/):
  trace_features.csv        one row per trace with metadata + binary features
  feature_prevalence_model_family.csv   prevalence table (long format)
  ols_results.txt           full statsmodels output for models (2)-(4)
  (traces_summary.md, BRAINSTORM.md, traces_subsection.tex are written by hand,
   informed by these numbers)
"""

import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

REPO = "/Users/kehangzh/Desktop/llm-auction"
ES = os.path.join(REPO, "Engineering_simplicity", "engineer_simplicity-main")
COMBINED_CSV = os.path.join(
    ES, "results", "all_experiments_combined_20260204_114522.csv")
V12 = os.path.join(REPO, "recovered_logs", "experiment_logs_gpt_4o", "V12")
OUT = os.path.join(REPO, "results", "traces")
os.makedirs(OUT, exist_ok=True)

np.random.seed(1299)
N_BOOT = 2000

# ---------------------------------------------------------------------------
# 1. Feature dictionary (tuned on actual traces; see traces_summary.md)
# ---------------------------------------------------------------------------
# All matching is on lowercased text. Features are binary (regex present).
FEATURES = {
    # -- normative-recognition features -------------------------------------
    # Recognizes/echoes dominance or truthfulness as the *reason* for the bid.
    "dominance_language": r"dominant strateg|weakly dominant|\bdominance\b|dominated strateg|is dominant|truthful",
    # States intent to bid exactly own value.
    "truthful_intent": r"bid(?:ding)? (?:exactly )?(?:my|your) (?:own |true |full )?value|bid at my (?:true )?value|equal to my (?:true )?value|bid(?:ding)? (?:my|your) true value",
    # Correctly rehearses the second-price payment rule (pays second-highest /
    # pays what others bid), beyond a bare mechanism name-drop.
    "payment_rule_correct": r"pay(?:s|ing)?(?: only)? the second[- ]highest|second[- ]highest bid(?:der)?s? (?:sets|determines|becomes)|pay what (?:the )?others? bid|i (?:would |will |only )?pay the second",
    # Any mention of "second-highest"/"second-price" (weaker: rule name-drop).
    "second_price_mention": r"second[- ]highest|second[- ]price",
    # Calls the (second-price) auction "first-price" -- explicit mechanism
    # confusion when it occurs in a second/third-price cell.
    "first_price_mention": r"first[- ]price",
    # -- opponent / belief reasoning ----------------------------------------
    "opponent_modeling": r"other (?:bidders?|players?)[’']? ?(?:will|might|may|likely|tend|could|probably|are likely)|others (?:will|might|may|probably)|they (?:will|might|may|probably) bid|assum\w+[^.]{0,45}other|expect\w*[^.]{0,45}(?:other bidders?|competitors?|rivals?|opponents?)|competitors? (?:will|might|may)|opponents? (?:will|might|may)|rivals? (?:will|might|may|bid)",
    "probability_reasoning": r"probabilit|chance[s]? of winning|likelihood",
    "expected_value_reasoning": r"expected (?:value|profit|payoff|utility)|in expectation",
    # -- stated bid intent (value-anchored) ----------------------------------
    "shading_intent": r"(?:below|under|less than|lower than) my (?:own |true )?value|shad(?:e|ing)|discount(?:ing)? my value|just under my (?:true )?value",
    "overbid_intent": r"bid(?:ding)? (?:slightly |a (?:bit|little) |just |marginally |well )?(?:above|over|higher than) my (?:own |true )?value|buffer above my value|bid above (?:my|your) value",
    # -- safety / risk rhetoric ----------------------------------------------
    # Worst-case / guarantee framing (target of axis1_contingent_worstcase).
    "worst_case": r"worst[- ]case|at worst|worst that (?:can|could) happen|downside|guarantee",
    # Echo of the Payoff Safety invariant ("bid determines IF you win, not
    # WHAT you pay") or no-loss safety statements.
    "safety_recognition": r"can'?t lose|cannot lose|no risk of los|risk[- ]free|nothing to lose|at no cost|determin\w+ (?:if|whether) (?:i|you) win|not what (?:i|you) (?:will )?pay|pay what others bid|maximum price|(?:my|your) bid only (?:sets|determines)",
    # Fear of overpaying / winner's-remorse rhetoric.
    "overpay_concern": r"overpay(?:ing)?|overbid(?:ding)?|pay(?:ing)? more than (?:my|the|its|it'?s|what it'?s)? ?(?:value|worth)|more than the item is worth",
    # "Bidding my value leaves zero profit" fallacy (false in SPSB except ties).
    "zero_profit_fallacy": r"(?:zero|no|little(?: to no)?) profit",
    # Profit-margin / buffer rhetoric used to justify shading.
    "margin_language": r"profit margin|margin for profit|room for profit|buffer|leave (?:some |a little |a )?room",
    # -- style ----------------------------------------------------------------
    "conservative_language": r"conservativ",
    "aggressive_language": r"aggressiv",
    "risk_language": r"\brisk",
}

FEATURE_COLS = list(FEATURES.keys())

# ---------------------------------------------------------------------------
# 2. Lever-family mapping (repo experiment -> family used for FE) and the
#    paper-facing label (06_ranking.tex families).
# ---------------------------------------------------------------------------
def lever_family(exp: str) -> str:
    e = exp.replace("_first", "").replace("_third", "")
    if e == "spsb":
        return "baseline_spsb"          # canonical SPSB baseline (paper A rung)
    if e.startswith("ascending_clock"):
        return "clock"                   # extensive-form change (paper A)
    if e == "axis2_forward_onestep":
        return "payoff_safety_B2"        # paper B2 "Payoff Safety" description
    if e == "intervention_menu":
        return "menu_B1"                 # paper B1 menu restatement
    if e == "intervention_proxy_breitmoser":
        return "clock_framing_B3"        # paper B3 clock-framing description
    if e.startswith("axis1_contingent"):
        return "contingent_C1"           # paper C1 contingent scaffolds
    if e == "axis2_forward_tree":
        return "payoff_tree_C1"          # paper C1 Payoff Tree
    if e in ("axis2_forward_baseline", "axis2_forward_backward_induct"):
        return "planning_C2"             # paper C2 planning scaffolds
    if e.startswith("axis3_beliefs"):
        return "beliefs_C3"              # paper C3 belief scaffolds
    if e.startswith("risk"):
        return "risk_D"                  # paper D preference framings
    if e.startswith("loss_aversion"):
        return "loss_D"                  # paper D preference framings
    if e.startswith("intervention_risk"):
        return "risk_D"
    if e.startswith("intervention_"):
        return "strategy_reveal"         # NE/nash/wrong strategy reveals (V12)
    return "other"


AXIS_BASELINES = {"axis1_contingent_baseline", "axis2_forward_baseline",
                  "axis3_beliefs_baseline"}

# ---------------------------------------------------------------------------
# 3. Load data
# ---------------------------------------------------------------------------
def load_combined() -> pd.DataFrame:
    df = pd.read_csv(COMBINED_CSV)
    out = pd.DataFrame({
        "source": "combined_csv",
        "model": df["model"],
        "experiment": df["experiment"],
        "mechanism": np.where(df["experiment"].eq("ascending_clock_closed"),
                              "ascending_clock", "spsb_sealed"),
        "run_id": df["model"].str[:12] + "|" + df["experiment"] + "|" + df["timestamp"],
        "value": df["player_value"].astype(float),
        "bid": df["bid"].astype(float),
        "plan": df["plan"].astype(str),
    })
    return out


def _rows_from_result_json(path, model, experiment, mechanism, source, run_id):
    """Parse one result_*.json (round_0 layout: value[], bidding history, plan[])."""
    rows = []
    try:
        with open(path) as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        return rows
    for rkey, rd in d.items():
        if not isinstance(rd, dict) or "plan" not in rd:
            continue
        vals = rd.get("value", [])
        hist = (rd.get("history") or {}).get("bidding history", [])
        plans = rd.get("plan", [])
        if not (len(vals) == len(hist) == len(plans)):
            continue  # skip malformed rounds rather than misalign
        for i, (v, h, p) in enumerate(zip(vals, hist, plans)):
            rows.append({
                "source": source, "model": model, "experiment": experiment,
                "mechanism": mechanism, "run_id": run_id,
                "value": float(v), "bid": float(h["bid"]), "plan": str(p),
            })
    return rows


def load_menu_proxy() -> pd.DataFrame:
    """ES experiment_logs flat result files: menu + proxy_breitmoser, 4 models."""
    model_map = {"gpt4o": "gpt-4o", "claude": "claude-3-5-haiku-20241022",
                 "gemini": "gemini-2.0-flash", "gemma": "google/gemma-3-27b-it"}
    rows = []
    for mdir, model in model_map.items():
        for exp in ("intervention_menu", "intervention_proxy_breitmoser"):
            files = sorted(glob.glob(os.path.join(
                ES, "experiment_logs", mdir, exp, "result_*.json")))
            run_id = f"{model[:12]}|{exp}|flat"
            for fp in files:
                rows.extend(_rows_from_result_json(
                    fp, model, exp, "spsb_sealed", "es_logs_flat", run_id))
    return pd.DataFrame(rows)


def load_v12_first_third() -> pd.DataFrame:
    """Recovered GPT-4o V12 grid, `_first` (FPSB) / `_third` (TPSB) cells only."""
    rows = []
    for fam in sorted(os.listdir(V12)):
        if not (fam.endswith("_first") or fam.endswith("_third")):
            continue
        mech = "fpsb_sealed" if fam.endswith("_first") else "tpsb_sealed"
        for run_dir in sorted(glob.glob(os.path.join(V12, fam, "run_*"))):
            run_id = f"gpt-4o|{fam}|{os.path.basename(run_dir)}"
            for fp in sorted(glob.glob(os.path.join(
                    run_dir, "raw_data", "result_*.json"))):
                rows.extend(_rows_from_result_json(
                    fp, "gpt-4o", fam, mech, "v12_recovered", run_id))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Build feature matrix
# ---------------------------------------------------------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    low = df["plan"].str.lower()
    for name, pat in FEATURES.items():
        df[name] = low.str.contains(pat, regex=True).astype(int)
    df["n_words"] = low.str.split().str.len()
    df["deviation"] = df["bid"] - df["value"]
    df["abs_dev"] = df["deviation"].abs()
    df["family"] = df["experiment"].map(lever_family)
    return df


def cluster_boot_ci(frame, stat_fn, n_boot=N_BOOT):
    """Cluster (run_id) bootstrap CI for a scalar statistic. Seeded globally."""
    clusters = frame["run_id"].unique()
    stats = []
    for _ in range(n_boot):
        pick = np.random.choice(clusters, size=len(clusters), replace=True)
        boot = pd.concat([frame[frame["run_id"] == c] for c in pick])
        stats.append(stat_fn(boot))
    return np.percentile(stats, [2.5, 97.5])


def main():
    print("Loading data ...", file=sys.stderr)
    combined = load_combined()
    menu_proxy = load_menu_proxy()
    v12 = load_v12_first_third()
    df = pd.concat([combined, menu_proxy, v12], ignore_index=True)
    df = add_features(df)
    df.to_csv(os.path.join(OUT, "trace_features.csv"), index=False)
    print(f"trace_features.csv: {len(df)} rows "
          f"(combined={len(combined)}, menu/proxy={len(menu_proxy)}, "
          f"v12 first/third={len(v12)})", file=sys.stderr)

    # ---- (1) prevalence by model x family (second-price cells + clock) -----
    main_df = df[df["mechanism"].isin(["spsb_sealed", "ascending_clock"])].copy()
    prev = (main_df.groupby(["model", "family"])[FEATURE_COLS]
            .mean().round(4).reset_index())
    prev["n_traces"] = (main_df.groupby(["model", "family"])
                        .size().reset_index(drop=True))
    prev.to_csv(os.path.join(OUT, "feature_prevalence_model_family.csv"),
                index=False)

    # Mechanism contrast prevalence (GPT-4o only: spsb vs fpsb vs tpsb).
    g4 = df[df["model"] == "gpt-4o"]
    mech_prev = g4.groupby("mechanism")[FEATURE_COLS].mean().round(4)
    mech_prev["n"] = g4.groupby("mechanism").size()
    mech_prev.to_csv(os.path.join(OUT, "feature_prevalence_mechanism_gpt4o.csv"))

    lines = []
    def emit(s=""):
        lines.append(s)
        print(s)

    emit("=" * 78)
    emit("TRACE FEATURE ANALYSIS -- OLS + mediation results")
    emit(f"rows total={len(df)}; sealed second-price rows={len(main_df[main_df.mechanism=='spsb_sealed'])}")
    emit("Deviations in $ (values Unif{0..49}); SMAD normalizer E[b*]=24.5.")
    emit("Cluster-robust SEs, clustered on run_id (run directory / flat cell).")
    emit("=" * 78)

    # ---- (2) OLS: |dev| ~ features + model FE + family FE ------------------
    # Restricted to sealed-bid second-price cells, where bid=value is the
    # dominant strategy and |deviation| is unambiguously an error.
    reg = main_df[main_df["mechanism"] == "spsb_sealed"].copy()
    feats_in_model = [c for c in FEATURE_COLS if reg[c].std() > 0]
    f2 = ("abs_dev ~ " + " + ".join(feats_in_model)
          + " + C(model) + C(family)")
    m2 = smf.ols(f2, data=reg).fit(
        cov_type="cluster", cov_kwds={"groups": reg["run_id"]})
    emit("\n### MODEL (2): |deviation| ~ features + model FE + family FE"
         " (sealed second-price cells)\n")
    emit(str(m2.summary()))
    # Comparison: FE-only model, to isolate incremental R2 of text features.
    m2_fe = smf.ols("abs_dev ~ C(model) + C(family)", data=reg).fit(
        cov_type="cluster", cov_kwds={"groups": reg["run_id"]})
    emit(f"\nR2 with features = {m2.rsquared:.4f}; "
         f"R2 FE only = {m2_fe.rsquared:.4f}; "
         f"incremental R2 of text features = {m2.rsquared - m2_fe.rsquared:.4f}")

    # ---- (3) signed deviation ~ stated intent -------------------------------
    f3 = ("deviation ~ shading_intent + overbid_intent + truthful_intent"
          " + C(model) + C(family)")
    m3 = smf.ols(f3, data=reg).fit(
        cov_type="cluster", cov_kwds={"groups": reg["run_id"]})
    emit("\n### MODEL (3): signed deviation ~ stated intent"
         " (sealed second-price cells)\n")
    emit(str(m3.summary()))

    # Stated-vs-revealed consistency table.
    emit("\n### Stated-vs-revealed consistency (sealed second-price cells)")
    shd = reg[reg["shading_intent"] == 1]
    ovb = reg[reg["overbid_intent"] == 1]
    tru = reg[reg["truthful_intent"] == 1]
    emit(f"shading_intent traces: n={len(shd)}, share with dev<0: "
         f"{(shd['deviation'] < 0).mean():.3f}, mean dev {shd['deviation'].mean():+.2f}")
    emit(f"overbid_intent traces: n={len(ovb)}, share with dev>0: "
         f"{(ovb['deviation'] > 0).mean():.3f}, mean dev {ovb['deviation'].mean():+.2f}")
    emit(f"truthful_intent traces: n={len(tru)}, share with |dev|<=0.5: "
         f"{(tru['abs_dev'] <= 0.5).mean():.3f}, mean |dev| {tru['abs_dev'].mean():.2f}")
    none = reg[(reg[["shading_intent", "overbid_intent", "truthful_intent"]]
                .sum(axis=1)) == 0]
    emit(f"no stated intent: n={len(none)}, mean dev {none['deviation'].mean():+.2f}, "
         f"mean |dev| {none['abs_dev'].mean():.2f}")

    # FPSB validity check: shading language should be (and is) modal where
    # shading is actually optimal.
    fp = df[df["mechanism"] == "fpsb_sealed"]
    sp_g4 = reg[reg["model"] == "gpt-4o"]
    emit("\n### Dictionary validity check (GPT-4o): shading_intent prevalence")
    emit(f"FPSB (shading optimal): {fp['shading_intent'].mean():.3f} (n={len(fp)})")
    emit(f"SPSB (truthful optimal): {sp_g4['shading_intent'].mean():.3f} (n={len(sp_g4)})")

    # ---- (4) Mediation sketch: Payoff Safety --------------------------------
    emit("\n### MODEL (4): mediation sketch -- Payoff Safety (axis2_forward_onestep)")
    emit("Mediators: safety_recognition (invariant echo), payment_rule_correct,")
    emit("           second_price_mention (weak rule name-drop).")
    treat = reg[reg["experiment"] == "axis2_forward_onestep"].copy()
    for base_name, base_set in [
            ("pooled axis baselines (canonical)", AXIS_BASELINES),
            ("spsb cell (paper's published comparison)", {"spsb"})]:
        ctrl = reg[reg["experiment"].isin(base_set)].copy()
        both = pd.concat([treat.assign(treated=1), ctrl.assign(treated=0)])
        emit(f"\n-- baseline = {base_name}: n_treat={len(treat)}, n_ctrl={len(ctrl)}")
        emit(f"   mean dev: treated {treat['deviation'].mean():+.3f} vs "
             f"control {ctrl['deviation'].mean():+.3f}; "
             f"mean |dev|: {treat['abs_dev'].mean():.3f} vs {ctrl['abs_dev'].mean():.3f}")
        for med in ["safety_recognition", "payment_rule_correct",
                    "second_price_mention"]:
            a = smf.ols(f"{med} ~ treated + C(model)", data=both).fit(
                cov_type="cluster", cov_kwds={"groups": both["run_id"]})
            emit(f"   1st stage {med}: treated coef = {a.params['treated']:+.4f} "
                 f"(p={a.pvalues['treated']:.3f}); "
                 f"prevalence T={treat[med].mean():.3f} vs C={ctrl[med].mean():.3f}")
        # Second stage within treatment.
        for med in ["safety_recognition", "payment_rule_correct",
                    "second_price_mention"]:
            if treat[med].std() == 0:
                emit(f"   2nd stage {med}: NA (no variation within treatment)")
                continue
            b = smf.ols(f"abs_dev ~ {med} + C(model)", data=treat).fit(
                cov_type="cluster", cov_kwds={"groups": treat["run_id"]})
            lo, hi = cluster_boot_ci(
                treat, lambda fr, m=med: (fr.loc[fr[m] == 1, "abs_dev"].mean()
                                          - fr.loc[fr[m] == 0, "abs_dev"].mean())
                if fr[m].nunique() > 1 else np.nan)
            emit(f"   2nd stage {med} (within treatment): coef = "
                 f"{b.params[med]:+.4f} (p={b.pvalues[med]:.3f}); "
                 f"raw gap boot 95% CI [{lo:+.3f}, {hi:+.3f}] (seed 1299)")

    # ---- Robustness: deduplicate byte-identical traces ----------------------
    # ~40% of sealed-bid rows are exact duplicates (same model+experiment+value
    # -> same plan AND same bid; sampling at temp 0.5 is near-deterministic
    # conditional on the value draw). Re-run models (2)/(3) on unique traces.
    dd = reg.drop_duplicates(subset=["model", "experiment", "value",
                                     "bid", "plan"]).copy()
    emit(f"\n### Robustness: deduplicated traces (n={len(dd)} of {len(reg)})")
    m2d = smf.ols(f2, data=dd).fit(
        cov_type="cluster", cov_kwds={"groups": dd["run_id"]})
    m2d_fe = smf.ols("abs_dev ~ C(model) + C(family)", data=dd).fit(
        cov_type="cluster", cov_kwds={"groups": dd["run_id"]})
    emit(f"Model (2) dedup: R2 = {m2d.rsquared:.4f} (FE only {m2d_fe.rsquared:.4f}; "
         f"incremental {m2d.rsquared - m2d_fe.rsquared:.4f})")
    keep = ["shading_intent", "overbid_intent", "truthful_intent",
            "payment_rule_correct", "conservative_language", "overpay_concern"]
    emit("key coefs (full-sample -> dedup):")
    for k in keep:
        emit(f"  {k}: {m2.params[k]:+.3f} -> {m2d.params[k]:+.3f} "
             f"(dedup p={m2d.pvalues[k]:.4f})")
    m3d = smf.ols(f3, data=dd).fit(
        cov_type="cluster", cov_kwds={"groups": dd["run_id"]})
    emit("Model (3) dedup intent coefs: "
         f"shading {m3d.params['shading_intent']:+.3f}, "
         f"overbid {m3d.params['overbid_intent']:+.3f}, "
         f"truthful {m3d.params['truthful_intent']:+.3f} (all vs no-intent ref)")

    # Secondary: worst-case lever raises worst_case language? (manipulation check)
    emit("\n### Manipulation check: axis1_contingent_worstcase vs axis1 baseline")
    wc = reg[reg["experiment"] == "axis1_contingent_worstcase"]
    wb = reg[reg["experiment"] == "axis1_contingent_baseline"]
    emit(f"worst_case language: treatment {wc['worst_case'].mean():.3f} vs "
         f"baseline {wb['worst_case'].mean():.3f}")
    emit(f"mean |dev|: treatment {wc['abs_dev'].mean():.3f} vs "
         f"baseline {wb['abs_dev'].mean():.3f}")

    with open(os.path.join(OUT, "ols_results.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\nWrote", os.path.join(OUT, "ols_results.txt"), file=sys.stderr)


if __name__ == "__main__":
    main()

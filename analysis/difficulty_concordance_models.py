"""
Rank concordance of the difficulty ordering: reconstructed humans vs EACH LLM.

WHAT THIS DOES
--------------
Generalizes analysis/difficulty_concordance.py (human vs GPT-4o only) to the
five models in the paper's capability ladder.  For each model it recomputes
per-format SMADs from bid level, then reports Kendall's tau-b between the
human anchor ranking and the model's SMAD ranking over

    (i)  the three sealed formats FPSB IPV, SPSB IPV, SP-APV  ("sealed3"),
         which every model has with n >= MIN_N, and
    (ii) every format the model has with n >= MIN_N            ("all_usable").

Human anchors (results/reconstruction_bands/bands.csv paper points):
    FPSB IPV 24.7639, SPSB IPV 5.646, SP-APV 9.31, AC 3.54, AC-B 5.83.

LLM cells:
    GPT-4o            experiment_logs/V10 (the published V10 cells; the
                      published-value asserts of difficulty_concordance.py
                      are kept for this model only).
    Claude 3.5 Haiku  robustness_logs/<key>_claude_sonnet   (claude-3-5-haiku-20241022)
    Gemini 2.0 Flash  robustness_logs/<key>_gemini          (gemini-2.0-flash)
    GPT-5-mini        robustness_logs/<key>_gpt5mini        (gpt-5-mini; no clock cells)
    Llama-3-8B        robustness_logs/<key>_llama           (meta-llama/Meta-Llama-3-8B-Instruct)

SMAD per cell = 100 * mean |b - b*(v)| / SCALING, with b*(v) = (2/3) v for
FPSB (N=3 uniform IPV) and b*(v) = v elsewhere; clock cells use non-winners
only (the winner's exit price is censored).  SCALING = 25 as in the paper.

UNCERTAINTY (same three layers as difficulty_concordance.py; B=2000, seed 1299)
    (a) LLM bootstrap: within-cell resampling of per-bid deviations, human fixed.
    (b) Human re-draws: reconstruction-calibration re-draws from
        difficulty_concordance.human_redraw_matrix() (replicates the published
        fragility_checks draws), LLM fixed.  Columns are subset to the formats
        in use.
    (c) Joint: LLM draw b paired with human re-draw b.

With k formats and no ties tau-b takes only k(k-1)/2 + 1 values; with the
three sealed formats the support is {-1, -1/3, +1/3, +1}.

OUTPUTS
-------
    results/analysis/difficulty_concordance_models.json
    results/analysis/difficulty_concordance_models.md
    results/analysis/difficulty_concordance_models.csv
    writeup/tables/concordance.tex   (tabular-only booktabs fragment)

Run (from repo root):
    python3 analysis/difficulty_concordance_models.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "analysis") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "analysis"))

# Reuse the GPT-4o cells, the human anchors, tau-b and the human re-draw
# machinery from the single-model script so nothing can drift from it.
import difficulty_concordance as dc  # noqa: E402

SEED = dc.SEED            # 1299
B = dc.B                  # 2000
SCALING = dc.SCALING      # 25.0
FORMATS = dc.FORMATS      # ["FPSB IPV", "SPSB IPV", "SP-APV", "AC", "AC-B"]
HUMAN_SMAD = dc.HUMAN_SMAD
MIN_N = 30

ROBUST = PROJECT_ROOT / "robustness_logs"
OUT_DIR = PROJECT_ROOT / "results" / "analysis"
TEX_DIR = PROJECT_ROOT / "writeup" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TEX_DIR.mkdir(parents=True, exist_ok=True)

SEALED3 = ["FPSB IPV", "SPSB IPV", "SP-APV"]

# robustness_logs directory key per format, and b*(v) / clock flag per format
FORMAT_KEY = {
    "FPSB IPV": "fpsb_ipv",
    "SPSB IPV": "spsb_ipv",
    "SP-APV": "spsb_apv",
    "AC": "ascending_clock_apv",
    "AC-B": "ascending_clock_apv_closed",
}
BSTAR = {fmt: dc.CELLS[fmt]["bstar"] for fmt in FORMATS}
IS_CLOCK = {fmt: dc.CELLS[fmt]["clock"] for fmt in FORMATS}

# Model registry.  `suffix` is the robustness_logs directory suffix; `model_id`
# is the value in the CSV `model` column (asserted, so a misnamed CSV such as
# ascending_clock_apv_closed_llama/.../*_gemini_results.csv is still checked
# by content rather than by filename).
MODELS = {
    "GPT-4o": dict(source="v10", tex="GPT-4o"),
    "Claude 3.5 Haiku": dict(source="robustness", suffix="claude_sonnet",
                             model_id="claude-3-5-haiku-20241022", tex="Claude 3.5 Haiku"),
    "Gemini 2.0 Flash": dict(source="robustness", suffix="gemini",
                             model_id="gemini-2.0-flash", tex="Gemini 2.0 Flash"),
    "GPT-5-mini": dict(source="robustness", suffix="gpt5mini",
                       model_id="gpt-5-mini", tex="GPT-5-mini"),
    "Llama-3-8B": dict(source="robustness", suffix="llama",
                       model_id="meta-llama/Meta-Llama-3-8B-Instruct", tex="Llama-3-8B"),
}

# Hand-computed SMADs (verified once from the CSVs) used as a soft
# consistency check for the robustness models; GPT-4o keeps the hard asserts
# of difficulty_concordance.load_llm_deviations().
EXPECTED_SMAD = {
    "Claude 3.5 Haiku": {"FPSB IPV": 24.09, "SPSB IPV": 9.72, "SP-APV": 9.58, "AC": 5.74},
    "Gemini 2.0 Flash": {"FPSB IPV": 27.05, "SPSB IPV": 3.01, "SP-APV": 8.02, "AC-B": 1.26},
    "GPT-5-mini": {"FPSB IPV": 0.08, "SPSB IPV": 0.20, "SP-APV": 1.36},
    "Llama-3-8B": {"FPSB IPV": 38.16, "SPSB IPV": 54.89, "SP-APV": 53.08, "AC": 104.1, "AC-B": 67.0},
}


# ---------------------------------------------------------------------------
# Bid-level deviations
# ---------------------------------------------------------------------------
def _read_cell_dir(cell_dir: Path) -> pd.DataFrame | None:
    """Concatenate all results CSVs under a robustness cell directory.

    Skips '*merged*' files when non-merged files exist; de-duplicates on
    (repetition_id, round, player_name).  Returns None if no CSV is present.
    """
    files = sorted(cell_dir.glob("**/results/*_results.csv"))
    if not files:
        return None
    non_merged = [f for f in files if "merged" not in f.name]
    if non_merged:
        files = non_merged
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df = df.drop_duplicates(subset=["repetition_id", "round", "player_name"])
    return df


def load_robustness_deviations(spec: dict) -> tuple[dict, dict]:
    """Per-bid |b - b*(v)| for every format cell available for a model."""
    devs, notes = {}, {}
    for fmt in FORMATS:
        cell_dir = ROBUST / f"{FORMAT_KEY[fmt]}_{spec['suffix']}"
        df = _read_cell_dir(cell_dir)
        if df is None:
            notes[fmt] = "no results CSV"
            continue
        models = set(df["model"].unique())
        assert models == {spec["model_id"]}, f"{cell_dir}: model ids {models}"
        if IS_CLOCK[fmt]:
            df = df[~df["is_winner"].astype(bool)].copy()
        devs[fmt] = np.abs(df["bid"].to_numpy(float)
                           - BSTAR[fmt](df["player_value"].to_numpy(float)))
    return devs, notes


def load_model_deviations(name: str) -> tuple[dict, dict]:
    spec = MODELS[name]
    if spec["source"] == "v10":
        devs, _, _ = dc.load_llm_deviations()     # hard asserts vs published values
        return devs, {}
    return load_robustness_deviations(spec)


def smad_of(dev: np.ndarray) -> float:
    return float(100.0 * dev.mean() / SCALING)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def bootstrap_smads(devs: dict, fmts: list[str], rng: np.random.Generator) -> np.ndarray:
    """(B, len(fmts)) within-cell resampled SMAD vectors.

    Same draw order as difficulty_concordance.bootstrap_llm_smads (per draw,
    then per format), so for GPT-4o over all five formats the matrix is
    identical to the one behind the published single-model numbers.
    """
    out = np.empty((B, len(fmts)))
    for b in range(B):
        for k, fmt in enumerate(fmts):
            d = devs[fmt]
            out[b, k] = 100.0 * rng.choice(d, size=len(d), replace=True).mean() / SCALING
    return out


def tau_dist(t: np.ndarray) -> dict:
    vals, counts = np.unique(np.round(t, 6), return_counts=True)
    return {f"{v:+.4f}": int(c) for v, c in zip(vals, counts)}


def concordance_block(devs: dict, fmts: list[str], hum_full: np.ndarray) -> dict:
    """Point tau-b plus the three uncertainty layers for one (model, format set)."""
    idx = [FORMATS.index(f) for f in fmts]
    human = HUMAN_SMAD[idx]
    hum = hum_full[:, idx]
    llm = np.array([smad_of(devs[f]) for f in fmts])
    ns = np.array([len(devs[f]) for f in fmts])

    tau_hand = dc.kendall_tau_b(human, llm)
    tau_scipy = stats.kendalltau(human, llm, variant="b").statistic
    assert abs(tau_hand - tau_scipy) < 1e-12, (tau_hand, tau_scipy)

    rng = np.random.default_rng(SEED)
    llm_boot = bootstrap_smads(devs, fmts, rng)

    taus_a = np.array([dc.kendall_tau_b(human, llm_boot[b]) for b in range(B)])
    taus_b = np.array([dc.kendall_tau_b(hum[b], llm) for b in range(B)])
    taus_j = np.array([dc.kendall_tau_b(hum[b], llm_boot[b]) for b in range(B)])

    i_fp, i_sp = fmts.index("FPSB IPV"), fmts.index("SPSB IPV")
    llm_fp_hardest = llm_boot.argmax(axis=1) == i_fp
    hum_fp_hardest = hum.argmax(axis=1) == i_fp
    llm_fp_gt_sp = llm_boot[:, i_fp] > llm_boot[:, i_sp]
    hum_fp_gt_sp = hum[:, i_fp] > hum[:, i_sp]

    def layer(t):
        ci = np.percentile(t, [2.5, 97.5])
        return {"ci95": [float(ci[0]), float(ci[1])],
                "frac_tau_positive": float(np.mean(t > 0)),
                "tau_distribution": tau_dist(t)}

    return {
        "formats": fmts,
        "n_formats": len(fmts),
        "human_smad": human.tolist(),
        "llm_smad": llm.tolist(),
        "llm_n": ns.tolist(),
        "tau_point": float(tau_hand),
        "fpsb_minus_spsb_llm": float(llm[i_fp] - llm[i_sp]),
        "fpsb_gt_spsb_llm_point": bool(llm[i_fp] > llm[i_sp]),
        "layer_a_llm_bootstrap": layer(taus_a),
        "layer_b_human_redraws": layer(taus_b),
        "layer_c_joint": layer(taus_j),
        # FPSB ranked hardest (strict max over the formats in use) ...
        "fpsb_hardest_share_llm": float(np.mean(llm_fp_hardest)),
        "fpsb_hardest_share_human": float(np.mean(hum_fp_hardest)),
        "fpsb_hardest_share_joint": float(np.mean(llm_fp_hardest & hum_fp_hardest)),
        "fpsb_hardest_every_draw": bool(np.all(llm_fp_hardest & hum_fp_hardest)),
        # ... and the FPSB-minus-SPSB sign
        "fpsb_gt_spsb_share_llm": float(np.mean(llm_fp_gt_sp)),
        "fpsb_gt_spsb_share_human": float(np.mean(hum_fp_gt_sp)),
        "fpsb_gt_spsb_share_joint": float(np.mean(llm_fp_gt_sp & hum_fp_gt_sp)),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def fmt_set_label(fmts: list[str]) -> str:
    extra = [f for f in fmts if f not in SEALED3]
    if len(fmts) == 5:
        return "all five"
    if not extra:
        return "3 sealed"
    return "3 sealed + " + " + ".join(extra)


def tex_num(x: float, nd: int = 2) -> str:
    s = f"{abs(x):.{nd}f}"
    return f"${'-' if x < 0 else '+'}{s}$"


def tex_ci(lo: float, hi: float) -> str:
    def one(v):
        return f"{'-' if v < 0 else '+'}{abs(v):.2f}"
    return f"$[{one(lo)}, {one(hi)}]$"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    hum_full = dc.human_redraw_matrix()
    # cross-check the human re-draws are the published ones
    assert float(np.mean(hum_full[:, 0] > hum_full[:, 1])) == 1.0
    assert abs(float(np.mean(hum_full[:, 4] < hum_full[:, 2])) - 0.926) < 0.01

    results = {
        "statistic": "Kendall tau-b, human vs LLM SMAD ranking, per model",
        "seed": SEED, "B": B, "scaling": SCALING, "min_n": MIN_N,
        "formats_canonical": FORMATS,
        "human_smad_canonical": HUMAN_SMAD.tolist(),
        "tau_support_note": ("with k formats and no ties tau-b takes k(k-1)/2+1 values; "
                             "for the 3 sealed formats the support is {-1, -1/3, +1/3, +1}; "
                             "for 4 formats {-1, -2/3, -1/3, 0, +1/3, +2/3, +1}; "
                             "for 5 formats {-1, -0.8, ..., +0.8, +1}"),
        "models": {},
    }
    csv_rows = []
    verify_lines = []

    for name, spec in MODELS.items():
        devs, notes = load_model_deviations(name)
        smads = {f: smad_of(devs[f]) for f in FORMATS if f in devs}
        ns = {f: int(len(devs[f])) for f in FORMATS if f in devs}
        usable = [f for f in FORMATS if f in devs and ns[f] >= MIN_N]
        assert all(f in usable for f in SEALED3), f"{name}: sealed formats below MIN_N"

        # soft verification against the hand-computed values
        for f, exp in EXPECTED_SMAD.get(name, {}).items():
            got = smads.get(f, np.nan)
            flag = "OK" if abs(got - exp) < 0.01 else "MISMATCH"
            verify_lines.append(f"  {name:17s} {f:8s} expected {exp:7.2f}  got {got:7.2f} (n={ns.get(f, 0):3d})  {flag}")

        blocks = {"sealed3": concordance_block(devs, SEALED3, hum_full),
                  "all_usable": concordance_block(devs, usable, hum_full)}

        results["models"][name] = {
            "source": spec["source"],
            "model_id": spec.get("model_id", "gpt-4o"),
            "smad_by_format": smads,
            "n_by_format": ns,
            "missing_or_excluded": {**notes,
                                    **{f: f"n={ns[f]} < MIN_N" for f in ns if ns[f] < MIN_N}},
            "usable_formats": usable,
            "format_sets": blocks,
        }
        for set_name, blk in blocks.items():
            csv_rows.append({
                "model": name,
                "format_set": set_name,
                "n_formats": blk["n_formats"],
                "formats": "|".join(blk["formats"]),
                "tau_point": round(blk["tau_point"], 6),
                "ci_llm_lo": round(blk["layer_a_llm_bootstrap"]["ci95"][0], 6),
                "ci_llm_hi": round(blk["layer_a_llm_bootstrap"]["ci95"][1], 6),
                "ci_human_lo": round(blk["layer_b_human_redraws"]["ci95"][0], 6),
                "ci_human_hi": round(blk["layer_b_human_redraws"]["ci95"][1], 6),
                "ci_joint_lo": round(blk["layer_c_joint"]["ci95"][0], 6),
                "ci_joint_hi": round(blk["layer_c_joint"]["ci95"][1], 6),
                "p_tau_pos_joint": round(blk["layer_c_joint"]["frac_tau_positive"], 6),
                "fpsb_hardest_share": round(blk["fpsb_hardest_share_joint"], 6),
                "fpsb_gt_spsb_share": round(blk["fpsb_gt_spsb_share_llm"], 6),
            })

    # --- GPT-4o over all five formats must reproduce the single-model script
    g = results["models"]["GPT-4o"]["format_sets"]["all_usable"]
    assert g["n_formats"] == 5
    assert abs(g["tau_point"] - 0.6) < 1e-12
    assert g["layer_a_llm_bootstrap"]["ci95"] == [0.6, 0.6], g["layer_a_llm_bootstrap"]["ci95"]
    assert g["layer_c_joint"]["ci95"] == [0.4, 1.0], g["layer_c_joint"]["ci95"]
    assert g["layer_c_joint"]["frac_tau_positive"] == 1.0
    ref_path = OUT_DIR / "difficulty_concordance.json"
    if ref_path.exists():
        ref = json.loads(ref_path.read_text())
        assert ref["layer_a_llm_bootstrap"]["ci95"] == g["layer_a_llm_bootstrap"]["ci95"]
        assert ref["layer_c_joint"]["ci95"] == g["layer_c_joint"]["ci95"]
        results["crosscheck_vs_difficulty_concordance_json"] = "GPT-4o all-five layer CIs identical"

    # --- write JSON / CSV
    (OUT_DIR / "difficulty_concordance_models.json").write_text(json.dumps(results, indent=2))
    csv_cols = ["model", "format_set", "n_formats", "formats", "tau_point",
                "ci_llm_lo", "ci_llm_hi", "ci_human_lo", "ci_human_hi",
                "ci_joint_lo", "ci_joint_hi", "p_tau_pos_joint",
                "fpsb_hardest_share", "fpsb_gt_spsb_share"]
    csv_df = pd.DataFrame(csv_rows, columns=csv_cols)
    csv_df.to_csv(OUT_DIR / "difficulty_concordance_models.csv", index=False)

    # --- markdown
    def pct(x):
        return f"{x*100:.1f}%"

    smad_rows = []
    for name, m in results["models"].items():
        cells = []
        for f in FORMATS:
            if f in m["smad_by_format"]:
                mark = "" if f in m["usable_formats"] else " (excl.)"
                cells.append(f"{m['smad_by_format'][f]:.2f} (n={m['n_by_format'][f]}){mark}")
            else:
                cells.append("--")
        smad_rows.append(f"| {name} | " + " | ".join(cells) + " |")
    human_row = "| Human (reconstruction) | " + " | ".join(f"{h:.2f}" for h in HUMAN_SMAD) + " |"

    res_rows = []
    for name, m in results["models"].items():
        for set_name in ("all_usable", "sealed3"):
            blk = m["format_sets"][set_name]
            if set_name == "sealed3" and blk["n_formats"] == m["format_sets"]["all_usable"]["n_formats"]:
                continue  # identical to all_usable; avoid duplicate row
            a, b_, j = blk["layer_a_llm_bootstrap"], blk["layer_b_human_redraws"], blk["layer_c_joint"]
            res_rows.append(
                f"| {name} | {fmt_set_label(blk['formats'])} ({blk['n_formats']}) | "
                f"{blk['tau_point']:+.2f} | [{a['ci95'][0]:+.2f}, {a['ci95'][1]:+.2f}] | "
                f"[{b_['ci95'][0]:+.2f}, {b_['ci95'][1]:+.2f}] | "
                f"[{j['ci95'][0]:+.2f}, {j['ci95'][1]:+.2f}] | {pct(j['frac_tau_positive'])} | "
                f"{pct(blk['fpsb_hardest_share_joint'])} | "
                f"{'+' if blk['fpsb_gt_spsb_llm_point'] else '-'} ({pct(blk['fpsb_gt_spsb_share_llm'])}) |")

    # handles for the data-driven prose below
    R = results["models"]
    cl3 = R["Claude 3.5 Haiku"]["format_sets"]["sealed3"]
    cl4 = R["Claude 3.5 Haiku"]["format_sets"]["all_usable"]
    ge4 = R["Gemini 2.0 Flash"]["format_sets"]["all_usable"]
    g5 = R["GPT-5-mini"]["format_sets"]["sealed3"]
    ll = R["Llama-3-8B"]["format_sets"]["sealed3"]
    g43 = R["GPT-4o"]["format_sets"]["sealed3"]
    ge3 = R["Gemini 2.0 Flash"]["format_sets"]["sealed3"]

    def share_at_one(blk, layer):
        return blk[layer]["tau_distribution"].get("+1.0000", 0) / B

    n_ties = sum(c for k, c in cl3["layer_a_llm_bootstrap"]["tau_distribution"].items()
                 if k not in ("-1.0000", "-0.3333", "+0.3333", "+1.0000"))
    cl3_flip = cl3["layer_a_llm_bootstrap"]["tau_distribution"].get("+1.0000", 0) / B
    ge4_zero = ge4["layer_c_joint"]["tau_distribution"].get("+0.0000", 0)

    md = f"""# Difficulty-ordering concordance: reconstructed humans vs each LLM

*Generated by `analysis/difficulty_concordance_models.py`, seed {SEED}, B={B}, MIN_N={MIN_N}.
Generalizes `difficulty_concordance.py` (GPT-4o only) to the five models of the
capability ladder; the GPT-4o all-five row reproduces that script exactly.*

## Per-format SMADs (100 * mean|b - b*(v)| / {SCALING:.0f}; clock cells non-winners only)

| | FPSB IPV | SPSB IPV | SP-APV | AC | AC-B |
|---|---:|---:|---:|---:|---:|
{human_row}
{chr(10).join(smad_rows)}

Cells marked "(excl.)" have n < {MIN_N} and are dropped from the "all usable" set; "--" means
no results CSV exists (GPT-5-mini was never run in the clock formats).

## Kendall tau-b, human anchor ranking vs LLM SMAD ranking

Columns: point tau-b; 95% percentile CIs for (a) LLM within-cell bid resampling with the
human ranking fixed, (b) human reconstruction re-draws with the LLM ranking fixed, (c) joint;
P(tau>0) in joint draws; share of joint draws in which FPSB is ranked hardest on both sides;
sign of the LLM's FPSB-minus-SPSB SMAD gap and the share of LLM draws in which it is positive
(the human side has FPSB > SPSB in 100% of re-draws).

| Model | formats (k) | tau-b | (a) LLM CI | (b) human CI | (c) joint CI | P(tau>0) joint | FPSB hardest (joint) | FPSB>SPSB (LLM) |
|---|---|---:|---|---|---|---:|---:|---:|
{chr(10).join(res_rows)}

Support note: with k formats and no ties tau-b takes only k(k-1)/2 + 1 values. Over the
three sealed formats it lives on {{-1, -1/3, +1/3, +1}}, so a "3 sealed" tau of +0.33 means
exactly one discordant pair and the CIs are unions of those four points; over four formats
the support is {{-1, -2/3, ..., +2/3, +1}} and over five {{-1, -0.8, ..., +0.8, +1}}. A
resampled LLM vector can contain an exact tie between two cells, which moves tau-b off this
lattice (e.g. 2/sqrt(6) = +0.82); this happened in {n_ties} of {B} Claude sealed-3 draws.

## Reading

* **GPT-4o** (all five formats): tau-b = +0.60, layer-(a) CI degenerate at [+0.60, +0.60],
  joint CI [+0.40, +1.00], tau > 0 in 100% of joint draws; FPSB hardest on both sides in every
  draw. Identical to `difficulty_concordance.md`. Over the three sealed formats the point
  value is +1.00 and stays there in {pct(share_at_one(g43, 'layer_c_joint'))} of joint draws
  (the rest are +0.33; every layer's 95% CI is [+1.00, +1.00]).
* **Claude 3.5 Haiku** (3 sealed + AC): tau-b = {cl4['tau_point']:+.2f}, joint CI
  [{cl4['layer_c_joint']['ci95'][0]:+.2f}, {cl4['layer_c_joint']['ci95'][1]:+.2f}], tau > 0 in
  {pct(cl4['layer_c_joint']['frac_tau_positive'])} of joint draws. The single discordance is
  SPSB IPV ({cl3['llm_smad'][1]:.2f}) > SP-APV ({cl3['llm_smad'][2]:.2f}), a
  {cl3['llm_smad'][1]-cl3['llm_smad'][2]:.2f}-point gap that bid resampling reverses in
  {cl3_flip*100:.0f}% of draws; hence over the three sealed formats the point value is
  {cl3['tau_point']:+.2f} but the layer-(a) CI is
  [{cl3['layer_a_llm_bootstrap']['ci95'][0]:+.2f}, {cl3['layer_a_llm_bootstrap']['ci95'][1]:+.2f}]
  (the human side almost never moves it: layer-(b) CI
  [{cl3['layer_b_human_redraws']['ci95'][0]:+.2f}, {cl3['layer_b_human_redraws']['ci95'][1]:+.2f}]).
* **Gemini 2.0 Flash** (3 sealed + AC-B): tau-b = {ge4['tau_point']:+.2f} (discordance: AC-B
  below SPSB IPV, the same AC-B pair that costs GPT-4o); +1.00 over the three sealed formats,
  in every LLM-bootstrap draw and {pct(share_at_one(ge3, 'layer_c_joint'))} of joint draws.
  Over the four usable formats the layer-(a) CI is degenerate at
  [{ge4['layer_a_llm_bootstrap']['ci95'][0]:+.2f}, {ge4['layer_a_llm_bootstrap']['ci95'][1]:+.2f}];
  the joint CI [{ge4['layer_c_joint']['ci95'][0]:+.2f}, {ge4['layer_c_joint']['ci95'][1]:+.2f}] and
  P(tau>0) = {pct(ge4['layer_c_joint']['frac_tau_positive'])} come from the human re-draws
  (tau = +0.33 in draws where the human AC-B re-draw rises above SP-APV; the {ge4_zero} draws
  at tau = 0 are those where the human SP-APV re-draw falls below both SPSB IPV and AC-B).
* **GPT-5-mini** (3 sealed only): tau-b = {g5['tau_point']:+.2f}. Its SMADs are
  {g5['llm_smad'][0]:.2f} / {g5['llm_smad'][1]:.2f} / {g5['llm_smad'][2]:.2f}, i.e. it bids the
  theory benchmark almost exactly in every format. There is no difficulty gradient left to
  rank -- the model sits at the **theory ceiling** -- so its ordering is uninformative about
  the human ordering rather than evidence against it. Concretely, bid resampling reverses its
  FPSB-vs-SPSB order in {pct(1-g5['fpsb_gt_spsb_share_llm'])} of draws, so P(tau>0) =
  {pct(g5['layer_c_joint']['frac_tau_positive'])} is essentially the coin-flip rate of a
  0.1-point gap; FPSB is never its hardest format.
* **Llama-3-8B** (3 sealed only): tau-b = {ll['tau_point']:+.2f}, tau > 0 in
  {pct(ll['layer_c_joint']['frac_tau_positive'])} of joint draws. SMADs are
  {ll['llm_smad'][0]:.0f} / {ll['llm_smad'][1]:.0f} / {ll['llm_smad'][2]:.0f} in the sealed
  cells and {R['Llama-3-8B']['smad_by_format']['AC']:.0f} / {R['Llama-3-8B']['smad_by_format']['AC-B']:.0f}
  in the (n<{MIN_N}) clock cells: uniformly far from the benchmark in every format, i.e. the
  **noise floor**. The perfectly inverted ordering reflects that SPSB/SP-APV overbidding is
  unbounded while an FPSB bid in [0, v] can deviate from (2/3)v by at most v/3 on the low
  side, not a meaningful difficulty judgement.

The human-ordering concordance is therefore a property of the mid-capability models
(GPT-4o, Claude 3.5 Haiku, Gemini 2.0 Flash), which all place FPSB hardest and rank the
remaining formats close to the human order; it disappears at both ends of the capability
ladder for opposite reasons.

## Caveats

Human-side uncertainty is reconstruction/calibration uncertainty (the parametric bootstrap of
`analysis/reconstruction_bands.py`), not human sampling error; the LLM CIs treat bids as
i.i.d. within cells (no clustering by round/session); the robustness-log cells are smaller
(n = 87-90 sealed, 46 clock) than the V10 GPT-4o cells (270-291 / 106-114), so their layer-(a)
CIs are wider; clock cells with n = 2 or 8 (Claude AC-B, Gemini AC, Llama AC/AC-B) are
reported but excluded from every tau; with k <= 5 formats tau-b is a coarse statistic taking
few values, and with k = 3 a single discordant pair moves it by 2/3.
"""
    (OUT_DIR / "difficulty_concordance_models.md").write_text(md)

    # --- LaTeX tabular fragment (booktabs; no table env / caption / label)
    tex_lines = [
        r"\begin{tabular}{llrlrlr}",
        r"\toprule",
        r"Model & Formats used ($n\geq 30$) & $\tau_b$ (all usable) & Joint 95\% CI & "
        r"$P(\tau_b>0)$ & $\tau_b$ (3 sealed) & FPSB$>$SPSB \\",
        r"\midrule",
    ]
    for name, m in results["models"].items():
        au, s3 = m["format_sets"]["all_usable"], m["format_sets"]["sealed3"]
        j = au["layer_c_joint"]
        fp_sign = "yes" if au["fpsb_gt_spsb_llm_point"] else "no"
        tex_lines.append(
            f"{MODELS[name]['tex']} & {fmt_set_label(au['formats'])} ({au['n_formats']}) & "
            f"{tex_num(au['tau_point'])} & {tex_ci(*j['ci95'])} & "
            f"{j['frac_tau_positive']*100:.0f}\\% & {tex_num(s3['tau_point'])} & "
            f"{fp_sign} ({au['fpsb_gt_spsb_share_llm']*100:.0f}\\%) \\\\"
        )
    tex_lines += [r"\bottomrule", r"\end{tabular}"]
    (TEX_DIR / "concordance.tex").write_text("\n".join(tex_lines) + "\n")

    # --- console
    print("SMAD verification vs hand-computed values (robustness models):")
    print("\n".join(verify_lines))
    print("\nGPT-4o all-five reproduces difficulty_concordance.py: "
          f"tau={g['tau_point']:.2f}, (a) CI {g['layer_a_llm_bootstrap']['ci95']}, "
          f"joint CI {g['layer_c_joint']['ci95']}, P(tau>0)={g['layer_c_joint']['frac_tau_positive']:.3f}")
    print()
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(csv_df.to_string(index=False))
    print(f"\nWrote {OUT_DIR/'difficulty_concordance_models.{json,md,csv}'} and {TEX_DIR/'concordance.tex'}")


if __name__ == "__main__":
    main()

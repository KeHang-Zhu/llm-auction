# PROVENANCE FINDING (2026-07-08): `axis2_forward_baseline` is not a neutral baseline

## What was found

The three `axis2_forward_*.txt` rule templates were never in the current repo tree — the
frontier battery failed on launch with `No such file: rule_template/auctions/axis2_forward_tree.txt`.
Recovery from the `engineer_simplicity` git history (`~/P_llm_auctions/engineer_simplicity`,
commit `89cf2896` "add results", 2026-02-03; deleted/renamed in `82106a70`, 2026-02-05) shows:

- `axis2_forward_onestep.txt` = the **Payoff Safety** text ("Your bid only matters for
  determining IF you win, not HOW MUCH you pay") — as the paper assumes. ✓
- `axis2_forward_tree.txt` = the **Payoff Tree** text (PATH A / PATH B decision tree). ✓
- `axis2_forward_baseline.txt` = **NOT a plain SPSB description.** It is a two-stage
  sealed-bid-as-clock-exit description ("STAGE 1: Sealed Bid ... determines your exit price
  for STAGE 2: Ascending Clock ... when the clock reaches your sealed bid, you automatically
  exit"). I.e., a Breitmoser-style clock-framing variant. The file survives as
  `rule_template/auctions/axis2_forward_baseline_DEPRECATED.txt` (byte-identical rename).

All four incumbent V12 `axis2_forward_baseline` runs (2026-02-03 22:27–22:42) fall inside the
window when this two-stage text was the live template, and all four run configs reference
`special_name: axis2_forward_baseline.txt`.

## Evidence it moved behavior (from existing data; no new runs needed)

Trace check (`results/traces/trace_features.csv`): share of plans containing
clock/exit/stage-2 language —

| cell | claude | gemini | gemma | gpt-4o |
|---|---|---|---|---|
| axis1_contingent_baseline | 0.0% | 0.0% | 0.0% | 0.0% |
| **axis2_forward_baseline** | **17.3%** | **24.7%** | **15.3%** | 0.0% |
| axis3_beliefs_baseline | 0.0% | 0.0% | 0.0% | 0.0% |

Behavior (`auction_cells.csv`, mean_dev): gemma **−0.59** under axis2-baseline vs −7.1 / −5.9 / −5.3
under axis1 / axis3 / spsb (framing ≈ fixes gemma, like the true clock does); gemini **−6.12** vs
−0.8 / −1.7 / −1.6 (framing strongly backfires for gemini); claude +0.37 and gpt-4o −2.46 ≈ flat.
GPT-4o neither echoes the framing nor moves — consistent with the paper's Finding 5
(mechanism-insensitive reasoning script).

## Implications

1. **POOLED_axis_baseline is contaminated** for claude/gemini/gemma (one of its three cells is
   treated). Every contrast wired against POOLED_axis_baseline or against `axis2_forward_baseline`
   (the builder contrasts axis-2 treatments — Payoff Safety B2, Payoff Tree C1 — against it)
   is biased toward zero (or away, for gemini). This mechanically explains two flags already
   raised: (a) the paper's "anomalously good Gemma axis-2 baseline"; (b) the mediation
   re-analysis finding that Payoff Tree's bid effect weakens vs its own-axis baseline.
2. **Reclassification**: `axis2_forward_baseline` should enter the taxonomy as a second
   clock-framing-style description cell (B3 variant, "two-stage exit-price description"),
   run on all four models — not as a baseline. Note the tension it creates with rung B3:
   this framing text produced strong effects only for gemma (helped) and gemini (hurt),
   while `intervention_proxy_breitmoser` produced the paper's d=−1.21 GPT-4o effect —
   two clock-framing texts, different effects: direct paraphrase-sensitivity evidence.
3. **Recomputation needed (integration pass)**: pooled axis baseline := {axis1, axis3} only;
   axis-2 treatment contrasts vs pooled(axis1,axis3) or the dedicated spsb cell; re-run
   `analysis/build_trace_mediation.py` and the ranking tier tests with the corrected baseline.
4. The frontier battery keeps the same three templates (restored verbatim from `89cf2896`)
   so frontier cells remain comparable to incumbent cells; the relabeling happens in analysis,
   not in the run configs.

## Files restored (verbatim from engineer_simplicity `89cf2896`)

- `rule_template/auctions/axis2_forward_onestep.txt`
- `rule_template/auctions/axis2_forward_tree.txt`
- `rule_template/auctions/axis2_forward_baseline.txt` (= the two-stage text; identical to
  `axis2_forward_baseline_DEPRECATED.txt`, restored under its config-referenced name so the
  V12-era configs and the frontier clones run unmodified)

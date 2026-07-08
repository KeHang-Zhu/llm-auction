# Reasoning-trace baseline analysis — summary

**Produced by:** `analysis/build_trace_features.py` (deterministic; bootstrap seed numpy 1299).
**Outputs:** `results/traces/trace_features.csv` (21,990 traces × 17 binary features + metadata),
`results/traces/feature_prevalence_model_family.csv`,
`results/traces/feature_prevalence_mechanism_gpt4o.csv`,
`results/traces/ols_results.txt` (full statsmodels output),
`results/traces/traces_subsection.tex` (draft LaTeX fragment),
`results/traces/BRAINSTORM.md` (ranked deeper options).

## Data

| Source | Rows | Clusters (run dirs) | Content |
|---|---|---|---|
| `all_experiments_combined_20260204_114522.csv` | 13,416 | 92 | 4 models × 23 sealed-bid SPSB cells + AC-closed, `plan` column |
| ES `experiment_logs/<model>/{intervention_menu, intervention_proxy_breitmoser}` | 1,167 | 8 | B1 menu + B3 clock-framing, all 4 models (flat result JSONs) |
| `recovered_logs/experiment_logs_gpt_4o/V12/*_{first,third}` | 7,407 | 52 | GPT-4o FPSB (3,711) + TPSB (3,696) mechanism contrast |

Un-suffixed V12 second-price cells were deliberately **excluded** (they duplicate combined-CSV conditions under a different run). Every trace row carries `run_id` (run directory, or model|experiment for flat cells) used for cluster-robust SEs.

**Baseline mapping used (per task ground rules):** canonical sealed-bid SPSB baseline = pooled axis baselines {`axis1_contingent_baseline`, `axis2_forward_baseline`, `axis3_beliefs_baseline`}; the mediation first stage is *also* reported against the `spsb` cell because that is the comparison published in `06_ranking.tex` (−2.67 → −1.53). **Payoff Safety (paper family B2) = repo experiment `axis2_forward_onestep`** — verified by exact match of pooled (−1.53) and per-model means (Gemini −0.38, GPT-4o −1.88, Gemma −4.17) to the draft. ⚠ Sign flag: the draft says Claude −0.49 → **−0.30**; the data give **+0.30** (same magnitude, overbidding). The writing pass should reconcile.

## Feature dictionary (17 regex features; full patterns in the script)

Normative recognition: `dominance_language`, `truthful_intent`, `payment_rule_correct`, `second_price_mention`, `first_price_mention` (mechanism confusion in 2nd/3rd-price cells). Opponent/beliefs: `opponent_modeling`, `probability_reasoning`, `expected_value_reasoning`. Stated intent (value-anchored): `shading_intent`, `overbid_intent`. Safety/risk rhetoric: `worst_case`, `safety_recognition` (echo of the B2 invariant / "can't lose"), `overpay_concern`, `zero_profit_fallacy`, `margin_language`. Style: `conservative_language`, `aggressive_language`, `risk_language`. The originally suggested safety phrases ("no risk", "can't lose", "nothing to lose") turned out to be **essentially absent** from real traces (see finding 4), so the dictionary was re-tuned on actual language ("overpay", "profit margin", "buffer", "zero profit").

## Findings

### 1. What models say: first-price reasoning in a second-price auction

Pooled prevalence over the 14,073 sealed second-price traces: `shading_intent` 53%, `overpay_concern` 55%, `margin_language` 31%, `probability_reasoning` 37%. Normative recognition is **rare**: `dominance_language` 2.1%, `payment_rule_correct` 3.8%, `truthful_intent` 6.8% (bare "second-highest" name-drop 28%). The modal story a model tells itself is textbook *first-price* logic — shade below value to protect a profit margin and avoid overpaying — applied to a mechanism where truthful bidding is dominant.

Model fingerprints (prevalence per model, sealed 2nd-price cells):
- **Gemini-2.0-flash**: near-pure shader — `shading_intent` 86%, `overbid_intent` 4.5%.
- **Claude-3.5-Haiku**: the only model that explicitly calls the auction "first-price" (10.0% of traces vs ≤0.1% elsewhere); also the most `overbid_intent` (30%) and most `truthful_intent` (12.6%) — noisiest stated strategy.
- **Gemma-3-27b**: least value-anchored language (`shading_intent` 10.6%) but most `opponent_modeling` (49%), `conservative_language` (75%), `overpay_concern` (83%); its vague, unanchored plans coincide with the largest bid errors.
- **GPT-4o**: `shading_intent` 67.5%; highest `zero_profit_fallacy` (2.6%: "bidding my value risks zero profit").

### 2. Stated intent predicts realized bids (dictionary validity)

- `shading_intent` traces: n=7,469, **97.1% underbid** (mean dev −1.84).
- `overbid_intent` traces: n=1,797, **87.6% overbid** (mean dev +1.88).
- `truthful_intent` traces: n=950, 77.6% within ±$0.50 of value (mean |dev| 1.03).
- **No stated intent** traces: n=4,541, mean dev **−4.84**, mean |dev| 5.51 — the un-anchored plans are where the big errors live (e.g. "bid slightly above half my value").

So the plans are *not* cheap talk: the stated direction almost always matches the realized bid. The failure is in *which* plan is chosen, not in plan–action consistency.

### 3. OLS: |deviation| ~ features + model FE + family FE (honest verdict)

Full output in `ols_results.txt`. R² = **0.251** with features vs **0.176** with FE only → **incremental R² of text features ≈ 0.075**. Statistically solid (cluster-robust by run) but modest: traces explain some, far from most, of the error variance. Largest stable coefficients (in $ of |deviation|): any value-anchored intent — `shading_intent` −2.06, `overbid_intent` −2.18, `truthful_intent` −1.50 (all vs the unanchored-reference traces), `payment_rule_correct` −0.77, `conservative_language` +0.76. Coefficients are stable when byte-identical duplicate traces are dropped (n=8,839; see robustness block).

**Verdict for the paper:** the pooled linear model is an appendix table, not a headline — its value is (a) showing that *articulating any value-anchored plan* is worth ~$1.5–2 of error reduction relative to vague plans, and (b) providing regression discipline behind Findings 2 and 4, which *are* main-text material.

### 4. Mediation sketch: a double dissociation (main-text material)

- **Payoff Safety (B2, `axis2_forward_onestep`) changes behavior without changing stated reasoning.** Behavior: mean dev −2.67 → −1.53 (vs `spsb`), mean |dev| 3.27 → 1.95 (vs pooled axis baselines). Language: the Vickrey invariant it asserts ("bid determines IF you win, not WHAT you pay") is echoed in **0 of 600** treated traces (3 of 21,990 overall); `payment_rule_correct` is *flat* (2.8% treated vs 3.5% axis-baseline, p=0.66). First stage of any classical mediation ≈ 0. Within treatment, traces that do rehearse the payment rule err less (|dev| −1.54, p<0.001; cluster-bootstrap 95% CI [−2.15, −0.56], seed 1299) — cross-sectional, not causal.
- **The worst-case scaffold (C1, `axis1_contingent_worstcase`) changes stated reasoning without changing behavior.** `worst_case` language jumps 2% → 43% (manipulation check passes) while |dev| moves 3.24 → 3.07 and mean dev −2.42 → −2.81.
- **Payoff Tree (C1, `axis2_forward_tree`) moves both**: "second-highest" rehearsal 7.5% → 26.7% and |dev| 3.41 → 1.29.

Interpretation: interventions act on bids *without passing through verbalized understanding* — stated plans keep the same shading rhetoric and simply shrink the shade to epsilon (e.g. "bid $31.9 on value $32 to keep a profit margin"). This supports describing B2 as changing *behavior*, not *stated comprehension*, and cautions against reading the traces as faithful mediators.

### 5. Mechanism-insensitive reasoning scripts (GPT-4o, V12 FPSB/TPSB)

Across the three sealed formats, GPT-4o's baseline traces and bids are nearly identical although optima differ sharply (SPSB: bid value; FPSB n=3 RNNE: ≈⅔·value; TPSB n=3: bid *above* value):

| Format | mean dev | mean bid/value | shading language | "second-highest" mention |
|---|---|---|---|---|
| SPSB | −2.78 | 0.88 | 70% | 25% |
| FPSB | −3.15 | 0.87 | 79% | 0% |
| TPSB | −3.40 | 0.84 | 72% | 0% |

One shading script for all payment rules: it *under*-shades where shading is optimal (FPSB) and *over*-shades where truthfulness is optimal (SPSB/TPSB). This is trace-level evidence for the paper's claim that the failure is mechanism comprehension, not optimization effort.

## Data-quality caveats

1. **~40% byte-identical duplicate traces** in the sealed-bid cells (same model+experiment+value ⇒ identical plan *and* bid; temp 0.5 is near-deterministic conditional on the value draw; 100% of duplicate groups share one value and one bid). Full-sample SEs are therefore optimistic; all headline coefficients re-run on deduplicated data (n=8,839) are stable (`ols_results.txt`, robustness block). Effective N per cell ≈ number of distinct value draws, not number of rows.
2. **Cluster counts**: 92 combined runs; the menu/proxy flat dirs give only 1 cluster per model×cell (8 total), so B1/B3 family SEs lean on few clusters.
3. **Keyword features are surface-level**: no negation handling (by design, `overpay_concern` counts "avoid overpaying" — it is concern rhetoric either way); `safety_recognition` has prevalence 3/21,990, so its OLS coefficient is meaningless noise (flagged in output).
4. **`intervention_proxy_breitmoser` provenance ambiguity** (paper TODO plan R6, iterative clock vs sealed clock-framing): the ES `experiment_logs` cells used here are treated as the sealed-bid B3 description; audit before quoting its family FE.
5. **V12 side is GPT-4o only** — Finding 5 needs the other models before it can be claimed as general (cheap to run: the dictionary is fixed).
6. The `plan` field is a stated plan (median 68 words), not a full chain of thought; models may compute more (or less) than they verbalize. Findings 2/4 should be phrased as *stated-reasoning* results.
6b. **Prompt-echo confound for rule-rehearsal features**: `second_price_mention`/`payment_rule_correct` partly echo the prompt's own vocabulary — the menu (B1) prompt removes the "second-highest" phrasing and its traces show 0% rehearsal by construction. Within-lever comparisons (e.g. Payoff Safety vs axis baselines, which share the standard rule text) are unaffected; cross-lever language comparisons involving B1 are not meaningful.
7. Ascending-clock traces (510 rows) are per-decision exit rationales, structurally different from sealed-bid plans; they are in `trace_features.csv` (mechanism = `ascending_clock`) but excluded from the OLS.

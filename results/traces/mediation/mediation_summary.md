# Formal mediation / process analysis of the trace double dissociation — summary (provenance-corrected baselines)

**Produced by:** `analysis/build_trace_mediation.py` (deterministic; numpy seed 1299; wild-cluster bootstrap 2000 reps, cluster permutation 5000 reps).  
**Input:** the frozen `results/traces/trace_features.csv` (21,990 traces) — no new data.  
**Outputs (all under `results/traces/mediation/`):** `manipulation_checks.csv`, `dissociation_2x2.csv` (+ `dissociation_2x2_precorrection.csv`), `mediation_b2.csv`, `axis2fb_treatment_per_model.csv`, `consistency_calibration.csv`, `consistency_calibration.pdf`, `mediation_tables.tex`, this file.

This upgrade promotes the descriptive mediation *sketch* of Finding 4 (`traces_summary.md`) to a defensible process analysis: (1) a manipulation-check table over **every** auction lever; (2) the 2×2 *moves-language × moves-bids* classification, tested rather than asserted; (3) a formal — and deliberately *bounded* — mediation statement for Payoff Safety; (4) per-model stated-vs-revealed consistency + $-amount calibration (option 4). This revision incorporates the **axis-2 baseline provenance correction** (`results/merged_ranking/_axis2_baseline_provenance.md`) throughout.

## 0. The provenance correction (what changed and why)

The V12 `axis2_forward_baseline` template — recovered from the engineer_simplicity git history and preserved as `rule_template/auctions/axis2_forward_baseline_DEPRECATED.txt` — was **not a plain SPSB description**: it was a two-stage sealed-bid-as-clock-exit (Breitmoser-style clock-framing) text. In the trace data, 17.3% / 24.7% / 15.3% of Claude/Gemini/Gemma plans in that cell contain clock/exit/stage-2 language vs **0.0%** in the axis-1 and axis-3 baselines (GPT-4o: 0.0% — it neither echoes nor reacts). Behaviorally the cell *fixes* Gemma (mean dev −0.59 vs −5 to −7 in its clean baselines) and *hurts* Gemini (−6.12 vs −0.8/−1.7). It is a treated cell, not a baseline. Consequences implemented here:

- **Corrected pooled baseline = {axis1_contingent_baseline, axis3_beliefs_baseline} only** (n=1,188, 8 clusters; mean dev −2.56, mean |dev| 3.20). The legacy pooled-of-three and the dedicated `spsb` cell are kept as clearly-labeled comparison columns.
- **`axis2_forward_baseline` enters the lever table as a treatment** (row 'Two-stage clock-exit descr.', family B3v), with `clock_exit_language` as its manipulation-check target.
- The axis-2 treatments (Payoff Safety, Payoff Tree) and the backward-induction cell are re-based to the corrected pooled baseline. All sanity checks against the provenance note's numbers pass exactly (see `mediation_log.txt`).

## Methods

- **Clustering.** Every sealed-bid cell is one run directory per model, so `run_id` gives exactly **4 clusters per experiment**. A treatment-vs-baseline contrast therefore has only 8 (own-axis baseline) to 16 (pooled-axis baseline) clusters. This is squarely the few-cluster regime where naive cluster-robust SEs over-reject. The **headline p-value for every treatment contrast is a wild-cluster bootstrap** (Rademacher weights, restricted residuals imposing the null, 2000 reps, seed 1299), with a **cluster-level permutation test** (5000 reps) as a cross-check. Naive cluster-robust p-values are computed and stored in the CSV but are not the headline; the few-cluster flag is documented.
- **Baselines (provenance-corrected).** Cells with a *clean* own-grid baseline keep it (axis-1 scaffolds → `axis1_contingent_baseline`; belief scaffolds → `axis3_beliefs_baseline`; loss frames → `loss_aversion_baseline`). Everything else — the axis-2 treatments (Payoff Safety, Payoff Tree, backward induction), the B/D presentation cells, and the reclassified two-stage clock-exit cell — is tested against the corrected pooled baseline {axis1, axis3}. The legacy pooled-of-three and dedicated-`spsb` behavioral comparisons are stored in `manipulation_checks.csv` as `absdev_*_legacy` / `absdev_*_spsb` columns; the B2 mediation table reports all three conventions.
- **Deduplication.** ~40% of sealed rows are byte-identical (model×cell×value ⇒ same plan and bid at temp 0.5). Every headline is re-run on the deduplicated sample and both are reported; flips flagged.
- **Prompt-echo confound (caveat 6b).** The target-language manipulation check is partly a check on whether the model parrots the prompt's new vocabulary. Rows are annotated. All language contrasts are lever-vs-its-own-baseline. The menu cell removes the second-price vocabulary, so its rule-rehearsal target is 0 by construction and is not interpreted as comprehension.
- **Scope.** Ascending-clock traces are excluded (as in the OLS); the lever analysis is on the sealed second-price cells only.

All cell means were sanity-checked before any join against both `traces_summary.md` (onestep dev −1.53, legacy pooled |dev| 3.27, onestep |dev| 1.95, spsb dev −2.67, worst-case language 43%, payoff-tree |dev| 1.29) and the provenance note (per-model clock-exit prevalence 17.3/24.7/15.3/0.0%; Gemma −0.59, Gemini −6.12; corrected baselines 0.0% clock language) — all matched to ±0.06.

## 1. The 2×2 dissociation (the headline, corrected baselines)

Behavior tested against the corrected pooled baseline {axis1, axis3} for Payoff Safety, the Payoff Tree, and the menu, and the own axis-1 baseline for the worst-case scaffold. ``Moves'' = WCB p<0.05. Cluster-permutation p (model-level) reported alongside because with only 4 model-clusters the two tests can disagree.

| Lever (family) | Moves language? (WCB p / perm p) | Moves bids? (WCB p / perm p) | Classification |
|---|---|---|---|
| Payoff Safety (B2) | no (—) [0.000->0.000] | yes (0.015 / 0.36) [3.20->1.95] | **bids-only** |
| Worst-case scaffold (C1) | yes (0.007 / 0.01) [0.020->0.430] | no (0.814 / 0.95) [3.24->3.07] | **language-only** |
| Payoff Tree (C1) | no (0.897 / 0.97) [0.330->0.327] | yes (0.017 / 0.13) [3.20->1.29] | **bids-only** |
| Menu restatement (B1) | no (n/a) [0.330->0.000] | no (0.658 / 0.77) [3.20->3.55] | **neither** |

**Few-cluster robustness flags (IMPORTANT):**

- **Payoff Safety:** bids: WCB p=0.014<.05 but cluster-perm p=0.36>=.05 (soft at the model-cluster level)
- **Payoff Tree:** bids: WCB p=0.017<.05 but cluster-perm p=0.13>=.05 (soft at the model-cluster level)

Deduplicated cross-check (byte-identical plan+bid dropped):

| Lever | Classification (full) | Classification (dedup) | Flip? |
|---|---|---|---|
| Payoff Safety | bids-only | bids-only | no |
| Worst-case scaffold | language-only | language-only | no |
| Payoff Tree | bids-only | bids-only | no |
| Menu restatement | neither | neither | no |

### 1b. What the baseline correction changes (vs the pre-correction run)

The pre-correction conventions (spsb for B2; own-axis2 for the Tree; legacy pooled-of-three for the menu) are re-computed in this same run for documentation (`dissociation_2x2_precorrection.csv`):

| Lever | Pre-correction class (bids WCB/perm p) | Corrected class (bids WCB/perm p) | Changed? |
|---|---|---|---|
| Payoff Safety | bids-only (0.007/0.39) | bids-only (0.015/0.36) | no |
| Worst-case scaffold | language-only (0.814/0.95) | language-only (0.814/0.95) | no |
| Payoff Tree | neither (0.074/0.07) | bids-only (0.017/0.13) | **YES** |
| Menu restatement | neither (0.719/0.80) | neither (0.658/0.77) | no |

(Note: the language column of the pre-correction rows above also uses the corrected-baseline manipulation check, so the Tree's row prints 'neither' rather than the 'language-only' the earlier run published — the earlier run's language test was itself against the contaminated cell.)

**Two provenance-explained reversals:**

1. *Behavioral side (both axis-2 treatments sharpen).* The pre-correction fragility flags (Payoff Tree 'not robustly both', Payoff Safety bid effect only p=0.055 vs legacy pooled) were artifacts of the contaminated control cell: it dragged Gemma's control mean toward truthful (−0.59 vs −6.53 in its clean baselines) and blunted the model-level signal. Corrected, every model's Payoff-Safety and Payoff-Tree contrast points the same way and both clear WCB p<0.05 (0.015 and 0.017), stable under deduplication (0.012 / 0.018). The model-level permutation test remains soft (0.36 / 0.13) — an honest 4-cluster power limit, no longer a contradiction.

2. *Language side (the Tree's 'moves language' claim dies).* The celebrated '7.5%→26.7% rule rehearsal' rise under the Payoff Tree (traces_summary Finding 4; the paper's `tab:trace-dissociation`) was measured against the contaminated cell, whose clock-exit narrative *crowded out* rule name-dropping (7.5%). The clean axis-1/axis-3 baselines name-drop 'second-highest' at **33.0%** — statistically identical to the Tree cell's 32.7% (WCB p=0.897). **The Payoff Tree does not raise rule-rehearsal language at all; it is bids-only, like Payoff Safety.** The corrected 2×2 therefore has an *empty* 'both' cell: no lever moves language and bids together — stated reasoning and behavior dissociate completely.

## 2. The reclassified cell: `axis2_forward_baseline` as a two-stage clock-exit description (B3 variant)

Pooled manipulation check vs the corrected baseline: `clock_exit_language` 0.000→0.143 (WCB p=0.002, perm p=0.0198); behavior |dev| 3.20→3.41 (WCB p=0.8761, perm p=0.8192). The pooled behavioral null **conceals fully offsetting per-model effects**:

| Model | clock lang (base→treat) | mean dev (base→treat) | shift | \|dev\| (base→treat) | Welch p (row-level, optimistic) |
|---|---|---|---|---|---|
| claude-3-5-haiku-20241022 | 0.000→0.173 | +0.54→+0.37 | -0.18 | 2.02→2.94 | 0.5766 |
| gemini-2.0-flash | 0.000→0.247 | -1.25→-6.12 | -4.87 | 1.25→6.12 | 0.0000 |
| google/gemma-3-27b-it | 0.000→0.153 | -6.53→-0.59 | +5.94 | 6.57→2.12 | 0.0000 |
| gpt-4o | 0.000→0.000 | -2.94→-2.46 | +0.48 | 2.95→2.46 | 0.0367 |

Per-model inference caveat: each model is ONE treated cluster vs TWO control clusters, so no within-model cluster test exists; Welch p is row-level on near-duplicate rows and is descriptive only.

**Paraphrase sensitivity (headline-relevant).** Two clock-framing texts, two different effect profiles: this two-stage exit-price text produces a **large correction for Gemma** (−6.53→−0.59, |dev| 6.57→2.12 — comparable to what the *true* clock achieves) and a **large backfire for Gemini** (−1.25→−6.12), with Claude ≈flat and GPT-4o inert in *both* language (0% echo) and bids (−2.94→−2.46); meanwhile the B3 `intervention_proxy_breitmoser` clock-framing text improves all four models modestly (the paper's ρ=+0.29 rung). Same design idea, different wording, different — even opposite-signed — per-model effects: direct evidence that description-lever effects are **paraphrase-sensitive**, and that pooled nulls can conceal offsetting model-level responses. GPT-4o's double inertness (no echo, no bid movement) is consistent with the paper's Finding 5 (mechanism-insensitive reasoning script).

## 3. Formal mediation bound — Payoff Safety (B2)

Total behavioral effect on mean $|b-v|$ (corrected baseline {axis1, axis3}): **-1.248** (cluster-boot 95% CI [-3.37, +1.17]). The legacy pooled-of-three and dedicated-spsb rows are in `mediation_b2.csv`, clearly labeled.

First stage (lever → verbalized-understanding mediator), which must be ≈0 for the mediation pathway to be shut:

| Mediator | prev T | prev C | first-stage a | 95% CI | WCB p |
|---|---|---|---|---|---|
| payment_rule_correct | 0.028 | 0.039 | -0.0104 | [-0.051, +0.029] | 0.603 |
| safety_recognition | 0.000 | 0.000 | +0.0000 | [+0.000, +0.000] | nan |
| second_price_mention | 0.282 | 0.330 | -0.0483 | [-0.227, +0.164] | 0.612 |

**Bound (product-of-coefficients, cluster-bootstrapped).** Pooling the three verbalized-understanding mediators into an *any-VU-fires* indicator, the mediated effect ACME = a·b has point estimate +0.016 (95% CI [-0.166, +0.145]); the implied mediated **share** of the total effect is -0.007 (95% CI [-0.401, +0.269]). The 95% upper bound on the absolute mediated share is **35.4%** (corrected baseline; under the legacy pooled-of-three it was 36.3%).

> **Honest statement (no causal claim):** verbalized understanding cannot mediate more than ~35% of the Payoff-Safety effect. We do *not* invoke sequential ignorability; the first-stage zero is itself the finding — the lever does not work by making agents verbalize why truth-telling is safe.

**Within-treatment cross-sectional association (NON-CAUSAL, labeled).** Among the 600 treated traces, those that *do* rehearse the payment rule err less:

| Mediator | within-treat gap in $|b-v|$ | 95% CI | second-stage b |
|---|---|---|---|
| payment_rule_correct | -1.405 | [-2.15, -0.56] | -1.539 |
| safety_recognition | — (no within-treatment variation) | — | — |
| second_price_mention | -0.697 | [-1.71, +0.02] | -0.488 |

This is a selection/confounding correlation (traces that rehearse the rule are also the more careful traces), not evidence of mediation — the first stage shows the lever does not *cause* more rule rehearsal.

## 4. Per-model stated-vs-revealed consistency + $-amount calibration (option 4)

Pooled over all sealed cells, per model:

| Model | dir. consistency | n (intent stated) | $ exact-match | corr(stated,realized) | mean \|stated−realized\| |
|---|---|---|---|---|---|
| claude-3-5-haiku-20241022 | 0.970 | 2896 | 0.410 | 0.980 | 0.82 |
| gemini-2.0-flash | 0.979 | 3136 | 0.972 | 0.973 | 0.40 |
| google/gemma-3-27b-it | 0.827 | 830 | 0.891 | 0.991 | 0.28 |
| gpt-4o | 0.978 | 2540 | 0.944 | 0.985 | 0.21 |

- **Direction consistency** = P(sign of realized deviation matches stated intent | a single shading/overbid/truthful intent is stated). Truthful intent scored as |dev|≤$0.5.
- **$-amount calibration** parses the stated intended bid (last $-amount following a bid-intent cue in the plan) and compares to the realized bid. Coverage ≈87% of traces; parses >$55 dropped as errors.
- Figure: `consistency_calibration.pdf` (binned realized vs stated bid, per model).

Per model × lever detail is in `consistency_calibration.csv`.

Two model-level nuances worth a sentence in the paper. (a) **Gemma** states a single clean value-anchored intent in only ~830 traces (vs ~2500–3100 for the others) — its plans are vague/unanchored, so its 0.827 direction-consistency is computed on a thin, self-selected slice; yet when Gemma *does* name a bid amount its calibration is the tightest of any model (corr 0.99, mean |stated−realized| $0.28). (b) **Claude's** $ exact-match is only 0.41 because it habitually states a round planning figure and then submits a nearby (often slightly higher) number — the orange curve sits just above the 45° line — but its correlation is 0.98, so the plan is still a faithful *direction* signal, not cheap talk. Across all models the plan predicts the bid essentially one-for-one (corr 0.97–0.99): the traces are faithful plans, not post-hoc rationalizations.

## 5. Flags for the paper (updated after the provenance correction)

1. **RESOLVED — the two pre-correction fragility flags were baseline contamination.** The earlier run of this analysis flagged (a) 'Payoff Tree is not robustly both' (bids WCB p=0.074 vs its own axis-2 baseline) and (b) 'Payoff Safety moves-bids is marginal under model-level permutation' (perm p=0.28–0.45). Both were artifacts of the contaminated `axis2_forward_baseline` control cell (`_axis2_baseline_provenance.md`): the treated clock-framing cell in the control pool dragged Gemma's control mean toward truthful (−0.59) and blunted the model-level signal. Section 1b reports the corrected classifications side by side with the pre-correction ones.

2. **The paper's `tab:trace-dissociation` needs substantive revision, not just re-basing.** (a) Its Payoff Tree row's language entry ('rule rehearsal 7.5%→26.7%') and its 'moves both' classification are contamination artifacts — against clean baselines the Tree's rule-rehearsal is flat (33.0%→32.7%, WCB p=0.897) and the lever is **bids-only** (see Section 1b); the corrected 2×2 has an empty 'both' cell, which *strengthens* the paper's dissociation thesis. (b) Its baseline columns mix the contaminated cell (Tree row |b−v| 3.41) and the legacy pooled-of-three (Safety row 3.27; corrected 3.20). (c) The `06_ranking.tex` presentation-baseline declaration ('pooled per-model means +0.48, −2.88, −2.78, −4.54, cross-model −2.43') averages over the contaminated cell and should be recomputed on {axis1, axis3} in the integration pass — as should any ρ computed against pooled-axis or axis-2 baselines. Gemma's 'anomalously good axis-2 baseline' caveat in `06_ranking.tex` is now *explained*, not just flagged, and should cite the provenance note.

3. **Behavioral inference still needs cluster discipline.** Even after the correction, the honest tests are the WCB/permutation reported here (4 model-clusters per cell, ~40% byte-identical duplicate rows), not row-level t-tests. Where WCB and permutation disagree at α=0.05, the CSV's `robust_note` says so.

4. **New tension for rung B3 (paraphrase sensitivity).** The paper presents clock-framing (B3) as 'universal in sign, modest' (ρ=+0.29). The reclassified two-stage clock-exit text is a *second* clock-framing description with a **sign-mixed** effect profile (Gemma strongly helped, Gemini strongly hurt, Claude/GPT-4o ≈flat — Section 2). The B3 rung's universality claim is therefore wording-specific; the two texts together are direct paraphrase-sensitivity evidence and belong in the discussion of description levers.

5. **Claude sign flag (already known, restated).** In these logs Claude's Payoff-Safety mean deviation is +0.30 (mild overbidding); the ES manuscript reports −0.30. Magnitude and every |dev| quantity here are unaffected. Consistent with the note in `traces_summary.md` and `appendix_traces.tex`.

## 6. Caveats

- **Few clusters.** Even with the wild-cluster bootstrap, 8–16 clusters is not many; the WCB is the best available correction but treat p-values near 0.05 as soft. Cluster-permutation cross-checks agree in sign (stored in the CSV).
- **Prompt echo** inflates every target-language increase for levers whose prompt seeds the target vocabulary (including the two clock-framing texts, where the echo IS the manipulation check). The scientifically clean contrasts are (i) Payoff Safety, whose invariant is echoed in 0/600 traces despite being asserted in the prompt, and (ii) the Payoff Tree, which shares the 'second-highest' rule vocabulary with the corrected {axis1, axis3} baselines. The menu's language column is uninterpretable (reverse echo).
- **Per-model effects for the reclassified axis-2 cell** rest on one treated cluster vs two control clusters per model; they are descriptive (magnitudes are large and sign-opposed, but no within-model cluster test is possible).
- **The mediation bound is a bound, not an estimate.** The product-of-coefficients uses a *within-treatment cross-sectional* second stage, which is confounded; the bound is conservative precisely because the first stage is ≈0.
- **Calibration parser** is a regex, not an LLM; it misses paraphrased bid statements and can be fooled by multi-number plans (mitigated by the bid-cue anchor and the $55 cap).


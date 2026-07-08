# Cardinal-calibration analysis (evidence base for Section 7)

**Question.** LLMs reproduce human comparative statics ordinally. What tuning makes them agree
*cardinally* — and is there one setting that works across mechanisms?

**Produced by** `analysis/build_cardinal_grid.py` (rerunnable; numpy seed 1299, 2000-rep bootstrap).
Full grid: `results/cardinal/cardinal_grid.csv` (95 cells; 93 with data, 2 NA).
Rank tables: `results/cardinal/rank_core_abs_delta_smad.csv`, `results/cardinal/rank_core_dir_gap.csv`.

## Conventions (read before quoting numbers)

* **SMAD** = 100 x E|b − b*(v)| / 24.5, where b* is each environment's own equilibrium
  (FP N=3: 2v/3; SP/SP-APV/AC/AC-B: v; TP N=5: 4v/3; TP N=3: 2v). CV formats use the paper's
  profit-based deviation (|pi_win − pi*|/20). NOTE: legacy figure CSVs
  (`plots/theoretical_deviation_results_updated.csv`, `plots/appendix2_*.csv`) normalized by 25,
  so numbers here are a uniform ~2% larger; the merged paper's intervention numbers
  (`writeup/auction-v2-numbers.txt`) already use 24.5.
* **Direction** = share of bids strictly above VALUE (tol 0.1 sealed / 0.5 clock; clock cells
  use non-winner exits only). Human targets from `plots/auction_human.csv`:
  FP 0.4% over value, SP 67.2%, TP(n=5) 89.8%, SP-APV 40%, AC 18%, AC-B 40%.
  *Discrepancy flag:* the task brief quoted "SPSB 96% overbid, FPSB 56.5% overbid". Neither is in
  the repo's canonical human file. 96% is consistent with overbids *among deviators*
  (67.2/(67.2+5.7) = 92.2%) or with the Kagel–Levin n=10 reconstruction (96.2%); 56.5% for FPSB is
  close to the share of bids above *RNNE* in the KL93 n=5 reconstruction (67%) averaged with n=10
  (47%). The grid also reports `llm_over_among_deviators` and `llm_over_vs_eq_share` so the writer
  can use either convention; conclusions below are robust to the choice.
* **Wasserstein-1** (`wasserstein_pp`): distance between scaled deviation-from-value distributions
  (LLM: (b−v)/24.5; human: (b−v)/E[v] on the source study's scale, x100), against the
  moment-matched synthetic reconstructions in `results/v12_interventions/moment_matching/`:
  FP & TP -> Kagel–Levin 1993 (n=5), SP -> Gonczarowski et al. 2022 "Traditional",
  SP-APV/AC -> Li 2017 (2P/AC), AC-B -> Breitmoser 2022 AC-DO (clock without dropout info). Units =
  SMAD percentage points. These are reconstructions, not raw human bids.
* **Baseline mapping for tests** (`baseline_id`, Welch t on |b−b*| and 2-proportion z on overbid
  share): temperature cells -> same-mechanism V10 T=0.5 anchor; risk personas -> same model's
  POOLED axis1/2/3 baselines (no risk-specific baseline exists); prospect frames -> the more
  specific `loss_aversion_baseline` of the same model & mechanism; rule-explanation -> explanation-ON
  anchor. FP/TP3 persona+frame cells and their baselines come from the recovered
  `recovered_logs/experiment_logs_gpt_4o/V12` tree (unconstrained-bid generation, verified against
  commit 3681685d); SP cells from the combined ES CSV
  (`Engineering_simplicity/.../all_experiments_combined_20260204_114522.csv`).

## VERDICT (crisp)

**There is no single tuning that produces cardinal agreement across mechanisms.** The knobs
decompose cleanly by axis, and the two axes demand incompatible settings:

1. **Level (ΔSMAD)** is best closed by *mild, knob-specific* adjustments — and for FP, SP, SP-APV
   the untuned or lightly-tuned model is already within 1–3 SMAD points of humans. Best per
   mechanism (GPT-4o): FP -> T=1.0 (25.50 vs human 24.76, Δ=0.74); SP -> WTA-WTP frame (7.24 vs
   5.65, Δ=1.59; −3.57 vs its baseline, p=0.005); SP-APV -> untuned anchor (10.95 vs 9.31);
   AC/AC-B -> T=1.0 (LLMs are *too good* at clock formats — SMAD 0.5–0.8 vs human 3.5–5.8 — so
   *adding noise moves them toward humans*); CV-FP -> T=1.0 (42.9 vs 47.6); CV-SP -> T=1.0 (33.5 vs
   18.2, still 15pp off). **Third price is un-tunable**: best TP cell in the whole grid is SMAD 44.1
   (T=0.1, n=5) vs human 7.7 — every knob leaves a 36+ point gap.
2. **Direction** is moved by exactly one knob: the **risk-seeking persona**. It is the only setting
   that makes LLMs overbid in second price (GPT-4o SP overbid share 0.4% -> 45.3%, p<10^-4; human
   67.2%) and third price (TP3: 0.2% -> 56.5%, p<10^-4; human 89.8%), and it *also* improves the SP
   and TP level and Wasserstein axes (TP3 SMAD −14.4, p=0.011; SP W1 23.8 -> 14.8pp). **But it
   exports dominated overbidding into first price** (FP overbid-above-value 0% -> 18.0% vs human
   0.4%, p<10^-4; FP SMAD +4.6, p=0.002). In the direction rank table risk-seeking is rank 1 on
   both SP and TP3 but 15/15 (worst) on FP — the sharpest possible statement of the trade-off.
3. **Tuning is also model-specific.** The same risk-seeking persona on SP: gemma-3-27b 20.7 -> 5.87
   SMAD (vs human 5.65 — the single best cardinal match in the grid) and gemini 11.7 -> 4.9, but
   claude-3.5-haiku 9.5 -> 35.0 (6x overshoot, 93% overbid). A persona calibrated on one model does
   not transfer.
4. **Temperature is not a cardinal dial** for sealed-bid formats: SP is non-monotone (T=0.5 anchor
   8.86; T=0.1 15.07; T=1.0 13.15, both worse, p<=10^-4) and FP/TP barely move. Its only clean use
   is adding human-like noise to the too-perfect clock formats.
5. **Rule-explanation on/off is a no-op** on all three axes (all level p>=0.53; largest effect is a
   small TP3 direction shift, 19.4% -> 12.6% overbid, p=0.02). Framing manipulations other than
   WTA-WTP (loss/gain/mixed/endowment) mostly *hurt* the SP level for GPT-4o (+2 to +8 SMAD vs
   loss-aversion baseline).

Frame for the paper: *cardinal agreement is achievable mechanism-by-mechanism (and sometimes
model-by-model) but not with a portable setting; the binding constraint is the direction axis —
matching human overbidding in SP/TP requires a disposition that immediately violates the no-
overbidding regularity humans display in FP.*

## Proposed main table for Section 7 (GPT-4o, core sealed-bid mechanisms)

Cells: LLM SMAD (human target) / overbid-vs-value share (human target). Bold = closest per column.

| Setting (knob) | FP: SMAD (24.76) | FP: over% (0.4) | SP: SMAD (5.65) | SP: over% (67.2) | TP3: SMAD (7.66*) | TP3: over% (89.8) |
|---|---|---|---|---|---|---|
| Untuned anchor (T=0.5, V10) | 28.11 | 0.0 | 8.86 | 16.7 | 108.28 | 19.4 |
| Axis-pooled baseline (V12) | 23.36 | 0.0 | 11.38 | 0.4 | 120.18 | 0.2 |
| Temperature T=0.1 | 28.64 | 0.0 | 15.07 | 10.2 | 112.54 | 1.3 |
| Temperature T=1.0 | **25.50** | 0.7 | 13.15 | 9.8 | 123.69 | 2.7 |
| Risk-averse persona | 14.98 | 0.0 | 18.33 | 0.0 | 129.18 | 0.0 |
| Risk-neutral persona | 20.90 | 0.0 | 11.02 | 2.7 | 121.26 | 6.7 |
| Risk-seeking persona | 27.98 | 18.0 | 10.48 | **45.3** | **105.76** | **56.5** |
| WTA-WTP frame | 23.00 | 0.0 | **7.24** | 0.0 | 114.01 | 0.0 |
| Rule explanation OFF | 28.08 | 0.0 | 8.70 | 16.0 | 111.31 | 12.6 |

\* human third-price target is Kagel–Levin n=5; the persona/frame TP cells are N=3 (deviation vs
own-environment RNNE 2v). The N=5 LLM cells (temperature knob only) give SMAD 44.1–48.2 with 3–7%
overbid — same qualitative gap. Companion cross-model row for the text: risk-seeking on SP =
{gpt-4o 10.48/45%, claude-haiku 35.03/93%, gemini 4.92/82%, gemma 5.87/56%} vs human 5.65/67%.

## Which knob wins on each axis (a)/(b), and the joint test (c)

* **(a) Level:** worst-case-rank winner on {FP, SP, TP3} is the WTA-WTP frame (worst rank 6/15,
  mean 3.7), narrowly ahead of risk-seeking (7/15) — but only because *every* setting is terrible
  on TP3, which compresses that column's information. Excluding TP: WTA-WTP and T=1.0 are the level
  winners for SP and FP respectively; no setting wins both.
* **(b) Direction:** risk-seeking is the only mover (SP gap 66.8 -> 21.9pp; TP3 89.6 -> 33.3pp) at
  the cost of FP (0.4 -> 17.6pp). Everything else leaves SP/TP direction gaps >= 50pp.
* **(c) Single setting?** No. Formally: no setting is in the top half of both the level and
  direction rank tables on all three core mechanisms (`rank_core_*.csv`). The Wasserstein axis
  agrees with this decomposition (risk-seeking best for SP/TP3 shape: 14.8/30.1pp; baselines best
  for FP shape: 2.1–3.0pp).

## Data-quality caveats

1. **NA cells:** AC and AC-B at T=0.1 (robustness run dirs exist but contain no results);
   CV explanation-OFF (git tree has no raw-data JSONs; profit metric uncomputable); TP5
   persona/frame cells were never run (personas exist only at N=3 for FP/TP).
2. **Tiny n:** AC-B T=1.0 has 12 rows -> 8 non-winner exits (SMAD 2.19, CI [0.36, 4.69]); AC T=1.0
   has 52 exits. Treat clock temperature rows as suggestive.
3. **Mislabeled filenames** in `robustness_logs/*gpt4o_temp*/` (e.g. `..._gemini_results.csv`);
   content verified via in-file `model`/`temperature` columns (all gpt-4o at stated temp).
4. **Rule-explanation manipulation is not verifiable from logs**: the saved prompt templates in the
   with/without trees are byte-identical and raw prompt JSONLs are empty in git; the contrast rests
   on the directory naming (`experiment_logs_without_explanation`, commit ce36a78b). The clock
   families are byte-identical runs across the two trees (no contrast possible). Given the measured
   no-op result this is low-stakes, but say "no detectable effect" rather than "explanation removed X".
5. **Run-generation drift:** temperature cells (Jan 26–31 runs) vs anchors (Jan 12); V12
   persona/frame cells (Jan 27, unconstrained-bid generation) vs combined-CSV SP cells (Feb 3 ES
   rerun). The SP anchor (8.86) vs SP axis-pooled baseline (11.38) difference illustrates
   between-generation variation ~2.5 SMAD points; treat cross-knob comparisons smaller than that
   with caution. Within-knob treatment-vs-baseline contrasts are same-generation and clean.
6. **Dependence:** sealed-bid cells have 3 bids per auction (5 for TP5); tests treat bids as iid,
   matching the paper's existing convention.
7. **Human synthetic reconstructions** are moment-matched simulations; the SP reconstruction
   (Gonczarowski Traditional) has far fatter tails (implied SMAD ~21% on its own scale) than the
   canonical SP target (5.65%), so W1 levels are not comparable across mechanisms — compare W1
   *across settings within a mechanism* only.
8. **Human FP direction share (0.4% over value)** is a vs-value convention; vs-RNNE the human
   share is ~67% (KL93 n=5 reconstruction). The grid's `llm_over_vs_eq_share` column supports the
   vs-RNNE comparison if the writer prefers it (e.g. FP anchor: 83.2% of GPT-4o bids above 2v/3).

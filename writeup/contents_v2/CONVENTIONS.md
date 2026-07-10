# auction-v2 Writer Conventions (coordination contract)

Master file: `writeup/auction-v2.tex` (already written — do NOT edit it; the integrator owns it).
Each writer produces exactly the `contents_v2/*.tex` file(s) assigned to them.
Architecture spec: `plan/plan.md` (read your section's row in §3, plus §2 intro skeleton, §4 ranking
spec, §5 reconciliation decisions, §7 cut list). This document pins the mechanics.

## 1. Files and section labels

| File | Top-level label(s) | Content |
|---|---|---|
| `00_abstract.tex` | — | `\begin{abstract}...\end{abstract}` only |
| `01_intro.tex` | `sec:intro` | 9-paragraph skeleton per plan §2 |
| `02_related.tex` | `sec:related` | six merged blocks per plan §3 |
| `03_framework.tex` | `sec:framework` | lever taxonomy + hypotheses H1–H3 |
| `04_design.tex` | `sec:design`, `sec:metrics`, `sec:reconstruction`, `tab:calibration-master` | environments, treatments, models, SMAD family + preservation index, human reconstruction |
| `05_validation.tex` | `sec:validation`, `fig:smad-comparison`, `fig:direction`, `tab:winners-curse`, `fig:ebay-sniping`, `tab:validity-map` | compressed benchmarking + eBay exhibit + validity map |
| `06_ranking.tex` | `sec:ranking`, `sec:ranking-extensive`, `sec:ranking-descriptions`, `sec:ranking-scaffolds`, `sec:ranking-synthesis`, `fig:osp-comparison`, `fig:descriptions`, `fig:contingent`, `fig:forward`, `fig:beliefs`, `fig:ranking`, `tab:ranking` | the product |
| `07_humans.tex` | `sec:humans` | rung-by-rung human anchoring + prediction |
| `08_discussion.tex` | `sec:discussion` | implications, practitioner box, scope, cost table `tab:cost`, limitations |
| `09_conclusion.tex` | `sec:conclusion` | ≤ half page |
| `appendix_human.tex` | `app:human`, `app:mixture`, `tab:mixture-calibration` | reconstruction details + mixture calibration |
| `appendix_procedures.tex` | `app:procedures`, `app:sealed-process`, `app:clock-process`, `app:ebay-process` | simulation procedures |
| `appendix_learning.tex` | `app:learning`, `fig:learning` | learning ablation |
| `appendix_ablations.tex` | `app:ablations`, `tab:temperature`, `tab:models` | temperature + model tiers |
| `appendix_prospect.tex` | `app:prospect` | prospect-theory / risk personas (ranking bottom rungs) |
| `appendix_prompts.tex` | `app:prompts`, `tab:intervention-inventory` | prompt library + old→new taxonomy map + run-status column |
| `appendix_da.tex` | `app:da` | DA implementation, Algorithm 1, Kendall-τ + Type-1/2 definitions |
| `appendix_ebay.tex` | `app:ebay`, `tab:ebay-revenue` | eBay details + hidden-reserve null + Myerson TODO |

Cross-reference ONLY labels from this table (plus your own subsection labels prefixed with your
file's prefix, e.g. `sec:design-da`). Appendix sections use `\section{...}\label{app:...}`.

## 2. Terminology (use exactly these)

- **SPSB** second-price sealed-bid; **FPSB** first-price; **TPSB** third-price.
- **AC** = open ascending clock (dropouts observed); **AC-B** = closed/blind clock. ES's clock = AC-B.
- **clock-framing** = sealed bid *described* as an automatic clock exit threshold (a description, NOT
  a mechanism change; repo template `intervention_proxy_breitmoser`). Never conflate with AC/AC-B.
- **menu restatement** (Gonczarowski menu description) vs **safety-exposing description**
  (Payoff Safety, Rejection Safety) — two different description sub-families (B1 vs B2), B3 = clock-framing.
- Scaffolds: **contingent reasoning** (C1, incl. Payoff Tree), **forward planning** (C2, lookahead,
  DA only), **belief formation** (C3, first/second order). Family D = preference framings (appendix).
- **direct DA** (one-shot rank-order list) vs **iterative DA** (OSP query protocol).
- **SMAD** = scaled mean absolute deviation (% of expected benchmark bid); DA analogue = normalized
  Kendall-τ error (%). **Preservation index** ρ = 1 − D(lever)/D(baseline).
- Tier language for the ranking (partial order), never "strict total order".
- Models: GPT-4o (2024-08-06, anchor), Claude 3.5 Haiku (2024-10-22), Gemini 2.0 Flash,
  Gemma 27B; appendix tiers: gpt-5-mini (frontier ceiling), Llama-3-8B (capability floor).
  Never "Claude Sonnet".

## 3. Canonical numbers (verified against sources — use these; cite nothing else without checking)

**Validation (from writeup/contents/results.tex + appendix):**
- IPV sealed: human FPSB SMAD 24.76% vs SPSB 5.65% (4.4×); GPT-4o 27.55% vs 8.69% (3.2×).
- Direction, SPSB-IPV — CANON UPDATED (2026-07, repo-canonical convention): humans overbid 67.2% of
  ALL bids (92.2% among deviators); GPT-4o deviations 81.6% underbids. The old 96.0%/81.3% figures
  are the ±2%-band convention — footnote-only where retained. FPSB: humans overbid 56.5%, GPT-4o 85.9%.
- APV: human SP 9.31%, AC 3.54%, AC-B 5.83%; GPT-4o SP 10.73%, AC 0.81%, AC-B 0.47%.
  Direction SP-APV: humans 64.7% over; GPT-4o 92.4% under. AC: GPT-4o 71.7% within ±2% vs humans 26.8%.
- Winner's curse (CV FPSB, mean winner profit (sd) / median / %positive): n=4: −2.54 (3.87)/−3.00/24%;
  n=5: −4.40 (3.63)/−4.00/6%; n=6: −5.46 (3.82)/−5.05/4%; n=7: −5.55 (2.93)/−5.30/0% (all p<.001).
  SPSB: +1.30 (4.87)/1.00/58% (p=.967); 0.07 (4.35)/0.00/46% (.542); −2.82 (3.50)/−1.75/18% (<.001);
  −2.83 (2.78)/−2.00/12% (<.001).
- Menu restatement — CANON (2026-07-10, ×4 models, CORRECTED axis1+axis3 baselines): sign-mixed,
  null on average (placebo sign test 3/8, p=0.73); Gemma improves (+$2.03, p<0.001), GPT-4o worsens
  (−$1.16, Welch p=0.013 / MW p=0.54 — report both), Claude marginally worse (+$0.82, Welch p=0.064
  / MW p<0.001), Gemini null (p=0.56). Never a clean placebo. FRONTIER: menu BREAKS claude-sonnet-5
  (0→−$8.71, SMAD 35.5%, d=−3.8) and degrades gemini-2.5-flash (2.3→9.1% SMAD); gpt-5/gpt-5-mini
  unmoved. (Legacy GPT-4o-only scaled cell −0.106 → −0.143 — historical only.)
- Clock-framing — CANON (2026-07-10, ×4 models, CORRECTED baselines): significant in all four but
  SIGN-MIXED — helps GPT-4o 12.1→6.3, Gemma 26.8→13.8, Claude 8.3→7.2 (SMAD%, each p<0.001);
  HURTS Gemini 5.1→9.5 (p<0.001; same model the two-stage clock-exit variant hurts). Pooled
  ρ = +0.30 [−0.77, +0.52]. Human-anchor agreement: 3/4 families, never "universal in sign".
- Learning ablation: FPSB SMAD first-5 0.2523 vs last-5 0.2524 (t p=0.997, MW p=0.913); SPSB 0.1282
  vs 0.1447 (n.s.).
- Appendix tiers: gpt-5-mini mean SMAD 6.68%; Llama-3-8B 57.58% (worse than humans in 6/7 formats).

**Ranking (from Engineering_simplicity/main.tex; $ = mean bid−value; DA = mean Kendall-τ error):**
- SPSB baseline: Claude −0.5, Gemini −1.6, GPT-4o −3.3, Gemma −5.3 (cross-model −2.67).
- Clock: Claude −0.1, Gemini −1.2, GPT-4o −0.5, Gemma −0.3 (cross-model ≈ −0.5).
- Direct DA: Claude 6%, Gemini 8%, GPT-4o 1%, Gemma 3% (μ = 4.2%); iterative DA — CANON UPDATED
  (E9 done): zero is exact for the pick-protocol in 3/4 models (rule-of-three 95% UBs 0.85–0.92%);
  Gemma 5 strict pick errors (1.6%); the yes/no-tree variant exposes Claude 24.1% Type-1. Never an
  unqualified "0.0% all models".
- Payoff Tree: auctions −2.67 → −1.13 (GPT-4o −3.28→−0.86, Gemma −5.27→−2.34, Gemini −1.63→−0.53,
  Claude −0.49 ≈ null); DA 4.2% → 1.7% (Claude 5.8→2.0, Gemini 7.6→2.8, GPT-4o 1.0→0.6, Gemma 2.6→1.4).
- Forward planning (DA only): one-step 4.2% → 7.8% (GPT-4o 1.0→4.8, Gemma 2.6→12.7); two-step → 5.1%.
- Beliefs: auctions first-order −3.04, second-order −3.47; DA first 5.1%, second 9.1% (Gemma
  2.6→14.3); Gemini ≈ immune in both domains.
- Safety descriptions: Payoff Safety −2.67 → −1.53 (Claude −0.49→−0.30, Gemini −1.63→−0.38,
  GPT-4o −3.28→−1.88, Gemma −5.27→−4.17); Rejection Safety 4.2% → 0.2%.
- Pooled ρ CANON (2026-07-10, corrected baselines, from concordance.md — supersedes all
  "provisional ρ" values): OSP +0.97 [+0.83,+1.00]; safety +0.78 [+0.39,+1.00]; menu-invariance-DA
  +0.65 [−0.52,+0.95]; tree +0.59 [+0.46,+0.68]; clock-framing +0.30 [−0.77,+0.52]; lookahead
  −0.00 [−2.12,+0.26]; menu-auction −0.14 [−1.00,+0.27]; 2nd-beliefs −0.35; 1st-beliefs −0.41;
  menu-mechanics-DA −1.67; risk-averse −1.82.
- Concordance CANON (corrected baselines): Kendall's W = 0.70 auctions (p=0.004), 0.90 DA
  (p=4e-4), 0.81 pooled (p=8.4e-7). Sign tests: T1>T2 7/8 (p=0.070); T2>T3 8/8 (p=0.008);
  T3-vs-T4 FAILS (4/8, p=1.0); T4>T5 8/8 (p=0.008). The axis-2 correction RAISED auction W from
  0.43 to 0.70 — cite as evidence the contamination was noise-injecting.

**PROVENANCE FLAGS (insert \TODO where these numbers appear):**
- CLOCK ENVIRONMENT (updated 2026-07-08): the incumbent acb clock cells are *described-as-APV,
  drawn-as-IPV* (template `affiliated_ac_closed.txt` + `private_value: "private"` ⇒ common=0,
  values Unif{0..49}). New clean IPV cells (`ascending_clock_ipv_closed`, IPV template + IPV draws,
  tick $0.5, seed 1299, K=50) exist for **gpt-4o and gemma** via OpenRouter; claude-3.5-haiku and
  gemini-2.0-flash are NOT servable on OpenRouter (no active endpoints) — those two E2 cells need
  native keys (Kehang).
- **AXIS-2 BASELINE CONTAMINATION (2026-07-08, load-bearing):** the V12 `axis2_forward_baseline`
  template was a two-stage sealed-bid-as-clock-exit description, NOT a plain SPSB text — see
  `results/merged_ranking/_axis2_baseline_provenance.md`. New canon: pooled axis baseline =
  {axis1, axis3} only; `axis2_forward_baseline` is a treated cell (B3-variant, "two-stage
  clock-exit description"); Gemma's "anomalously good axis-2 baseline" is explained, not noise.
  All †-flagged pooled-axis contrasts in tab:ranking must be recomputed on the corrected pool.
- ES SPSB *baseline* means: provenance RESOLVED — ES published numbers = dedicated spsb runs;
  per-axis baselines differ; both declared (§4 baseline declaration).
- Knife-edge margins (Rejection Safety 0.2% vs OSP 0.0%) carry no SEs yet: \TODO{E6 statistics}.
- B2 "no human anchor" claim: WRONG as stated — see
  `results/merged_ranking/_b2_human_anchor_literature.md` (GHIT-2024 Menu-SP; Katuščák–Kittsteiner
  2024; Guillén–Hakimov 2018 mechanics-backfire anchor). §7 prediction must be repositioned.

## 4. Figures (verified assets — use these paths; \graphicspath is already set)

Available now (reference by bare filename):
- `figure1.png` (human vs GPT-4o SMAD, 7 formats) → fig:smad-comparison
- `figure2_by_auction_type_10pct.png` (under/over decomposition) → fig:direction
- `smad_rounds.png` (learning) → fig:learning
- `appendix2_temperature_comparison.png`, `appendix2_model_comparison.png` (appendix ablations)
- `fig1_osp_comparison.pdf` (4 models × SPSB/clock + DA direct/iterative) → fig:osp-comparison
- `fig2_contingent.pdf` → fig:contingent; `fig3_forward_da.pdf` → fig:forward;
  `fig4_beliefs.pdf` → fig:beliefs; `fig5_mechanism_description.pdf` → fig:descriptions
- `appendix_loss_aversion_auctions.pdf`, `appendix_loss_aversion_da.pdf`,
  `appendix_risk_preferences_auctions.pdf`, `appendix_risk_preferences_da.pdf` (appendix E)
- extra PNGs from the imported pipeline (appendix use only): `da_vs_osp.png`,
  `da_osp_yesno_vs_direct.png`, `da_direct_variants.png`, `all_interventions_combined.png`, etc.

FORMERLY MISSING — all four now exist with generating scripts (2026-07 analysis cycle):
`ranking_forest.pdf` (fig:ranking; `scripts/plots/ranking_forest.py`),
`figure3_intervention_comparison.png` (`scripts/plots/intervention_comparison.py`),
the four eBay PNGs (`scripts/plots/regenerate_ebay_figures.py`).
NEW available: `figure1_bands.png`/`.pdf` (fig:smad-comparison with Monte-Carlo reconstruction
bands; `scripts/plots/figure1_bands.py`) — adopt in place of `figure1.png` in the integration pass.
NOTE: `ranking_forest.pdf` must be regenerated after the corrected-baseline recomputation
(axis-2 contamination) and the frontier/E2/E4 fold-in.

## 5. Citations

- Bib file: `writeup/auction_v2.bib` (118 entries; base = es_bib + jiang2025incentive,
  ravindranath2023data, wang2026llm, levin1996revenue). Before citing a key, `grep` it in the bib.
- **Never cite `zhu2024evidence`** — internalized; replace with internal `\ref` (e.g., "as shown in
  Section~\ref{sec:validation}").
- natbib author-year: `\citep{}` parenthetical, `\citet{}` textual.

## 6. Style and hygiene

- Econ working-paper register. Reuse source text verbatim where plan §3 says "reuse" — but fix the
  known typos (gaTme, todays', widelyused, "2025-0205", double period) and never copy `\khz/\dcp`
  comment macros (de-macro the two intro khz blocks into body text per plan).
- Do not re-define macros, `\newcommand`, or packages in content files (master owns the preamble).
- Do not write `\section*`; everything numbered. No `\newpage` in content files.
- `\TODO{...}` for anything awaiting re-runs/decisions; be liberal — this is a working draft.
- The claim discipline of plan §4 is binding: tiers, not strict total order; report within-tier
  domain flips honestly; keep the OSP-DA 0% observability caveat verbatim wherever the 0% appears.

## 7. Report back (each writer's final message)

(1) file(s) written; (2) labels defined; (3) labels/figures you \ref that others define;
(4) numbers used outside §3's canon (with source file:line); (5) TODOs inserted; (6) open issues.

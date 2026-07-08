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
- Direction, SPSB-IPV (±2% band removed): humans overbid 96.0%/underbid 4.0%; GPT-4o underbid
  81.3%/overbid 18.7%, 29.2% within band. FPSB: humans overbid 56.5%, GPT-4o 85.9%.
- APV: human SP 9.31%, AC 3.54%, AC-B 5.83%; GPT-4o SP 10.73%, AC 0.81%, AC-B 0.47%.
  Direction SP-APV: humans 64.7% over; GPT-4o 92.4% under. AC: GPT-4o 71.7% within ±2% vs humans 26.8%.
- Winner's curse (CV FPSB, mean winner profit (sd) / median / %positive): n=4: −2.54 (3.87)/−3.00/24%;
  n=5: −4.40 (3.63)/−4.00/6%; n=6: −5.46 (3.82)/−5.05/4%; n=7: −5.55 (2.93)/−5.30/0% (all p<.001).
  SPSB: +1.30 (4.87)/1.00/58% (p=.967); 0.07 (4.35)/0.00/46% (.542); −2.82 (3.50)/−1.75/18% (<.001);
  −2.83 (2.78)/−2.00/12% (<.001).
- Menu restatement (GPT-4o, scaled dev): −0.106 → −0.143, std 0.099 → 0.166; MW p=0.228; Welch
  p=0.017, d=0.27. REPORT BOTH TESTS; frame as "no robust distributional shift; if anything slightly
  worse", never an unqualified "null".
- Clock-framing (GPT-4o): −0.106 → −0.019 (≈82% reduction), std 0.099 → 0.024, MW & Welch p<0.001,
  d = −1.21.
- Learning ablation: FPSB SMAD first-5 0.2523 vs last-5 0.2524 (t p=0.997, MW p=0.913); SPSB 0.1282
  vs 0.1447 (n.s.).
- Appendix tiers: gpt-5-mini mean SMAD 6.68%; Llama-3-8B 57.58% (worse than humans in 6/7 formats).

**Ranking (from Engineering_simplicity/main.tex; $ = mean bid−value; DA = mean Kendall-τ error):**
- SPSB baseline: Claude −0.5, Gemini −1.6, GPT-4o −3.3, Gemma −5.3 (cross-model −2.67).
- Clock: Claude −0.1, Gemini −1.2, GPT-4o −0.5, Gemma −0.3 (cross-model ≈ −0.5).
- Direct DA: Claude 6%, Gemini 8%, GPT-4o 1%, Gemma 3% (μ = 4.2%); iterative DA: 0.0% all models.
- Payoff Tree: auctions −2.67 → −1.13 (GPT-4o −3.28→−0.86, Gemma −5.27→−2.34, Gemini −1.63→−0.53,
  Claude −0.49 ≈ null); DA 4.2% → 1.7% (Claude 5.8→2.0, Gemini 7.6→2.8, GPT-4o 1.0→0.6, Gemma 2.6→1.4).
- Forward planning (DA only): one-step 4.2% → 7.8% (GPT-4o 1.0→4.8, Gemma 2.6→12.7); two-step → 5.1%.
- Beliefs: auctions first-order −3.04, second-order −3.47; DA first 5.1%, second 9.1% (Gemma
  2.6→14.3); Gemini ≈ immune in both domains.
- Safety descriptions: Payoff Safety −2.67 → −1.53 (Claude −0.49→−0.30, Gemini −1.63→−0.38,
  GPT-4o −3.28→−1.88, Gemma −5.27→−4.17); Rejection Safety 4.2% → 0.2%.
- Provisional ρ (plan §4): OSP clock ≈0.8 / iterative DA 1.0; clock-framing ≈0.8 (GPT-4o only);
  safety 0.43 auct / 0.95 DA; tree 0.58 / 0.60; menu ≈0 (MW) but slightly negative signed;
  1st-order beliefs −0.14 / −0.21; lookahead −0.86 (DA); 2nd-order −0.30 / −1.17; risk-averse
  persona −0.76 / ≈−3.5.

**PROVENANCE FLAGS (insert \TODO where these numbers appear):**
- ES clock cells reproduce from the imported pipeline (`writeup/auction-v2-numbers.txt`: closed
  clock mean dev Claude −0.05, Gemini −1.24, GPT-4o −0.45, Gemma −0.33) — but the pipeline's clock
  configs are **APV (common [0,29]) with open/blind variants and mixed increments (1 vs 0.5)**, not
  the IPV clock ES main.tex describes. Sealed-bid cells are IPV (seed 1299).
- ES SPSB *baseline* means do NOT reproduce exactly from the pipeline CSV (per-axis baselines
  differ; pooling provenance unclear). Cite the ES paper numbers (they match the included figures)
  and add: \TODO{harmonized re-run (plan E3/E8) will finalize; pipeline CSV per-axis baselines differ}.
- Knife-edge margins (Rejection Safety 0.2% vs OSP 0.0%) carry no SEs yet: \TODO{E6 statistics}.

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

MISSING (use `\MISSINGFIG{<description + regeneration source>}` inside the figure environment,
keep caption + label so refs resolve):
- ranking forest/ladder figure (fig:ranking) — the money figure; spec in plan §4; typeset
  `tab:ranking` with the provisional ρ values as the interim main-text asset
- `figure3_intervention_comparison.png` (menu + clock-framing distributions)
- `ebay-winning-bid-non-closing.png`, `ebay-final-winning-closing.png`, `ebay_cdf_final_bid.png`
- `ebay_revenue_by_type.png` (appendix H)

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

# STATE.md — auction-v2 merged paper: current state

**Last updated:** 2026-07-10 (Anand's Claude session: provenance corrections + full run cycle + integration)
**Paper:** `writeup/auction-v2.tex` → `auction-v2.pdf` — compiles clean; page/TODO counts in the
build-log comment block of the master (recounted at the final commit of this cycle).
Build: `pdflatex auction-v2 && bibtex auction-v2 && pdflatex auction-v2 && pdflatex auction-v2`.

---

## 1. What changed this cycle (2026-07-08 → 07-10)

### A. Provenance discovery that changed the analysis conventions (LOAD-BEARING — PI should ratify)

The V12 `axis2_forward_baseline` template was never a plain SPSB baseline: git archaeology on the
engineer_simplicity repo shows it was a **two-stage sealed-bid-as-clock-exit description**
(Breitmoser-style clock-framing variant). Trace evidence is decisive (15–25% of claude/gemini/gemma
plans in that cell reason about the clock/exit framing vs 0% in axis-1/axis-3 baselines); behavior
too (it fixes Gemma, −6.5→−0.6, and wrecks Gemini, −1.25→−6.12). Full memo:
`results/merged_ranking/_axis2_baseline_provenance.md`.

**New canon** (implemented in `analysis/build_auction_cells.py`, `scripts/plots/ranking_forest.py`,
`analysis/build_trace_mediation.py`, and all affected text):
- Pooled axis baseline = **{axis1, axis3} only** (per-model means +0.54 / −1.25 / −2.94 / −6.53;
  cross-model −$2.55). Legacy pool kept as `POOLED_axis_baseline_legacy` for comparison.
- `axis2_forward_baseline` is analyzed as a **treated B3-variant cell** ("two-stage clock-exit
  description") — reported in §6.2 as direct paraphrase-sensitivity evidence.
- Axis-2 treatments (Payoff Safety, Payoff Tree) contrast against the corrected pool.

**The correction strengthens the paper**: auction Kendall's W 0.43→**0.70** (p=0.004; pooled 0.81),
T2>T3 sign test 7/8→**8/8**, Payoff Tree CI tightens to [+0.46,+0.68] with all-positive auction
cells, and Gemma's "anomalous axis-2 baseline" is explained rather than waved at.

### B. Corrected results now in the paper (all recomputed, seed 1299)

| Finding | Where |
|---|---|
| Traces: **complete dissociation, empty "both" cell** — Payoff Safety AND Payoff Tree are bids-only (tree's old "moves language" reading was contamination artifact); worst-case = language-only; menu = neither. B2 comprehension-mediated share ≤~35% (95% UB). | §6.5, tab:trace-dissociation, results/traces/mediation/ |
| Clock-framing (B3) is **sign-mixed**: helps GPT-4o 12.1→6.3, Gemma 26.8→13.8, Claude 8.3→7.2 (p<0.001 each); **hurts Gemini 5.1→9.5** (p<0.001). Pooled ρ=+0.30 [−0.77,+0.52]. Human-anchor agreement 3/4 — never write "universal in sign". | §6.2, §7.1 |
| Two clock-framing texts (canonical + the reclassified two-stage cell) both hurt Gemini, otherwise differ — measured paraphrase sensitivity, partially retires the paraphrase TODO | §6.2 |
| Menu (auction, corrected baselines): Gemma +$2.03 toward truthful (p<0.001), GPT-4o −$1.16 away (Welch .013/MW .54), Claude marginal, Gemini null; placebo sign test p=0.73 | §6.2, §7.1, intro P5 |
| Ranking ladder (corrected): OSP +0.97; safety +0.78; menu-invariance-DA +0.65; tree +0.59; clock-framing +0.30; lookahead −0.00; menu-auction −0.14; beliefs −0.35/−0.41; menu-mechanics-DA −1.67; risk-averse −1.82 | tab:ranking, fig:ranking, concordance.md |
| **B2 "no human anchor" was false**: GHIT-2024's Menu-SP and Katuščák–Kittsteiner (Mgmt Sci 2024) test invariant-exposing descriptions (understanding ≫ behavior in GHIT; positive behavior in K&K); Guillén–Hakimov 2018 mechanics-backfire **anchors our menu-mechanics cell**; Masuda et al. 2022 = advice (type b), cited for the taxonomy. §7 prediction repositioned to: auction domain + magnitude. Memo: `results/merged_ranking/_b2_human_anchor_literature.md`. 4 bib entries added. | §2, §6.4, §7, tab:ranking anchors |
| Reconstruction bootstrap bands on all 6 human anchors (all reproduce exactly; FPSB≫SPSB and clock orderings survive 100% of draws; **AC-B<SP-APV holds in only 92.6%** — disclosed). `figure1_bands` available. | app:human fragments in results/reconstruction_bands/ |
| Cost table corrected: Li 2017 = 548 subjects across two experiments, ~$5.4K documented for the main one (the old "$15,000" was unsourced); GHIT-2024 payment details verified from the paper | tab:cost |

### C. New experimental cells (all via OpenRouter; configs + logs committed)

- **E2 (IPV clock)**: `ascending_clock_ipv_closed` for **gpt-4o (K=50, SMAD 1.5%)** and **gemma
  (K=44, 1.8%)** — clean IPV description+draws; identification survives. **claude-3.5-haiku and
  gemini-2.0-flash are NOT servable on OpenRouter** (no active endpoints) — those two cells need
  native keys (runbook §2 unchanged). NOTE: audit found the legacy acb clock cells are
  *described-APV, drawn-IPV* (`private_value: "private"` + affiliated template) — §6.1 discloses.
- **E4 (Gemma fidelity)**: 6 sealed formats, K=30 (`configs/robustness_gemma/`, logs in
  `robustness_logs/*_gemma27b`). Gemma's difficulty ordering is much flatter than GPT-4o's
  (FPSB 24.8 vs SPSB 19.9 SMAD; ratio 1.25 vs human 4.4) — fidelity ordering is model-specific.
  Clock cells SKIPPED (per-tick mode ≈7h/cell; survey-vs-tick harmonization = native-key decision).
- **Frontier grid ×4** (gpt-5-mini, gpt-5, claude-sonnet-5, gemini-2.5-flash): full auction
  intervention battery + DA battery (DA: 3 models; gpt-5 DA skipped). Headlines: all ≈exactly
  truthful at every sealed baseline; **menu restatement collapses claude-sonnet-5** (0→−$8.71,
  SMAD 35.5%, d=−3.8) and degrades gemini-2.5-flash (2.3→9.1%); **true clock makes frontier play
  worse** (sonnet-5 0.27→8.6% SMAD) — the top rung inverts at the frontier. §6.4 frontier
  paragraph + app:ablations table. gpt-5 cells have reduced K=5–50 (model often omits
  <PLAN> tags; unparseable reps dropped; spsb cell top-up may still be finishing).
- Frontier DA: direct error 0–0.4% vs incumbents' 1–8%; OSP 0% (gemini-2.5 1.4% pick errors).

### D. Infrastructure (for whoever runs next)

- `new/topup_runs.py` — reruns ONLY missing rep-ids of a config with per-rep retries (safe with
  the builder's run-dir pooling; use instead of task_controller for partial cells). NOTE: it
  detects completed reps from `raw_output__run{N}.jsonl` cache files, which are gitignored
  (2026-07-10) — on a fresh clone it will think every rep is missing; the committed
  `result_*.json`/CSVs are the data of record.
- Frontier + E2 + E4 configs are OpenRouter-routed (`service_name: open_router`; canonical model
  ids restored by `MODEL_ALIASES` in build_auction_cells.py). `OPEN_ROUTER_API_KEY` required;
  ~$36 credit remained at last check.
- DA extraction fallback patched (util_da.py): uses OpenRouter gpt-4o-mini when only that key exists.
- **Fixed repo bug**: `configs/clock/01_07_..._gpt5mini.yaml` had `model: gpt-4-mini` (invalid) —
  this is why the gpt-5-mini AC-B robustness cells were empty. Fixed; frontier clock cell supersedes.
- Missing-template recovery: `axis2_forward_{onestep,tree,baseline}.txt` restored verbatim from
  engineer_simplicity git (`89cf2896`); `private_ac_closed.txt` written for E2.
- edsl pinned 1.0.6 in `.venv` (Python 3.12 via uv). gpt-5-mini/gpt-5 fail to emit <PLAN> tags on
  some prompts (systematic for clock-framing) — cells flagged with reduced K rather than imputed.

## 2. Remaining open items

**Needs native API keys (Kehang):** E2 claude/gemini incumbent clock cells; any harmonized
incumbent re-runs (E8-style); Gemma fidelity clock cells (+ survey-vs-tick decision);
gpt-5-mini/gpt-5 clock-framing cells if wanted (PLAN-tag parse issue, likely needs a prompt tweak).

**PI decisions (unchanged from last cycle):** EC'26 #2577 status; FPSB/TPSB intervention scope
(plan §11 Q7); LLM-judge trace taxonomy (needs ~2–3 author-hours of human labels); ratify the
axis-2 reclassification (§1A above) and the B2-literature repositioning.

**Analysis nice-to-haves:** adopt `figure1_bands` in place of `figure1.png` (fragments ready);
AC-B fragility footnote in §5/§7 (bands memo); paraphrase battery beyond the two clock-framing
texts; sonnet-5 menu-break trace read (why does the menu wording break it? traces are in
`experiment_logs/claude_sonnet5/intervention_menu/`).

## 3. History

- 2026-07-03/06/07: plan → first draft (86pp) → analysis+restructure cycles (107pp; Kehang's loop).
- 2026-07-08/10: this cycle — axis-2 provenance correction, mediation re-analysis, reconstruction
  bands, B2 literature repositioning, E2/E4/frontier batteries via OpenRouter, corrected-baseline
  recomputation of the full ranking (W 0.70/0.90/0.81), frontier scope section, integration.
  Checkpoint commit `5ec06a9`; final commit at end of cycle.

## Addendum (2026-07-10, PM): frontier failure-mode autopsy

Trace autopsies + one new cell resolved WHY the frontier breaks:
- **Menu break = wrong-formula retrieval**: claude-sonnet-5's menu traces announce the
  first-price equilibrium "(n-1)/n·v" and execute it flawlessly (−$8.71 ≈ −⅓E[v]), despite the
  prompt stating the winner pays the highest rival bid. Re-classification of the game, not noise.
- **"Clock inversion" = affiliation-language trigger, NOT the extensive form**: sonnet-5's clock
  exits (75% early) invoke the winner's curse; a clean IPV-described rerun
  (`experiment_logs/claude_sonnet5/ascending_clock_ipv_closed`, K=50) restores near-perfect play
  (SMAD 8.6%→2.0%, early exits 75%→3%). One sentence of affiliation language costs eight SMAD
  points by activating the wrong playbook. gpt-5/gpt-5-mini clock shifts are tick granularity.
- Framing adopted in §6.4/§8/app:ablations: **frontier failure mode = retrieval selection**
  (surface wording chooses which memorized playbook runs; wrong match executed flawlessly);
  incumbents fail by under-computation, frontier models by mis-retrieval; obviousness is
  reasoner-relative. Interpretation credit: Anand (2026-07-10 discussion).

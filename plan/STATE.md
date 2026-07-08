# STATE.md — auction-v2 merged paper: current state

**Last updated:** 2026-07-07 (after the restructure + analysis cycle)
**Paper:** `writeup/auction-v2.tex` → `auction-v2.pdf` — **107 pages, compiles clean**
(0 errors, 0 undefined refs/citations, 0 duplicate labels, 0 missing figures).
Build: `pdflatex auction-v2 && bibtex auction-v2 && pdflatex auction-v2 && pdflatex auction-v2` (verified from scratch).
**Counts:** 31 `\TODO` flags (was 61), 0 `\MISSINGFIG` (was 4). Classification in the master's build-log comment block.

---

## 1. Current architecture (after this cycle's restructure)

- **Main domain = auctions.** DA/matching moved to `appendix_da.tex` ("Robustness in a Second
  Domain: Two-Sided Matching") per PI directive — main text carries a one-paragraph forward pointer.
- **§1–4** intro / related / lever-space framework (H1–H3) / design (with baseline-declaration
  paragraph and master calibration table).
- **§5 Validation** vs human data + eBay field exhibit (all four eBay figures now real) + validity map.
- **§6 The ranking** (auctions): extensive form → descriptions → scaffolds → synthesis
  (tier table with pooled ρ [95% CI], Kendall's W, sign tests) + **new traces subsection**
  (`sec:ranking-traces`, the double-dissociation result).
- **§7 (`07_humans.tex`, retitled)** — "Ordinal Agreement and the Limits of Cardinal Calibration":
  ordinal case (rung-by-rung human anchors) + the new cardinal analysis (tab:cardinal; verdict:
  no single tuning works across mechanisms).
- **§8 Discussion** (frontier scope conditions, traces implication, practitioner box, cost table),
  **§9 Conclusion**.
- **Appendices:** human reconstruction / procedures / learning / ablations (incl. new genuine
  frontier table) / prospect–risk / prompts+inventory / **traces details (new)** / **DA robustness
  (rebuilt)** / eBay (+reserve audit).

## 2. Key results now in the paper (computed this cycle, seed 1299, all reproducible)

| Finding | Where |
|---|---|
| Menu restatement ×4 models: sign-mixed, null on average (placebo sign test p=0.73); Gemini actually improves, GPT-4o worsens | §6.2, results/merged_ranking/auction_cells_summary.md |
| Clock-framing ×4 models: improves all, significant 3/4, ρ=+0.29 [+0.17,+0.45] — modest, NOT ≈OSP (old GPT-4o-only claim corrected) | §6.2 |
| True clock ×4 models: SMAD 1.4–5.2%, p<0.001 all | §6.1 |
| SPSB baseline provenance RESOLVED: ES published numbers = dedicated spsb runs; axis baselines differ; both declared | §4 baseline declaration |
| Tier structure: Kendall's W 0.49/0.90/0.69; 3 of 4 tier boundaries hold; baseline-vs-menu fails (4/8) — invariance-content story sharpened | §6.4, concordance.md |
| DA: all published numbers reproduce; NEW: menu-property improves (4.2→1.8%), menu-mechanics worsens (4.2→6.9%), textbook-SP = 0.0% ×4 | app:da (E7 done) |
| "Zero misreports" RESCOPED: exact for pick-protocol in 3/4 models (rule-of-three UBs ~0.9%); yes/no tree exposes Claude 24.1% Type-1 | app:da (E9 done) |
| Traces double dissociation: Payoff Safety moves bids w/o changing stated reasoning; worst-case scaffold changes reasoning w/o moving bids; 53% shading intent, 2% dominance language | §6.5 + app:traces |
| Cardinal verdict: NO single tuning aligns LLMs with humans across mechanisms; risk-seeking persona = only direction-fixer (SP/TP) but breaks FPSB; TPSB un-tunable | §7, results/cardinal/ |
| Frontier (genuine gpt-5-mini): SPSB near-perfect (0.2% SMAD), FPSB ≈ exact RNE, TPSB fails (60% SMAD) — constraints migrate, don't vanish | §8 + app:ablations |
| eBay: sniping + soft-close reproduce (MW p=3.5e-05); T4-further-dampens claim REMOVED (data contradicts); revenue null conditioned on disabled price-lift channel | §5.3 + app:ebay |

**Direction-share convention fixed everywhere:** repo-canonical (humans overbid 67.2% of bids /
92.2% among deviators), old 96%/81.3% band-convention figures footnoted where retained.

## 3. Data & assets produced this cycle

- `results/merged_ranking/`: auction_cells.csv (294 cells, 45,909 bids), da_cells.csv (254 rows),
  concordance.md, ranking_forest_data.csv, ebay_summary.md + ebay_figure_stats.json, frontier_summary.md
- `results/cardinal/`: cardinal_grid.csv (95 cells), cardinal_summary.md, section7_evidence.tex
- `results/traces/`: trace_features.csv (21,990 traces × 18 features), ols_results.txt,
  traces_summary.md, BRAINSTORM.md, prevalence CSVs
- `analysis/`: build_auction_cells.py, build_da_cells.py, build_cardinal_grid.py, build_trace_features.py
- `scripts/plots/`: ranking_forest.py, intervention_comparison.py, regenerate_ebay_figures.py
- `writeup/figures/`: ranking_forest.pdf (money figure), figure3_intervention_comparison.png (2×4),
  4 eBay PNGs — all previously missing figures now exist with generating scripts
- `recovered_logs/`: git-recovered V12 GPT-4o grid (7,356 files), Claude partial, eBay full grid
  (7 treatment folders restored from commit 734c0e88). NOTE: `recovered_logs/experiment_logs_with_explanation`
  is **GPT-4o, not gpt-5-mini** (config-verified) — never cite it as frontier data.
- `Engineering_simplicity/engineer_simplicity-main/configs_{auction,da}/frontier/`: 56 ready-to-run
  frontier configs (claude-sonnet-5, gpt-5-mini, gpt-5†, gemini-2.5-flash†; † = verify model ID)
- `plan/FRONTIER_RUNBOOK.md`: exact commands, env keys, ~$75–120 estimated cost, fold-in instructions

## 4. Remaining `\TODO`s (31), classified

**Blocked on API keys (~19):**
- Frontier intervention battery (configs + runbook ready; retires the §6/§8 scope-condition TODOs)
- E2: IPV ascending clock ×4 models (the biggest remaining provenance caveat — current clock cells
  are APV with mixed increments)
- E4: Gemma 27B fidelity battery (+ regenerate appendix2_model_comparison.png, dropping the
  misattributed gpt-5-mini series)
- E8: harmonized SPSB re-run at pinned K; paraphrase robustness (3×2); eBay r∈{70,85} with the
  price-lift bug fixed; traces cross-model FPSB/TPSB runs (BRAINSTORM option 3)

**Analysis-only (~7):** reconstruction-uncertainty bootstrap bands on human anchors;
Monte-Carlo bands in fig:smad-comparison; Myerson binding-frequency exhibit polish; minor PNG regens.

**Co-author decisions (~4-5):**
1. **Traces next step** (see §5 below — PI decision requested)
2. `\ifanon` build still doesn't scrub intro's open-source sentence + Disclosure paragraph
3. Winner's-curse table significance stars (vs theory — allowed under R8, flag for uniformity)
4. Cost-table dollar figures verification ($400 / $15,000 / $2,000)
5. EC'26 #2577 status (gates any submission)

## 5. OPEN DECISION: reasoning traces next step (user asked for options)

Baseline analysis + double dissociation are already IN the paper. `results/traces/BRAINSTORM.md`
ranks six deeper options. **Recommended bundle: option 2 + option 1** (fold 4 into 2):

1. **LLM-judge strategy taxonomy** (~$20–50 API + 100-trace human validation set; 2–3 days) —
  turns regexes into a defensible instrument; classifies all 22k traces into strategy types.
2. **Formal mediation analysis of the double dissociation** (FREE, 1–2 days, existing CSV) —
  manipulation-check table per lever + the "moves language / moves bids" 2×2 — the strongest
  zero-new-data upgrade.
3. Cross-model script-invariance (needs small API runs or recovered logs, ~$20).
4. Stated-vs-revealed consistency metric (free, 1 day, foldable into 2).
5. Early-warning classifier for large errors (medium; talk-demo value).
6. Embedding clustering (low referee value; robustness appendix at best).

## 6. Known caveats a referee could find (all disclosed in-text)

- Clock cells are APV (not IPV as ES claimed); IPV clock re-run pending (E2).
- Ranking's DA ρ values are ratio-unstable for GPT-4o (1.0% baseline) — clipped, ranks unaffected.
- ~40% duplicate traces (temp-0.5 determinism) — dedup-robust, full-sample SEs optimistic.
- eBay reserve channel partly mechanical (simulator never lifts price to met reserve).
- 17% tied DA values — tie-robust τ provided; prior "misreports" for 3 models were tie artifacts.
- Cross-model means are unweighted (stated in captions).

## 7. Suggested next actions (in order)

1. PI: read the 107pp PDF — priority: abstract, §6.4 (tier revision), §6.5 (traces), §7 (cardinal), app:da.
2. PI: decide traces bundle (§5) and EC #2577 status.
3. Export API keys → run `plan/FRONTIER_RUNBOOK.md` battery + E2 IPV clock + E4 Gemma (one command
  each; ~$100–150 total) → `python3 analysis/build_auction_cells.py && build_da_cells.py` →
  regenerate ranking figure (`scripts/plots/ranking_forest.py`) — retires ~19 TODOs.
4. Free analysis: traces option 2 (mediation) + reconstruction bootstrap bands.
5. Co-author circulation (STATE.md + PDF); then update CONVENTIONS.md §3 canon (now stale on
  menu/clock-framing/direction conventions) before any further text edits.

## 8. History

- 2026-07-03: plan/plan.md written (3-design × 3-judge architecture selection; Design B chosen).
- 2026-07-06: auction-v2 first full draft (86pp clean; 61 TODOs; 9 writers + integrator).
- 2026-07-07: analysis cycle (6 agents: cells/DA/eBay/traces/cardinal + figures) + restructure
  cycle (6 rewriters + integrator): DA→appendix, §7 rewrite, 30 TODOs resolved, all figures real,
  107pp clean. Workflow runs: wf_d7c8f5c3 (plan), wf_5eed586b (draft), wf_d67d83b2 (analysis),
  wf_5f5e35ef (restructure).

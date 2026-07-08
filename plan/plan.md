# Merged-Paper Plan: Benchmarking + Engineering Simplicity → One Strong Econ Paper

**Last updated:** 2026-07-03
**Decision:** Merge `Engineering_simplicity/` into `writeup/` as one paper whose central object is an
**empirical simplicity-preservation ranking** of mechanism-design levers, with the writeup's
human-benchmarking as the validation layer that licenses the ranking. (Architecture chosen after a
3-design × 3-judge comparison; see §12 for the record.)

---

## 0. Thesis and title

**Thesis (one sentence).** Across two canonical strategy-proof domains (second-price auctions and
deferred acceptance) and four LLM families, the levers available to a mechanism designer form a
stable empirical simplicity-preservation hierarchy of **tiers** — OSP extensive forms at the top;
incentive-exposing descriptions and contingent-reasoning scaffolds in a strong second tier (whose
internal order flips across domains); baseline and menu restatements doing nothing; and
forward-planning and belief scaffolds, which actively **backfire** — an ordering that parallels the
theoretical simplicity hierarchy and matches human experimental evidence on every rung where a
human benchmark exists. (Tier language here deliberately matches the claim discipline in §4 —
do not let the thesis assert a strict total order the data may not support.)

**Title options** (prefer 1 — do not brand the merged paper as "Engineering Simplicity v2"):
1. *What Makes Truth-Telling Obvious? An Empirical Ranking of Simplicity-Preserving Design for LLM Agents*
2. *Simple Mechanisms for Artificial Agents: Human Benchmarks and a Ranking of Simplicity-Preserving Design Levers*
3. *Obvious to Machines: Implementation, Description, and Reasoning Scaffolds in Dominant-Strategy Mechanisms with LLM Bidders*

**Why this is one paper, not two stapled.** One question owns every section — *which
implementation/presentation levers keep dominant-strategy play intact for boundedly rational
agents?* — answered in four moves: (i) define the lever space from simplicity theory; (ii) build
the LLM testbed and validate its behavioral fidelity against moment-matched human data (the
writeup's benchmarking becomes the **license**, not a co-headliner); (iii) deliver the ranking
(ES results + the writeup's menu/clock-framing interventions as rungs ES was missing); (iv) anchor
every rung to human evidence where it exists, and issue the unanchored rungs as predictions for
future human experiments.

---

## 1. Pre-flight gates (resolve BEFORE any writing — these protect months of work)

- [ ] **G1 — DA pipeline existence.** The DA code, configs, raw data, and Kendall-τ analysis exist
  **nowhere in this repo or its git history** — only `rule_template/DA/` prompts and 9 final PDFs in
  `Engineering_simplicity/plots/`. The paper's two most-quoted numbers (0.0% OSP-DA; Rejection
  Safety 4.2%→0.2%) are currently unreproducible here. **Confirm the external ES pipeline exists and
  is importable** (which machine/repo?). If lost: re-implement (4×4 Gale–Shapley + Ashlagi–
  Gonczarowski OSP query tree + Kendall-τ ≈ 2–3 days, prompts already templated) and re-run.
- [ ] **G2 — EC'26 #2577 status.** If accepted → merged paper is the journal "full version"
  superseding both predecessors and must say so. If under review → submitting the merge anywhere
  violates overlap policy. If rejected → merge freely. Also note `writeup/main.tex` itself carries EC
  scaffolding ("Submission 230").
- [ ] **G3 — Re-run budget commitment.** The ranking as currently stated **splices non-harmonized
  runs** (different value grids, increments, APV-vs-IPV clock cells, model coverage, zero SEs on ES
  numbers, knife-edge margins like 0.2% vs 0.0% at N=50). The merged paper is therefore a ~2–3-week
  experimental program (§6), not a writing exercise. Get co-author + API-budget sign-off on that.
- [ ] **G4 — Co-author sign-off on the cut list** (§7), especially: eBay hidden-reserve → appendix,
  eBay sniping compressed to a field-validation exhibit, Llama/gpt-5-mini → appendix tiers. These
  touch multiple co-authors' contributions.

---

## 2. Narrative: introduction skeleton (9 paragraphs)

The intro carries the paper. Claim → backing result:

1. **P1 The design question.** Incentive compatibility on paper ≠ dominant-strategy play in minds;
   simplicity theory (Li 2017 OSP; Börgers–Li; Pycia–Troyan; Li 2024's three cognitive axes) says
   which implementations make good play cognitively feasible. As LLM agents begin to transact, the
   question becomes operational: which designer levers preserve truthful play for this new bounded
   reasoner? Hook: GPT-4o deviates −$3.3 on values averaging $24.5 in SPSB — yet a one-sentence
   description change nearly eliminates the error.
2. **P2 What we do.** Three lever families (extensive form / descriptions / reasoning scaffolds),
   two strategy-proof domains (SPSB auction N=3 IPV; student-proposing DA 4×4 Ergin-acyclic), four
   model families (GPT-4o anchor, Claude 3.5 Haiku, Gemini 2.0 Flash, Gemma 27B) → the ranking.
3. **P3 Why the testbed is credible.** Moment-matched reconstructions of human data (Kagel–Levin
   1993; Li 2017; Breitmoser 2022; Gonczarowski et al.) + unified SMAD metric; LLMs reproduce the
   human difficulty ranking (FPSB 27.55% vs SPSB 8.69%, mirroring humans' 24.76% vs 5.65%), the
   winner's-curse comparative statics, eBay sniping under hard close; no cross-round learning.
4. **P4 Ranking result 1 — OSP tops.** Clock compresses deviations −2.67→≈−0.5 and kills tails;
   iterative OSP DA achieves 0% observable misreports across all four models — first experimental
   OSP-DA test with any agent.
5. **P5 Ranking result 2 — descriptions split.** Menu restatement: **no robust distributional
   shift** (MW p=0.228; but report Welch p=0.017 with small d=0.27 and signed mean −0.106→−0.143 —
   i.e., "null, if anything slightly worse"; do NOT write an unqualified "null", a referee will
   find the Welch rejection) — consistent with the Gonczarowski human null. Safety-exposing text:
   large (Payoff Safety halves auction deviations; Rejection Safety 4.2%→0.2% ≈ full OSP;
   clock-framing d=−1.21 ≈ true clock). Active ingredient = exposing the incentive invariant, not
   re-wording rules.
6. **P6 Ranking result 3 — scaffolds double-edged.** Payoff Tree (contingent) halves deviations in
   both domains; forward-planning lookahead and belief scaffolds systematically backfire
   (DA 4.2%→7.8%/9.1%; auctions −2.67→−3.47), worst in the weakest models.
7. **P7 The assembled ranking + theory parallel.** Tier structure concordant across models×domains
   (Kendall's W); localizes the constraint: not *computing* the dominant strategy but *seeing that
   truth-telling is safe*.
8. **P8 Human anchors + the divergence that strengthens the claim.** Every human-anchored rung
   agrees in sign. Humans overbid SPSB (96%), GPT-4o underbids (81%) — yet identical levers fix
   both populations ⇒ constraints live in the strategic problem, not human psychology. The
   unanchored rung (safety descriptions) is delivered as a cheap, falsifiable prediction for the
   next human experiment.
9. **P9 Implications + contributions.** (1) the ranking; (2) first OSP-DA experiment; (3)
   moment-matching methodology + SMAD family, open-sourced; (4) design guidance: honest safety-
   exposing descriptions recover most of OSP without redesign; never scaffold strategizing.

---

## 3. Section outline (source mapping: reuse / rewrite / cut / new)

New tex tree `paper/` (leave `writeup/` and `Engineering_simplicity/` frozen as sources — this also
sidesteps the trap that `writeup/contents/discussion.tex` actually contains the **eBay section** and
`limitation.tex` contains the **Discussion**):

| § | File | Content and sources |
|---|---|---|
| 1 | `01_intro.tex` | NEW per §2 skeleton. De-macro the two live `\khz{}` blocks (`intro.tex:5,7`). Internalize all six `zhu2024evidence` self-cites (ES main.tex:71,75,110,220,279,294) as internal cross-refs. Cut ES sonnets/bar-exam hook; cut "cheap proxy" as thesis (→ one clause). |
| 2 | `02_related.tex` | Merge, six blocks: auctions [W related_work.tex:3–6], simplicity theory [ES 93–97], descriptions/framing [W:8 + ES:106], matching/DA [ES 99–106], LLMs-as-agents + 3-category taxonomy [W:15–24], automated MD trimmed [W:10–13]. Add `levin1996revenue` (cited in results.tex, in **neither** bib — compile-breaking). |
| 3 | `03_framework.tex` | NEW ~1.5pp: the lever taxonomy + ex-ante hypotheses H1–H3 (theory-derived, pre-empting the prompt-engineering attack). Families: **A** extensive form (clock; iterative DA) · **B1** menu-restating / **B2** safety-exposing / **B3** clock-framing descriptions · **C1** contingent / **C2** forward-planning / **C3** belief scaffolds · **D** preference framings (appendix). |
| 4 | `04_design.tex` | Experimental design: mechanisms/environments [W methods.tex:95–169 + ES 126–214 (DA, keep near-verbatim)], **canonical calibration table T1** (kills all cross-paper drift, §5), treatments grid, model policy, SMAD family + preservation index ρ, human reconstruction [W methods.tex:5–49, epistemic status rewritten — see R8]. |
| 5 | `05_validation.tex` | Compressed W results §§1–3 (~2.5pp): difficulty ranking + direction divergence (promoted, load-bearing) · winner's curse (table stays) · **eBay sniping/soft-close as a one-paragraph field-validation exhibit + 1 figure** (graft — do NOT cut entirely; hidden-reserve null → appendix) · stability (learning/temperature pointers). Ends with **the validity map** (graft from Design C): table of phenomenon × human finding × LLM finding × verdict (transfers / diverges). The humans-overbid/LLMs-underbid red cell is declared here, then shown irrelevant to lever ordering in §7. |
| 6 | `06_ranking_*.tex` | The product (~6pp), three subsections + synthesis: **6.1** extensive forms (merge W results.tex:47–68 APV cell [human-anchored] + ES §3 IPV cell [pure-cognitive identification]; DA 0% with observability caveat kept verbatim). Then the **bridge** (graft from Design A): "OSP bundles game-tree change, action coarsening, and safety salience — which margin does the work?" → **6.2** descriptions (menu null + clock-framing [W results.tex:104–124] + Payoff/Rejection Safety [ES §4.4] + NEW menu-in-DA cell) → **6.3** scaffolds (ES §4.1–4.3, keep Gemini-immunity/Gemma-fragility heterogeneity) → **6.4** the assembled ranking: money figure + tier claim + concordance stats + honest within-tier flips (tree beats safety in auctions; safety beats tree in DA). |
| 7 | `07_humans.tex` | NEW ~1.5pp: rung-by-rung human anchoring; direction-reversal reframed from "proxy failure" to "substrate independence of the levers"; the out-of-sample prediction (safety-exposing text on human subjects). |
| 8 | `08_discussion.tex` | Design implications + **practitioner guidance box** (graft: if you must keep a direct mechanism — add safety description + payoff tree; never prompt lookahead/beliefs; audit vendor "reasoning enhancements" as backfire levers) · scope conditions (gpt-5-mini near-optimal ⇒ frontier check is a *finding* delimiting the bounded-rationality regime, not a gap) · **one reconciled cost table** (replaces $400 / $15,000 / $2,000 / $10 scattered claims) · limitations (reconstruction is model-based; prompt-template specificity; 0% observability). |
| 9 | `09_conclusion.tex` | NEW, ≤0.5pp. Cut: nation-scale voting (W conclusion.tex:16), orphaned "risk-averse bidding" claim (conclusion.tex:6 — its CRRA/CARA support exists only commented-out in drafts). |
| A–H | `appendix_*.tex` | A human reconstruction + mixture table + NEW reconstruction-uncertainty bootstrap · B procedures/prompts (merged, dedupe the ×12 `fig:sealbid_prompt` labels; split the `intervention_proxy_breitmoser` name collision → `osp_clock_iterative` vs `desc_clock_framing`) · C learning ablation · D model/temperature ablations (de-star, rewrite temperature text, Claude naming fix; Llama = capability floor, gpt-5-mini = frontier ceiling) · E prospect/risk personas (ES App B = ranking's bottom rungs) · F prompt library + old→new taxonomy mapping + run-status column for the ~19 declared-but-unreported variants · G DA Algorithm 1 · H eBay details incl. hidden-reserve null + Myerson-reserve check. |

---

## 4. The ranking: construction and presentation (the paper's product)

- **Object.** For lever L, domain d ∈ {auction, DA}, model m: D(L,d,m) = scaled deviation from
  dominant strategy (SMAD % of E[b*]=24.5 for auctions; normalized Kendall-τ error % for DA).
- **Headline statistic** (graft from Design C): **preservation index ρ = 1 − D(L)/D(baseline)**,
  computed within model×domain (immunizes the ranking against cross-model level disputes — this is
  what makes the W-vs-ES Claude-ordering contradiction moot). ρ=1 perfect play, ρ=0 no effect,
  ρ<0 backfires.
- **Claim discipline (pre-committed NOW).** The headline is a **tier structure (partial order)**,
  not a strict total order: A > {B2,B3,C1} > baseline ≈ B1 > {C2,C3} > D-averse. Do **not** assert
  "8/8 cell concordance" in the intro before harmonized data exist — write "concordant across
  models and domains (Kendall's W = …)" with CIs, and report within-tier domain flips honestly.
- **Statistics:** Kendall's W across the 8 model×domain cells; pairwise sign tests for adjacent
  tiers; bootstrap CIs on every ρ; MW + Welch + Cohen's d vs own baseline; N→100 top-up on
  knife-edge cells (Rejection Safety 0.2% vs OSP 0.0%).
- **Money figure (F1).** Horizontal forest/lollipop, rows = levers grouped by family, ordered by
  pooled ρ; baseline as bold zero line; shaded region ρ<0 labeled "backfires"; per-cell marks
  (shape = domain, color = model) + pooled median with CI; **gold diamonds = human anchors**
  computed from the moment-matched reconstructions (clock, AC-B, menu, baseline) with
  reconstruction-bootstrap whiskers; shaded band "no human experiment exists — lab prediction" over
  the unanchored rungs; Panel B inset: cross-model rank-agreement heatmap.
- **Provisional rungs** (finalized by re-runs): OSP clock ρ≈0.8 / iterative DA ρ=1.0 · clock-framing
  ρ≈0.8 (GPT-4o only → must extend ×4 models) · safety descriptions ρ≈0.43 auctions / 0.95 DA ·
  Payoff Tree ρ≈0.58 / 0.60 (note: tree beats safety in auctions, safety beats tree in DA — hence
  one tier) · menu ≈0 by MW but slightly negative on signed mean (report both tests) · first-order
  beliefs ρ≈−0.14 / −0.21 · lookahead ρ≈−0.86 (DA) · second-order beliefs ρ≈−0.30 / −1.17 ·
  risk-averse persona ρ≈−0.76 / −3.5. Current clock cells are K=40 (config `repetitions: 40`),
  below the pinned K≥50 — top up in the re-runs.

---

## 5. Reconciliation decisions (concrete, not options)

1. **Model set.** Canonical four = GPT-4o (2024-08-06, anchor) + Claude 3.5 Haiku (2024-10-22) +
   Gemini 2.0 Flash + **Gemma 27B** (ES's open-weight choice wins; re-run Gemma on the auction
   battery rather than Llama across ~30 lever cells). Llama-3-8B → appendix capability floor
   (SMAD 57.6%); gpt-5-mini → appendix frontier ceiling — its near-optimal play (SMAD 6.68%) *is*
   the evidence for excluding reasoning models from the bounded-rationality grid.
2. **Claude naming.** `claude-3-5-haiku-20241022` everywhere; fix "Claude Sonnet 3.5" at
   `writeup/contents/appendix.tex:292,301`; footnote that `robustness_logs/*claude_sonnet*` dirs
   actually ran Haiku (configs confirm).
3. **SPSB-IPV model-ordering contradiction** (W: Claude SMAD 9.72 > GPT-4o 8.69; ES: Claude −0.5
   best). Recompute **both SMAD and signed mean on one canonical dataset per model**; report both;
   if "Claude best-signed / worse-absolute" persists, that's a feature of reporting both metrics.
   The ranking itself uses within-model ρ, so it is invariant to this. Drop ES main.tex:318's
   "decreasing order of success" sentence.
4. **Canonical calibration (table T1).** IPV v ~ Unif{0..49}, bid grid **$0.1** (ES's "$0.01" at
   main.tex:228 is wrong per configs), clock tick **$0.5** (fix "$1 increments" at W
   appendix.tex:456), N=3, T=0.5, one-shot; APV c~U[0,29]+ε~U[0,20]; CV V~U[20,29], η~U[−20,20];
   eBay U[0,99] declared separately; DA c~U[40,70]+ε~U[0,20]. K pinned per cell: anchor 100,
   robustness/lever grid ≥50, DA 50, clock 50.
5. **IPV vs APV clock cells: keep both, purpose-labeled.** APV = human-benchmark comparability
   (Li/Breitmoser); IPV = identification (clock reveals nothing payoff-relevant ⇒ purely cognitive
   channel). ES's clock = W's **AC-B (closed)**; state in T1.
6. **The L7 conflation (load-bearing — resolve empirically).** The name `intervention_proxy_breitmoser`
   refers to the **true iterative clock** in the ES appendix but the **sealed-bid clock-framing
   template** in the repo. Until provenance of ES Fig 1's clock column is audited (or superseded by
   the IPV clock re-run), ranking rungs 1 and 2 are not empirically distinguished — and that
   distinction (presentation alone ≈ extensive-form change) is the paper's most interesting claim.
   Split prompt IDs: `osp_clock_iterative` vs `desc_clock_framing`.
7. **Taxonomy fixes.** Payoff Tree = contingent (C1), overriding the repo filename
   `axis2_forward_tree.txt`; Rejection Safety = description (B2), not axis-2; clock-framing = B3.
   Old→new mapping table in Appendix F; `results/v12_interventions/intervention_rankings.csv`
   carries old labels — map in analysis code.
8. **Statistics standard.** SMAD family everywhere; ES auction results recomputed as SMAD
   (÷ E[b*]=24.5); every treatment effect gets SE/MW/Welch/d/CI. **Drop all significance stars
   against reconstructed humans** (statistically circular; `appendix.tex:324–326`); replace with
   Monte-Carlo bands. Rewrite the epistemic-status sentence: *comparisons to reconstructed humans
   are made at the level of rankings, directions, and comparative statics; levels and tests are
   reserved for theory benchmarks.*
9. **Temperature text** (`appendix.tex:246–253`) contradicts its own table (T=0.1 strictly best in
   3/7 formats — AC-B, AC-APV, FP-CV — and worst in 4/7). Rewrite: effects modest and
   non-monotonic; T=0.5 kept as convention for comparability, not performance.
10. **Bibliography.** Base = `es_bib.bib` → `paper/merged.bib`. Actual delta (verified): 89 of
    `llm_auction.bib`'s 92 unique keys are already in es_bib; add the **3 W-only keys**
    (`jiang2025incentive`, `ravindranath2023data`, `wang2026llm` — all cited in related_work.tex)
    + `levin1996revenue`; dedupe the 9 internal duplicate entries in `llm_auction.bib`; delete
    `zhu2024evidence`.
11. **Anonymity/boilerplate.** Named working-paper master with `\ifanon` toggle; collapse W's
    duplicate `\title`/preamble blocks (the "Submission 230" author line at main.tex:177 is already
    commented out — just delete it); one Claude-assistance disclosure; `\Comments=0`; scrub
    NeurIPS'23 footnote + GitHub URL under anon builds.
12. **One-shot consistency.** Fix `appendix.tex:191` ("10 independent rounds") → single-shot T=1
    canonical; the learning appendix justifies it for both studies.

---

## 6. Experiments and analyses

**Must-have (blocking):**
| ID | What | Feasibility |
|---|---|---|
| E1 | **DA pipeline import or re-implementation + full DA grid re-run** (2 base × ~8 levers × 4 models × 50 reps) | Critical path; see gate G1 |
| E2 | **IPV ascending clock × 4 models** (repo clock data is APV-only) | HIGH — config edit from `configs/clock/` |
| E3 | **Cross-model auction lever grid**: {menu, clock-framing, Payoff Tree, Payoff Safety, 1st/2nd-order beliefs} × {Claude, Gemini, Gemma} × 50 reps | HIGH — templates in `rule_template/V10,V12`; ~2,700 calls/model. **Clock-framing ×4 models is non-negotiable** (currently GPT-4o-only, and it is rung 2 of the headline) |
| E4 | **Gemma 27B on the fidelity battery** (~9 configs × 40–100 reps) | HIGH — add provider config |
| E5 | **Git recovery**: `git checkout 921203c0^ -- experiment_logs_gpt_4o experiment_logs_claude old/experiment_logs_old` (V12 scaffold raw data, 7,356 files; eBay logs under `old/experiment_logs_old/V10/ebay_closing_rule/`). Note: the `.gitignore` patterns (`experiment_logs/**/*.jsonl`) do NOT match these paths, and `git checkout <commit> -- <path>` stages files regardless — recovery is clean | HIGH |
| E6 | **Statistical layer** over every ES number (SE/MW/Welch/d/CI, Kendall's W, sign tests) + N→100 top-ups on knife-edge cells | Analysis-only |
| E7 | **Menu restatement in DA** (`rule_template/DA/da_direct_menu_*` exist, zero results) — completes the sharpest contrast (matched menu-null vs safety-large) across both domains, with the cleanest human anchor | Requires E1 |
| E8 | **Harmonized SPSB-IPV baseline** ×4 models + gpt-5-mini (GPT-4o K=100) — the canonical cell every figure keys off | HIGH |
| E9 | **OSP-DA error accounting**: Type-1/Type-2 per node, rule-of-three upper CI on the 0% | Analysis-only |
| E10 | **Regenerate 5 missing writeup figures** (`figure3_intervention_comparison`, 3 eBay timing figs, `ebay_revenue_by_type`) — paper currently doesn't compile with all figures | After E5 |

**Nice-to-have (ordered):** eBay reserves at/above Myerson level r∈{70,85} + binding-frequency stat
(retires DCP's commented objection at `writeup/drafts/llm_auction.tex:829–830`) · combined levers
(safety + tree = minimal-intervention frontier) · gpt-5-mini on 3–4 key levers (ranking flattens at
the frontier — measured scope condition) · paraphrase robustness (3 paraphrases × 2 headline
levers) · no-CoT ablation restored from `writeup/drafts/llm_auction.tex:1906–1941` (baseline CoT
prompt is itself a measured scaffold — cheap, reinforces the anti-prompt-engineering defense).

**Scope decision needed — third-price / first-price intervention batteries.** The repo contains
full FPSB/TPSB intervention templates and configs (`rule_template/V12/third_price_interventions/`,
`first_price_interventions/`, `configs/intervention_{gpt5,claude}/intervention_proxy_breitmoser_{first,third}.yaml`)
and recent TPSB N=5 work (commit `0f2e202f`); the writeup derives the TPSB equilibrium in methods
(`methods.tex:21,26`) and reconstructs Kagel–Levin TPSB humans (`appendix.tex:23`) but reports no
TPSB results section — an inherited dangling thread. **Default decision:** TPSB stays a Fig-1 +
appendix fidelity datapoint only; the FPSB/TPSB *intervention* batteries are out of the ranking's
scope (the ranking is about strategy-proof mechanisms; FPSB's benchmark is BNE, a different
object) — park them as an appendix robustness note or explicit future work. Confirm with
co-authors (§11 Q7).

---

## 7. Cut list (with reasons)

1. **eBay hidden-reserve subsection from main text** → Appendix H (all-null t-tests |t|<0.15 +
   unresolved Myerson objection = referee bait). eBay **sniping stays** as a one-paragraph field
   exhibit (co-author equity + only field validation).
2. **"LLMs as cheap human proxies" as thesis** → one cost paragraph + cost table. Nation-scale
   voting, online-laboratory framing, combinatorial-auction futures: cut.
3. **Conclusion's orphaned risk-aversion claim** (support only in commented-out draft CRRA/CARA).
4. **Llama-3-8B and gpt-5-mini from main-text figures** → appendix floor/ceiling.
5. **Significance stars vs reconstructed humans** (circular).
6. **ES's sonnets/bar-exam opener + philosophical coda** → one Discussion paragraph.
7. **ES's broken rule-following promise** (main.tex:320): either restore from V10 advice data as an
   appendix or delete the promise — do not ship the dangling reference.
8. **~19 declared-but-unreported prompt variants** in ES's inventory table: add a run-status column
   or delete rows; a declared-but-silent grid is a referee gift.
9. **Old-draft material stays cut**: all-pay, currency/language robustness, semantic analysis,
   post-bidding interviews (exception: no-CoT ablation, §6).
10. Mechanical: duplicate abstract/`\title`/preamble, EC boilerplate, ToC page, `\COMMENT` macro.

---

## 8. Venue and referee defense

**Venue.** Primary **Management Science** (market design / behavioral interface); alternates *GEB*
(simplicity-literature lineage) or *AEJ: Micro*; conference stamp via EC only after G2 resolves.

**Attack 1 — "ranking splices non-harmonized runs, no inference, knife-edge margins."**
→ E1–E8 harmonized single-config re-runs; E6 statistics; tier-structure claim discipline; N=100 on
knife-edge cells; observability caveat never dropped.

**Attack 2 — "human benchmarks are simulations of simulations; circular."**
→ ranking never depends on reconstructed humans (they anchor transferability only, structurally
separated in §5 vs §6); no tests against reconstructions; reconstruction-uncertainty bootstrap into
every anchor; KL93 internal-inconsistency footnote kept (credibility asset); eBay field exhibit
needs no reconstruction.

**Attack 3 — "prompt engineering; wordings idiosyncratic; obsolete at the frontier."**
→ taxonomy derived ex ante from published theory (H1–H3 in §3); menu-null is a built-in placebo;
half the taxonomy backfires (cherry-pickers don't publish failures — and backfiring is the
theoretically predicted signature); 4 families × 2 domains × multiple variants + paraphrase check;
frontier obsolescence measured (gpt-5-mini), not denied — deployed fleets occupy the
bounded-rationality regime for cost reasons.

---

## 9. Execution milestones

- **M0 Gates + hygiene (days 1–2).** Resolve G1–G4. Branch `merge/simplicity-paper`. Git-recover
  data (E5). Track `Engineering_simplicity/` in git. Bib merge. Rewrite `data_map.md`. Beware:
  `writeup/drafts/papers/engineering_complexity.tex` is a third, older draft of the ES paper living
  inside `writeup/` — freeze it with the other sources and never copy text from it (stale
  taxonomy labels).
- **M1 Skeleton (day 2).** `paper/` tree per §3; move text unedited first (compile checkpoint);
  label sweep (`session:`→`sec:`; fix dangling `\ref{sec:Intervention}` at methods.tex:169; dedupe
  ×12 `fig:sealbid_prompt`).
- **M2 Experiments (weeks 1–3, parallel).** E1 (critical path) → E8 → E2 → E4 → E3 → E7; nice-to-
  haves as budget allows. All runs on T1 calibration, K pinned; freeze one master results CSV
  (`results/merged_ranking/master.csv`) that every figure reads.
- **M3 Analysis (week 3).** E6 + E9; SMAD recomputation of all ES cells; ρ-index incl. human
  anchors from `results/v12_interventions/moment_matching/`.
- **M4 Figures (week 4).** `scripts/plots/ranking_forest.py` (F1, the money figure); validity-map
  table; re-plots of figure1/figure2/OSP comparison; regenerate the 5 missing PNGs; consolidate ES
  figs 2–4 into one scaffold grid. (Note: **no generating scripts exist for the 9 ES PDFs** —
  recreate them in-repo.)
- **M5 Writing (weeks 3–5, overlapping).** Intro per §2 → §3 framework → §6 ranking → §5
  validation compression → §7/§8 → appendices → abstract last. Draft with `\TODO{recompute}` flags
  where M2 numbers are pending.
- **M6 Claim audit + release (week 5).** Every number traceable to `master.csv`; tier-concordance
  wording matched to what the data actually show; typo sweep (gaTme, todays', widelyused,
  "2025-0205", double period at intro.tex:7); both `\ifanon` builds compile; tag release with
  configs+logs for the open-source claim; update stale README.

**Critical path:** G1/E1 (DA) → E7/E6 → F1. Everything else parallelizes.

---

## 10. Mechanical hygiene checklist (all referee-cheap, fix in M0–M1)

- [ ] `contents/discussion.tex` = eBay section, `contents/limitation.tex` = Discussion (swapped names) — never reuse these filenames
- [ ] Dangling `\ref{sec:Intervention}` (methods.tex:169 vs label `session:Intervention`)
- [ ] 5 referenced figure PNGs missing repo-wide (won't compile)
- [ ] `levin1996revenue` cited but in neither bib
- [ ] ×12 duplicate `fig:sealbid_prompt` labels (appendix.tex)
- [ ] "Claude Sonnet 3.5" vs claude-3-5-haiku (appendix.tex:292,301)
- [ ] Temperature-ablation text contradicts its own table (appendix.tex:248–253)
- [ ] "10 independent rounds" vs T=1 single-shot (appendix.tex:191)
- [ ] "$1 increments" in clock prompt vs $0.5 configs (appendix.tex:456)
- [ ] ES "$0.01 increment" vs $0.1 configs (ES main.tex:228)
- [ ] Significance stars vs reconstructed humans (appendix.tex:324–326)
- [ ] Two `\title` blocks + duplicated preamble in writeup/main.tex
- [ ] `\Comments=1` leaves red khz blocks in the compiled PDF
- [ ] Typos: "gaTme" (ES 267), "todays'" (ES 423), "widelyused", "2025-0205", double period (intro.tex:7)

---

## 11. Open questions for co-authors

1. G1: where does the DA pipeline live, and who owns importing it?
2. G2: what is EC'26 #2577's status?
3. Approve the demotion of "LLM-as-human-proxy" from thesis to validation layer + prediction engine?
4. Approve eBay compression (sniping = exhibit; hidden reserve = appendix with Myerson re-run)?
5. Model-set change: Gemma in, Llama to appendix — anyone attached to Llama?
6. API budget for E1–E8 (ballpark: the V12-scale grids ran at ~$400 total; the new program is of the
   same order, plus Gemma hosting).
7. TPSB/FPSB intervention batteries: confirm the default scope decision in §6 (fidelity datapoint
   only; intervention batteries parked) — this touches the recent third-price work (commit
   `0f2e202f`).

---

## 12. Decision record (how this plan was chosen)

Three architectures were drafted independently and judged by three lenses (econ-referee /
feasibility / narrative-unity):
- **A "three-act" (validate → diagnose → design):** scores 77–83. Best transition logic (the OSP-
  decomposition bridge — grafted into §6), best hygiene checklist (grafted into §10), preserves the
  most co-author material; but relocates the two-paper seam rather than removing it, and its
  headline only crystallizes in §6.5.
- **B "ranking-centric" (chosen):** scores 82/87/86 — unanimous winner. One question owns every
  section; thesis = the user directive nearly verbatim; ranking invariant to cross-model level
  disputes; menu-null as built-in placebo. Known hostages (mitigated above): don't pre-assert 8/8
  concordance; don't cut eBay entirely; don't brand as ES v2.
- **C "synthetic-lab instrument":** scores 65–70. Institutionalized stapling ("Study 1/Study 2") and
  recenters the proxy thesis; but contributed the validity map, the ρ-index figure semantics, the
  reconstruction-uncertainty bootstrap, and the practitioner box — all grafted in.

Full design documents and judge reports archived in the session scratchpad
(`merge-plan/*.md`, workflow run `wf_d7c8f5c3-f11`).

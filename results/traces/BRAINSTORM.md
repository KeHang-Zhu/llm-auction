# Deeper trace-analysis options — ranked brainstorm for co-authors

Context: the baseline keyword analysis (`traces_summary.md`) already delivers (a) prevalence fingerprints, (b) stated-intent → realized-bid consistency (97%/88%), (c) a behavior-vs-verbalization double dissociation around Payoff Safety and the worst-case scaffold, and (d) GPT-4o's mechanism-insensitive shading script. The options below are ranked by referee-value per unit of effort. Estimated costs assume the existing `trace_features.csv` (21,990 traces with aligned bids/values/conditions).

---

## 1. LLM-judge strategy taxonomy (highest value / moderate cost) — RECOMMENDED
**What:** classify every trace into a small closed taxonomy with a judge model, e.g. {truthful-dominance, epsilon-shading-for-margin, expected-value shading, opponent-anchored guess, midpoint/heuristic, overbid-to-win, mechanism-confused (first-price logic), other}, plus a binary "does the trace state *why* truthful bidding is safe?". Keyword features validate the judge; the judge fixes keyword blind spots (negation, paraphrase, the 4,541 "no stated intent" traces where the big errors live).
**Shows:** clean strategy-share shifts under each lever; whether Payoff Safety moves traces from "shading-for-margin" to "epsilon-shading" without ever creating "dominance-recognized" traces (sharpens Finding 4 into a taxonomy statement); per-model strategy portfolios.
**Needs:** API access (~22k short classifications; one cheap model pass ≈ tens of dollars; sample 5k stratified if budget-bound), a 100-trace human-labeled validation set (2–3 author-hours) to report judge–human agreement — referees will ask.
**Effort:** ~2–3 days incl. validation. **Referee value: high** — turns "we did regexes" into a defensible measurement instrument; this is what the "do something with the traces" comment usually wants.

## 2. Formal mediation / process analysis of the double dissociation (high value / low cost)
**What:** promote the mediation sketch to a proper analysis: (i) manipulation-check table for every lever (does lever X raise its target language?), (ii) causal-mediation bounds (Imai-style sensitivity, or simply report first-stage ≈ 0 ⇒ verbalized understanding cannot mediate B2's effect), (iii) the 2×2 "moves language / moves bids" matrix over all levers (worst-case: language-only; Payoff Safety: bids-only; Payoff Tree: both; menu: neither — a built-in placebo row).
**Shows:** interventions act *without passing through stated comprehension*; the strongest and most novel trace claim we can make with zero new data.
**Needs:** nothing beyond `trace_features.csv`; optionally judge labels from option 1 as a second mediator measurement.
**Effort:** 1–2 days. **Referee value: high** — converts a descriptive subsection into an identified (or explicitly bounded) claim, and pre-empts "traces are cheap talk" objections with the 97%/88% consistency stats.

## 3. Cross-mechanism reasoning-script invariance, all models (medium-high value / low-moderate cost)
**What:** extend Finding 5 (GPT-4o's identical shading script across SPSB/FPSB/TPSB) to Claude/Gemini/Gemma. FPSB/TPSB traces for the other models may exist in recovered logs or need small runs (~50 auctions × 2 formats × 3 models). Then quantify: within-model trace similarity across mechanisms (feature-vector or embedding distance) vs across-model similarity within a mechanism.
**Shows:** "models have a house style that swamps the mechanism" — a memorable, quotable result tying traces to the paper's comprehension thesis; FPSB also gives the one cell where shading language is *correct*, sharpening interpretation everywhere else.
**Needs:** existing V12 for GPT-4o; either recovered logs or ~$20 of API runs for the rest.
**Effort:** 1–2 days if logs exist; +1 day if new runs. **Referee value: medium-high**.

## 4. Stated-vs-revealed consistency as a per-model metric (medium value / low cost)
**What:** formalize Finding 2 into a scalar per model×lever: P(realized deviation direction matches stated intent), plus a calibration curve (stated shade size, parsed from "$X" mentions in the plan, vs realized shade). We already see models differ (GPT-4o overbid-intent traces only 61% actually overbid vs Claude 98%).
**Shows:** whether traces are faithful *plans* or post-hoc rationalizations, per model — feeds the interpretability/faithfulness literature and justifies (or kills) any use of traces as diagnostics.
**Needs:** nothing; a $-amount parser on the plan text (regex) for the calibration curve.
**Effort:** ~1 day. **Referee value: medium** — strong as a paragraph + one figure, not a subsection on its own.

## 5. Trace-based early-warning classifier for large errors (medium value / medium cost)
**What:** predict |deviation| > $5 from trace features alone (logistic/GBM, grouped CV by run). Baseline dictionary AUC first; embeddings (option 6) as an upper bound. Deployment story: "an auctioneer/platform could flag likely-erroneous agent bids from their stated plans before execution."
**Shows:** practical utility of traces; the honest headline may be that unanchored, vague plans are the best single red flag (mean |dev| 5.5 vs 1.8–2.0).
**Needs:** sklearn (already available); embeddings optional.
**Effort:** 1–2 days. **Referee value: medium** — nice applied hook for an economics+AI audience, but reviewers may see it as bolt-on unless tied to the market-design framing.

## 6. Embedding clustering / reasoning-style fingerprints (lower value / low-moderate cost)
**What:** embed all traces (any sentence-transformer or API embedder), cluster (HDBSCAN/k-means), map clusters to models, levers, and error rates; visualize with UMAP colored by model and by |deviation|.
**Shows:** unsupervised confirmation of the fingerprints and of script invariance (options 3/4 without hand-built features); pretty figure.
**Needs:** local sentence-transformers (no API) or embedding API; ~22k short texts is trivial compute.
**Effort:** ~1 day. **Referee value: low-medium** — descriptive; referees rarely credit clustering unless it feeds a downstream test. Best used as a robustness appendix for options 1/3 rather than standalone.

---

### Suggested bundle
Given one writing cycle: **do 2 (free, identified claim) + 1 (measurement instrument)**, fold 4 in as a paragraph inside 2, and keep 3 as the first new-data extension (it reuses the fixed dictionary, so it is pre-registered in spirit). Options 5–6 only if a demo/figure is wanted for talks.

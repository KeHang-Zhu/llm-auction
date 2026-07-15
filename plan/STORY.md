# STORY.md — the one story for the revision (2026-07-15)

Product of a structured brainstorm (Anand + Claude + Codex/gpt-5.4 adversarial rounds; full
transcripts: scratchpad story_brief.md / codex_round1.md / codex_round2.md, archived in this
commit under plan/story_debate/). Supersedes the "three stories" diagnosis in Kehang's review;
incorporates the review's structural moves and the PI's constraints (keep winner's curse, add +X,
frontier prominent, drop DA/eBay from main text, no "calibrated", no personas).

## The story (one sentence)

**Successful auction implementation is a joint property of the mechanism, its representation, and
the reasoner: using Li's simplicity decomposition to build an ordinally human-validated LLM
stress test, we find that one honest sentence explaining why truthful bidding is safe captures
roughly half the benefit of a full clock redesign while restating mechanics or prompting
deliberation can backfire — and that frontier models require transfer tests, because exactly
truthful baseline play can conceal brittle playbook retrieval.**

Product noun: a **theory-guided ordinal stress test** (not "screening tool" — bloodless; not
"design map" — overclaims interactions we haven't run).

## Why this framing (what died in the debate)

- "Recognition, not computation" (the S3 spine) died: recognition has no measurement independent
  of the bids it is invoked to explain, and the trace dissociation + false-invariant pilot mean
  the true safety sentence may act through the same salience/credulity channel as a lie. Calling
  one "recognition supplied" and the other "recognition corrupted" is unfalsifiable.
- Its replacement, **behavioral implementation robustness**, is observable: bid behavior relative
  to prescribed play, under theory-guided perturbations of structure, wording, and prompts.
- The dissociation result stops being a curiosity and becomes the METHOD's justification: you
  cannot certify an implementation by quizzing comprehension (stated reasoning doesn't move when
  bids do, and vice versa) — so robustness must be audited behaviorally, under perturbation.
  This is the stitch that fuses the two halves: the ranking is the constructive use of the stress
  test; the frontier/transfer results are its destructive necessity.
- The frontier is the culmination, not a footnote: baseline truthfulness is not robustness
  (menu collapse; affiliation-sentence winner's-curse misfire; IPV rerun restores play).

## Where the theory lives (this stays an economics paper)

1. The perturbation dimensions ARE Li's decomposition (OSP structure; contingent reasoning;
   forward planning; belief formation) — the stress test's coordinate system, not prompt space.
2. Every lever maps ex ante to the burden it removes/preserves/adds; ~half the taxonomy was
   predicted to backfire, and did (H1–H3 survive as the ex-ante prediction table).
3. Claim language: **"theory-generated comparative statics show ordinal portability across the
   studied human settings and incumbent LLM families, despite opposite baseline errors."**
   NEVER "substrate independence" (implies shared mechanism), never "calibrated".
4. The frontier is the measured boundary of that portability (incumbent under-computation vs
   frontier mis-retrieval).

## Abstract emphasis order

problem → tool (one sentence, quickly) → **invariance-content headline** (one honest sentence ≈
half of OSP; mechanics restatement null-to-harmful; "design regularity" in cautious passages) →
theory-parallel ranking + human-anchor agreement → trace dissociation (behavior must be audited)
→ frontier transfer failure (closing result) → cost/adoption (~$10/cell vs $2K–15K) LAST.

Draft opening (Codex, amended — cost moved out of sentence 2):
"An auction can make truthful bidding the best choice and still fail when participants face
unfamiliar wording, extra instructions, or prompts that invite unnecessary strategizing. We use
the theory of simple mechanisms to build a stress test for this problem, administered to a panel
of LLM bidding agents that reproduces known human rankings of auction difficulty without claiming
to reproduce human bid levels. Across four model families, one honest sentence explaining why
truthful bidding is safe delivers roughly half the improvement of redesigning the auction as an
ascending clock, whereas merely restating the rules does nothing on average and can make behavior
worse."

## Seven-section skeleton

1. **Introduction** — from correct incentives to robust implementation; invariance-content result
   led; contributions (theory-guided test, ranking, dissociation, frontier boundary, cost).
   Related work diffused into intro (MS convention).
2. **Theory and ex-ante predictions** — Li decomposition → lever taxonomy → complete directional
   predictions incl. backfires; the ex-ante prediction table with human-evidence status column
   (direct anchor / nearby / prediction / N-A).
3. **A theory-guided ordinal stress test** — panel, metrics, frozen robustness score; ordinal
   validation (difficulty ordering; winner's-curse comparative statics as a validation row;
   opposite-signed baseline errors make agreement informative); cardinal matching explicitly out
   of scope (95-cell grid → appendix).
4. **What improves implementation** — the incumbent hierarchy (structure > safety text > tree >
   clock-framing(sign-mixed) > baseline ≈ menu > beliefs/lookahead > persona); the
   invariance-content regularity; each rung vs its human anchor.
5. **Why explanations cannot certify implementation** — trace–behavior dissociation (two-panel
   flow chart per Kehang's review); methodological implication.
6. **Transfer tests and the frontier regime** — baseline ceilings; menu collapse (first-price
   formula retrieval); affiliation/IPV reversal; **preregistered 2P+X / AC+X outcomes** (Li
   human anchors: 2P+X 3.99 vs AC+X 1.83); incumbent under-computation vs frontier mis-retrieval.
   [Gullibility pilot: exploratory paragraph only if co-authors ratify texts; else future work.]
7. **Design workflow, boundaries, implications** — adoption protocol (define population → map
   burdens → perturb → inspect worst-case → escalate to human testing); predictions ledger;
   preregistered human safety-text experiment as the standing prospective prediction.

Appendix policy: cardinal grid; one-page DA external-robustness appendix ONLY for the
menu-content split (invariance-carrying menu helps, mechanics-only backfires — Guillén–Hakimov
anchor); full prompts/prediction files/score construction. eBay and third-price REMOVED
(third-price replaced by +X).

## Minimal gap list (ranked; feasibility judged)

1. **Freeze the theory→treatment prediction table** (≈1 day; mostly exists as H1–H3 + Table 1 —
   add predicted-sign and human-evidence-status columns; commit before new results).
2. **Preregister and run +X** (~days + ≈$15 API): commit a prediction file BEFORE running —
   per family: sign of deviation in 2P+X and AC+X, sign of the gap G_m = E[d|2P+X] − E[d|AC+X],
   unadjusted-vs-prescribed criteria, hit/miss/inconclusive rules, frozen robustness score;
   then run 2P+X/AC+X on the servable panel; publish the ledger. NOTE (design fact): in 2P+X
   truthful bidding is STILL dominant — the stress is the unfamiliar win/payment rule
   (win iff bid > 2nd + X; pay 2nd + X). Retrieval prediction: sonnet-5's deviation reappears
   under the novel wording (menu precedent) while gpt-5/gpt-5-mini stay clean; incumbents show
   the Li-style 2P+X > AC+X gap. AC+X needs a small simulator change (price continues X past
   last dropout; winner must keep bidding).
3. **Preregister the human safety-text experiment** (protocol appendix now; running it is
   program-level — IRB, subjects, months — and should NOT gate submission. Strategic option:
   partner with Shengwu Li or the Gonczarowski–Heffetz group, who run exactly these designs).
NOT minimal: combined-lever grid (only if we claim substitutes/complements — we won't);
lie-on-clock (only if we claim structure protects against manipulation); gullibility
confirmatory battery (exploratory or future work until texts ratified).

## Venue

Management Science first (the MS arc above; tool + actionable regularity + theory architecture);
GEB fallback with emphasis inverted (theory test first); TEAC third. Title candidate:
"Behavioral Implementation Robustness in Auctions: A Theory-Guided LLM Stress Test" —
alternates: "Beyond Strategy-Proofness: Stress-Testing Auction Designs with LLM Agents";
"Truthful by Design, Brittle in Use".

# STORY.md — the one story for the revision (2026-07-15)

Product of a structured brainstorm (Anand + Claude + Codex/gpt-5.4 adversarial rounds; full
transcripts: scratchpad story_brief.md / codex_round1.md / codex_round2.md, archived in this
commit under plan/story_debate/). Supersedes the "three stories" diagnosis in Kehang's review;
incorporates the review's structural moves and the PI's constraints (keep winner's curse, add +X,
frontier prominent, drop DA/eBay from main text, no "calibrated", no personas).

## The story (one sentence)

**Successful auction implementation is an *irreducibly* joint property of the mechanism, its
representation, and the reasoner — you cannot predict implementation success from mechanism plus
representation alone; the reasoner's cognition flips the sign. Using Li's simplicity decomposition
as a coordinate system for cognitive burden, we build an ordinally human-validated LLM stress test
and show: one honest sentence explaining why truthful bidding is safe captures roughly half the
benefit of a full clock redesign while restating mechanics or prompting deliberation can backfire;
the same lever's sign depends on the reasoner (interaction cells prove the jointness is not
additive); and the failure mode is *capability-indexed* — weaker agents under-compute, frontier
agents retrieve the wrong memorized playbook and execute it flawlessly, so exactly truthful
baseline play certifies nothing.**

Product noun: a **theory-guided ordinal stress test** that yields an *interaction-aware design
map* — not a bloodless "screening tool," and no longer merely a ranked list of main effects.
The interactions are load-bearing: they are what makes the jointness thesis *necessary* rather
than a truism ("outcomes depend on everything"). See "The jointness must be irreducible" below.

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

## The jointness must be irreducible (SCOPE CHANGE — Kehang to bless)

STATUS: proposed reversal of this doc's earlier "we won't claim interactions; a design map
overclaims." Anand supports it; final call is Kehang's. Recorded here so the decision is explicit
and reviewable, not silently flipped.

The argument: the one-sentence thesis says implementation is a *joint* property of mechanism,
representation, and reasoner. Stated with **main effects only**, that is a truism — "outcomes
depend on everything." It becomes a real, necessary claim only if the jointness is *irreducible*:
a case where mechanism + representation predict one sign and the reasoner flips it, i.e. a genuine
interaction that additive main effects cannot reproduce. Main-effect rankings (current B) cannot
earn the headline sentence; an interaction result can.

We already have ONE such interaction, unlabeled: the affiliation sentence helps nothing on
incumbents but triggers sonnet-5's winner's-curse script on the clock (removed by IPV wording) —
representation × reasoner, sign-flipping. The proposal is to make interactions a first-class,
pre-registered object rather than an anecdote:

- **lie × structure** (lie-on-clock): does OSP extensive form neutralize manipulative content that
  wrecks the sealed-bid format? content × structure. This is the keystone cell — it is the
  cleanest "mechanism+representation say X, reasoner-facing content flips it" demonstration, and
  it converts the gullibility pilot from an exploratory footnote into the paper's structural
  punchline.
- **safety-text × payoff-tree** and **safety-text × clock-framing**: are the top two message
  levers substitutes (redundant, sub-additive) or complements? This is the design-map content —
  it tells a designer whether to stack levers or pick one. Predicted sub-additive (both supply
  the same invariance content), which is itself a testable, non-obvious claim.
- **lever × reasoner (capability tier)**: the same lever's sign across incumbent vs frontier is
  itself the irreducible-jointness evidence at the population level (positive levers help
  incumbents, do nothing for truthful frontier baselines, and menu-content HURTS frontier). This
  we already have — it needs to be *named* as an interaction, not re-run.

Caveat we must not overclaim: interactions license "these two levers are substitutes/complements
in the studied cells," NOT a complete optimal-bundle map over the full lever cross-product. The
combined-lever grid stays bounded to the theoretically motivated pairs above; we do not run the
full cross-product and we say so.

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

TWO defensible orderings — Kehang picks. Both now lead the *necessity/urgency* (strategy-proofness
becomes empirical for AI agents; failure is capability-indexed) before the design rules, because
"one sentence ≈ half a clock" is a citable engineering fact but not, by itself, why the paper is
necessary.

- **Order A (necessity-first, recommended for the AI-agents urgency):** problem (strategy-proof ≠
  truthful play once you don't control the reasoner; AI agents entering real mechanisms make this
  empirical, now) → **capability-indexed failure headline** (weaker agents under-compute; frontier
  agents retrieve the wrong memorized playbook and execute it flawlessly, so baseline truthfulness
  certifies nothing) → tool (Li's decomposition as the coordinate system for a cheap
  theory-structured stress test whose failures are diagnostic) → constructive payoff (one honest
  sentence ≈ half a clock; mechanics restatement null-to-harmful; interaction cells show the sign
  is reasoner-dependent) → ordinal human-anchor validation → trace dissociation → cost LAST.
- **Order B (invariance-content-first, the prior plan):** problem → tool → invariance-content
  headline → ranking + human anchors → dissociation → frontier transfer failure (closing) → cost.

Draft opening — Order A (elevate the two clauses that make it necessary/urgent/exciting):
"An auction can make truthful bidding a dominant strategy and still fail when the bidder is a
reasoner whose cognition the designer does not control — and AI agents are now entering real
mechanisms, making 'will strategy-proofness translate into truthful play' an empirical question
rather than a theorem. We show it fails, and fails differently at every capability tier: weaker
models under-compute the dominant strategy, while frontier models retrieve a memorized auction
solution and execute the WRONG one flawlessly when surface wording cues it — so exactly truthful
baseline play certifies nothing. Using the theory of simple mechanisms as a coordinate system for
cognitive burden, we build a cheap, theory-structured stress test whose failures are diagnostic:
it recovers the human ordering of auction difficulty, shows one honest sentence explaining why
truthful bidding is safe buys roughly half the benefit of redesigning the auction as an ascending
clock while merely restating the rules does nothing on average and can backfire, and — through
interaction cells — that the same lever's sign depends on the reasoner it faces."

Draft opening — Order B (Codex, amended, retained as fallback):
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
4. **What improves implementation (main effects)** — the incumbent hierarchy (structure > safety
   text > tree > clock-framing(sign-mixed) > baseline ≈ menu > beliefs/lookahead > persona); the
   invariance-content regularity; each rung vs its human anchor.
5. **The jointness is irreducible (interactions)** — NEW section, contingent on Kehang blessing
   interaction scope. lie × structure (lie-on-clock keystone: does OSP neutralize manipulative
   content?); safety-text × tree and safety-text × clock-framing (substitutes vs complements);
   lever × capability-tier (the same lever's sign flips incumbent→frontier). This is the section
   that earns the "joint property" thesis; without it the thesis is a truism. Pre-registered signs
   + a formal test that additive main effects cannot reproduce the observed cell.
6. **Why explanations cannot certify implementation** — trace–behavior dissociation (two-panel
   flow chart per Kehang's review); methodological implication.
7. **Transfer tests and the capability-indexed frontier regime** — baseline ceilings; menu
   collapse (first-price formula retrieval); affiliation/IPV reversal; **preregistered 2P+X / AC+X
   and +n-in-SPSB outcomes** (Li human anchors: 2P+X 3.99 vs AC+X 1.83; +n tests whether deviation
   grows with the number of pivotal states = a contingent-reasoning dose); incumbent
   under-computation vs frontier mis-retrieval, framed as *training-to-benchmark overfit* (frontier
   memorizes auction solutions; surface cues select which one runs).
   [Gullibility pilot: exploratory paragraph only if co-authors ratify texts; else future work.]
8. **Design workflow, boundaries, implications** — adoption protocol (define population → map
   burdens → perturb → inspect worst-case AND worst-case interaction → escalate to human testing);
   predictions ledger; preregistered human safety-text experiment as the standing prospective
   prediction.

(Skeleton grew from 7 to 8 sections with the interaction section; if Kehang keeps interactions as
a subsection of §4 rather than standalone, revert to 7.)

Appendix policy: cardinal grid; one-page DA external-robustness appendix ONLY for the
menu-content split (invariance-carrying menu helps, mechanics-only backfires — Guillén–Hakimov
anchor); full prompts/prediction files/score construction. eBay and third-price REMOVED
(third-price replaced by +X).

## Minimal gap list (ranked; feasibility judged)

1. **Freeze the theory→treatment prediction table** (≈1 day; mostly exists as H1–H3 + Table 1 —
   add predicted-sign and human-evidence-status columns; commit before new results).
2. **Preregister and run +X and +n** (~days + ≈$25 API): commit ONE prediction file for the whole
   transfer battery BEFORE running — per family: sign of deviation in 2P+X and AC+X, sign of the
   gap G_m = E[d|2P+X] − E[d|AC+X], and for +n the sign of ∂deviation/∂n in SPSB (does error grow
   with the number of pivotal states = a contingent-reasoning dose?); unadjusted-vs-prescribed
   criteria, hit/miss/inconclusive rules, frozen robustness score; then run on the servable panel;
   publish the ledger. NOTE (design fact): in 2P+X truthful bidding is STILL dominant — the stress
   is the unfamiliar win/payment rule (win iff bid > 2nd + X; pay 2nd + X). Retrieval prediction:
   sonnet-5's deviation reappears under the novel wording (menu precedent) while gpt-5/gpt-5-mini
   stay clean; incumbents show the Li-style 2P+X > AC+X gap. +X and +n double-dissociate
   recall-failure (+X: true strategy hidden behind unfamiliar wording) from computation-failure
   (+n: strategy unchanged, contingent-reasoning load scaled). AC+X needs a small simulator change
   (price continues X past last dropout; winner must keep bidding).
3. **Preregister and run the interaction cells** (SCOPE CHANGE, Kehang to bless; ~days + ≈$15 API):
   lie × structure (lie-on-clock keystone), safety-text × tree, safety-text × clock-framing. These
   are what make the "joint property" thesis necessary rather than a truism (see "The jointness
   must be irreducible"). Pre-register: predicted sign of each cell, and the formal test that
   additive main effects (fitted on the single-lever cells) cannot reproduce the observed cell.
   Bounded to the theoretically-motivated pairs — NOT the full lever cross-product; we say so.
   Gate: lie × structure needs the false-invariant texts co-author-ratified first.
4. **Preregister the human safety-text experiment** (protocol appendix now; running it is
   program-level — IRB, subjects, months — and should NOT gate submission. Strategic option:
   partner with Shengwu Li or the Gonczarowski–Heffetz group, who run exactly these designs).
NOT minimal: FULL combined-lever cross-product (we run only the theory-motivated pairs above);
gullibility confirmatory battery (exploratory or future work until texts ratified).

## Venue

Management Science first (the MS arc above; tool + actionable regularity + theory architecture);
GEB fallback with emphasis inverted (theory test first); TEAC third. Title candidate:
"Behavioral Implementation Robustness in Auctions: A Theory-Guided LLM Stress Test" —
alternates: "Beyond Strategy-Proofness: Stress-Testing Auction Designs with LLM Agents";
"Truthful by Design, Brittle in Use".

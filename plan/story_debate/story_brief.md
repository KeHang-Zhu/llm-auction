# Story brainstorm brief — auction-v2 paper reframe

## The problem
The current 116pp draft (repo: /Users/avshah/P_llm_auctions/llm-auction, writeup/contents_v2/*.tex)
is schizophrenic — it tells three stories at once: (1) how to design mechanisms for LLM
participants; (2) whether LLMs can simulate human bidders; (3) whether simplicity theory (Li 2017
OSP; Li 2024 cognitive decomposition) governs all bounded reasoners. Coauthor review (Kehang) says
pick ONE: "LLM panel as an ordinal design-screening tool." Senior coauthor (Parkes): drop
"calibrated" language, no personas, weaken proxy claims; venue Management Science-ish (or GEB/TEAC).
PI decisions already made: KEEP winner's-curse validation; ADD Li's +X auctions (2P+X / AC+X);
keep frontier results prominent (do NOT bury); DROP deferred-acceptance domain and eBay from the
paper.

## The assets the story must house (all established, seed-1299 reproducible)
A. Ordinal validation: LLM bidders reproduce the human difficulty ordering (FPSB SMAD ≫ SPSB:
   27.6 vs 8.7 LLM, 24.8 vs 5.6 human) and winner's-curse comparative statics (winner losses grow
   with n, attenuate under 2nd-price) — while making OPPOSITE-signed baseline errors (humans
   overbid SPSB 67-92%, LLMs underbid 74-92%). Same levers repair opposite errors.
B. The lever ranking (4 incumbent model families, K=50/cell): OSP clock (rho≈.97) > safety-invariant
   text (+.78) > payoff-tree scaffold (+.59) > clock-framing (+.30, sign-mixed: helps 3, hurts
   Gemini) > baseline ≈ menu restatement (null-avg, sign-mixed) > belief/lookahead scaffolds
   (backfire) > risk-persona (worst). Kendall's W = 0.70 across families (p=.004).
C. Invariance-content law: text that asserts WHY truth-telling is safe helps (≈half of the OSP
   gain from ONE sentence); text that restates mechanics is null-to-harmful. Human anchors agree
   on every observed rung (Li 2017 clock; Breitmoser-SK clock-framing; Gonczarowski menu null;
   Guillén-Hakimov mechanics-backfire; GHIT-2024 Menu-SP nearby-evidence).
D. Traces (22k stated plans): complete dissociation — every lever that moves bids leaves stated
   reasoning unchanged (safety invariant echoed in 0/600 treated traces; mediation through
   verbalized understanding bounded ≤35%), and the lever that moves stated reasoning doesn't move
   bids. Modal stated plan is first-price logic (shade for margin) applied to a second-price rule.
E. Frontier grid (gpt-5-mini, gpt-5, claude-sonnet-5, gemini-2.5-flash): all bid exactly
   truthfully at baseline (nothing for positive levers to do), BUT: a menu restatement collapses
   claude-sonnet-5 to severe underbidding — its traces announce the FIRST-PRICE equilibrium
   formula (2/3·v) and execute it flawlessly, ignoring the stated payment rule; one sentence of
   affiliation language triggers a misapplied winner's-curse script on the clock (removed by
   IPV wording). Frontier failure mode = retrieval selection: surface cues choose which memorized
   playbook runs. Two regimes: incumbents fail by under-computation, frontier by mis-retrieval.
F. Gullibility pilot (unpublished, co-author ratification pending): FALSE invariant sentences
   steer incumbent bids in whichever direction the lie points — including 75-89% OVERBIDDING
   (never observed natively; beats every legitimate tuning knob). Everything needed to falsify
   the lie is in the same prompt, unused. Frontier models immune to the lies (they recite the
   dominant strategy) — immune via retrieval, not verification: the same models ignore TRUE
   rules under unfamiliar wording. Content-credulity (incumbents) vs format-credulity (frontier).
G. Cardinal boundary: no tuning (temperature/personas/framings, 95-cell grid) matches human
   levels/directions across mechanisms; the ordinal claim is the ceiling. (→ appendix per review.)
H. Economics: $10/treatment-cell vs $2K-15K human experiments.
PLANNED (gaps we can fill): Li's 2P+X / AC+X cells (human-anchored; in +X the memorized string
"bid your value" is WRONG, so it cleanly separates recognition/understanding from recall —
frontier prediction: substantial unadjusted-value bidding); combined-lever cells
(substitutes/complements for a true design MAP); lie-on-the-clock cell (does OSP structure
neutralize manipulative text? "gullibility-proofness").

## Candidate stories
S1 (Kehang): "LLM panel as ordinal design-screening tool." Validate ordinally → theory-guided
   design map (anchored cells vs prediction cells) → traces as diagnostics → frontier as scope
   footnote. Weakness: instrumentalizes the most interesting economics; frontier results fit
   awkwardly; "screening" begs for a demonstrated discovery.
S2 "Simplicity is substrate-independent": same hierarchy binds humans and LLMs with opposite
   surface errors ⇒ simplicity is a property of the strategic problem, not the mind. Weakness:
   the frontier regime FRACTURES this (frontier models aren't bound the same way — different
   failure kind), and econ referees ask why LLM cognition is evidence about human theory.
S3 "Recognition, not computation" (What makes truth-telling obvious?): the binding constraint in
   strategy-proof mechanisms is recognizing that truthful play is safe; we measure where
   recognition comes from (structure > honest invariant text > contingency scaffolds), how it is
   corrupted (strategizing prompts, lies), and how it is faked (frontier retrieval — perfect play
   without recognition, unmasked by re-descriptions and +X). LLM panel = the instrument, screening
   = the method payoff. Fusion: S3 spine + S1 payoff.
S4 "Mechanism design as alignment layer for agentic markets": too grand for the venue.

## My current best candidate (fusion S3+S1), one sentence:
"Strategy-proof mechanisms fail when participants don't RECOGNIZE that truth-telling is safe; we
build an ordinally-validated LLM testbed to measure where recognition comes from — finding it can
be supplied by structure or one honest sentence, corrupted by prompts that invite strategizing or
lie about the invariant, and convincingly FAKED by frontier models that retrieve rather than
recognize — yielding both a ranked map of recognition channels (anchored to five decades of human
experiments where anchors exist, falsifiable predictions where they don't) and a $10-per-cell
screening instrument for mechanism designers."

Arc: (1) recognition problem [humans deviate; agents entering markets] → (2) the instrument
[cheap panel; ordinal validation; opposite-errors-same-cures makes agreement informative] → (3)
the recognition hierarchy [ranking + invariance-content law] → (4) recognition acts without
articulation [traces; audit implication] → (5) stress tests: lies + frontier retrieval [+X as the
litmus; obviousness is reasoner-relative → the map must be re-estimated per population → which is
exactly what the cheap instrument is for — closes the loop] → (6) design payoff [map, guidance,
predictions].

## Known gaps for the best story
- +X cells not yet run (templates needed; Li 2017 human numbers to extract).
- Combined-lever cells (map claims interactions; we have main effects only).
- Lie-on-clock cell (structure-protects-recognition punchline) — pilot-stage ethics/framing OK'd?
- Does the recognition story NEED the gullibility material in v1, or is it future work?
- Is "recognition" the right word vs Li's "obviousness"? Terminology risk.
- MS audience: does the spine read as economics or as LLM-evaluation? Title implications.

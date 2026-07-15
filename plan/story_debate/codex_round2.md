# Round 2: From Theory-Guided Perturbations to Behavioral Implementation Robustness

## Push-back 1: Where theory lives

Your proposed repair is right. Theory should not appear merely as an interpretation of the ranking after the benchmark has been run. Li’s framework should determine the experiment before outcomes are observed.

Theory lives in four places in the arc:

1. **The coordinate system.** The perturbations are not arbitrary prompt variations. OSP structure, contingent reasoning, forward planning, belief formation, and mechanics-only restatements define the dimensions along which implementation is stressed.

2. **The treatment taxonomy.** Each lever must be mapped ex ante to the theoretical burden it removes, preserves, or adds. This includes the important negative predictions: prompts that invite belief formation or additional lookahead should worsen implementation even though they appear to provide more “help.”

3. **The directional hypotheses.** The theory predicts an ordinal hierarchy before the model results are introduced. The fact that roughly half the taxonomy was predicted to backfire—and did—is much stronger evidence than discovering ex post that some prompts help and others hurt.

4. **The cross-reasoner finding.** The empirical ordering matches the theoretical simplicity hierarchy, and the available human anchors agree on every observed rung. That is evidence that Li’s comparative statics travel farther across reasoner types than one might have expected.

The thin claim is safe, but I would not call it “substrate independence.” That phrase invites the original staple by suggesting a common cognitive mechanism or a universal property of minds. The defensible claim is:

> Theory-generated comparative statics exhibit ordinal portability across the studied human settings and incumbent LLM families, despite opposite baseline errors.

This says that signs and rankings travel. It does not say that humans and LLMs use the same internal process, that LLMs proxy human bid levels, or that the hierarchy governs every reasoner. The frontier results then become a meaningful boundary: the theory travels across incumbent reasoners but does not eliminate representation-sensitive retrieval failures in frontier systems.

The human-anchor presentation also needs discipline. Because the anchors come from different studies, they should be shown in a single ex ante theory table that distinguishes:

- direct tests from nearby evidence;
- predicted sign from observed sign;
- comparable rungs from suggestive comparisons;
- missing human evidence from contradictory evidence.

The language should be “every rung for which we have an observed human anchor agrees,” not “humans establish the entire joint ranking.”

With this structure, the paper is not theory plus an LLM benchmark. It is an economics paper in which theory designs the stress test, predicts the ranking—including failures—and the LLM panel supplies a cheap new population on which to test the theory’s ordinal reach.

## Push-back 2: Ranking the constructive headlines

### 1. Invariance-content law

This should be the lead empirical headline.

“One honest sentence recovers roughly half the effect of a full OSP redesign” is precise, surprising, inexpensive, and immediately actionable. The contrast with mechanics restatement makes it a design principle rather than another prompt effect:

> Explain why truthful action is safe; do not merely repeat how the mechanism works.

It also has the best bridge between economics and managerial relevance. OSP supplies the structural benchmark, the safety sentence isolates the relevant content, and the Guillén–Hakimov backfire result provides a human anchor for the harmful side of the contrast. I would call it a “design regularity” in the most cautious passages and reserve “invariance-content law” for the framing, since the positive human anchor is presently nearby rather than a direct matched replication.

### 2. Stress-test methodology and cost

This is the enabling contribution and the adoption path, but not the first scientific result. The approximately $10 treatment-cell cost matters because it makes population-specific robustness testing feasible. Ordinal validation and the explicit cardinal boundary make the tool credible.

The abstract should establish the tool quickly, then spend more emphasis on what it discovers. Cost alone cannot carry the paper.

### 3. Frontier retrieval regimes

This is the culmination and scope result, not the opening headline. It demonstrates why baseline success and fluent explanations cannot certify implementation robustness. It is intellectually striking, but currently narrower and less directly actionable than the invariance-content finding.

The abstract order should therefore be:

1. implementation problem and theory-guided stress test;
2. invariance-content headline;
3. broader theory-parallel ranking;
4. trace dissociation;
5. frontier transfer failure as the closing result;
6. cost and adoption implication.

## Push-back 3: Prospective +X prediction mechanics

Yes—with one important distinction.

The preregistered +X exercise satisfies the requirement for a genuinely prospective test of **LLM transfer behavior** and of the retrieval interpretation. It does not, by itself, establish that the screen predicts an unknown human result, because Li’s human outcomes are already known. The standing human safety-text experiment is therefore complementary:

- **+X:** prospective model transfer test;
- **safety-text experiment:** prospective test of whether the screen identifies a new human design effect.

Together they make a compelling mini demonstration of screening rather than retrospective concordance.

A credible prediction file should freeze the following.

### 1. Administrative provenance

- Timestamp and immutable public commit, release, or registration.
- Exact paper and code version.
- Acknowledgment that Li’s human results were known when predictions were made.
- Confirmation that no +X model outputs had been inspected.
- Procedure for model-version changes: a changed checkpoint creates a new preregistration, not an amendment to the old prediction.

A mutable repository commit is weaker than an immutable release or external registration. At minimum, publish the commit hash and signed release before running the cells.

### 2. The theoretical benchmark

For every auction and value realization, specify the theoretically prescribed bid \(b^*(v,X)\). Also define:

- the sign convention for deviations;
- the bid scale used for normalization;
- how invalid, bounded, or nonnumeric bids are handled;
- what counts as “unadjusted-value bidding” rather than merely being close by chance.

For example, define signed deviation as

\[
d_{ic}=\frac{b_{ic}-b^*_{ic}}{\text{fixed bid range}_c}.
\]

An unadjusted-value response should require the bid to fall within a frozen tolerance of \(v\) while being outside the tolerance around \(b^*(v,X)\).

### 3. Family-specific predictions

For every named model family, precommit to:

- the predicted sign of deviation in 2P+X;
- the predicted sign of deviation in AC+X;
- the predicted sign of the between-mechanism gap;
- whether unadjusted-value bidding is predicted;
- a minimum substantively meaningful effect or magnitude bin;
- the predicted ordering across incumbent and frontier families.

The gap must be an equation, not prose. For example:

\[
G_m=\mathbb{E}[d\mid 2P+X,m]-\mathbb{E}[d\mid AC+X,m].
\]

Then predict the sign of \(G_m\) for each family.

### 4. Hit, miss, and inconclusive rules

Direction-only predictions are too easy to score after the fact. Freeze a rule such as:

- **Hit:** estimate is on the predicted side and exceeds the prespecified minimum effect.
- **Miss:** estimate is substantively on the opposite side.
- **Inconclusive:** uncertainty overlaps the no-effect region.

Predicted nulls require an equivalence interval; failure to reject zero cannot count as a successful null prediction. Report every family-level result, not only a pooled hit rate.

### 5. Frozen robustness score

A simple interpretable score is preferable. One option is:

\[
e_{ic}=\min\left(1,\frac{|b_{ic}-b^*_{ic}|}{\text{fixed bid range}_c}\right),
\qquad
Q_{mc}=1-\mathbb{E}[e_{ic}],
\]

followed by a worst-case robustness score across the preregistered perturbations:

\[
R_m=\min_{c\in\mathcal{C}} Q_{mc}.
\]

This measures implementation relative to the prescribed action, not resemblance to human bid levels. Report the signed deviations alongside the composite so that overbidding and underbidding cannot cancel or disappear inside one score.

Freeze:

- the perturbation set \(\mathcal{C}\);
- aggregation across trials and families;
- model weights;
- treatment of missing cells;
- clipping and normalization;
- tie-breaking;
- whether the primary endpoint is worst-case, average, or both.

### 6. Execution and analysis protocol

- Exact model identifiers and access dates.
- System and user prompts.
- Decoding settings, seeds, sample size, and repetitions.
- Value draws and randomization.
- Parsing and exclusion rules.
- Primary and secondary outcomes.
- Confidence intervals, equivalence margins, and multiplicity treatment.
- Which analyses are confirmatory and which are exploratory.

The paper should then publish a literal prediction ledger: prediction, outcome, hit/miss/inconclusive, and interpretation. Misses are scientifically valuable; quietly revising the retrieval account after seeing them would defeat the exercise.

## Push-back 4: Product noun, venue, and abstract opening

The best product noun is **theory-guided ordinal stress test**.

“Stress test” conveys perturbation, brittleness, worst-case behavior, and an adoption workflow. “Ordinal” states the validation ceiling. “Theory-guided” prevents it from sounding like generic prompt benchmarking.

“Ordinal screening tool” is accurate as a functional description, but too bloodless for the main noun. “Design map” overclaims until interactions or bundles are tested; the current evidence supports a ranked menu of levers, not a complete map of substitutes and complements.

The best venue for this asset bundle is **Management Science**. The main payoff is a low-cost design procedure plus the actionable invariance-content finding. Li’s theory supplies the economic architecture and falsifiable predictions. GEB would require theory and cross-reasoner comparative statics to dominate, with cost and adoption demoted; it would also expose the heterogeneous human anchors and frontier boundary to more pressure as a theory test.

The venue choice changes emphasis, not the underlying evidence:

- **MS arc:** implementation problem → theory-guided test → ordinal validation → invariance-content result → behavioral audit → frontier transfer → adoption.
- **GEB arc:** Li decomposition → hypotheses → human/LLM comparative statics → scope conditions → implications for simplicity theory.

The first is the stronger paper here.

### Revised first three abstract sentences

An auction can make truthful bidding the best choice and still fail when participants face unfamiliar wording, extra instructions, or prompts that invite unnecessary strategizing. We develop an approximately $10-per-treatment-cell, theory-guided LLM stress test that recovers known human rankings of auction difficulty without claiming to reproduce human bid levels. Across four model families, one honest sentence explaining why truthful bidding is safe delivers roughly half the improvement of a full clock redesign, whereas merely restating the rules does nothing on average and can make behavior worse.

# Final synthesis

## A. One-sentence story

Successful auction implementation is a joint property of the mechanism, its representation, and the reasoner: using Li’s simplicity decomposition to construct an ordinally human-validated LLM stress test, we find that one honest safety sentence captures roughly half the benefit of an OSP redesign while mechanics and deliberation prompts can backfire, and that frontier models require transfer tests because correct baseline bids can conceal brittle playbook retrieval.

## B. Seven-section paper skeleton

1. **Introduction — From correct incentives to robust implementation.** Motivate representation-sensitive failure, lead with the invariance-content result, and state the theory, method, frontier, and cost contributions.

2. **Economic theory and ex ante predictions.** Use OSP, contingent reasoning, forward planning, and belief formation to generate the lever taxonomy and its complete directional ordering, including predicted backfires.

3. **A theory-guided ordinal stress test.** Describe the panel and score, validate it against the human auction-difficulty ordering and winner’s-curse comparative statics as one validation row, and state explicitly that cardinal human matching is outside scope.

4. **What improves implementation: the invariance-content law.** Report the incumbent hierarchy, quantify the one-sentence effect relative to OSP, contrast invariant content with mechanics restatement, and align each observed rung with its human anchor.

5. **Why explanations cannot certify implementation.** Present the trace–behavior dissociation and derive the methodological implication that robustness must be audited through controlled behavioral perturbations.

6. **Transfer tests and the frontier regime.** Give frontier results a full main-text section: baseline ceilings, menu collapse, affiliation/IPV reversal, preregistered 2P+X/AC+X outcomes, and the distinction between incumbent under-computation and frontier mis-retrieval.

7. **Design workflow, boundaries, and implications.** Provide the adoption protocol—define the population, map theory burdens, run perturbations, inspect worst-case degradation, and escalate promising designs to human testing—while limiting claims to ordinal screening.

Appendix policy:

- Put the 95-cell cardinal boundary in the appendix.
- Permit a one-page DA appendix only as external robustness for the menu-content split.
- Remove eBay.
- Include full prompts, prediction files, score construction, model specifications, and secondary analyses in the technical appendix.

## C. Definitive minimal gap list

### 1. Freeze the theory-to-treatment prediction table

Before adding new results, commit the complete mapping from each lever to Li’s theoretical dimension, predicted direction, and human evidence status.

**What it buys:** It turns the benchmark into an ex ante economics test, makes the backfire successes falsifiable, and prevents the hierarchy from looking post hoc.

### 2. Preregister and run the +X transfer exercise

Freeze prompts, exact model versions, family-level signs, the 2P+X-versus-AC+X gap, the unadjusted-value criterion, the robustness score, and hit/miss/inconclusive rules before viewing outputs.

**What it buys:** It provides the held-out demonstration the screening claim currently lacks and directly tests whether frontier baseline success reflects transferable rule use or familiar-string retrieval.

### 3. Preregister and run the human safety-text experiment

Test the positive safety-invariant sentence against neutral and mechanics-only text, using the same primary contrast highlighted by the LLM screen.

**What it buys:** It supplies a genuinely prospective human result, tests the positive half of the invariance-content claim directly, and converts the tool from a cheap LLM diagnostic into evidence for prioritizing human design experiments.

The following are not minimal:

- A full combined-lever grid is unnecessary unless the paper uses “design map” or claims optimal bundles, substitution, or complementarity.
- The lie-on-clock crossing is unnecessary unless the paper claims that OSP structure protects against manipulation.
- The gullibility pilot should remain exploratory or be omitted until ratified and confirmatorily replicated; the core story does not need it.

## D. Best title

**Behavioral Implementation Robustness in Auctions: A Theory-Guided LLM Stress Test**
tokens used
20,139
The workspace is read-only, so I could not create `codex_round2.md`. Below is the complete intended contents.

# Round 2: From Theory-Guided Perturbations to Behavioral Implementation Robustness

## Push-back 1: Where theory lives

Your proposed repair is right. Theory should not appear merely as an interpretation of the ranking after the benchmark has been run. Li’s framework should determine the experiment before outcomes are observed.

Theory lives in four places in the arc:

1. **The coordinate system.** The perturbations are not arbitrary prompt variations. OSP structure, contingent reasoning, forward planning, belief formation, and mechanics-only restatements define the dimensions along which implementation is stressed.

2. **The treatment taxonomy.** Each lever must be mapped ex ante to the theoretical burden it removes, preserves, or adds. This includes the important negative predictions: prompts that invite belief formation or additional lookahead should worsen implementation even though they appear to provide more “help.”

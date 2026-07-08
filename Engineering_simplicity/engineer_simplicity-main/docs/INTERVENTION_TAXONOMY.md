# Comprehensive Intervention Taxonomy

## Theoretical Framework (Li 2017, Li 2024)

This document provides a unified taxonomy of behavioral interventions for both auction and matching mechanism experiments, based on Shengwu Li's theoretical framework.

### Three Cognitive Axes (Li 2024 "Designing Simple Mechanisms")

**Axis 1: Contingent Reasoning** — Case-by-case thinking about unobserved opponent moves
- Example: "If opponent bids $30, I get X; if $40, I get Y; if $50, I get Z"
- Li: "It is harder to account for hypothetical contingencies than to reason about observed events"
- Tested via prompts that force enumeration of possible opponent actions

**Axis 2: Forward Planning** — Planning across multiple own decision points (k-step foresight)
- Only applies to mechanisms with sequential decisions (NOT SPSB!)
- Per Pycia & Troyan (2023): k=0 (myopic), k=1, k=2, ... k=∞ (full backward induction)
- Tested via prompts that scaffold varying amounts of lookahead

**Axis 3: Belief Reasoning** — Reasoning about others' beliefs
- First-order: "What do others believe?"
- Second-order: "What do others believe I believe?"
- Higher-order: Infinite regress
- Li: Strategy-proof mechanisms don't require any belief reasoning (dominant strategy)
- If belief interventions affect play, LLM is confused about dominance

### OSP (Li 2017)
> "A strategy is obviously dominant if, for any deviation, at any information set where both strategies first diverge, the best outcome under the deviation is no better than the worst outcome under the dominant strategy."

Key: Agent sees clinchable options (what they can get RIGHT NOW) at each decision point.

---

## Auctions: Intervention Taxonomy

### Mechanism Context

SPSB is a **one-shot game**. There is NO forward planning axis because there are no sequential decisions. What we previously labeled "Axis 2" interventions are actually testing mechanism comprehension through different framings.

### Axis 1: Contingent Reasoning

These interventions test whether prompting case-by-case reasoning about others' bids helps LLMs see that truthfulness (bid=value) is optimal.

| File | What It Tests | Expected Effect |
|------|---------------|-----------------|
| `axis1_contingent_baseline.txt` | Raw LLM behavior | Baseline (~0 to +1 overbid) |
| `axis1_contingent_enumerate.txt` | Lists others' possible bids | May cause unnecessary strategizing |
| `axis1_contingent_dominated.txt` | Identify dominated strategies | Should help find optimal |
| `axis1_contingent_worstcase.txt` | Focus on worst-case analysis | May support truthful bidding |

### Mechanism Comprehension (Reclassified from "Axis 2")

These interventions help LLMs understand the SPSB mechanism better. They were mislabeled as "forward planning" but SPSB has no sequential decisions.

| File | What It Tests | Theoretical Basis |
|------|---------------|-------------------|
| `axis1_contingent_onestep.txt` | "Bid sets IF you win, not what you pay" | Clarifies payment rule |
| `axis1_contingent_tree.txt` | PATH A (win) vs PATH B (lose) payoff tree | Visualizes contingencies |
| `axis1_contingent_backward_induct.txt` | Fake two-stage framing | Tests if sequential framing helps |

**Key Insight**: `onestep` improves play because it explains the mechanism, not because of forward planning.

### Axis 3: Belief Reasoning

Since SPSB has a dominant strategy, belief interventions SHOULD NOT affect rational play. Any effect reveals confusion about dominance.

| File | What It Tests | Rational Prediction |
|------|---------------|---------------------|
| `axis3_beliefs_baseline.txt` | Standard competitor framing | Baseline |
| `axis3_beliefs_firstorder.txt` | "What do you think others will bid?" | No effect |
| `axis3_beliefs_secondorder.txt` | "What do others think YOU will bid?" | No effect |
| `axis3_beliefs_common_knowledge.txt` | Emphasize common knowledge of rationality | No effect |

### Risk Preferences & Loss Aversion

These test behavioral effects that theoretically shouldn't matter for SPSB with private values.

| File | What It Tests | Finding |
|------|---------------|---------|
| `intervention_risk_averse.txt` | "You are risk averse" | GPT-4o/Gemma underbid |
| `intervention_risk_neutral.txt` | "You are risk neutral" | Baseline |
| `intervention_risk_seeking.txt` | "You are risk seeking" | Claude/GPT-4o overbid |
| `loss_aversion_gain_frame.txt` | Frame as gains | Baseline comparison |
| `loss_aversion_loss_frame.txt` | Frame as losses | Tests loss aversion |
| `loss_aversion_mixed_frame.txt` | Mixed framing | Standard effects |
| `loss_aversion_endowment.txt` | Explicit endowment | WTA > WTP |
| `loss_aversion_WTA_WTP.txt` | WTA vs WTP comparison | Direct test |

### Ascending Clock vs SPSB

| Mechanism | Mean Deviation | What We Learn |
|-----------|---------------|---------------|
| SPSB | +1 to +3 (overbid) | LLMs slightly overbid |
| Ascending Clock | ~0 | Iterative structure helps |

**Key Result**: Iterative mechanisms improve play. This tests iterative structure, not specifically OSP.

---

## DA (Deferred Acceptance): Intervention Taxonomy

### Mechanism Context

Direct-revelation DA is a one-shot game, but the mechanism has internal rounds. Forward planning (Axis 2) applies because we can scaffold thinking about the algorithm's rounds.

### Current "OSP" Implementation Status

**IMPORTANT**: The current "OSP" mode tests iterative vs direct revelation structure, NOT the true OSP property. True OSP requires showing the clinchable/budget set at each decision point.

| Condition | Mean Kendall τ | Interpretation |
|-----------|---------------|----------------|
| Direct baseline | ~15-20% errors | Some ranking errors |
| "OSP" (iterative choice) | ~0% errors | Perfect - but trivially easy task |

**Recommendation**: Rename to "Iterative vs Direct" rather than "OSP" until the clinchable set is shown.

### Axis 1: Contingent Reasoning

| File | What It Tests |
|------|---------------|
| `axis1_da_enumerate.txt` | List others' possible rankings |
| `axis1_da_dominated.txt` | Identify dominated rankings |
| `axis1_da_worstcase.txt` | Focus on worst-case obtainable set |
| `axis1_da_onestep.txt` | Frame as simple one-step decision |
| `axis1_da_tree.txt` | Present DA as decision tree |
| `axis1_da_backward_induct.txt` | Prompt backward induction through rounds |

### Axis 2: Forward Planning (k-step Foresight)

**Approach A: Simulation Scaffolding**

| File | k-step | What It Tests |
|------|--------|---------------|
| `axis2_da_0step.txt` | k=0 | Baseline - no simulation guidance |
| `axis2_da_1step.txt` | k=1 | "Think about first rejection" |
| `axis2_da_2step.txt` | k=2 | "Think through first two rejections" |
| `axis2_da_fullsim.txt` | k=∞ | "Mentally simulate entire algorithm" |

**Approach B: Monotonicity Framing**

These capture the OSP intuition by explaining WHY truthful play is safe.

| File | What It Tests |
|------|---------------|
| `axis2_da_monotonic_options.txt` | "Your options never shrink" |
| `axis2_da_monotonic_safety.txt` | "Rejections only redirect, never eliminate" |
| `axis2_da_monotonic_outcome.txt` | "Obtainable set determines outcome" |

### Axis 3: Belief Reasoning

Like auctions, these SHOULD NOT affect play since DA is strategy-proof. Any effect = confusion.

| File | What It Tests |
|------|---------------|
| `axis3_da_firstorder.txt` | "What do you think others will rank?" |
| `axis3_da_secondorder.txt` | "What do others think YOU will rank?" |
| `axis3_da_common_knowledge.txt` | Emphasize common knowledge of rationality |

### Risk Preferences & Loss Aversion

Same as auctions - tests behavioral effects.

| File | What It Tests |
|------|---------------|
| `intervention_risk_averse.txt` | Risk averse persona |
| `intervention_risk_neutral.txt` | Risk neutral persona |
| `intervention_risk_seeking.txt` | Risk seeking persona |
| `loss_aversion_*.txt` | Various loss aversion frames |

---

## What We Globally Probe and Learn

### Finding 1: Iterative Structure Helps
- Ascending clock beats SPSB (auctions)
- Iterative choice beats direct revelation (DA)
- Aligns with Li (2017): making mechanism sequential reduces cognitive burden

### Finding 2: Mechanism Comprehension Matters
- `onestep` ("bid sets IF you win, not what you pay") improves auction play
- This is NOT forward planning - it's explanation of payment rule
- LLMs don't inherently understand second-price mechanism

### Finding 3: Risk Framing Affects LLM Behavior
- "You are risk averse" → significant underbidding
- "You are risk seeking" → significant overbidding
- True even though risk preferences shouldn't matter for SPSB with private values

### Finding 4: Belief Interventions Reveal Confusion
- If Axis 3 interventions affect play, LLMs don't understand dominant strategy
- Rational players ignore others' beliefs in strategy-proof mechanisms

### What's Not Yet Tested

1. **True OSP**: Budget set / clinchable options not shown in current implementation
2. **True Forward Planning for Auctions**: SPSB is one-shot, no sequential decisions
3. **k-step Foresight Effects**: DA Axis 2 interventions need full analysis

---

## Recommendations

### Immediate Changes
1. ✅ Rename "OSP" comparison to "Iterative vs Direct" (see task #2)
2. ✅ Reclassify auction interventions per above tables (already done 2026-02-04)

### For True OSP Testing
Add to iterative DA prompts: "School X would accept you RIGHT NOW if you chose it"
This shows the clinchable set and tests whether OSP framing (vs just iterative) matters.

### For Better Auction Analysis
Acknowledge SPSB has no forward planning axis. The "comprehension" interventions (`onestep`, `tree`) are valuable but test something different from k-step foresight.

---

## Key References

1. Li, S. (2024). "Designing Simple Mechanisms." Journal of Economic Perspectives 38(4): 175-192.
2. Li, S. (2017). "Obviously Strategy-Proof Mechanisms." American Economic Review 107(11): 3257-87.
3. Börgers, T. & Li, J. (2019). "Strategically Simple Mechanisms." Econometrica 87(6): 2003-35.
4. Pycia, M. & Troyan, P. (2023). "A Theory of Simplicity in Games and Mechanism Design." Econometrica 91(4): 1495-526.
5. Ashlagi, I. & Gonczarowski, Y. A. (2018). "Stable Matching Mechanisms Are Not Obviously Strategy-Proof." JET 177: 405-25.
6. Dreyfuss, B., Heffetz, O. & Rabin, M. (2022). "Expectations-Based Loss Aversion May Help Explain Seemingly Dominated Choices in Strategy-Proof Mechanisms." AEJ: Micro 14(4): 515-55.
7. Kahneman, D. & Tversky, A. (1979). "Prospect Theory." Econometrica 47(1): 263-91.

---

## Changelog

### 2026-02-09: Initial Comprehensive Taxonomy
- Created unified taxonomy document covering both auctions and DA
- Properly categorized all interventions according to Li 2017/2024 framework
- Clarified that SPSB has no forward planning axis
- Documented what's actually being tested vs. what we claim to test

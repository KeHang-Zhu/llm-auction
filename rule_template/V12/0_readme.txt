# V11 Behavioral Interventions for SPSB Auctions

This folder contains systematic behavioral interventions designed to test specific
cognitive/behavioral axes in Second-Price Sealed-Bid (SPSB) auctions.

## Theoretical Framework

### Shengwu Li's Three Axes of Mechanism Complexity

From "Designing Simple Mechanisms" (JEP 2024), Li identifies three cognitive challenges
that participants must overcome to recognize incentive-compatibility:

**Axis 1: Contingent Reasoning about Others' Moves**
- Some mechanisms require case-by-case reasoning about opponents' possible actions
- SPSB requires this: to see bid=value is optimal, you must compare payoffs across
  all possible opponent bid profiles
- Ascending auctions do NOT require this (obviously strategy-proof): worst-case from
  truthful play beats best-case from deviation at each decision point
- Key insight from Li: "Psychologically, it is harder to account for hypothetical
  contingencies than to reason about observed events"

**Axis 2: Forward Planning (Backward Induction)**
- Some mechanisms require planning far ahead through future decision nodes
- Dynamic mechanisms can require backward induction through many steps
- "One-step simple" mechanisms: optimal play emerges from looking just one step ahead
- Key example: In ascending auction, bidder can reason "if I quit now → $0; if I
  continue and plan to quit next step → at least $0" without full backward induction

**Axis 3: Higher-Order Beliefs**
- Some mechanisms require reasoning about what others believe (and believe about beliefs)
- Double auction with α=0.5 requires infinite regress of beliefs
- SPSB does NOT require this (dominant strategy independent of beliefs about others)
- Key insight: Strategy-proof mechanisms are "strategically simple" - can play well
  using only first-order beliefs

### Prospect Theory (Kahneman & Tversky 1979)

**Loss Aversion**
- Losses loom larger than equivalent gains (λ ≈ 2.25)
- Reference-dependent evaluation of outcomes
- Endowment effect: WTA > WTP
- Dreyfuss, Heffetz & Rabin (2022) show loss aversion may explain mistakes in
  strategy-proof mechanisms (cited in Li 2024)

---

## Mapping of Existing V10 Interventions to Axes

The following V10 interventions can be categorized within this framework:

### Axis 1: Contingent Reasoning
| V10 File | Description | Axis 1 Relevance |
|----------|-------------|------------------|
| `intervention_nash_deviation.txt` | Prompts to enumerate deviations and others' responses | **Direct test** - forces contingent reasoning |
| `intervention_menu.txt` | "Price to win" framing (proxy bidding) | **Reduces complexity** - makes SPSB more like ascending auction (OSP-like) |
| `intervention_dominated.txt` (if exists) | Dominated strategy identification | Reduces need for case-by-case comparison |

### Axis 2: Forward Planning
| V10 File | Description | Axis 2 Relevance |
|----------|-------------|------------------|
| `intervention_proxy_breitmoser.txt` | Two-stage sealed→clock framing | **Direct test** - requires understanding clock stage to set sealed bid |

### Axis 3: Higher-Order Beliefs
| V10 File | Description | Axis 3 Relevance |
|----------|-------------|------------------|
| (None directly) | - | SPSB has dominant strategy, so Axis 3 less relevant |

### Preference Manipulation (Not Complexity Axes)
| V10 File | Description | Category |
|----------|-------------|----------|
| `intervention_risk_averse.txt` | Risk averse persona | Preference (not complexity) |
| `intervention_risk_neutrality.txt` | Risk neutral persona | Preference (not complexity) |
| `intervention_risk_seeking.txt` | Risk seeking persona | Preference (not complexity) |

### Information/Belief Manipulation
| V10 File | Description | Category |
|----------|-------------|----------|
| `intervention_NE_strat_reveal.txt` | Tells LLM the dominant strategy is bid=value | Strategy revelation (reduces all axes) |
| `intervention_wrong_strat_reveal.txt` | Tells LLM wrong strategy (bid=50% value) | Tests anchoring/authority bias |

---

## New V11 Intervention Files

### Axis 1: Contingent Reasoning
Tests whether LLMs can reason about how their optimal action depends on others' possible moves.

- `axis1_contingent_baseline.txt` - Standard SPSB, no guidance
- `axis1_contingent_enumerate.txt` - Explicitly prompt to enumerate others' possible bids
- `axis1_contingent_dominated.txt` - Ask to identify dominated strategies
- `axis1_contingent_worstcase.txt` - Focus on worst-case analysis (OSP-like reasoning)

**Li's Key Insight**: In SPSB, to see that bid=$40 beats bid=$50, you must understand:
"if truthful bid would win at $30, then $50 also wins at $30; if truthful bid loses,
then $50 only wins at prices above $40 (undesirable)." This case-by-case reasoning
is hard. In ascending auction, you just compare "quit now → $0" vs "continue → ≥$0".

### Axis 2: Forward Planning
Tests whether LLMs can backward-induct through sequential decision problems.

- `axis2_forward_baseline.txt` - Two-stage auction (sealed bid → clock)
- `axis2_forward_backward_induct.txt` - Explicitly prompt backward induction
- `axis2_forward_onestep.txt` - Frame as one-step decision (reduces complexity)
- `axis2_forward_tree.txt` - Present decision tree explicitly

**Li's Key Insight**: Ascending auctions are "one-step simple" - looking one step ahead
at each point reproduces optimal play, even though partial plans are inconsistent.
At $1: "plan to quit at $2" → keep going. At $2: revise to "plan to quit at $3".

### Axis 3: Higher-Order Beliefs
Tests whether LLMs reason about what others believe (and believe about beliefs).

- `axis3_beliefs_baseline.txt` - Standard SPSB with competitor framing
- `axis3_beliefs_firstorder.txt` - Ask: "What do you think others will bid?"
- `axis3_beliefs_secondorder.txt` - Ask: "What do others think YOU will bid?"
- `axis3_beliefs_common_knowledge.txt` - Emphasize common knowledge of rationality

**Li's Key Insight**: SPSB is "strategically simple" (Börgers & Li 2019) because
bid=value is dominant - you don't need to reason about others' beliefs at all.
If higher-order belief prompts affect LLM bidding, it reveals confusion about dominance.

### Loss Aversion
Tests whether LLMs exhibit loss aversion (overweighting losses vs gains).

- `loss_aversion_baseline.txt` - Standard SPSB framing
- `loss_aversion_gain_frame.txt` - Frame outcomes as gains from zero
- `loss_aversion_loss_frame.txt` - Frame outcomes as losses from endowment
- `loss_aversion_mixed_frame.txt` - Mixed framing (some gains, some losses)
- `loss_aversion_endowment.txt` - Given explicit starting endowment
- `loss_aversion_WTA_WTP.txt` - Prompts WTA vs WTP comparison

**Connection to Li**: Dreyfuss, Heffetz & Rabin (2022) argue loss aversion may explain
why dynamic random priority outperforms static random priority - not just strategic
mistakes. This is an alternative explanation for some OSP vs non-OSP differences.

---

## Predictions

| Intervention | Rational Response | Human-like Bias |
|-------------|-------------------|-----------------|
| Axis 1 (contingent) | Bid = Value regardless | Shade bid based on others' perceived bids |
| Axis 2 (forward) | Bid = Value (truthful is optimal) | Underbid in complex sequential framing |
| Axis 3 (beliefs) | Bid = Value (dominant strategy) | Adjust bid based on beliefs about others |
| Loss aversion | Bid = Value (frame-invariant) | Overbid in loss frame, underbid in gain frame |

## Methodology

Following Bini et al. (2024) "Behavioral Economics of AI: LLM Biases and Corrections":
- Each axis has a baseline and 3+ treatment variants
- Clear predictions for "rational" vs "human-like" responses
- Can measure treatment effects via regression on bid shading

## Key References

1. Li, S. (2024). "Designing Simple Mechanisms." Journal of Economic Perspectives 38(4): 175-192.
2. Li, S. (2017). "Obviously Strategy-Proof Mechanisms." American Economic Review 107(11): 3257-87.
3. Börgers, T. & Li, J. (2019). "Strategically Simple Mechanisms." Econometrica 87(6): 2003-35.
4. Pycia, M. & Troyan, P. (2023). "A Theory of Simplicity in Games and Mechanism Design." Econometrica 91(4): 1495-526.
5. Dreyfuss, B., Heffetz, O. & Rabin, M. (2022). "Expectations-Based Loss Aversion May Help Explain Seemingly Dominated Choices in Strategy-Proof Mechanisms." AEJ: Micro 14(4): 515-55.
6. Bini et al. (2024). "Behavioral Economics of AI: LLM Biases and Corrections."
7. Kahneman, D. & Tversky, A. (1979). "Prospect Theory." Econometrica 47(1): 263-91.

# V11 Behavioral Interventions - Design Document

## Overview

This document describes the systematic behavioral interventions for SPSB auctions, following the methodology of Bini et al. (2024) "Behavioral Economics of AI."

## Theoretical Framework

### Shengwu Li's Three Axes of Mechanism Complexity

From "Designing Simple Mechanisms" (JEP 2024) and "Obviously Strategy-Proof Mechanisms" (AER 2017):

1. **Axis 1 - Contingent Reasoning**: The extent to which optimal play requires case-by-case reasoning about opponents' possible moves
   - Key formal concept: **Obviously Strategy-Proof (OSP)** - A strategy is *obviously dominant* if, at any information set where it first diverges from a deviation, the worst-case payoff under the dominant strategy is at least as good as the best-case payoff under the deviation
   - SPSB is NOT OSP: bidding your value can lead to $0 (if you lose), while overbidding can yield positive payoff
   - Ascending auctions ARE OSP: at any price below your value, worst-case from continuing ≥ $0 = best-case from quitting

2. **Axis 2 - Forward Planning**: The extent to which optimal play requires backward induction through future decision nodes
   - Key formal concept: **One-Step Simple** (Pycia & Troyan 2023) - Truthful play can be induced by partial strategic plans looking just one step ahead
   - Ascending auctions are one-step simple: at each price, compare "quit now" vs "continue and quit next step"
   - Chess is NOT one-step simple despite having obviously dominant strategies in won positions

3. **Axis 3 - Higher-Order Beliefs**: The extent to which optimal play requires reasoning about others' beliefs
   - Key formal concept: **Strategically Simple** (Börgers & Li 2019) - For every first-order belief, there exists a robust strategy
   - SPSB is strategically simple: bid=value is dominant, no need for higher-order beliefs
   - Double auction with α=0.5 is NOT strategically simple: optimal bid requires beliefs about beliefs about beliefs...

### Prospect Theory

From Kahneman & Tversky (1979):

- **Loss Aversion**: Losses loom larger than equivalent gains (λ ≈ 2.25 typically)
- **Reference Dependence**: Outcomes evaluated relative to a reference point
- **Endowment Effect**: WTA > WTP due to loss aversion

---

## Axis 1: Contingent Reasoning

### Theoretical Background

In SPSB, truthful bidding (bid = value) is a **dominant strategy** - optimal regardless of what others do. This means contingent reasoning about others' bids is actually *unnecessary*.

However, human subjects often engage in contingent reasoning anyway, leading to suboptimal bidding. LLMs might similarly be led astray by prompts that encourage such reasoning.

### Interventions

| File | Description | Prediction |
|------|-------------|------------|
| `axis1_contingent_baseline.txt` | Standard SPSB | Baseline bidding behavior |
| `axis1_contingent_enumerate.txt` | Prompt to enumerate others' possible bids | May cause bid-shading if LLM tries to "respond" to others |
| `axis1_contingent_dominated.txt` | Prompt to identify dominated strategies | Should help LLM discover truthful bidding |
| `axis1_contingent_worstcase.txt` | Focus on worst-case analysis | Worst-case of truthful = $0 profit; should support truthful bidding |

### Measurement

- **Rational response**: Bid = Value (or very close)
- **Human-like bias**: Bid < Value (shading) especially in `enumerate` condition
- **Key metric**: |Bid - Value| / Value (bid shading ratio)

### Theoretical Prediction

In SPSB, contingent reasoning prompts should have *minimal* effect on rational bidders since the dominant strategy doesn't depend on others. If LLMs are swayed by these prompts, it reveals they don't fully understand dominance.

---

## Axis 2: Forward Planning

### Theoretical Background

SPSB with a "proxy bidding" or "ascending clock" interpretation requires understanding that:
1. Your sealed bid sets an exit threshold
2. The price rises until one bidder remains
3. Winner pays second-highest bid

A bidder who myopically bids low (to "save money") fails to understand that their bid doesn't determine their payment - only whether they win.

### Interventions

| File | Description | Prediction |
|------|-------------|------------|
| `axis2_forward_baseline.txt` | Two-stage auction (sealed → clock) | Tests basic forward planning |
| `axis2_forward_backward_induct.txt` | Explicit backward induction prompt | Should improve performance |
| `axis2_forward_onestep.txt` | Frame as one-step decision | Reduces complexity, should help |
| `axis2_forward_tree.txt` | Present explicit decision tree | Makes structure transparent |

### Measurement

- **Rational response**: Bid = Value
- **Human-like bias**: Underbidding in baseline (failing to backward induct)
- **Key metric**: Improvement from baseline to treatment conditions

### Theoretical Prediction

Li (2017) shows that making mechanisms "obviously strategy-proof" (OSP) helps boundedly rational agents. The `onestep` and `tree` conditions reduce forward planning requirements and should improve bidding.

---

## Axis 3: Higher-Order Beliefs

### Theoretical Background

In SPSB, optimal play does NOT require reasoning about others' beliefs because truthful bidding is dominant. However, framing that emphasizes strategic interaction and mutual rationality might cause LLMs to over-think.

Higher-order beliefs become relevant in games without dominant strategies (like FPSB), but not in SPSB.

### Interventions

| File | Description | Prediction |
|------|-------------|------------|
| `axis3_beliefs_baseline.txt` | Standard SPSB with "rational opponents" | Baseline |
| `axis3_beliefs_firstorder.txt` | "What will others bid?" | May cause unnecessary strategizing |
| `axis3_beliefs_secondorder.txt` | "What do others think YOU will bid?" | Higher complexity, may confuse |
| `axis3_beliefs_common_knowledge.txt` | Common knowledge of rationality | Should help if LLM reasons correctly |

### Measurement

- **Rational response**: Bid = Value (independent of beliefs)
- **Human-like bias**: Adjusting bid based on beliefs about others
- **Key metric**: Sensitivity of bid to belief prompts

### Theoretical Prediction

If LLMs correctly understand SPSB, higher-order belief prompts should NOT affect bidding. Any effect indicates confusion about dominant strategies.

---

## Loss Aversion

### Theoretical Background

Loss aversion predicts that losses are weighted ~2.25x more than equivalent gains. In auctions:
- **Loss frame**: Emphasizes payment as "losing money" → should cause overbidding (to avoid losing auction)
- **Gain frame**: Emphasizes profit as "gaining money" → should cause more neutral bidding
- **Endowment effect**: If given endowment, WTA > WTP

### Interventions

| File | Description | Prediction |
|------|-------------|------------|
| `loss_aversion_baseline.txt` | Neutral SPSB framing | Baseline |
| `loss_aversion_gain_frame.txt` | All outcomes framed as gains | More conservative bidding? |
| `loss_aversion_loss_frame.txt` | Outcomes framed as losses from endowment | Overbidding to avoid "losing" |
| `loss_aversion_mixed_frame.txt` | Explicit gains AND losses | Standard loss aversion effects |
| `loss_aversion_endowment.txt` | Given explicit endowment | Endowment effect testing |
| `loss_aversion_WTA_WTP.txt` | Prompt WTA vs WTP comparison | Direct endowment effect test |

### Measurement

- **Rational response**: Bid = Value (frame-invariant)
- **Human-like bias**: Bid varies with frame (higher in loss frame)
- **Key metrics**:
  - Bid difference between gain and loss frames
  - Bid/Value ratio by condition

### Theoretical Prediction

Following Bini et al., more advanced LLMs may show MORE human-like biases on preference-based tasks (like loss aversion) while being MORE rational on belief-based tasks.

---

## Experimental Design

### Suggested Comparisons

1. **Within-axis**: Compare baseline to treatments within each axis
2. **Cross-axis**: Compare effect sizes across axes (which matters most?)
3. **Model comparison**: Test across GPT-4, Claude, Gemini, etc.
4. **Temperature effects**: Test at T=0 vs T=1

### Regression Specification

Following Bini et al., use probit/linear regression:

```
Bid_Shading = β₀ + β₁(Treatment) + β₂(Model) + β₃(Treatment × Model) + ε
```

Where:
- Bid_Shading = (Value - Bid) / Value
- Treatment = dummy for intervention condition
- Model = categorical for LLM type

### Sample Size

Recommend N ≥ 100 auction rounds per condition for statistical power.

---

## References

1. Li, S. (2017). Obviously strategy-proof mechanisms. American Economic Review.
2. Kahneman, D., & Tversky, A. (1979). Prospect theory. Econometrica.
3. Bini et al. (2024). Behavioral Economics of AI: LLM Biases and Corrections.

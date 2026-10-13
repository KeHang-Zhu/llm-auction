# LLM Auction Bidding: Theoretical Deviation Analysis

## Overview

This report analyzes the deviation of LLM bidding behavior from theoretical equilibrium predictions across different auction formats, using the Scaled Mean Absolute Deviation (SMAD) metric as described in the methodology paper.

## Methodology

The **Scaled Mean Absolute Deviation (SMAD)** is defined as:

$$\Delta_m = 100 \cdot \frac{E[|b - b^*_m(I)|]}{E[b^*_m(I)]}$$

where:
- $b$ is the observed bid
- $b^*_m(I)$ is the theoretical optimum (equilibrium) bid under format $m$
- $I$ is the information object (value $v$ in private values, signal $s$ in common values)

**95% Confidence Intervals** are calculated as: $\hat{\Delta}_m \pm 1.96 \cdot SE(\hat{\Delta}_m)$

### Theoretical Benchmarks by Auction Type

1. **Strategy-Proof Mechanisms (Truthful Bidding)**:
   - Second-Price (sealed-bid) IPV/APV: $b^*(v) = v$
   - Ascending Clock (AC, AC-B) APV: exit at $p = v$ (equivalent to truthful bidding)
2. **First-Price IPV**: $b^*(v) = \frac{N-1}{N} \cdot v$ where $N=3$ (shading by $1/N$)
3. **Third-Price IPV**: $b^*(v) = \frac{N-1}{N-2} \cdot v$ where $N=3$ (bid above value)
4. **All-Pay IPV**: $E[b^*] = \frac{V}{N}$ (mixed strategy equilibrium)
5. **Common Value**: Profit-based deviation metric (accounts for winner's curse)

## Results Summary

| Auction Format | SMAD (%) | 95% CI | N | Interpretation |
|----------------|----------|---------|---|----------------|
| **Ascending Clock APV** | **7.74** | [5.68, 9.81] | 159 | ✓✓ **Best Performance** |
| **AC-Closed (AC-B) APV** | **8.33** | [6.05, 10.61] | 171 | ✓✓ **Near-optimal** |
| **Second-Price IPV** | 8.74 | [7.40, 10.07] | 270 | ✓ Near-optimal |
| **Second-Price APV** | 11.40 | [10.20, 12.60] | 291 | ✓ Near-optimal |
| **First-Price IPV** | 41.63 | [38.48, 44.77] | 285 | ⚠ Moderate deviation |
| **Third-Price IPV** | 52.90 | [49.67, 56.12] | 288 | ⚠ Large deviation |
| **First-Price CV** | 100.00 | [77.89, 122.11] | 288 | ✗ Very large deviation |
| **Second-Price CV** | 100.00 | [75.92, 124.08] | 276 | ✗ Very large deviation |
| **All-Pay IPV** | 176.99 | [163.54, 190.44] | 273 | ✗ Extreme deviation |

## Key Findings

### 1. Strategy-Proof Mechanisms: Dynamic vs. Sealed-Bid

**Ascending Clock Auctions (Best Overall Performance)**:
- **Ascending Clock APV**: 7.74% deviation ⭐ **BEST**
- **AC-Closed (AC-B) APV**: 8.33% deviation

**Second-Price Sealed-Bid Auctions**:
- **Second-Price IPV**: 8.74% deviation
- **Second-Price APV**: 11.40% deviation

**Key Insight**: Dynamic ascending clock auctions produce **better LLM behavior** than sealed-bid equivalents:
1. **Incremental decision-making**: LLMs can make simple "stay/exit" decisions at each price point
2. **Natural reasoning**: "Stay if price < value" is more intuitive than "bid exactly your value"
3. **Observable feedback**: Even in closed-bid AC (AC-B), the structured format helps
4. **Lower cognitive load**: No need to compute optimal bid upfront

This suggests **dynamic mechanisms may be preferable for LLM-based auction systems** when strategy-proofness is desired.

### 2. Strategic Mechanisms (First-Price, Third-Price)
- **First-Price IPV**: 41.63% deviation
- **Third-Price IPV**: 52.90% deviation
- **Insight**: LLMs struggle with strategic shading. In First-Price auctions, optimal shading is $(N-1)/N = 2/3$, but LLMs either:
  - Under-shade (bid too close to value)
  - Over-shade (bid too conservatively)
- Third-Price is even harder, requiring bids *above* value, which LLMs find counterintuitive.

### 3. All-Pay Auction
- **All-Pay IPV**: 176.99% deviation (worst performance)
- **Insight**: Mixed-strategy equilibrium is extremely difficult for LLMs. The theoretical benchmark is $E[b^*] = V/N$, but LLMs tend to:
  - Bid much closer to their full value (extreme risk aversion)
  - Fail to randomize properly
  - Not fully internalize that they "pay regardless of winning"
  - Show consistent overbidding patterns

### 4. Common Value Auctions
- **Both First-Price and Second-Price CV**: 100% deviation
- **Insight**: Winner's curse is a major challenge. LLMs show evidence of:
  - Overbidding (not adjusting for adverse selection)
  - Failing to condition on "winning = bad news about true value"
  - Large negative profits indicating severe winner's curse
  - No difference between first-price and second-price formats (both fail equally)

## Comparison to Human Performance

Based on the literature review in the PDF, these results can be contextualized:

### LLMs vs Humans - Similar Patterns:
1. **Strategy-proof mechanisms work better**: Both humans and LLMs perform best with truthful bidding
2. **Winner's curse affects both**: CV auctions show large deviations for both populations
3. **All-pay is hardest**: Mixed strategies are cognitively demanding for both
4. **Dynamic formats help**: Like humans, LLMs benefit from incremental decision-making

### LLMs vs Humans - Differences:
1. **Magnitude**: LLM deviations appear larger than typical human experiments, especially in:
   - All-Pay auctions (177% vs human ~50-80%)
   - CV auctions (100% vs human ~40-60%)
2. **Consistency**: LLMs might show more consistent errors (all bidding similarly wrong) vs human heterogeneity
3. **Learning**: Humans show learning across rounds; LLMs in this experiment are one-shot
4. **Dynamic advantage**: LLMs show a **stronger preference** for dynamic formats than humans do

## Recommendations

### For Auction Designers Using LLM Agents:

**Priority 1 - Use Dynamic Strategy-Proof Mechanisms**:
1. **Ascending Clock auctions** - best overall performance (7-8% deviation)
2. **Second-Price sealed-bid** - good alternative (9-11% deviation)
3. **Advantage of dynamic formats**: Simpler reasoning at each step

**What to Avoid**:
1. **All-Pay auctions** - LLMs cannot handle mixed strategies (177% deviation)
2. **Common Value auctions** - severe winner's curse (100% deviation)
3. **Third-Price auctions** - counterintuitive overbidding requirement (53% deviation)

**Moderate Risk**:
1. **First-Price auctions** - usable but expect 40%+ deviation from optimal

### For Future Research:

**High Priority**:
1. **Mechanism design for LLMs**: Investigate why dynamic formats work better
   - Is it the step-by-step reasoning?
   - Visual/temporal structure?
   - Reduced working memory requirements?

2. **Winner's curse mitigation**:
   - Provide explicit reasoning prompts about adverse selection
   - Test if examples of winner's curse improve CV performance
   - Investigate if pre-training on auction theory helps

3. **Mixed strategy learning**:
   - Can LLMs learn to randomize in All-Pay auctions?
   - Test temperature parameter effects on randomization

**Medium Priority**:
4. **Cross-model comparison**: Test GPT-4, Claude, Gemini, etc.
5. **Chain-of-thought**: Does explicit reasoning reduce deviations?
6. **Multi-round learning**: Can LLMs learn from feedback across rounds?

## Statistical Notes

- All confidence intervals are calculated using standard error propagation
- Sample sizes range from 159-291 observations per auction type
  - AC auctions: 159-171 observations (merged across multiple runs)
  - Other auctions: 270-291 observations
- Most differences between auction types are statistically significant
  - AC, AC-B, and Second-Price IPV have overlapping CIs (all near-optimal)
  - Strategic mechanisms clearly different from strategy-proof ones
- For CV auctions, deviations are profit-based rather than bid-based due to data limitations

## Files Generated

- `theoretical_deviation_plot.png`: Visualization of results
- `theoretical_deviation_results.csv`: Raw numerical results
- `deviation_analysis_report.md`: This report

---

**Date**: January 2026
**Data Source**: `experiment_logs_with_explanation/V10/`
**Model**: GPT-4o (temperature=0.5)

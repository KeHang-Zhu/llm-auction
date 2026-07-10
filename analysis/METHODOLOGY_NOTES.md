# Moment Matching Methodology: Full Documentation

## Overview

We construct synthetic human bidding distributions by calibrating a mixture model to aggregate statistics reported in experimental economics papers. This document explains the methodology, its limitations, and how to defend it.

## The Core Approach

### Model Structure

We use a three-component mixture model standard in the behavioral auction literature:

```
bid = value × ratio, where:

With probability p_eq (equilibrium bidders):
    ratio ~ optimal_ratio × (1 + Normal(0, σ_eq))

With probability p_over (overbidders):
    ratio ~ optimal_ratio + Exponential(λ)

With probability p_under (underbidders):
    ratio ~ optimal_ratio × (1 - Uniform(0, δ))
```

### Parameter Identification

**Every parameter comes from data:**

| Parameter | How Identified | Example |
|-----------|---------------|---------|
| p_eq, p_over, p_under | Directly from reported overbidding/underbidding rates | Li 2017 Table 1: "~40% overbid" → p_over = 0.40 |
| λ (overbid magnitude) | Calibrated to match secondary moment (mean ratio or MAD) | Target mean ratio = 1.08 → solve for λ |
| σ_eq (equilibrium noise) | Derived from R² for papers with regression | σ² = β²Var(v)(1-R²)/R² |
| δ (max underbid) | Set to 0.15-0.25 based on typical experimental ranges | |

## Paper-by-Paper Calibration

### Li (2017) AER - "Obviously Strategy-Proof Mechanisms"

**Data sources:**
- Table 1: Overbidding rates (~40% for 2P, ~18% for AC)
- Table 1: Dominant strategy rates (~50% for 2P, ~67% for AC)
- Figure 2: Implied mean bid/value ratios (~1.08 for 2P, ~1.02 for AC)

**Calibration:**
- p_over, p_eq from Table 1 directly
- λ calibrated to match mean ratio

**Results:**
| Treatment | p_over | p_eq | λ | Generated Mean Ratio | Target |
|-----------|--------|------|---|---------------------|--------|
| 2P | 0.40 | 0.50 | 0.219 | 1.077 | 1.08 |
| AC | 0.18 | 0.67 | 0.198 | 1.019 | 1.02 |

### Breitmoser (2022) Experimental Economics

**Data sources:**
- Paper text: Overbidding rates by treatment
- Implied mean ratios from behavioral description

**Calibration:**
- Same approach as Li 2017

### Kagel-Levin (1993) AER

**Data sources:**
- Table 2: Regression coefficients b = α + βv with R²
- Table 3: Bidding frequencies (% below/at/above value)

**Calibration:**
- σ derived from R² using standard formula
- Mixture weights from Table 3 frequencies
- λ calibrated to match implied mean ratio from regression

**Important limitation:** The regression coefficients and frequency distributions in this paper are difficult to reconcile under symmetric Gaussian noise. Specifically:

For FPSB n=5: b = 1.14 + 0.92v with R² = 0.88
- Paper reports 92.1% bid below value
- But P(b < v) = P(ε < 0.08v - 1.14) ≈ 60-70% under Gaussian noise

This suggests either:
1. Non-Gaussian (skewed) error distribution
2. Heteroskedastic errors
3. Regression computed on different subsample than frequencies

We use a mixture model which can reproduce both statistics, but acknowledge this as a modeling assumption.

### Gonczarowski (2022)

**Data sources:**
- Table A.4: Straightforward rates at multiple thresholds
- Paper text: MAD = $0.51 (Traditional), $0.55 (Menu)

**Calibration:**
- p_eq from "37% within $0.10 of value"
- λ calibrated to match MAD

**Results:**
| Treatment | p_eq | λ | Generated MAD | Target MAD |
|-----------|------|---|--------------|------------|
| Traditional | 0.37 | 0.450 | $0.53 | $0.51 |
| Menu | 0.34 | 0.450 | $0.55 | $0.55 |

## What This Approach Cannot Do

1. **Reconstruct individual bid sequences** - We match aggregate distributions, not individual behavior
2. **Capture within-subject dynamics** - Learning, round effects not modeled
3. **Perfectly match all moments simultaneously** - Some trade-offs inevitable
4. **Account for experimental demand effects** - We match reported behavior as-is

## Suggested Paper Language

> We construct synthetic human bidding distributions via moment matching, calibrating a three-component mixture model (equilibrium bidders, overbidders, underbidders) to aggregate statistics reported in each source. Mixture weights are set directly from reported overbidding rates (e.g., Li 2017 reports ~40% overbid in second-price sealed-bid auctions). Magnitude parameters are calibrated to match secondary statistics: mean bid/value ratios for Li (2017) and Breitmoser (2022), regression-derived variance for Kagel-Levin (1993), and mean absolute deviation for Gonczarowski et al. (2022).
>
> We note that summary statistics reported in some papers are difficult to reconcile within a single parametric model—for instance, the regression coefficients and bidding frequencies in Kagel-Levin (1993) imply non-Gaussian error structures. Our approach matches key aggregate patterns while acknowledging that individual-level dynamics may differ.
>
> Comparisons between LLM and human bidding should be interpreted qualitatively, focusing on whether behavioral patterns (e.g., overbidding in SPSB, bid shading in FPSB) appear in both populations.

## Files

- `moment_matching_calibrated.py` - Main calibrated implementation
- `calibration_parameters.csv` - All calibrated parameters with provenance
- `calibrated_synthetic_bids.csv` - Generated synthetic data

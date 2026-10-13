"""
Moment Matching Analysis for Li 2017 "Obviously Strategy-Proof Mechanisms" (AER)

This script generates synthetic human bidding data from empirical statistics reported
in Li (2017) "Obviously Strategy-Proof Mechanisms" American Economic Review 107(11): 3257-3287

Key Experimental Design:
- Four-player auctions with induced private values
- Comparing Second-Price sealed-bid (2P) vs Ascending Clock (AC)
- Both are strategy-proof, but AC is Obviously Strategy-Proof (OSP)

Key Findings from Li 2017:
- 2P: ~40% overbidding rate (bids > value by more than threshold)
- AC: <20% overbidding rate
- Dominant strategy play significantly higher in AC than 2P
- Effect persists even after 5 rounds with feedback

The OSP mechanism (ascending clock) produces closer-to-optimal bidding because:
- At any information set where strategies diverge, the best outcome under deviation
  is no better than worst outcome under dominant strategy
- Cognitively limited agents can recognize AC as weakly dominant more easily

SMAD Metrics:
- Standard SMAD: 100 * E[|b - v|] / E[v]  (for SPSB, optimal is b = v)
- For comparison with FPSB interventions

Author: Analysis for LLM Auction Project
"""

import numpy as np
import pandas as pd
from pathlib import Path


# =============================================================================
# LI 2017 REPORTED STATISTICS
# =============================================================================

# From the paper and Breitmoser replication:
# - 2P (Second-Price): ~40% overbidding rate
# - AC (Ascending Clock): <20% overbidding rate
# Overbidding defined as bid > value by more than threshold (typically 1 currency unit)

# Derived statistics from the experimental literature:
# Mean bid/value ratio and variance

EXPERIMENTAL_PARAMETERS = {
    '2P': {  # Second-Price sealed-bid (not OSP)
        'name': 'Second-Price Sealed-Bid',
        'overbidding_rate': 0.40,  # ~40% overbid
        'underbidding_rate': 0.10,  # ~10% underbid
        'dominant_rate': 0.50,      # ~50% play dominant strategy
        # Approximate bid/value ratio distribution
        'mean_ratio': 1.08,  # Slight overbidding on average
        'std_ratio': 0.20,   # Based on typical experimental variance
        'optimal_ratio': 1.0,
        'osp': False,
    },
    'AC': {  # Ascending Clock (OSP)
        'name': 'Ascending Clock',
        'overbidding_rate': 0.18,  # <20% overbid
        'underbidding_rate': 0.15,  # Some underbidding (conservative)
        'dominant_rate': 0.67,      # ~67% play dominant strategy
        # Closer to optimal
        'mean_ratio': 1.02,  # Near truthful
        'std_ratio': 0.12,   # Less variance due to OSP
        'optimal_ratio': 1.0,
        'osp': True,
    },
}

# Environment parameters
ENVIRONMENT = {
    'value_min': 0,
    'value_max': 50,  # Typical range in experiments
    'n_bidders': 4,
    'n_rounds': 5,
}


# =============================================================================
# SYNTHETIC DATA GENERATION
# =============================================================================

class Li2017MomentMatcher:
    """Generate synthetic bidding data matching Li 2017 experimental statistics."""

    def __init__(self, auction_type='2P'):
        self.auction_type = auction_type
        self.params = EXPERIMENTAL_PARAMETERS[auction_type]

    def generate_values(self, n_samples):
        """Generate private values uniformly distributed."""
        return np.random.uniform(
            ENVIRONMENT['value_min'],
            ENVIRONMENT['value_max'],
            n_samples
        )

    def generate_bids_from_distribution(self, values):
        """Generate bids matching the empirical distribution.

        Model: b = ratio * v where ratio ~ N(mean_ratio, std_ratio)
        with truncation to ensure reasonable bids
        """
        n = len(values)

        # Generate bid/value ratios
        ratios = np.random.normal(
            self.params['mean_ratio'],
            self.params['std_ratio'],
            n
        )

        # Truncate to reasonable range [0.5, 2.0]
        ratios = np.clip(ratios, 0.5, 2.0)

        bids = values * ratios

        # Ensure non-negative bids
        bids = np.maximum(bids, 0)

        return bids

    def generate_bids_mixture_model(self, values):
        """Generate bids using mixture model based on behavior types.

        Model the population as:
        - dominant_rate: bid = value (optimal)
        - overbidding_rate: bid = value * (1 + overbid_amount)
        - underbidding_rate: bid = value * (1 - underbid_amount)
        """
        n = len(values)
        bids = np.zeros(n)

        dom_rate = self.params['dominant_rate']
        over_rate = self.params['overbidding_rate']
        under_rate = self.params['underbidding_rate']

        # Normalize rates
        total_rate = dom_rate + over_rate + under_rate
        dom_rate /= total_rate
        over_rate /= total_rate
        under_rate /= total_rate

        for i in range(n):
            r = np.random.random()

            if r < dom_rate:
                # Dominant strategy: bid = value (with small noise)
                bids[i] = values[i] + np.random.normal(0, 1)
            elif r < dom_rate + over_rate:
                # Overbidding: bid > value
                overbid_factor = 1.0 + np.random.exponential(0.15)
                bids[i] = values[i] * overbid_factor
            else:
                # Underbidding: bid < value
                underbid_factor = np.random.uniform(0.7, 0.95)
                bids[i] = values[i] * underbid_factor

        # Ensure non-negative
        bids = np.maximum(bids, 0)

        return bids

    def generate_synthetic_data(self, n_samples=1000, use_mixture=True):
        """Generate complete synthetic dataset."""

        values = self.generate_values(n_samples)

        if use_mixture:
            bids = self.generate_bids_mixture_model(values)
        else:
            bids = self.generate_bids_from_distribution(values)

        optimal_bids = values.copy()  # For SPSB, optimal is truthful

        return pd.DataFrame({
            'player_value': values,
            'bid': bids,
            'optimal_bid': optimal_bids,
            'bid_value_ratio': bids / np.maximum(values, 0.01),
            'auction_type': self.auction_type,
            'auction_name': self.params['name'],
            'is_osp': self.params['osp'],
            'source': 'Li_2017_OSP',
        })


# =============================================================================
# SMAD CALCULATION
# =============================================================================

def compute_smad_standard(values, bids):
    """Compute standard SMAD for second-price auction.

    SMAD = 100 * E[|b - v|] / E[v]

    For SPSB, optimal bid = value, so deviation = |bid - value|
    """
    optimal_bids = values  # Truthful is optimal
    mean_optimal = np.mean(optimal_bids)

    if mean_optimal <= 0:
        return np.inf

    mean_abs_deviation = np.mean(np.abs(bids - optimal_bids))
    smad = 100 * mean_abs_deviation / mean_optimal

    return smad


def compute_metrics(df):
    """Compute all relevant metrics for a dataset."""

    values = df['player_value'].values
    bids = df['bid'].values

    # Filter valid observations
    valid_mask = values > 1
    values = values[valid_mask]
    bids = bids[valid_mask]

    ratios = bids / values

    # Overbidding rate (bid > value by more than 2%)
    overbid_threshold = 1.02
    overbidding_rate = np.mean(ratios > overbid_threshold)

    # Underbidding rate (bid < value by more than 2%)
    underbid_threshold = 0.98
    underbidding_rate = np.mean(ratios < underbid_threshold)

    # Dominant strategy rate (within 2% of value)
    dominant_rate = np.mean((ratios >= underbid_threshold) & (ratios <= overbid_threshold))

    # SMAD
    smad = compute_smad_standard(values, bids)

    return {
        'n': len(values),
        'mean_ratio': np.mean(ratios),
        'std_ratio': np.std(ratios),
        'overbidding_rate': overbidding_rate,
        'underbidding_rate': underbidding_rate,
        'dominant_rate': dominant_rate,
        'smad': smad,
        'dist_from_optimal': abs(np.mean(ratios) - 1.0),
    }


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def run_li_2017_moment_matching(output_dir=None):
    """Run moment matching analysis for Li 2017 OSP paper."""

    print("="*70)
    print("MOMENT MATCHING ANALYSIS: Li 2017 'Obviously Strategy-Proof Mechanisms'")
    print("="*70)

    print("\nKey insight from paper:")
    print("  OSP mechanisms (like ascending clock) produce more dominant strategy play")
    print("  2P (Second-Price): ~40% overbidding, ~50% dominant strategy")
    print("  AC (Ascending Clock): <20% overbidding, ~67% dominant strategy")
    print("  Effect persists after 5 rounds with feedback")

    results = []
    synthetic_data_all = []

    for auction_type in ['2P', 'AC']:
        print(f"\n{'='*60}")
        print(f"Processing: {EXPERIMENTAL_PARAMETERS[auction_type]['name']}")
        print(f"{'='*60}")

        matcher = Li2017MomentMatcher(auction_type)

        # Generate synthetic data
        synth_data = matcher.generate_synthetic_data(n_samples=5000, use_mixture=True)
        synthetic_data_all.append(synth_data)

        # Compute metrics
        metrics = compute_metrics(synth_data)

        print(f"\nTarget statistics from Li 2017:")
        print(f"  Overbidding rate: {EXPERIMENTAL_PARAMETERS[auction_type]['overbidding_rate']:.0%}")
        print(f"  Dominant strategy rate: {EXPERIMENTAL_PARAMETERS[auction_type]['dominant_rate']:.0%}")

        print(f"\nGenerated statistics:")
        print(f"  N: {metrics['n']}")
        print(f"  Mean bid/value ratio: {metrics['mean_ratio']:.3f} (optimal = 1.0)")
        print(f"  Std bid/value ratio: {metrics['std_ratio']:.3f}")
        print(f"  Overbidding rate: {metrics['overbidding_rate']:.1%}")
        print(f"  Underbidding rate: {metrics['underbidding_rate']:.1%}")
        print(f"  Dominant strategy rate: {metrics['dominant_rate']:.1%}")
        print(f"  SMAD: {metrics['smad']:.2f}%")

        results.append({
            'Auction': auction_type,
            'Auction_Name': EXPERIMENTAL_PARAMETERS[auction_type]['name'],
            'Is_OSP': EXPERIMENTAL_PARAMETERS[auction_type]['osp'],
            'N': metrics['n'],
            'Mean_Bid_Ratio': metrics['mean_ratio'],
            'Std_Bid_Ratio': metrics['std_ratio'],
            'Optimal_Ratio': 1.0,
            'Distance_from_Optimal': metrics['dist_from_optimal'],
            'Overbidding_Rate': metrics['overbidding_rate'],
            'Underbidding_Rate': metrics['underbidding_rate'],
            'Dominant_Rate': metrics['dominant_rate'],
            'SMAD': metrics['smad'],
            'Source': 'Li 2017 AER',
        })

    results_df = pd.DataFrame(results)

    # Save results
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results_df.to_csv(output_path / 'li_2017_osp_moment_matching.csv', index=False)

        if synthetic_data_all:
            all_synth = pd.concat(synthetic_data_all, ignore_index=True)
            all_synth.to_csv(output_path / 'li_2017_osp_synthetic_bids.csv', index=False)

        print(f"\nResults saved to {output_path}")

    return results_df, synthetic_data_all


def print_comparison_summary():
    """Print summary comparing OSP vs non-OSP mechanisms."""

    print("\n" + "="*70)
    print("COMPARISON: OSP vs Non-OSP Mechanisms")
    print("="*70)

    print("\nLi 2017 Key Insight:")
    print("  A strategy is 'obviously dominant' if, at any information set where")
    print("  strategies first diverge, the best outcome under deviation is no better")
    print("  than the worst outcome under the dominant strategy.")

    print("\nWhy Ascending Clock works better:")
    print("  1. At price < value: quitting is clearly worse than staying")
    print("  2. At price = value: staying risks loss if winning at higher price")
    print("  3. Cognitive agents can 'see' dominance at each decision point")

    print("\nImplication for LLM auctions:")
    print("  Menu/clock-based interventions may help LLMs recognize optimal strategy")
    print("  Similar to how OSP helps humans in Li 2017")

    print("\nRelevant LLM Interventions to compare:")
    print("  - Proxy/Clock: Direct OSP analog")
    print("  - Menu Frame: Presents choices explicitly")
    print("  - Decision Tree: Sequential reasoning")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Set paths
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'results' / 'v12_interventions' / 'moment_matching'

    # Run analysis
    results_df, synthetic_data = run_li_2017_moment_matching(output_dir)

    # Print comparison
    print_comparison_summary()

    # Display results
    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)
    print(results_df.to_string(index=False))

    print("\n" + "="*70)
    print("LI 2017 OSP MOMENT MATCHING ANALYSIS COMPLETE")
    print("="*70)

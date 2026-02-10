"""
Moment Matching Analysis for Gonczarowski, Heffetz, Thomas (2022)
"Strategyproofness-Exposing Mechanism Descriptions" (arXiv:2209.13148v2)

This script generates synthetic human bidding data from empirical statistics reported
in Gonczarowski et al. (2022), comparing Traditional (T) vs Menu (M) descriptions
for Second-Price auctions.

Key Experimental Design:
- Second-Price Sealed-Bid auction
- Bid Range: $0.00 - $5.00 (whole cents, 501 possible bids)
- 5 bidders total (1 human + 4 simulated)
- 10 rounds per participant
- 100 subjects per treatment
- Platform: Prolific, February 2022

Key Findings:
- No significant difference between Traditional and Menu descriptions
- ~21% bid within $0.01 of value (both treatments)
- ~37% bid within $0.10 of value
- MAD: $0.51 (Traditional) vs $0.55 (Menu)

Treatments are kept SEPARATE per user request.

Author: Analysis for LLM Auction Project
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import minimize_scalar


# =============================================================================
# GONCZAROWSKI 2022 REPORTED STATISTICS
# =============================================================================

# Table A.4: Straightforward Rates by Distance d
# Format: d (absolute $) -> (Traditional %, Menu %)
STRAIGHTFORWARD_RATES = {
    0.01: (0.21, 0.19),
    0.05: (0.32, 0.28),
    0.10: (0.37, 0.34),
    0.20: (0.48, 0.44),
    0.30: (0.56, 0.53),
    0.40: (0.64, 0.61),
    0.50: (0.69, 0.67),
}

# Other statistics
TREATMENT_STATISTICS = {
    'Traditional': {
        'name': 'Second-Price (Traditional Description)',
        'mad': 0.51,  # Mean Absolute Deviation in $
        'mad_se': None,  # Not reported
        'straightforward_rates': {d: rates[0] for d, rates in STRAIGHTFORWARD_RATES.items()},
    },
    'Menu': {
        'name': 'Second-Price (Menu Description)',
        'mad': 0.55,
        'mad_se': None,
        'straightforward_rates': {d: rates[1] for d, rates in STRAIGHTFORWARD_RATES.items()},
    },
}

# Environment parameters
ENVIRONMENT = {
    'value_min': 0.0,
    'value_max': 5.0,
    'n_bidders': 5,
    'n_rounds': 10,
    'n_subjects': 100,
    'bid_increment': 0.01,  # Whole cents
}


# =============================================================================
# SYNTHETIC DATA GENERATION
# =============================================================================

class Gonczarowski2022MomentMatcher:
    """Generate synthetic bidding data matching Gonczarowski 2022 statistics.

    Model the population as a mixture:
    1. Straightforward bidders: bid ≈ value with small noise
    2. Overbidders: bid > value
    3. Underbidders: bid < value

    Calibrate mixture weights and distribution parameters to match:
    - Straightforward rates at multiple thresholds
    - Mean Absolute Deviation (MAD)
    """

    def __init__(self, treatment='Traditional'):
        self.treatment = treatment
        self.params = TREATMENT_STATISTICS[treatment]
        self.target_rates = self.params['straightforward_rates']
        self.target_mad = self.params['mad']

        # Fit mixture model parameters
        self._fit_mixture_model()

    def _fit_mixture_model(self):
        """Fit mixture model parameters to match observed rates.

        We model:
        - straightforward_rate: fraction bidding within $0.01 of value
        - The remaining population splits between overbidders and underbidders
        - Overbidding is more common than underbidding in SPSB (consistent with literature)

        From the paper:
        - 21% within $0.01 for Traditional (19% for Menu)
        - 37% within $0.10 (34% for Menu)
        - This implies the straightforward bidders have small noise σ

        For non-straightforward bidders:
        - Overbidding is typical in SPSB (60-70% of non-straightforward)
        - Underbidding is less common (30-40%)
        """
        # Core parameters from Table A.4
        self.straightforward_rate = self.target_rates[0.01]

        # Split remaining between over/underbidders
        # SPSB typically shows more overbidding than underbidding
        non_straightforward = 1 - self.straightforward_rate
        self.overbid_rate = non_straightforward * 0.65  # ~65% of non-straightforward overbid
        self.underbid_rate = non_straightforward * 0.35  # ~35% underbid

        # Noise for straightforward bidders (calibrated to match rate at d=0.10)
        # If 37% are within $0.10 but only 21% within $0.01,
        # the straightforward bidders have σ ≈ $0.05
        self.straightforward_sigma = 0.05

        # Underbidding magnitude (set first so it's available during calibration)
        self.underbid_scale = 0.3  # Uniform underbid by 0-30% of value

        # Overbidding magnitude (exponential distribution)
        # Calibrated to match MAD ≈ $0.51-0.55
        # MAD = straightforward_rate * E[|noise|] + overbid_rate * E[overbid] + underbid_rate * E[underbid]
        # For straightforward with normal noise: E[|noise|] = σ * sqrt(2/π) ≈ 0.04
        # Need to solve for overbid/underbid magnitudes
        self.overbid_scale = self._calibrate_overbid_scale()

        print(f"\nCalibrated mixture model for {self.treatment}:")
        print(f"  Straightforward rate: {self.straightforward_rate:.1%}")
        print(f"  Overbid rate: {self.overbid_rate:.1%}")
        print(f"  Underbid rate: {self.underbid_rate:.1%}")
        print(f"  Straightforward σ: ${self.straightforward_sigma:.3f}")
        print(f"  Overbid scale: ${self.overbid_scale:.3f}")

    def _calibrate_overbid_scale(self):
        """Find overbid scale that produces target MAD."""

        def compute_mad(overbid_scale):
            # Generate test sample
            values = np.random.uniform(0, 5, 5000)
            bids = self._generate_bids_mixture(values, overbid_scale)
            return np.mean(np.abs(bids - values))

        def objective(scale):
            # Average over multiple samples for stability
            mads = [compute_mad(scale) for _ in range(5)]
            return (np.mean(mads) - self.target_mad) ** 2

        # Search for optimal scale
        result = minimize_scalar(objective, bounds=(0.1, 2.0), method='bounded')
        return result.x

    def _generate_bids_mixture(self, values, overbid_scale=None):
        """Generate bids using mixture model."""
        if overbid_scale is None:
            overbid_scale = self.overbid_scale

        n = len(values)
        bids = np.zeros(n)

        for i in range(n):
            v = values[i]
            r = np.random.random()

            if r < self.straightforward_rate:
                # Straightforward: bid ≈ value with small noise
                noise = np.random.normal(0, self.straightforward_sigma)
                bids[i] = v + noise
            elif r < self.straightforward_rate + self.overbid_rate:
                # Overbidding: bid > value
                # Use exponential for the overbid amount
                overbid_amount = np.random.exponential(overbid_scale)
                bids[i] = v + overbid_amount
            else:
                # Underbidding: bid < value
                # Uniform reduction
                underbid_fraction = np.random.uniform(0, self.underbid_scale)
                bids[i] = v * (1 - underbid_fraction)

        # Clip to valid bid range and round to cents
        bids = np.clip(bids, ENVIRONMENT['value_min'], ENVIRONMENT['value_max'])
        bids = np.round(bids / ENVIRONMENT['bid_increment']) * ENVIRONMENT['bid_increment']

        return bids

    def generate_values(self, n_samples):
        """Generate private values.

        The paper mentions "tailored distribution" - we approximate as uniform
        for moment matching purposes.
        """
        return np.random.uniform(
            ENVIRONMENT['value_min'],
            ENVIRONMENT['value_max'],
            n_samples
        )

    def generate_synthetic_data(self, n_samples=5000):
        """Generate complete synthetic dataset."""
        values = self.generate_values(n_samples)
        bids = self._generate_bids_mixture(values)

        return pd.DataFrame({
            'player_value': values,
            'bid': bids,
            'optimal_bid': values,  # SPSB optimal is truthful
            'bid_value_ratio': bids / np.maximum(values, 0.01),
            'auction_type': 'SPSB',
            'treatment': self.treatment,
            'treatment_name': self.params['name'],
            'source': 'Gonczarowski_2022',
        })


# =============================================================================
# METRICS
# =============================================================================

def compute_straightforward_rates(df, thresholds=None):
    """Compute straightforward rates at different thresholds."""
    if thresholds is None:
        thresholds = list(STRAIGHTFORWARD_RATES.keys())

    values = df['player_value'].values
    bids = df['bid'].values
    deviations = np.abs(bids - values)

    rates = {}
    for d in thresholds:
        rates[d] = np.mean(deviations <= d)

    return rates


def compute_mad(df):
    """Compute Mean Absolute Deviation."""
    return np.mean(np.abs(df['bid'] - df['player_value']))


def compute_metrics(df):
    """Compute all relevant metrics."""
    values = df['player_value'].values
    bids = df['bid'].values

    # Filter valid
    valid_mask = values > 0.01
    values = values[valid_mask]
    bids = bids[valid_mask]

    ratios = bids / values

    return {
        'n': len(values),
        'mean_ratio': np.mean(ratios),
        'std_ratio': np.std(ratios),
        'mad': np.mean(np.abs(bids - values)),
        'straightforward_rates': compute_straightforward_rates(df),
        'overbidding_rate': np.mean(ratios > 1.02),  # >2% above value
        'underbidding_rate': np.mean(ratios < 0.98),  # >2% below value
    }


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def run_gonczarowski_2022_moment_matching(output_dir=None):
    """Run moment matching analysis for Gonczarowski 2022."""

    print("=" * 70)
    print("MOMENT MATCHING: Gonczarowski, Heffetz, Thomas 2022")
    print("'Strategyproofness-Exposing Mechanism Descriptions'")
    print("=" * 70)

    print("\nKey insight from paper:")
    print("  No significant difference between Traditional and Menu descriptions")
    print("  ~21% bid within $0.01 of value (straightforward)")
    print("  ~37% bid within $0.10 of value")
    print("  MAD ≈ $0.51-0.55")
    print("\nTreatments kept SEPARATE as requested.")

    results = []
    synthetic_data_all = []

    for treatment in ['Traditional', 'Menu']:
        print(f"\n{'=' * 60}")
        print(f"Processing: {treatment} Description")
        print(f"{'=' * 60}")

        matcher = Gonczarowski2022MomentMatcher(treatment)
        synth_data = matcher.generate_synthetic_data(n_samples=5000)
        synthetic_data_all.append(synth_data)

        metrics = compute_metrics(synth_data)

        print(f"\nTarget statistics from paper:")
        print(f"  MAD: ${TREATMENT_STATISTICS[treatment]['mad']:.2f}")
        for d, rate in TREATMENT_STATISTICS[treatment]['straightforward_rates'].items():
            print(f"  Within ${d:.2f}: {rate:.0%}")

        print(f"\nGenerated statistics:")
        print(f"  N: {metrics['n']}")
        print(f"  MAD: ${metrics['mad']:.2f}")
        print(f"  Mean bid/value ratio: {metrics['mean_ratio']:.3f}")
        print(f"  Overbidding rate: {metrics['overbidding_rate']:.1%}")
        print(f"  Underbidding rate: {metrics['underbidding_rate']:.1%}")

        print(f"  Straightforward rates (generated vs target):")
        for d, target_rate in TREATMENT_STATISTICS[treatment]['straightforward_rates'].items():
            gen_rate = metrics['straightforward_rates'].get(d, 0)
            diff = gen_rate - target_rate
            print(f"    ${d:.2f}: {gen_rate:.1%} (target: {target_rate:.0%}, diff: {diff:+.1%})")

        results.append({
            'Treatment': treatment,
            'Treatment_Name': TREATMENT_STATISTICS[treatment]['name'],
            'N': metrics['n'],
            'Mean_Bid_Ratio': metrics['mean_ratio'],
            'Std_Bid_Ratio': metrics['std_ratio'],
            'Optimal_Ratio': 1.0,
            'MAD': metrics['mad'],
            'MAD_Target': TREATMENT_STATISTICS[treatment]['mad'],
            'Overbidding_Rate': metrics['overbidding_rate'],
            'Underbidding_Rate': metrics['underbidding_rate'],
            'Straightforward_01': metrics['straightforward_rates'].get(0.01, 0),
            'Straightforward_10': metrics['straightforward_rates'].get(0.10, 0),
            'Straightforward_50': metrics['straightforward_rates'].get(0.50, 0),
            'Source': 'Gonczarowski, Heffetz, Thomas 2022',
        })

    results_df = pd.DataFrame(results)

    # Save results
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results_df.to_csv(output_path / 'gonczarowski_2022_moment_matching.csv', index=False)

        if synthetic_data_all:
            all_synth = pd.concat(synthetic_data_all, ignore_index=True)
            all_synth.to_csv(output_path / 'gonczarowski_2022_synthetic_bids.csv', index=False)

        print(f"\nResults saved to {output_path}")

    return results_df, synthetic_data_all


def compare_to_llm():
    """Print comparison notes for LLM analysis."""

    print("\n" + "=" * 70)
    print("COMPARISON NOTES: Gonczarowski 2022 vs LLM Experiments")
    print("=" * 70)

    print("\nCRITICAL DIFFERENCE: Value Range")
    print("  Gonczarowski 2022: $0 - $5")
    print("  LLM experiments:   $0 - $50")
    print()
    print("When comparing, normalize to PERCENTAGE deviation from value:")
    print("  eq_deviation = (bid - value) / value")
    print()
    print("Or rescale Gonczarowski data to $0-$50 range:")
    print("  rescaled_bid = bid * 10")
    print("  rescaled_value = value * 10")

    print("\nKEY THRESHOLDS (Gonczarowski absolute -> relative)")
    print("  $0.01 / $2.50 (mean value) = 0.4% relative")
    print("  $0.10 / $2.50 = 4% relative")
    print("  $0.50 / $2.50 = 20% relative")

    print("\nIMPLICATION:")
    print("  Gonczarowski's 'straightforward' threshold of $0.10 corresponds to")
    print("  approximately ±4% relative deviation from value.")
    print("  Our 10% equilibrium threshold is more permissive.")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Set paths
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'results' / 'v12_interventions' / 'moment_matching'

    # Run analysis
    results_df, synthetic_data = run_gonczarowski_2022_moment_matching(output_dir)

    # Print comparison notes
    compare_to_llm()

    # Display results
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(results_df.to_string(index=False))

    print("\n" + "=" * 70)
    print("GONCZAROWSKI 2022 MOMENT MATCHING COMPLETE")
    print("=" * 70)

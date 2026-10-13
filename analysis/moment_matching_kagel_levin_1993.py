"""
Moment Matching Analysis for Kagel-Levin 1993 IPV Paper

This script generates synthetic human bidding data from empirical statistics reported
in Kagel & Levin (1993) "Independent Private Value Auctions" and compares to LLM data.

Key Statistics from Kagel-Levin 1993:
- Environment: Uniform [0, $28.30], n=5 or 10 bidders
- Regression coefficients: b = α + βx
- Bidding frequencies: Pr(b < x), Pr(b = x), Pr(b > x), Pr(b > RNNE)

SMAD Metric: Δ = 100 × E[|b - b*(I)|] / E[b*(I)]

Author: Analysis for LLM Auction Project
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from pathlib import Path


# =============================================================================
# KAGEL-LEVIN 1993 REPORTED STATISTICS
# =============================================================================

# Table 2: OLS Regression Results (b = α + βx)
# Format: (alpha, beta, R2, n_obs, se_alpha, se_beta)
# Note: Papers report standard errors on coefficients. From the paper:
# - Standard errors are in parentheses in Table 2
# - The residual std σ can be derived from R² and variance of bids
REGRESSION_COEFFICIENTS = {
    'FPSB': {
        # From Table 2, Kagel-Levin 1993, page 1283
        # SE in parentheses, approximated from paper
        'n5_pooled': (1.14, 0.92, 0.88, 640, 0.15, 0.01),   # Pooled across sessions
        'n5_exp_1': (0.58, 0.96, 0.93, None, None, None),    # Experienced session 1
        'n5_exp_2': (0.53, 0.94, 0.93, None, None, None),    # Experienced session 2
        'n10_pooled': (0.73, 0.94, 0.93, 720, 0.10, 0.01),  # Pooled across sessions
        'n10_exp_1': (0.27, 0.96, 0.94, None, None, None),   # Experienced session 1
        'n10_exp_2': (0.18, 0.97, 0.95, None, None, None),   # Experienced session 2
    },
    'SPSB': {
        'n5_pooled': (0.23, 1.08, 0.97, 640, 0.08, 0.01),   # From paper
        'n10_pooled': (0.16, 1.05, 0.97, 720, 0.06, 0.01),
    },
    'TPSB': {
        'n5_pooled': (-0.09, 1.25, 0.94, 640, 0.12, 0.01),  # From paper
        'n5_exp': (-0.16, 1.27, 0.96, None, None, None),
        'n10_pooled': (-0.19, 1.23, 0.95, 720, 0.10, 0.01),
        'n10_exp': (-0.22, 1.21, 0.96, None, None, None),
    }
}

# Bidding frequencies from Kagel-Levin 1993 (percentages)
# Format: (below_value, at_value, above_value, above_rnne)
BIDDING_FREQUENCIES = {
    'FPSB': {
        'n5_inexp': (92.6, 7.1, 0.3, 12.5),   # Inexperienced
        'n5_exp': (91.7, 7.9, 0.4, 10.2),     # Experienced
        'n5_pooled': (92.1, 7.5, 0.4, 11.4),  # My calculation from paper
        'n10_inexp': (93.1, 6.6, 0.3, 6.2),
        'n10_exp': (94.0, 5.8, 0.2, 4.5),
        'n10_pooled': (93.5, 6.2, 0.3, 5.4),
    },
    'SPSB': {
        'n5_pooled': (5.7, 27.0, 67.2, 67.2),   # Above value = above RNNE
        'n10_pooled': (4.2, 28.5, 67.3, 67.3),
    },
    'TPSB': {
        'n5_pooled': (4.2, 6.1, 89.8, 27.3),   # Above RNNE is different
        'n5_exp': (3.8, 5.5, 90.7, 24.1),
        'n10_pooled': (3.5, 5.8, 90.7, 19.8),
        'n10_exp': (3.1, 5.2, 91.7, 17.2),
    }
}

# Environment parameters from Kagel-Levin 1993
ENVIRONMENT = {
    'value_min': 0,
    'value_max': 28.30,  # $28.30 in Euros
    'increment': 0.10,   # 10 cent increments
}


# =============================================================================
# THEORETICAL EQUILIBRIUM BID FUNCTIONS
# =============================================================================

def rnne_bid_fpsb(value, n):
    """Risk-Neutral Nash Equilibrium bid for First-Price Sealed-Bid auction.

    b*(v) = (n-1)/n * v

    With n=5: b*(v) = 0.8v
    With n=3: b*(v) = 0.667v
    """
    return ((n - 1) / n) * value


def optimal_bid_spsb(value, n):
    """Dominant strategy bid for Second-Price Sealed-Bid auction.

    b*(v) = v (truthful bidding)
    """
    return value


def rnne_bid_tpsb(value, n):
    """Risk-Neutral Nash Equilibrium bid for Third-Price Sealed-Bid auction.

    b*(v) = (n-1)/(n-2) * v

    With n=5: b*(v) = 4/3 * v = 1.333v
    With n=3: b*(v) = 2v
    """
    if n <= 2:
        raise ValueError("TPSB requires n > 2")
    return ((n - 1) / (n - 2)) * value


# =============================================================================
# MOMENT MATCHING: GENERATE SYNTHETIC DATA
# =============================================================================

class MomentMatcher:
    """Generate synthetic human bidding data via moment matching.

    Model: b = α + βx + ε, where ε ~ N(0, σ²)

    We derive σ from R² using the relationship:
        R² = 1 - Var(ε) / Var(b)
        Var(ε) = (1 - R²) * Var(b)
        σ = sqrt((1 - R²) * Var(b))

    For uniform values on [0, V_max]:
        E[b] = α + β * E[x] = α + β * V_max/2
        Var(b) ≈ β² * Var(x) + Var(ε) = β² * V_max²/12 + σ²

    Solving: σ² = (1 - R²) / R² * β² * V_max²/12
    """

    def __init__(self, auction_type, n_bidders, experience='pooled'):
        self.auction_type = auction_type
        self.n_bidders = n_bidders
        self.experience = experience
        self.key = f'n{n_bidders}_{experience}'

        # Get regression coefficients
        if self.key in REGRESSION_COEFFICIENTS[auction_type]:
            coefs = REGRESSION_COEFFICIENTS[auction_type][self.key]
            self.alpha, self.beta, self.r2 = coefs[0], coefs[1], coefs[2]
            self.n_obs = coefs[3] if len(coefs) > 3 else None
            self.se_alpha = coefs[4] if len(coefs) > 4 else None
            self.se_beta = coefs[5] if len(coefs) > 5 else None
        else:
            raise ValueError(f"No data for {auction_type} {self.key}")

        # Derive residual standard deviation from R²
        # Var(x) = (V_max - V_min)² / 12 for uniform distribution
        v_max = ENVIRONMENT['value_max']
        var_x = v_max**2 / 12

        # From regression: Var(b) = β² * Var(x) + Var(ε)
        # R² = β² * Var(x) / Var(b) = β² * Var(x) / (β² * Var(x) + σ²)
        # Solving for σ²:
        # R² * (β² * Var(x) + σ²) = β² * Var(x)
        # R² * σ² = β² * Var(x) * (1 - R²)
        # σ² = β² * Var(x) * (1 - R²) / R²
        if self.r2 > 0:
            self.sigma = np.sqrt(self.beta**2 * var_x * (1 - self.r2) / self.r2)
        else:
            self.sigma = 2.0  # fallback

        # Get bidding frequencies
        if self.key in BIDDING_FREQUENCIES[auction_type]:
            self.freq_below, self.freq_at, self.freq_above, self.freq_above_rnne = \
                BIDDING_FREQUENCIES[auction_type][self.key]
        else:
            print(f"Warning: No frequency data for {auction_type} {self.key}")
            self.freq_below = self.freq_at = self.freq_above = self.freq_above_rnne = None

        # Equilibrium bid function
        if auction_type == 'FPSB':
            self.rnne_bid = lambda v: rnne_bid_fpsb(v, n_bidders)
        elif auction_type == 'SPSB':
            self.rnne_bid = lambda v: optimal_bid_spsb(v, n_bidders)
        elif auction_type == 'TPSB':
            self.rnne_bid = lambda v: rnne_bid_tpsb(v, n_bidders)

    def generate_values(self, n_samples):
        """Generate random values from uniform distribution."""
        return np.random.uniform(
            ENVIRONMENT['value_min'],
            ENVIRONMENT['value_max'],
            n_samples
        )

    def generate_bids_from_regression(self, values, mu=0, sigma=1, skew=0):
        """Generate bids using the regression model with noise.

        b = α + βx + ε

        If skew=0: ε ~ N(μ, σ²)
        If skew≠0: ε ~ skew-normal with given skewness parameter
        """
        from scipy.stats import skewnorm

        if skew != 0:
            # Skew-normal: negative skew means left-skewed (more underbidding)
            noise = skewnorm.rvs(skew, size=len(values)) * sigma
        else:
            noise = np.random.normal(mu, sigma, len(values))

        bids = self.alpha + self.beta * values + noise

        # Enforce non-negative bids and round to increment
        bids = np.maximum(bids, 0)
        bids = np.round(bids / ENVIRONMENT['increment']) * ENVIRONMENT['increment']

        return bids

    def generate_bids_from_frequencies(self, values):
        """Generate bids matching reported frequency distributions.

        This approach directly samples from distributions that match:
        - Pr(b < v), Pr(b = v), Pr(b > v)
        - Uses the regression line as the conditional mean

        For each value, we sample:
        - With prob p_below: bid uniformly from [0, value)
        - With prob p_at: bid = value
        - With prob p_above: bid uniformly from (value, value * 1.5]
        """
        if self.freq_below is None:
            return self.generate_bids_from_regression(values, self.mu_opt, self.sigma_opt)

        n = len(values)
        bids = np.zeros(n)

        p_below = self.freq_below / 100
        p_at = self.freq_at / 100
        p_above = self.freq_above / 100

        # Normalize in case they don't sum to 1
        p_total = p_below + p_at + p_above
        p_below, p_at, p_above = p_below/p_total, p_at/p_total, p_above/p_total

        for i, v in enumerate(values):
            r = np.random.random()

            if r < p_below:
                # Bid below value: use truncated normal centered on regression
                mean_bid = self.alpha + self.beta * v
                # Sample from regression distribution, reject if >= v
                for _ in range(100):  # max attempts
                    bid = mean_bid + np.random.normal(0, self.sigma)
                    if bid < v:
                        break
                else:
                    bid = v * 0.8  # fallback
            elif r < p_below + p_at:
                # Bid at value
                bid = v
            else:
                # Bid above value
                mean_bid = self.alpha + self.beta * v
                # Sample from regression distribution, reject if <= v
                for _ in range(100):
                    bid = mean_bid + np.random.normal(0, self.sigma)
                    if bid > v:
                        break
                else:
                    bid = v * 1.1  # fallback

            bids[i] = max(0, bid)

        # Round to increment
        bids = np.round(bids / ENVIRONMENT['increment']) * ENVIRONMENT['increment']

        return bids

    def compute_frequencies(self, values, bids):
        """Compute bidding frequencies from simulated data."""
        n = len(values)

        # Frequencies relative to value
        below_value = np.sum(bids < values) / n * 100
        at_value = np.sum(np.isclose(bids, values, atol=ENVIRONMENT['increment']/2)) / n * 100
        above_value = np.sum(bids > values + ENVIRONMENT['increment']/2) / n * 100

        # Frequency above RNNE
        rnne_bids = np.array([self.rnne_bid(v) for v in values])
        above_rnne = np.sum(bids > rnne_bids + ENVIRONMENT['increment']/2) / n * 100

        return below_value, at_value, above_value, above_rnne

    def objective_function(self, params, values, target_freqs, weights=None):
        """Objective function for moment matching optimization.

        Minimize weighted sum of squared differences between
        simulated and target frequencies.
        """
        mu, sigma = params
        if sigma <= 0:
            return 1e10

        # Generate multiple samples for stable estimates (reduced for speed)
        n_bootstrap = 10
        freq_estimates = []

        for _ in range(n_bootstrap):
            bids = self.generate_bids_from_regression(values, mu, sigma)
            freqs = self.compute_frequencies(values, bids)
            freq_estimates.append(freqs)

        mean_freqs = np.mean(freq_estimates, axis=0)

        if weights is None:
            weights = np.ones(len(target_freqs))

        # Weighted sum of squared errors
        error = np.sum(weights * (mean_freqs - np.array(target_freqs))**2)

        return error

    def fit_noise_parameters(self, n_samples=5000, verbose=True, use_skew=True):
        """Derive noise parameters, optionally fitting skew to match frequencies.

        From the regression b = α + βx + ε:
            R² = Var(predicted) / Var(b) = β²Var(x) / (β²Var(x) + σ²)

        Solving for σ:
            σ² = β² * Var(x) * (1 - R²) / R²

        If use_skew=True and frequencies are available, we fit a skew parameter
        to match the reported P(b < x).
        """
        sigma_r2 = self.sigma  # Already computed in __init__
        skew_opt = 0

        # Try to find skew that matches frequencies
        if use_skew and self.freq_below is not None:
            skew_opt = self._fit_skew_parameter(sigma_r2, n_samples)

        if verbose:
            print(f"\n{'='*60}")
            print(f"Moment Matching Results: {self.auction_type} n={self.n_bidders}")
            print(f"{'='*60}")
            print(f"Regression: b = {self.alpha:.2f} + {self.beta:.2f}x + ε")
            print(f"R² = {self.r2:.2f}")
            if self.se_beta is not None:
                print(f"SE(β) = {self.se_beta:.3f}")
            print(f"Residual σ (from R²): {sigma_r2:.3f}")

            if skew_opt != 0:
                print(f"Fitted skew parameter: {skew_opt:.1f}")

            # Show what the regression implies with optimal skew
            values = self.generate_values(n_samples)
            bids = self.generate_bids_from_regression(values, mu=0, sigma=sigma_r2, skew=skew_opt)
            sim_freqs = self.compute_frequencies(values, bids)

            print(f"\nSimulated Frequencies (skew-normal model):")
            print(f"  Below value:  {sim_freqs[0]:.1f}%")
            print(f"  At value:     {sim_freqs[1]:.1f}%")
            print(f"  Above value:  {sim_freqs[2]:.1f}%")
            print(f"  Above RNNE:   {sim_freqs[3]:.1f}%")

            if self.freq_below is not None:
                print(f"\nReported Frequencies (paper):")
                print(f"  Below value:  {self.freq_below:.1f}%")
                print(f"  At value:     {self.freq_at:.1f}%")
                print(f"  Above value:  {self.freq_above:.1f}%")
                print(f"  Above RNNE:   {self.freq_above_rnne:.1f}%")

                # Check match quality
                diff = abs(sim_freqs[0] - self.freq_below)
                if diff < 5:
                    print(f"\n  ✓ Good match to reported frequencies (within {diff:.1f}pp)")
                elif diff < 10:
                    print(f"\n  ~ Moderate match (off by {diff:.1f}pp)")
                else:
                    print(f"\n  ⚠ Poor match (off by {diff:.1f}pp)")

        self.sigma_r2 = sigma_r2
        self.skew_opt = skew_opt
        self.mu_opt = 0.0
        self.sigma_opt = sigma_r2

        return 0.0, sigma_r2

    def _fit_skew_parameter(self, sigma, n_samples=5000):
        """Find skew parameter that matches reported P(b < x)."""
        from scipy.optimize import minimize_scalar

        target = self.freq_below / 100

        def objective(skew):
            values = self.generate_values(n_samples)
            bids = self.generate_bids_from_regression(values, sigma=sigma, skew=skew)
            sim_below = np.sum(bids < values) / len(values)
            return (sim_below - target)**2

        # Search for optimal skew (negative for underbidding auctions)
        # FPSB typically needs negative skew, TPSB/SPSB may need positive
        if self.freq_below > 50:
            # Most bids below value -> need negative skew
            result = minimize_scalar(objective, bounds=(-30, 0), method='bounded')
        else:
            # Most bids above value -> need positive skew
            result = minimize_scalar(objective, bounds=(0, 30), method='bounded')

        return result.x

    def generate_synthetic_data(self, n_samples=1000):
        """Generate synthetic human bidding data using regression with fitted skew.

        Uses b = α + βx + ε where:
        - σ is derived from R²
        - skew is fitted to match reported frequencies
        """
        if not hasattr(self, 'sigma_r2'):
            self.fit_noise_parameters(verbose=False)

        values = self.generate_values(n_samples)
        skew = getattr(self, 'skew_opt', 0)
        bids = self.generate_bids_from_regression(values, mu=0, sigma=self.sigma_r2, skew=skew)

        return pd.DataFrame({
            'value': values,
            'bid': bids,
            'auction_type': self.auction_type,
            'n_bidders': self.n_bidders,
            'source': 'kagel_levin_1993',
            'skew_parameter': skew
        })


# =============================================================================
# SMAD CALCULATION
# =============================================================================

def compute_smad(values, bids, equilibrium_bid_func):
    """Compute SMAD (Scaled Mean Absolute Deviation).

    SMAD = 100 × E[|b - b*(v)|] / E[b*(v)]

    This is the percentage deviation from equilibrium.
    """
    equilibrium_bids = np.array([equilibrium_bid_func(v) for v in values])

    # Avoid division by zero
    mean_eq_bid = np.mean(equilibrium_bids)
    if mean_eq_bid == 0:
        return np.inf

    mean_abs_deviation = np.mean(np.abs(bids - equilibrium_bids))
    smad = 100 * mean_abs_deviation / mean_eq_bid

    return smad


def compute_bid_ratio(values, bids):
    """Compute mean bid/value ratio."""
    # Avoid division by zero for very small values
    valid_mask = values > 0.1
    return np.mean(bids[valid_mask] / values[valid_mask])


# =============================================================================
# COMPARISON WITH LLM DATA
# =============================================================================

def load_llm_data(results_path):
    """Load LLM experiment data from CSV."""
    csv_path = Path(results_path) / 'bid_vs_value_summary.csv'
    if csv_path.exists():
        return pd.read_csv(csv_path)
    else:
        print(f"Warning: Could not find {csv_path}")
        return None


def compare_human_llm(human_data, llm_summary_df, auction_type, n_bidders_llm=3):
    """Compare synthetic human data to LLM experiment results."""

    # Get equilibrium function
    if auction_type == 'FPSB':
        eq_func_human = lambda v: rnne_bid_fpsb(v, human_data['n_bidders'].iloc[0])
        eq_func_llm = lambda v: rnne_bid_fpsb(v, n_bidders_llm)
        optimal_ratio_llm = (n_bidders_llm - 1) / n_bidders_llm  # 2/3 for n=3
    elif auction_type == 'TPSB':
        eq_func_human = lambda v: rnne_bid_tpsb(v, human_data['n_bidders'].iloc[0])
        eq_func_llm = lambda v: rnne_bid_tpsb(v, n_bidders_llm)
        optimal_ratio_llm = (n_bidders_llm - 1) / (n_bidders_llm - 2)  # 2 for n=3
    else:
        eq_func_human = eq_func_llm = lambda v: v
        optimal_ratio_llm = 1.0

    # Compute human metrics
    human_smad = compute_smad(
        human_data['value'].values,
        human_data['bid'].values,
        eq_func_human
    )
    human_bid_ratio = compute_bid_ratio(
        human_data['value'].values,
        human_data['bid'].values
    )
    n_human = human_data['n_bidders'].iloc[0]
    optimal_ratio_human = rnne_bid_fpsb(1, n_human) if auction_type == 'FPSB' else \
                          (rnne_bid_tpsb(1, n_human) if auction_type == 'TPSB' else 1.0)

    # Get LLM metrics from summary (baseline)
    llm_auction = auction_type
    llm_baseline = llm_summary_df[
        (llm_summary_df['Auction'] == llm_auction) &
        (llm_summary_df['Intervention'].str.contains('Baseline', case=False))
    ]

    if len(llm_baseline) == 0:
        print(f"No LLM baseline data found for {auction_type}")
        return None

    llm_bid_ratio = llm_baseline['Mean_Bid_Ratio'].values[0]
    llm_dist_from_opt = llm_baseline['Distance_from_Optimal'].values[0]

    results = {
        'Auction': auction_type,
        'Human_n': n_human,
        'Human_Bid_Ratio': human_bid_ratio,
        'Human_Optimal_Ratio': optimal_ratio_human,
        'Human_SMAD': human_smad,
        'LLM_n': n_bidders_llm,
        'LLM_Bid_Ratio': llm_bid_ratio,
        'LLM_Optimal_Ratio': optimal_ratio_llm,
        'LLM_Dist_from_Optimal': llm_dist_from_opt,
    }

    return results


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def analyze_reconciliation():
    """Analyze possible reconciliations between regression and frequencies."""

    print("\n" + "="*70)
    print("RECONCILIATION ANALYSIS: Can regression match reported frequencies?")
    print("="*70)

    from scipy.stats import norm, skewnorm

    v_max = ENVIRONMENT['value_max']

    # FPSB n=5 case
    alpha, beta, r2 = 1.14, 0.92, 0.88
    freq_below_target = 92.1

    print(f"\nFPSB n=5: b = {alpha} + {beta}x + ε")
    print(f"Target: {freq_below_target}% bid below value")

    # For bid < value across all values:
    # P(b < x) = P(α + βx + ε < x) = P(ε < x(1-β) - α) = P(ε < 0.08x - 1.14)

    # This threshold varies with x:
    # At x=0: threshold = -1.14
    # At x=14.15 (median): threshold = -0.01
    # At x=28.30 (max): threshold = 1.12

    # For uniform x, we need to integrate:
    # P(b < x) = (1/V_max) * ∫₀^V_max P(ε < (1-β)x - α) dx

    # With Gaussian ε ~ N(0, σ²):
    # P(b < x) = (1/V_max) * ∫₀^V_max Φ((0.08x - 1.14)/σ) dx

    # Derive σ from R²
    var_x = v_max**2 / 12
    sigma_r2 = np.sqrt(beta**2 * var_x * (1 - r2) / r2)

    print(f"\nσ from R² = {sigma_r2:.3f}")

    # Compute expected P(b < x) with this σ
    n_samples = 10000
    x_vals = np.linspace(0.01, v_max, n_samples)
    thresholds = (1 - beta) * x_vals - alpha
    prob_below = np.mean(norm.cdf(thresholds / sigma_r2))

    print(f"P(b < x) with Gaussian N(0, {sigma_r2:.2f}²): {prob_below*100:.1f}%")

    # What σ would we need for 92.1%?
    # We need to find σ such that average Φ((0.08x - 1.14)/σ) = 0.921
    print(f"\n--- Checking different σ values ---")
    for sigma_test in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]:
        prob = np.mean(norm.cdf(thresholds / sigma_test))
        print(f"  σ = {sigma_test:.1f}: P(b < x) = {prob*100:.1f}%")

    # The problem: with the regression slope β=0.92, we can't get 92% below value
    # because at high values, the bid is almost as high as value

    print(f"\n--- Analysis ---")
    print("The threshold for b < x is: ε < 0.08x - 1.14")
    print("At low x (near 0): threshold ≈ -1.14 (hard to satisfy)")
    print("At high x (28.3): threshold ≈ +1.12 (easy to satisfy)")
    print("The regression implies many bids ABOVE value at low x!")

    # Check what fraction bid below at different value ranges
    print(f"\n--- P(b < x) by value range (σ = {sigma_r2:.2f}) ---")
    for x_low, x_high in [(0, 5), (5, 10), (10, 15), (15, 20), (20, 28.3)]:
        x_range = np.linspace(x_low + 0.1, x_high, 1000)
        thresh_range = (1 - beta) * x_range - alpha
        prob_range = np.mean(norm.cdf(thresh_range / sigma_r2))
        print(f"  x ∈ [{x_low}, {x_high}]: P(b < x) = {prob_range*100:.1f}%")

    print("\n--- Possible Reconciliations ---")

    # 1. Heteroskedastic errors: σ(x) = σ₀ + σ₁/x (larger variance at low values)
    print("\n1. HETEROSKEDASTICITY: σ varies with x")
    print("   If σ is larger at low values, more mass falls below threshold")

    # 2. Skewed errors
    print("\n2. SKEWED ERRORS: ε ~ skew-normal with negative skew")
    # Try skew-normal
    for skew_param in [-5, -10, -20]:
        samples = skewnorm.rvs(skew_param, size=100000) * sigma_r2
        x_test = np.random.uniform(0, v_max, 100000)
        thresh_test = (1 - beta) * x_test - alpha
        prob_skew = np.mean(samples < thresh_test)
        print(f"   Skew = {skew_param}: P(b < x) = {prob_skew*100:.1f}%")

    # 3. Censored at value (can't bid above value)
    print("\n3. CENSORING: Bids truncated at value")
    print("   If b > x is rounded down to x, 'above value' becomes 'at value'")
    print(f"   Paper reports 7.5% 'at value' - could include truncated overbids")

    # 4. Different subsamples
    print("\n4. SUBSAMPLES: Frequencies may be from different data than regression")
    print("   Regression is OLS on all bids; frequencies might exclude outliers")

    # 5. Median regression
    print("\n5. MEDIAN REGRESSION: If regression is median (not mean), different σ")

    return sigma_r2


def run_full_analysis(output_dir=None):
    """Run complete moment matching analysis for Kagel-Levin 1993."""

    print("="*70)
    print("MOMENT MATCHING ANALYSIS: Kagel-Levin 1993 IPV Paper")
    print("="*70)

    # First run reconciliation analysis
    analyze_reconciliation()

    results = []
    synthetic_data_all = []

    # Run moment matching for each auction type and n
    configs = [
        ('FPSB', 5, 'pooled'),
        ('FPSB', 10, 'pooled'),
        ('SPSB', 5, 'pooled'),
        ('SPSB', 10, 'pooled'),
        ('TPSB', 5, 'pooled'),
        ('TPSB', 10, 'pooled'),
    ]

    for auction_type, n_bidders, exp in configs:
        print(f"\n{'='*60}")
        print(f"Processing: {auction_type} n={n_bidders} ({exp})")
        print(f"{'='*60}")

        try:
            matcher = MomentMatcher(auction_type, n_bidders, exp)
            mu, sigma = matcher.fit_noise_parameters(n_samples=10000)

            if mu is not None:
                # Generate synthetic data from regression
                synth_data = matcher.generate_synthetic_data(n_samples=5000)
                synthetic_data_all.append(synth_data)

                # Compute metrics
                if auction_type == 'FPSB':
                    eq_func = lambda v, n=n_bidders: rnne_bid_fpsb(v, n)
                elif auction_type == 'TPSB':
                    eq_func = lambda v, n=n_bidders: rnne_bid_tpsb(v, n)
                else:
                    eq_func = lambda v: v

                smad = compute_smad(synth_data['value'], synth_data['bid'], eq_func)
                bid_ratio = compute_bid_ratio(synth_data['value'], synth_data['bid'])

                results.append({
                    'Auction': auction_type,
                    'n_bidders': n_bidders,
                    'experience': exp,
                    'alpha': matcher.alpha,
                    'beta': matcher.beta,
                    'mu_noise': mu,
                    'sigma_noise': sigma,
                    'skew': getattr(matcher, 'skew_opt', 0),
                    'Mean_Bid_Ratio': bid_ratio,
                    'SMAD': smad,
                    'Source': 'Kagel-Levin 1993'
                })

                print(f"\nMetrics:")
                print(f"  Mean Bid Ratio: {bid_ratio:.4f}")
                print(f"  SMAD: {smad:.2f}%")

        except Exception as e:
            print(f"Error processing {auction_type} n={n_bidders}: {e}")

    # Create results dataframe
    results_df = pd.DataFrame(results)

    # Save results
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save moment matching results
        results_df.to_csv(output_path / 'kagel_levin_1993_moment_matching.csv', index=False)

        # Save synthetic data
        if synthetic_data_all:
            all_synth = pd.concat(synthetic_data_all, ignore_index=True)
            all_synth.to_csv(output_path / 'kagel_levin_1993_synthetic_bids.csv', index=False)

        print(f"\nResults saved to {output_path}")

    return results_df, synthetic_data_all


def compare_to_llm_experiments(results_df, llm_results_path):
    """Compare Kagel-Levin synthetic data to LLM experiment results."""

    print("\n" + "="*70)
    print("COMPARISON: Human (Kagel-Levin 1993) vs LLM")
    print("="*70)

    llm_summary = load_llm_data(llm_results_path)
    if llm_summary is None:
        return None

    comparison_results = []

    for auction_type in ['FPSB', 'TPSB', 'SPSB']:
        human_data = results_df[results_df['Auction'] == auction_type]

        if len(human_data) == 0:
            continue

        # Use n=5 data (more comparable sample size dynamics)
        human_n5 = human_data[human_data['n_bidders'] == 5]

        if len(human_n5) == 0:
            continue

        # Get LLM baseline for comparison
        llm_baseline = llm_summary[
            (llm_summary['Auction'] == auction_type) &
            (llm_summary['Intervention'].str.contains('Baseline', case=False))
        ]

        if len(llm_baseline) == 0:
            print(f"No LLM baseline for {auction_type}")
            continue

        row = human_n5.iloc[0]

        # Calculate optimal ratios
        if auction_type == 'FPSB':
            human_optimal = (5 - 1) / 5  # 0.8 for n=5
            llm_optimal = (3 - 1) / 3    # 0.667 for n=3
        elif auction_type == 'TPSB':
            human_optimal = (5 - 1) / (5 - 2)  # 1.333 for n=5
            llm_optimal = (3 - 1) / (3 - 2)    # 2.0 for n=3
        else:  # SPSB
            human_optimal = 1.0
            llm_optimal = 1.0

        comparison_results.append({
            'Auction': auction_type,
            'Human_n': 5,
            'Human_Bid_Ratio': row['Mean_Bid_Ratio'],
            'Human_Optimal_Ratio': human_optimal,
            'Human_Pct_of_Optimal': row['Mean_Bid_Ratio'] / human_optimal * 100,
            'Human_SMAD': row['SMAD'],
            'LLM_n': 3,
            'LLM_Bid_Ratio': llm_baseline['Mean_Bid_Ratio'].values[0],
            'LLM_Optimal_Ratio': llm_optimal,
            'LLM_Pct_of_Optimal': llm_baseline['Mean_Bid_Ratio'].values[0] / llm_optimal * 100,
            'LLM_Dist_from_Optimal': llm_baseline['Distance_from_Optimal'].values[0],
        })

    comparison_df = pd.DataFrame(comparison_results)

    # Print formatted comparison
    print("\n" + "="*70)
    print("NORMALIZED COMPARISON (% of Equilibrium Prediction)")
    print("="*70)

    for _, row in comparison_df.iterrows():
        print(f"\n{row['Auction']}:")
        print(f"  Human (n={row['Human_n']}): {row['Human_Pct_of_Optimal']:.1f}% of equilibrium")
        print(f"    Bid ratio: {row['Human_Bid_Ratio']:.3f}, Optimal: {row['Human_Optimal_Ratio']:.3f}")
        print(f"    SMAD: {row['Human_SMAD']:.1f}%")
        print(f"  LLM (n={row['LLM_n']}): {row['LLM_Pct_of_Optimal']:.1f}% of equilibrium")
        print(f"    Bid ratio: {row['LLM_Bid_Ratio']:.3f}, Optimal: {row['LLM_Optimal_Ratio']:.3f}")
        print(f"    Distance from optimal: {row['LLM_Dist_from_Optimal']:.3f}")

        # Interpretation
        human_dev = abs(100 - row['Human_Pct_of_Optimal'])
        llm_dev = abs(100 - row['LLM_Pct_of_Optimal'])
        if llm_dev < human_dev:
            print(f"  → LLMs closer to equilibrium by {human_dev - llm_dev:.1f} pp")
        else:
            print(f"  → Humans closer to equilibrium by {llm_dev - human_dev:.1f} pp")

    return comparison_df


# =============================================================================
# PLOTTING
# =============================================================================

def plot_bid_distributions(synthetic_data_list, output_dir=None):
    """Plot bid distributions for synthetic human data."""

    if not synthetic_data_list:
        return

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    all_data = pd.concat(synthetic_data_list, ignore_index=True)

    for idx, (auction_type, n) in enumerate([
        ('FPSB', 5), ('FPSB', 10),
        ('SPSB', 5), ('SPSB', 10),
        ('TPSB', 5), ('TPSB', 10)
    ]):
        ax = axes[idx]
        subset = all_data[(all_data['auction_type'] == auction_type) &
                          (all_data['n_bidders'] == n)]

        if len(subset) == 0:
            ax.set_visible(False)
            continue

        # Plot bid vs value
        ax.scatter(subset['value'], subset['bid'], alpha=0.3, s=5)

        # Plot 45-degree line (bid = value)
        max_val = ENVIRONMENT['value_max']
        ax.plot([0, max_val], [0, max_val], 'k--', label='bid = value', alpha=0.5)

        # Plot equilibrium
        values = np.linspace(0, max_val, 100)
        if auction_type == 'FPSB':
            eq_bids = rnne_bid_fpsb(values, n)
            label = f'RNNE: b = {(n-1)/n:.2f}v'
        elif auction_type == 'TPSB':
            eq_bids = rnne_bid_tpsb(values, n)
            label = f'RNNE: b = {(n-1)/(n-2):.2f}v'
        else:
            eq_bids = values
            label = 'Optimal: b = v'

        ax.plot(values, eq_bids, 'r-', linewidth=2, label=label)

        ax.set_xlabel('Value ($)')
        ax.set_ylabel('Bid ($)')
        ax.set_title(f'{auction_type} n={n}\nKagel-Levin 1993 (Synthetic)')
        ax.legend(fontsize=8)
        ax.set_xlim(0, max_val)
        ax.set_ylim(0, max_val * 1.5)

    plt.tight_layout()

    if output_dir:
        plt.savefig(Path(output_dir) / 'kagel_levin_1993_bid_distributions.png', dpi=150)
        print(f"Plot saved to {output_dir}")

    plt.show()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Set paths
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'results' / 'v12_interventions' / 'moment_matching'
    llm_results_path = project_root / 'results' / 'v12_interventions' / 'bid_vs_value'

    # Run analysis
    results_df, synthetic_data = run_full_analysis(output_dir)

    # Compare to LLM
    comparison = compare_to_llm_experiments(results_df, llm_results_path)
    if comparison is not None:
        comparison.to_csv(output_dir / 'human_vs_llm_comparison.csv', index=False)

    # Generate plots (skip display on headless)
    import os
    if os.environ.get('DISPLAY') or os.name == 'nt':
        plot_bid_distributions(synthetic_data, output_dir)
    else:
        # Save without display
        import matplotlib
        matplotlib.use('Agg')
        plot_bid_distributions(synthetic_data, output_dir)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

"""
Moment Matching Analysis for Kagel-Levin 1986 Common Value Paper

This script generates synthetic human bidding data from empirical statistics reported
in Kagel & Levin (1986) "The Winner's Curse and Public Information in Common Value Auctions"

Key Statistics from Kagel-Levin 1986 (Table 4, page 17):
- Environment: x_0 ~ U[$25, $225], signals x_i = x_0 + epsilon_i where epsilon_i ~ U[-eps, +eps]
- Regression: b(x_i) = 1.00*x_i - 0.74*eps + 0.65*N (R^2 = 0.99, sigma_u = 4.94)
- Winner's curse: E[x_0 | x_i = max] < x_i

SMAD Metrics:
- Standard SMAD: 100 * E[|b - b*(x)|] / E[b*(x)]
- Signal-range normalized SMAD: 100 * E[|b - b*(x)|] / (2*eps)

RNNE Equilibrium for CV First-Price:
b*(x_i) = E[x_0 | x_i = max, win] = x_i - eps + Y
where Y is a small adjustment term for finite N

Author: Analysis for LLM Auction Project
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from pathlib import Path


# =============================================================================
# KAGEL-LEVIN 1986 REPORTED STATISTICS
# =============================================================================

# Table 4: Regression Results (b = a*x + b*eps + c*N)
# Format: (coef_signal, coef_eps, coef_N, R2, sigma_residual, n_obs)
REGRESSION_COEFFICIENTS = {
    'FP_CV': {
        # From Table 4, Kagel-Levin 1986
        # b(x_i) = 1.00*x_i - 0.74*eps + 0.65*N
        # R^2 = 0.99, sigma_u = 4.94 (residual std)
        'pooled': {
            'coef_signal': 1.00,
            'coef_eps': -0.74,
            'coef_N': 0.65,
            'R2': 0.99,
            'sigma_residual': 4.94,
        },
    },
}

# Environment parameters from Kagel-Levin 1986
# Different epsilon values used in experiments
ENVIRONMENT = {
    'x0_min': 25,       # $25 minimum common value
    'x0_max': 225,      # $225 maximum common value
    'eps_values': [12, 18, 24, 30],  # Different precision conditions
    'N_values': [4, 5, 6, 7],        # Different number of bidders
}


# =============================================================================
# THEORETICAL EQUILIBRIUM BID FUNCTIONS FOR CV
# =============================================================================

def rnne_bid_cv_firstprice(signal, eps, n):
    """Risk-Neutral Nash Equilibrium bid for CV First-Price Sealed-Bid auction.

    The RNNE accounts for winner's curse. Conditional on winning, the winner
    has the highest signal, so the expected common value is less than the signal.

    For symmetric bidders with signals x_i ~ U[x_0 - eps, x_0 + eps]:

    b*(x_i) = E[x_0 | x_i = max_j x_j, win] = x_i - eps + Y(n)

    where Y(n) is a small adjustment that depends on n.

    For large n: Y(n) -> 0, so b*(x) -> x - eps (bid = lower bound of support)
    For n=2: Y(2) = eps/2, so b*(x) = x - eps/2

    General formula: b*(x) = x - eps * (n-1)/n for interior signals

    More precisely, from the paper's equilibrium:
    b*(x_i) = x_i - eps + eps/(n) = x_i - eps*(n-1)/n

    But this assumes bidders shade fully for winner's curse.
    The paper notes that naive bidders often bid E[x_0|x_i] = x_i (ignoring WC).
    """
    # Full RNNE with winner's curse correction
    # b*(x) = x - eps * (n-1)/n
    # This ensures expected profit conditional on winning is non-negative

    # For n bidders, the expected value conditional on having highest signal:
    # E[x_0 | x_i = max] = x_i - eps * (n-1)/n for symmetric uniform signals

    return signal - eps * (n - 1) / n


def naive_bid_cv(signal):
    """Naive bid that ignores winner's curse.

    b_naive(x_i) = E[x_0 | x_i] = x_i

    This is what bidders would bid if they didn't account for the
    selection effect of winning.
    """
    return signal


# =============================================================================
# MOMENT MATCHING: GENERATE SYNTHETIC DATA
# =============================================================================

class CVMomentMatcher:
    """Generate synthetic human bidding data for CV auctions via moment matching.

    Model from Kagel-Levin 1986:
    b(x_i) = a*x_i + b*eps + c*N + u

    where:
    - a, b, c are regression coefficients
    - u ~ N(0, sigma_u^2) is the residual
    """

    def __init__(self, regression_key='pooled'):
        self.params = REGRESSION_COEFFICIENTS['FP_CV'][regression_key]
        self.coef_signal = self.params['coef_signal']
        self.coef_eps = self.params['coef_eps']
        self.coef_N = self.params['coef_N']
        self.R2 = self.params['R2']
        self.sigma_residual = self.params['sigma_residual']

    def generate_signals(self, n_samples, eps, n_bidders=None):
        """Generate random signals from the CV environment.

        x_0 ~ U[x0_min, x0_max]
        x_i = x_0 + epsilon_i where epsilon_i ~ U[-eps, +eps]

        If n_bidders is specified, generates the highest signal (winner).
        """
        # Draw common values
        x0 = np.random.uniform(
            ENVIRONMENT['x0_min'],
            ENVIRONMENT['x0_max'],
            n_samples
        )

        if n_bidders is None:
            # Single signal per observation
            epsilon = np.random.uniform(-eps, eps, n_samples)
            signals = x0 + epsilon
        else:
            # Generate n_bidders signals and take the max (winner's signal)
            signals = np.zeros(n_samples)
            for i in range(n_samples):
                bidder_signals = x0[i] + np.random.uniform(-eps, eps, n_bidders)
                signals[i] = np.max(bidder_signals)

        # Clip to valid range
        signals = np.clip(signals,
                         ENVIRONMENT['x0_min'] - eps,
                         ENVIRONMENT['x0_max'] + eps)

        return signals, x0

    def generate_bids_from_regression(self, signals, eps, N):
        """Generate bids using the regression model.

        b(x_i) = coef_signal * x_i + coef_eps * eps + coef_N * N + u

        where u ~ N(0, sigma_residual^2)
        """
        mean_bid = (self.coef_signal * signals +
                    self.coef_eps * eps +
                    self.coef_N * N)

        noise = np.random.normal(0, self.sigma_residual, len(signals))
        bids = mean_bid + noise

        # Enforce non-negative bids (can't bid negative)
        bids = np.maximum(bids, 0)

        return bids

    def compute_optimal_bids(self, signals, eps, N):
        """Compute RNNE optimal bids accounting for winner's curse."""
        return np.array([rnne_bid_cv_firstprice(s, eps, N) for s in signals])

    def compute_naive_bids(self, signals):
        """Compute naive bids (ignoring winner's curse)."""
        return signals.copy()

    def generate_synthetic_data(self, n_samples=1000, eps=18, N=5):
        """Generate synthetic human bidding data using regression model.

        Args:
            n_samples: Number of bid observations
            eps: Signal precision (smaller = more precise)
            N: Number of bidders
        """
        signals, x0 = self.generate_signals(n_samples, eps)
        bids = self.generate_bids_from_regression(signals, eps, N)
        optimal_bids = self.compute_optimal_bids(signals, eps, N)
        naive_bids = self.compute_naive_bids(signals)

        return pd.DataFrame({
            'common_value': x0,
            'signal': signals,
            'bid': bids,
            'optimal_bid_rnne': optimal_bids,
            'naive_bid': naive_bids,
            'eps': eps,
            'N': N,
            'source': 'kagel_levin_1986',
        })


# =============================================================================
# SMAD CALCULATION (TWO VARIANTS)
# =============================================================================

def compute_smad_standard(signals, bids, optimal_bid_func, eps, N):
    """Compute standard SMAD (Scaled Mean Absolute Deviation).

    SMAD = 100 * E[|b - b*(x)|] / E[b*(x)]

    This is percentage deviation from equilibrium.
    Issue for CV: E[b*(x)] can be large, making SMAD appear small.
    """
    optimal_bids = np.array([optimal_bid_func(s, eps, N) for s in signals])

    # Avoid division by zero
    mean_optimal = np.mean(optimal_bids)
    if mean_optimal <= 0:
        return np.inf

    mean_abs_deviation = np.mean(np.abs(bids - optimal_bids))
    smad = 100 * mean_abs_deviation / mean_optimal

    return smad


def compute_smad_signal_normalized(signals, bids, optimal_bid_func, eps, N):
    """Compute signal-range normalized SMAD.

    SMAD = 100 * E[|b - b*(x)|] / (2 * eps)

    Normalizes by the signal range (2*eps), which represents the
    informativeness of the signal. This allows comparison across
    different precision conditions and auction types.

    Interpretation: How many "signal widths" away from optimal?
    """
    optimal_bids = np.array([optimal_bid_func(s, eps, N) for s in signals])

    if eps <= 0:
        return np.inf

    mean_abs_deviation = np.mean(np.abs(bids - optimal_bids))
    smad = 100 * mean_abs_deviation / (2 * eps)

    return smad


def compute_bid_ratio(signals, bids):
    """Compute mean bid/signal ratio.

    For CV auctions, this shows how close to "naive" bidding.
    Ratio = 1 means bidding signal (naive, ignoring winner's curse).
    """
    valid_mask = signals > 1
    return np.mean(bids[valid_mask] / signals[valid_mask])


def compute_winner_curse_correction(signals, bids, eps, N):
    """Compute how much bidders correct for winner's curse.

    Full correction: bid = signal - eps * (N-1)/N
    No correction (naive): bid = signal

    Returns: fraction of full correction applied
    """
    expected_correction = eps * (N - 1) / N
    actual_underbid = signals - bids

    # Average correction relative to signal
    mean_correction = np.mean(actual_underbid)

    if expected_correction <= 0:
        return 0

    return mean_correction / expected_correction


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def run_cv_moment_matching(output_dir=None):
    """Run complete moment matching analysis for Kagel-Levin 1986 CV paper."""

    print("="*70)
    print("MOMENT MATCHING ANALYSIS: Kagel-Levin 1986 CV Paper")
    print("="*70)

    matcher = CVMomentMatcher()

    # Print regression info
    print(f"\nRegression from paper (Table 4):")
    print(f"b(x_i) = {matcher.coef_signal:.2f}*x_i + ({matcher.coef_eps:.2f})*eps + {matcher.coef_N:.2f}*N + u")
    print(f"R² = {matcher.R2:.2f}, σ_u = {matcher.sigma_residual:.2f}")

    print("\nInterpretation:")
    print("  - Coefficient on signal (1.00): Bids track signals 1-to-1")
    print("  - Coefficient on eps (-0.74): Some winner's curse correction")
    print("    (Full correction would be -1.00)")
    print("  - Coefficient on N (0.65): Bid higher with more bidders")
    print("    (Competition effect dominates additional WC from more bidders)")

    results = []
    synthetic_data_all = []

    # Run for different eps and N combinations
    for eps in [12, 18, 24]:  # Different precision levels
        for N in [4, 6]:  # Different numbers of bidders
            print(f"\n{'='*60}")
            print(f"Processing: eps={eps}, N={N}")
            print(f"{'='*60}")

            # Generate synthetic data
            synth_data = matcher.generate_synthetic_data(
                n_samples=5000, eps=eps, N=N
            )
            synthetic_data_all.append(synth_data)

            # Compute SMAD metrics
            smad_standard = compute_smad_standard(
                synth_data['signal'].values,
                synth_data['bid'].values,
                rnne_bid_cv_firstprice,
                eps, N
            )

            smad_normalized = compute_smad_signal_normalized(
                synth_data['signal'].values,
                synth_data['bid'].values,
                rnne_bid_cv_firstprice,
                eps, N
            )

            bid_ratio = compute_bid_ratio(
                synth_data['signal'].values,
                synth_data['bid'].values
            )

            wc_correction = compute_winner_curse_correction(
                synth_data['signal'].values,
                synth_data['bid'].values,
                eps, N
            )

            # Compute expected values for context
            mean_signal = np.mean(synth_data['signal'])
            mean_bid = np.mean(synth_data['bid'])
            mean_optimal = np.mean(synth_data['optimal_bid_rnne'])
            expected_wc_adj = eps * (N - 1) / N

            print(f"\nMetrics:")
            print(f"  Mean Signal: ${mean_signal:.2f}")
            print(f"  Mean Bid: ${mean_bid:.2f}")
            print(f"  Mean Optimal (RNNE): ${mean_optimal:.2f}")
            print(f"  Expected WC Adjustment: ${expected_wc_adj:.2f}")
            print(f"  Bid/Signal Ratio: {bid_ratio:.4f} (1.0 = naive)")
            print(f"  WC Correction Fraction: {wc_correction:.2%}")
            print(f"\nSMAD Metrics:")
            print(f"  Standard SMAD: {smad_standard:.2f}%")
            print(f"  Signal-Normalized SMAD: {smad_normalized:.2f}%")

            results.append({
                'Auction': 'FP_CV',
                'eps': eps,
                'N': N,
                'coef_signal': matcher.coef_signal,
                'coef_eps': matcher.coef_eps,
                'coef_N': matcher.coef_N,
                'sigma_residual': matcher.sigma_residual,
                'Mean_Signal': mean_signal,
                'Mean_Bid': mean_bid,
                'Mean_Optimal_RNNE': mean_optimal,
                'Bid_Signal_Ratio': bid_ratio,
                'WC_Correction_Fraction': wc_correction,
                'SMAD_Standard': smad_standard,
                'SMAD_Signal_Normalized': smad_normalized,
                'Source': 'Kagel-Levin 1986'
            })

    results_df = pd.DataFrame(results)

    # Save results
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results_df.to_csv(output_path / 'kagel_levin_1986_cv_moment_matching.csv', index=False)

        if synthetic_data_all:
            all_synth = pd.concat(synthetic_data_all, ignore_index=True)
            all_synth.to_csv(output_path / 'kagel_levin_1986_cv_synthetic_bids.csv', index=False)

        print(f"\nResults saved to {output_path}")

    return results_df, synthetic_data_all


def analyze_winner_curse_behavior(output_dir=None):
    """Analyze winner's curse behavior in detail."""

    print("\n" + "="*70)
    print("WINNER'S CURSE ANALYSIS")
    print("="*70)

    matcher = CVMomentMatcher()

    # The key insight from the regression:
    # b = 1.00*x - 0.74*eps + 0.65*N
    #
    # Rearranging: b = x - 0.74*eps + 0.65*N
    #
    # Full RNNE: b* = x - eps*(N-1)/N = x - eps + eps/N
    #
    # For N=5: b* = x - 0.8*eps  (coefficient would be -0.8)
    # For N=6: b* = x - 0.833*eps
    # For N=4: b* = x - 0.75*eps

    print("\nRegression: b = 1.00*x - 0.74*eps + 0.65*N")
    print("\nFull RNNE would be: b* = x - eps*(N-1)/N")
    print("  For N=4: b* = x - 0.75*eps")
    print("  For N=5: b* = x - 0.80*eps")
    print("  For N=6: b* = x - 0.833*eps")
    print("\nObserved coefficient on eps: -0.74")
    print("→ Bidders correct for ~74-99% of theoretical winner's curse")
    print("  (depending on N)")

    print("\nHowever, the +0.65*N term is anomalous for RNNE.")
    print("In RNNE, b* = x - eps + eps/N, so coefficient on N would be +eps/N")
    print("For eps=18: theoretical coef would be +3.6")
    print("Observed: +0.65")
    print("\nThis suggests competition/revenue effects dominate the")
    print("additional winner's curse from more bidders.")

    return matcher


def plot_cv_bid_distributions(synthetic_data_list, output_dir=None):
    """Plot bid distributions for CV synthetic human data."""

    if not synthetic_data_list:
        return

    all_data = pd.concat(synthetic_data_list, ignore_index=True)

    # Get unique eps, N combinations
    configs = all_data.groupby(['eps', 'N']).size().reset_index()
    n_configs = len(configs)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for idx, (_, row) in enumerate(configs.iterrows()):
        if idx >= len(axes):
            break

        ax = axes[idx]
        eps, N = row['eps'], row['N']

        subset = all_data[(all_data['eps'] == eps) & (all_data['N'] == N)]

        # Plot bid vs signal
        ax.scatter(subset['signal'], subset['bid'], alpha=0.2, s=5, label='Bids')

        # Plot optimal (RNNE)
        signals_sorted = np.sort(subset['signal'].unique())
        optimal_bids = [rnne_bid_cv_firstprice(s, eps, N) for s in signals_sorted]
        ax.plot(signals_sorted, optimal_bids, 'r-', linewidth=2, label='RNNE')

        # Plot naive (bid = signal)
        ax.plot(signals_sorted, signals_sorted, 'k--', alpha=0.5, label='Naive (b=x)')

        ax.set_xlabel('Signal')
        ax.set_ylabel('Bid')
        ax.set_title(f'FP CV: eps={eps}, N={N}\nKagel-Levin 1986')
        ax.legend(fontsize=8)

    # Hide unused axes
    for idx in range(n_configs, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()

    if output_dir:
        plt.savefig(Path(output_dir) / 'kagel_levin_1986_cv_bid_distributions.png', dpi=150)
        print(f"Plot saved to {output_dir}")

    plt.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Set paths
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'results' / 'v12_interventions' / 'moment_matching'

    # Run analysis
    results_df, synthetic_data = run_cv_moment_matching(output_dir)

    # Analyze winner's curse behavior
    analyze_winner_curse_behavior(output_dir)

    # Generate plots
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    plot_cv_bid_distributions(synthetic_data, output_dir)

    print("\n" + "="*70)
    print("CV MOMENT MATCHING ANALYSIS COMPLETE")
    print("="*70)
    print("\nKey findings from Kagel-Levin 1986:")
    print("1. Bidders track signals 1-to-1 (coef = 1.00)")
    print("2. Partial winner's curse correction (coef_eps = -0.74)")
    print("3. Competition effect dominates additional WC (coef_N = +0.65)")
    print("\nSMAD metrics computed with both denominators:")
    print("- Standard: E[b*] in denominator")
    print("- Signal-normalized: 2*eps in denominator")

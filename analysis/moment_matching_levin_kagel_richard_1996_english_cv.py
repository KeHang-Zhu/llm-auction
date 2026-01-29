"""
Moment Matching Analysis for Levin-Kagel-Richard 1996 English CV Paper

This script generates synthetic human bidding data from empirical statistics reported
in Levin, Kagel & Richard (1996) "Revenue Effects and Information Processing in
English Common Value Auctions" (AER)

Key Statistics from LKR 1996:
- Environment: x_0 ~ U[$50, $250], signals x_i = x_0 + epsilon_i where epsilon_i ~ U[-eps, +eps]
- English (ascending clock) auction with irrevocable exit
- Bidders use "signal-averaging rule": average own signal with dropout prices

The paper finds that bidders follow a signal-averaging heuristic rather than
full Nash equilibrium bidding. The key behavioral model is:

    gamma_ij = (1/j) * x_i + ((j-1)/j) * d_{j-1}

where:
- gamma_ij is bidder i's reservation price in round j
- x_i is bidder i's private signal
- d_{j-1} is the previous dropout price

For the FIRST dropout (j=1), the bid depends only on own signal:
    d_1 = alpha_1 + beta_1 * x_1 + epsilon

From Tables 5 and 6:
- beta_1 ~ 1.0 (bidders bid approximately their signal)
- R^2 ~ 0.97-0.999

SMAD Metrics:
- Standard SMAD: 100 * E[|b - b*(x)|] / E[b*(x)]
- Signal-range normalized SMAD: 100 * E[|b - b*(x)|] / (2*eps)

RNNE for English CV: The equilibrium dropout price reveals the signal value.
The winner pays the second-highest signal value (approximately).
Optimal strategy: drop out when price = E[x_0 | own signal, dropout info]

Author: Analysis for LLM Auction Project
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from pathlib import Path


# =============================================================================
# LEVIN-KAGEL-RICHARD 1996 REPORTED STATISTICS
# =============================================================================

# Environment parameters from LKR 1996
ENVIRONMENT = {
    'x0_min': 50,       # $50 minimum common value
    'x0_max': 250,      # $250 maximum common value
    'eps_values': [6, 12, 18, 24, 30],  # Different precision conditions
    'N_values': [4, 7],  # Number of bidders
}

# From Tables 5 and 6: OLS estimates for drop-out prices
# The first dropout (d_1k) depends only on own signal
# d_1k = alpha + beta * x_1k + epsilon
#
# Table 5 (n=4):
#   Super-experienced: alpha=1.16, beta=0.99, R2=0.915
#   One-time exp:      alpha=-0.62, beta=1.01, R2=0.987
#   Inexperienced:     alpha=0.66, beta=1.00, R2=0.987
#
# Table 6 (n=7):
#   Super-experienced: alpha=-4.21, beta=0.97, R2=0.971
#   One-time exp:      alpha=-2.22, beta=1.00, R2=0.962
#   Inexperienced:     alpha=-3.39, beta=1.03, R2=0.979

REGRESSION_COEFFICIENTS = {
    'English_CV': {
        # First dropout regression: d_1 = alpha + beta * x + epsilon
        # Format: (alpha, beta, R2, sigma_residual_approx)
        'n4_super_exp': {
            'alpha': 1.16,
            'beta': 0.99,
            'R2': 0.915,
            'sigma_residual': 8.0,  # Approximated from SE
        },
        'n4_one_time_exp': {
            'alpha': -0.62,
            'beta': 1.01,
            'R2': 0.987,
            'sigma_residual': 4.0,
        },
        'n4_inexperienced': {
            'alpha': 0.66,
            'beta': 1.00,
            'R2': 0.987,
            'sigma_residual': 4.0,
        },
        'n7_super_exp': {
            'alpha': -4.21,
            'beta': 0.97,
            'R2': 0.971,
            'sigma_residual': 6.0,
        },
        'n7_one_time_exp': {
            'alpha': -2.22,
            'beta': 1.00,
            'R2': 0.962,
            'sigma_residual': 7.0,
        },
        'n7_inexperienced': {
            'alpha': -3.39,
            'beta': 1.03,
            'R2': 0.979,
            'sigma_residual': 5.0,
        },
        # Pooled estimates (weighted average)
        'n4_pooled': {
            'alpha': 0.40,
            'beta': 1.00,
            'R2': 0.96,
            'sigma_residual': 5.5,
        },
        'n7_pooled': {
            'alpha': -3.27,
            'beta': 1.00,
            'R2': 0.97,
            'sigma_residual': 6.0,
        },
    },
}

# Signal-averaging rule coefficients from Tables 5 and 6
# For round j > 1: gamma_ij = lambda_j * x_i + mu_j * d_{j-1}
# Under signal-averaging: lambda_j = 1/j, mu_j = (j-1)/j
SIGNAL_AVERAGING = {
    'n4': {
        # From Table 5 - coefficients on x_ik and d_{j-1}
        'round_2': {'lambda': 0.80, 'mu': 0.80},   # Theory: 0.5, 0.5
        'round_3': {'lambda': 0.17, 'mu': 0.76},   # Theory: 0.33, 0.67
        'round_4': {'lambda': 0.07, 'mu': 0.07},   # Last bidder
    },
    'n7': {
        # From Table 6 - coefficients on x_ik and d_{j-1}
        'round_2': {'lambda': 0.56, 'mu': 0.56},
        'round_3': {'lambda': 0.15, 'mu': 0.49},
        'round_4': {'lambda': 0.26, 'mu': 0.73},
        'round_5': {'lambda': 0.20, 'mu': 0.20},
        'round_6': {'lambda': 0.44, 'mu': 0.02},
    },
}


# =============================================================================
# THEORETICAL EQUILIBRIUM BID FUNCTIONS FOR ENGLISH CV
# =============================================================================

def rnne_dropout_english_cv(signal, eps, n, x0_min, x0_max):
    """Risk-Neutral Nash Equilibrium dropout price for English CV auction.

    In English CV with symmetric RNNE, the dropout price reveals signal value.

    The first bidder to drop out does so at a price where they are indifferent
    between winning and losing. Given their signal x_1 (the lowest), they know
    the item value is in [x_1 - eps, x_1 + eps].

    Under symmetric equilibrium with signal-averaging interpretation:
    - Each bidder drops at price = average of all revealed signals + own signal
    - For the first dropout: d_1* = x_1 (approximately)

    More precisely, the equilibrium involves dropping when:
    d* = E[x_0 | x_i, winning means having highest signal]

    For the lowest bidder (first to drop), this is approximately:
    d_1* = x_1 - eps + eps/n  (similar to first-price sealed bid)

    But in English auctions, the equilibrium is for dropout price to equal
    the signal value (since this reveals information to others).

    We use d*(x) = x as the benchmark (signal-revealing equilibrium).
    """
    # In English CV, the equilibrium dropout reveals the signal
    # This is because continuing past your signal risks paying more than x_0
    return signal


def signal_averaging_dropout(signal, dropout_prices, round_j):
    """Compute dropout price using signal-averaging heuristic.

    gamma_ij = (1/j) * x_i + ((j-1)/j) * d_{j-1}

    This is what the paper finds bidders actually do.
    """
    if round_j == 1 or len(dropout_prices) == 0:
        return signal

    j = round_j
    lambda_j = 1.0 / j
    mu_j = (j - 1) / j

    # Average of previous dropout prices
    avg_dropout = np.mean(dropout_prices)

    return lambda_j * signal + mu_j * avg_dropout


# =============================================================================
# MOMENT MATCHING: GENERATE SYNTHETIC DATA
# =============================================================================

class EnglishCVMomentMatcher:
    """Generate synthetic human bidding data for English CV auctions.

    Model from LKR 1996:
    For first dropout: d_1 = alpha + beta * x_1 + epsilon

    The paper finds beta ~ 1.0, meaning bidders approximately reveal
    their signal value when they drop out.
    """

    def __init__(self, n_bidders, experience='pooled'):
        self.n_bidders = n_bidders
        self.experience = experience
        self.key = f'n{n_bidders}_{experience}'

        if self.key in REGRESSION_COEFFICIENTS['English_CV']:
            params = REGRESSION_COEFFICIENTS['English_CV'][self.key]
            self.alpha = params['alpha']
            self.beta = params['beta']
            self.R2 = params['R2']
            self.sigma_residual = params['sigma_residual']
        else:
            # Default to pooled
            self.key = f'n{n_bidders}_pooled'
            params = REGRESSION_COEFFICIENTS['English_CV'][self.key]
            self.alpha = params['alpha']
            self.beta = params['beta']
            self.R2 = params['R2']
            self.sigma_residual = params['sigma_residual']

    def generate_signals(self, n_samples, eps):
        """Generate random signals from the CV environment.

        x_0 ~ U[x0_min, x0_max]
        x_i = x_0 + epsilon_i where epsilon_i ~ U[-eps, +eps]
        """
        x0 = np.random.uniform(
            ENVIRONMENT['x0_min'],
            ENVIRONMENT['x0_max'],
            n_samples
        )

        epsilon = np.random.uniform(-eps, eps, n_samples)
        signals = x0 + epsilon

        # Clip to valid range
        signals = np.clip(signals,
                         ENVIRONMENT['x0_min'] - eps,
                         ENVIRONMENT['x0_max'] + eps)

        return signals, x0

    def generate_dropouts_from_regression(self, signals, eps):
        """Generate first-round dropout prices using regression model.

        d_1 = alpha + beta * x + epsilon
        """
        mean_dropout = self.alpha + self.beta * signals
        noise = np.random.normal(0, self.sigma_residual, len(signals))
        dropouts = mean_dropout + noise

        # Enforce reasonable bounds
        dropouts = np.maximum(dropouts, ENVIRONMENT['x0_min'] - 2*eps)

        return dropouts

    def compute_optimal_dropouts(self, signals):
        """Compute RNNE optimal dropout prices.

        In English CV, optimal dropout = signal (reveals information).
        """
        return signals.copy()

    def generate_synthetic_data(self, n_samples=1000, eps=18):
        """Generate synthetic human bidding data using regression model."""

        signals, x0 = self.generate_signals(n_samples, eps)
        dropouts = self.generate_dropouts_from_regression(signals, eps)
        optimal_dropouts = self.compute_optimal_dropouts(signals)

        return pd.DataFrame({
            'common_value': x0,
            'signal': signals,
            'dropout_price': dropouts,  # This is the "bid" in English auction
            'optimal_dropout': optimal_dropouts,
            'eps': eps,
            'N': self.n_bidders,
            'experience': self.experience,
            'source': 'levin_kagel_richard_1996',
        })


# =============================================================================
# SMAD CALCULATION (TWO VARIANTS)
# =============================================================================

def compute_smad_standard(signals, dropouts, optimal_dropout_func, eps, N):
    """Compute standard SMAD.

    SMAD = 100 * E[|d - d*(x)|] / E[d*(x)]

    For English CV, d*(x) = x (signal-revealing equilibrium).
    """
    optimal_dropouts = np.array([optimal_dropout_func(s) for s in signals])

    mean_optimal = np.mean(optimal_dropouts)
    if mean_optimal <= 0:
        return np.inf

    mean_abs_deviation = np.mean(np.abs(dropouts - optimal_dropouts))
    smad = 100 * mean_abs_deviation / mean_optimal

    return smad


def compute_smad_signal_normalized(signals, dropouts, optimal_dropout_func, eps, N):
    """Compute signal-range normalized SMAD.

    SMAD = 100 * E[|d - d*(x)|] / (2 * eps)
    """
    optimal_dropouts = np.array([optimal_dropout_func(s) for s in signals])

    if eps <= 0:
        return np.inf

    mean_abs_deviation = np.mean(np.abs(dropouts - optimal_dropouts))
    smad = 100 * mean_abs_deviation / (2 * eps)

    return smad


def compute_dropout_ratio(signals, dropouts):
    """Compute mean dropout/signal ratio.

    Ratio = 1 means dropping at signal (optimal in English CV).
    """
    valid_mask = signals > 1
    return np.mean(dropouts[valid_mask] / signals[valid_mask])


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def run_english_cv_moment_matching(output_dir=None):
    """Run complete moment matching analysis for LKR 1996 English CV paper."""

    print("="*70)
    print("MOMENT MATCHING ANALYSIS: Levin-Kagel-Richard 1996 English CV Paper")
    print("="*70)

    print("\nKey insight from paper:")
    print("  Bidders use 'signal-averaging' heuristic, not full Nash equilibrium")
    print("  First dropout: d_1 = alpha + beta * x_1 + epsilon")
    print("  beta ~ 1.0 means dropouts approximately reveal signal values")
    print("  This is close to optimal behavior in English CV auctions")

    results = []
    synthetic_data_all = []

    # Run for different n and eps combinations
    for n in [4, 7]:
        for eps in [12, 18, 24]:
            for exp in ['pooled']:
                print(f"\n{'='*60}")
                print(f"Processing: English CV, n={n}, eps={eps}, experience={exp}")
                print(f"{'='*60}")

                try:
                    matcher = EnglishCVMomentMatcher(n, exp)

                    print(f"\nRegression: d_1 = {matcher.alpha:.2f} + {matcher.beta:.2f}*x + epsilon")
                    print(f"R² = {matcher.R2:.3f}, σ_residual = {matcher.sigma_residual:.2f}")

                    # Generate synthetic data
                    synth_data = matcher.generate_synthetic_data(
                        n_samples=5000, eps=eps
                    )
                    synthetic_data_all.append(synth_data)

                    # Compute SMAD metrics
                    # For English CV, optimal dropout = signal
                    optimal_func = lambda x: x

                    smad_standard = compute_smad_standard(
                        synth_data['signal'].values,
                        synth_data['dropout_price'].values,
                        optimal_func,
                        eps, n
                    )

                    smad_normalized = compute_smad_signal_normalized(
                        synth_data['signal'].values,
                        synth_data['dropout_price'].values,
                        optimal_func,
                        eps, n
                    )

                    dropout_ratio = compute_dropout_ratio(
                        synth_data['signal'].values,
                        synth_data['dropout_price'].values
                    )

                    # Compute expected values
                    mean_signal = np.mean(synth_data['signal'])
                    mean_dropout = np.mean(synth_data['dropout_price'])
                    mean_optimal = np.mean(synth_data['optimal_dropout'])

                    print(f"\nMetrics:")
                    print(f"  Mean Signal: ${mean_signal:.2f}")
                    print(f"  Mean Dropout Price: ${mean_dropout:.2f}")
                    print(f"  Mean Optimal Dropout: ${mean_optimal:.2f}")
                    print(f"  Dropout/Signal Ratio: {dropout_ratio:.4f} (1.0 = optimal)")
                    print(f"\nSMAD Metrics:")
                    print(f"  Standard SMAD: {smad_standard:.2f}%")
                    print(f"  Signal-Normalized SMAD: {smad_normalized:.2f}%")

                    results.append({
                        'Auction': 'English_CV',
                        'eps': eps,
                        'N': n,
                        'experience': exp,
                        'alpha': matcher.alpha,
                        'beta': matcher.beta,
                        'R2': matcher.R2,
                        'sigma_residual': matcher.sigma_residual,
                        'Mean_Signal': mean_signal,
                        'Mean_Dropout': mean_dropout,
                        'Mean_Optimal': mean_optimal,
                        'Dropout_Signal_Ratio': dropout_ratio,
                        'SMAD_Standard': smad_standard,
                        'SMAD_Signal_Normalized': smad_normalized,
                        'Source': 'Levin-Kagel-Richard 1996'
                    })

                except Exception as e:
                    print(f"Error processing n={n}, eps={eps}: {e}")

    results_df = pd.DataFrame(results)

    # Save results
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results_df.to_csv(output_path / 'levin_kagel_richard_1996_english_cv_moment_matching.csv', index=False)

        if synthetic_data_all:
            all_synth = pd.concat(synthetic_data_all, ignore_index=True)
            all_synth.to_csv(output_path / 'levin_kagel_richard_1996_english_cv_synthetic_bids.csv', index=False)

        print(f"\nResults saved to {output_path}")

    return results_df, synthetic_data_all


def compare_fp_vs_english_cv():
    """Compare First-Price CV (KL86) vs English CV (LKR96) behavior."""

    print("\n" + "="*70)
    print("COMPARISON: First-Price CV vs English CV")
    print("="*70)

    print("\nFirst-Price CV (Kagel-Levin 1986):")
    print("  b(x) = 1.00*x - 0.74*eps + 0.65*N")
    print("  Bidders partially correct for winner's curse (74% correction)")
    print("  Competition effect (+0.65*N) dominates additional WC")

    print("\nEnglish CV (Levin-Kagel-Richard 1996):")
    print("  d_1(x) = alpha + 1.00*x")
    print("  First dropout approximately equals signal (beta ~ 1.0)")
    print("  Signal-averaging rule for subsequent rounds")
    print("  English auctions help overcome winner's curse through")
    print("  information revelation from dropout prices")

    print("\nKey Behavioral Difference:")
    print("  FP: Bidders must explicitly correct for WC (partial success)")
    print("  English: Dropout prices reveal signals, providing 'public info'")
    print("  that helps bidders avoid the curse")


def plot_english_cv_distributions(synthetic_data_list, output_dir=None):
    """Plot dropout distributions for English CV synthetic data."""

    if not synthetic_data_list:
        return

    all_data = pd.concat(synthetic_data_list, ignore_index=True)

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

        # Plot dropout vs signal
        ax.scatter(subset['signal'], subset['dropout_price'], alpha=0.2, s=5, label='Dropouts')

        # Plot optimal (dropout = signal)
        signals_sorted = np.sort(subset['signal'].unique())
        ax.plot(signals_sorted, signals_sorted, 'r-', linewidth=2, label='Optimal (d=x)')

        ax.set_xlabel('Signal')
        ax.set_ylabel('Dropout Price')
        ax.set_title(f'English CV: eps={eps}, N={N}\nLKR 1996')
        ax.legend(fontsize=8)

    for idx in range(n_configs, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()

    if output_dir:
        plt.savefig(Path(output_dir) / 'levin_kagel_richard_1996_english_cv_distributions.png', dpi=150)
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
    results_df, synthetic_data = run_english_cv_moment_matching(output_dir)

    # Compare FP vs English CV
    compare_fp_vs_english_cv()

    # Generate plots
    import matplotlib
    matplotlib.use('Agg')
    plot_english_cv_distributions(synthetic_data, output_dir)

    print("\n" + "="*70)
    print("ENGLISH CV MOMENT MATCHING ANALYSIS COMPLETE")
    print("="*70)
    print("\nKey findings from Levin-Kagel-Richard 1996:")
    print("1. First dropout price ~ signal (beta ~ 1.0)")
    print("2. Signal-averaging rule characterizes subsequent rounds")
    print("3. English auctions help bidders avoid winner's curse")
    print("4. Revenue effects depend on experience level")
    print("\nSMAD metrics computed with both denominators:")
    print("- Standard: E[d*] in denominator")
    print("- Signal-normalized: 2*eps in denominator")

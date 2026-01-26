"""
Monte Carlo DGP to reconstruct bid distributions from Kagel & Levin (1993) Table 2
(rows 1, 2 pooled, 3 pooled; N=5), then compute MAD and SE.

Goal:
- Use the table's regression form b = alpha + beta * x + eps
- Calibrate eps ~ Normal(mu, sigma) so that the model matches TWO moments from Table 2:
    (i)   P(b > x)      (bidding frequencies relative to X)
    (ii)  P(b > RNNE)   (bidding frequencies relative to RNNE)
- Then run MC (R=100) to compute MAD = E[|b - b*|] and its SE.

Notes:
- For SPA (2nd-price), theoretical optimum is truthful: b*(x)=x.
- For FPA (1st-price, IPV, N=5), RNNE: b*(x)=((N-1)/N)*x = 0.8 x.
- For TPA (3rd-price, IPV, N=5), RNNE: b*(x)=((N-1)/(N-2))*x = 4/3 x.
- x is treated as uniform on [0, x_max]. (KL93 uses x in [0, 28.30].)
"""

import numpy as np
from dataclasses import dataclass
from scipy.stats import norm
from scipy.integrate import quad
from scipy.optimize import root

# ----------------------------
# 1) Inputs from Table 2 (N=5)
# ----------------------------

@dataclass
class SeriesSpec:
    name: str
    alpha: float
    beta: float
    beta_star: float          # RNNE slope (or truthful slope=1)
    target_p_gt_x: float      # from "Bidding frequencies relative to X": % bids > x
    target_p_gt_rnne: float   # from "Bidding frequencies relative to RNNE": % bids > RNNE
    x_max: float = 28.30      # KL93 value support upper bound (adjust if needed)


# Row 1 (series 1): alpha=1.14, beta=0.92; >x = 0.4%; >RNNE = 77.9%
# Row 2 pooled (series 2 pooled): alpha=1.08, beta=1.02; >x = 67.2%; >RNNE = 67.2%
# Row 3 pooled (series 3 pooled): alpha=2.44, beta=1.15; >x = 89.8%; >RNNE = 38.0%
series_list = [
    SeriesSpec(
        name="1 (FPA-like; row 1)",
        alpha=1.14, beta=0.92,
        beta_star=4/5,               # (N-1)/N with N=5
        target_p_gt_x=0.004,
        target_p_gt_rnne=0.779
    ),
    SeriesSpec(
        name="2 pooled (SPA; row 2 pooled)",
        alpha=1.08, beta=1.02,
        beta_star=1.0,               # truthful slope
        target_p_gt_x=0.672,
        target_p_gt_rnne=0.672
    ),
    SeriesSpec(
        name="3 pooled (TPA; row 3 pooled)",
        alpha=2.44, beta=1.15,
        beta_star=4/3,               # (N-1)/(N-2) with N=5
        target_p_gt_x=0.898,
        target_p_gt_rnne=0.380
    ),
]

# ----------------------------
# 2) Moment equations (analytic integration over x ~ U[0, x_max])
# ----------------------------

def avg_prob_gt_threshold(alpha, beta, mu, sigma, x_max, threshold_slope, threshold_intercept=0.0):
    """
    Compute E_x [ P( alpha + beta x + eps > threshold_intercept + threshold_slope x ) ]
    where eps ~ N(mu, sigma^2), x ~ Uniform(0, x_max).
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    # For a given x:
    # P(b > thr) = 1 - Phi( (thr(x) - (alpha+beta x + mu)) / sigma )
    def integrand(x):
        thr = threshold_intercept + threshold_slope * x
        z = (thr - (alpha + beta * x + mu)) / sigma
        return 1.0 - norm.cdf(z)

    val, _ = quad(integrand, 0.0, x_max, limit=200)
    return val / x_max


def calibrate_mu_sigma(spec: SeriesSpec):
    """
    Calibrate (mu, sigma) to match:
      p1 = P(b > x)
      p2 = P(b > RNNE(x)=beta_star x)
    using nonlinear root finding.
    """
    alpha, beta, x_max = spec.alpha, spec.beta, spec.x_max
    beta_star = spec.beta_star
    targ1, targ2 = spec.target_p_gt_x, spec.target_p_gt_rnne

    # Solve in variables (mu, log_sigma) to keep sigma>0
    def F(theta):
        mu = theta[0]
        sigma = np.exp(theta[1])

        p_gt_x = avg_prob_gt_threshold(alpha, beta, mu, sigma, x_max, threshold_slope=1.0)
        p_gt_rnne = avg_prob_gt_threshold(alpha, beta, mu, sigma, x_max, threshold_slope=beta_star)

        return np.array([p_gt_x - targ1, p_gt_rnne - targ2])

    # Heuristic init: small negative mu and moderate sigma
    theta0 = np.array([0.0, np.log(2.0)])

    sol = root(F, theta0, method="hybr")
    if not sol.success:
        raise RuntimeError(f"Calibration failed for {spec.name}: {sol.message}")

    mu_hat = sol.x[0]
    sigma_hat = float(np.exp(sol.x[1]))
    return mu_hat, sigma_hat


# ----------------------------
# 3) Monte Carlo: compute MAD and SE (R=100)
# ----------------------------

def simulate_mad(spec: SeriesSpec, mu, sigma, n_obs=5000, rng=None):
    """
    Draw x ~ U[0, x_max], eps ~ N(mu, sigma), b = alpha + beta x + eps
    Compute MAD = mean(|b - b*(x)|), where b*(x)=beta_star x for FPA/TPA and =x for SPA.
    """
    if rng is None:
        rng = np.random.default_rng()

    x = rng.uniform(0.0, spec.x_max, size=n_obs)
    eps = rng.normal(mu, sigma, size=n_obs)
    b = spec.alpha + spec.beta * x + eps

    # theoretical optimum bid function (RNNE/truthful)
    b_star = spec.beta_star * x if spec.beta_star != 1.0 else x

    d = np.abs(b - b_star)
    mad_hat = float(d.mean())

    # within-sample SE of MAD (optional; not the MC SE across repetitions)
    se_hat = float(d.std(ddof=1) / np.sqrt(n_obs))
    return mad_hat, se_hat


def run_mc(series_list, R=100, n_obs=5000, seed=123):
    rng = np.random.default_rng(seed)
    out = {}

    for spec in series_list:
        mu_hat, sigma_hat = calibrate_mu_sigma(spec)
        mads = []
        ses_within = []

        for r in range(R):
            mad_r, se_r = simulate_mad(spec, mu_hat, sigma_hat, n_obs=n_obs, rng=rng)
            mads.append(mad_r)
            ses_within.append(se_r)

        mads = np.array(mads)
        ses_within = np.array(ses_within)

        # Monte Carlo SE of MAD estimate across R replications
        se_mc = float(mads.std(ddof=1))

        out[spec.name] = {
            "calibrated_mu": float(mu_hat),
            "calibrated_sigma": float(sigma_hat),
            "MAD_mean_over_MC": float(mads.mean()),
            "MAD_MC_SE": se_mc,                          # variability across MC runs
            "avg_within_sample_SE": float(ses_within.mean()),
            "R": R,
            "n_obs_per_run": n_obs,
        }

    return out


if __name__ == "__main__":
    results = run_mc(series_list, R=100, n_obs=5000, seed=1)

    # Pretty print
    for k, v in results.items():
        print(f"\n=== Series {k} ===")
        print(f"mu={v['calibrated_mu']:.4f}, sigma={v['calibrated_sigma']:.4f}")
        print(f"MAD (mean over {v['R']} MC runs) = {v['MAD_mean_over_MC']:.4f}")
        print(f"MC SE (std of MAD across runs)   = {v['MAD_MC_SE']:.4f}")
        print(f"Avg within-sample SE of MAD      = {v['avg_within_sample_SE']:.4f}")

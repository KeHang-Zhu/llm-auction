#!/usr/bin/env python3
"""Shows that the Kagel & Levin (1993) moments conflict (paper Sec. 2.1, sec:kl93_conflict).

For N=5, takes the reported bid regression b = alpha + beta*x with its R^2, derives the
residual sd sigma^2 = beta^2 Var(x) (1-R^2)/R^2 for x ~ U[0, 28.30], and reports the
below/at/above-value shares and the SMAD that this linear-Gaussian model implies,
next to the shares the article reports. Deterministic (numerical integration).
"""
import math
from statistics import NormalDist

N = NormalDist()
VMAX = 28.30
VARX = VMAX ** 2 / 12
TOL = 0.05  # "at value" = within 5 cents (bids are on a 10-cent grid)
CASES = [  # name, alpha, beta, R2, equilibrium slope s, reported (below, at, above) %
    ("FPSB", 1.14, 0.92, 0.88, 0.8, (92.1, 7.5, 0.4)),
    ("SPSB", 0.23, 1.08, 0.97, 1.0, (5.7, 27.0, 67.2)),
]

for name, a, b, r2, s, rep in CASES:
    sig = math.sqrt(b * b * VARX * (1 - r2) / r2)
    K = 20000
    above = at = num = den = 0.0
    for i in range(K):
        x = (i + 0.5) / K * VMAX
        m = a + b * x
        above += 1 - N.cdf((x + TOL - m) / sig)
        at += N.cdf((x + TOL - m) / sig) - N.cdf((x - TOL - m) / sig)
        d = m - s * x
        z = d / sig
        num += d * (2 * N.cdf(z) - 1) + 2 * sig * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        den += s * x
    ab, at_ = 100 * above / K, 100 * at / K
    print(f"{name}: sigma = {sig:.2f}; implied below/at/above = {100 - ab - at_:.1f}/{at_:.1f}/{ab:.1f}% "
          f"(reported {rep[0]}/{rep[1]}/{rep[2]}%); mean ratio = {(a + b * VMAX / 2) / (VMAX / 2):.3f}; "
          f"SMAD (regression + Gaussian) = {100 * num / den:.1f}%")

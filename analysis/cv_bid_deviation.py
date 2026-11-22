"""
cv_bid_deviation.py -- bid-based deviation for the common-value cells.

Convention: Delta_CV = 100 * mean|b - b*(s)| / (2*eps), the mean absolute
deviation of bids from the equilibrium bid, scaled by the signal range 2*eps.

LLM design (experiment_logs/V10/common_value_*): V ~ U[20, 29], signal
s = V + eta, eta ~ U[-20, 20], N = 3.  The value range (9) is narrower than
the signal range (40), so the interior-region formulas of Kagel and Levin
(1986) do not apply; the symmetric equilibrium is computed numerically:
  second price: b*(s) = E[V | own signal = s, highest rival signal = s]
  first price : b*'(s) = (v(s,s) - b*(s)) * f_Y1(s|s) / F_Y1(s|s), b*(s_min) = 20

Human anchors (closed form, evaluated at n = 4, eps = $12, the cell that
Levin, Kagel and Richard (1996) run in both formats):
  first price: b = x - 0.74*eps + 0.65*N + u, sd(u) = 4.94 (regression quoted in
               analysis/moment_matching_kagel_levin_1986_cv.py), b* = x - eps + Y
  English    : first dropout d = 0.40 + 1.00*x + u, sd(u) = 5.5 (pooled values in
               analysis/moment_matching_levin_kagel_richard_1996_english_cv.py), d* = x

Also reports mean winner profit by model and format.
Output: results/analysis/cv_bid_deviation.csv.  Not part of reproduce_one_llm.py.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
V10, ROB = ROOT / "experiment_logs" / "V10", ROOT / "robustness_logs"
L, H, EPS, N = 20.0, 29.0, 20.0, 3
MODELS = {"GPT-4o": None, "Claude 3.5 Haiku": "claude_sonnet", "Gemini 2.0 Flash": "gemini",
          "GPT-5-mini": "gpt5mini", "Llama-3-8B": "llama",
          "GPT-4o (T=0.1)": "gpt4o_temp01", "GPT-4o (T=1.0)": "gpt4o_temp10"}


def equilibrium():
    """Equilibrium bid functions {'first': f, 'second': f} for the LLM design."""
    vg = np.linspace(L, H, 901)
    xs = np.linspace(L - EPS + 1e-3, H + EPS - 1e-3, 4000)

    def terms(x):
        return (vg >= x - EPS) & (vg <= x + EPS), np.clip((x - vg + EPS) / (2 * EPS), 0, 1)

    vxx, haz = np.empty_like(xs), np.empty_like(xs)
    for i, x in enumerate(xs):
        ok, F = terms(x)
        w = ok * F ** (N - 2)
        vxx[i] = (vg * w).sum() / w.sum()
        haz[i] = (ok * (N - 1) * F ** (N - 2) / (2 * EPS)).sum() / (ok * F ** (N - 1)).sum()
    b, dx = np.empty_like(xs), xs[1] - xs[0]
    b[0] = vxx[0]
    for i in range(1, len(xs)):          # implicit Euler; the ODE is stiff at the lower end
        b[i] = (b[i - 1] + dx * haz[i] * vxx[i]) / (1 + dx * haz[i])
    return {"first": lambda s: np.interp(s, xs, b), "second": lambda s: np.interp(s, xs, vxx)}


def load(fmt, key):
    d = V10 / fmt if key is None else ROB / f"{fmt}_{key}"
    rows = []
    for f in sorted(d.glob("**/raw_data/result_*.json")):
        for k, r in json.load(open(f)).items():
            if not k.startswith("round_"):
                continue
            w = r["history"]["winner"]["winner"]
            for i, bi in enumerate(r["history"]["bidding history"]):
                rows.append((r["value"][i], float(bi["bid"]), r["common"], bi["agent"] == w, r["profit"][i]))
    return np.array(rows, float)


def folded_normal_mean(mu, sd):
    return sd * np.sqrt(2 / np.pi) * np.exp(-mu ** 2 / (2 * sd ** 2)) + mu * (1 - 2 * norm.cdf(-mu / sd))


def human_first_price(n=4, eps=12.0, sd=4.94, x_lo=25.0, x_hi=225.0):
    xs = np.linspace(x_lo + eps, x_hi - eps, 4001)
    y = (2 * eps / (n + 1)) * np.exp(-(n / (2 * eps)) * (xs - (x_lo + eps)))
    return 100 * folded_normal_mean(0.26 * eps + 0.65 * n - y, sd).mean() / (2 * eps)


def human_english(eps=12.0, alpha=0.40, sd=5.5):
    return 100 * folded_normal_mean(alpha, sd) / (2 * eps)


def main():
    bstar = equilibrium()
    out = [dict(bidder="Human", format="first", n_bids=np.nan, smad_bid=human_first_price()),
           dict(bidder="Human", format="second", n_bids=np.nan, smad_bid=human_english())]
    for name, key in MODELS.items():
        for fmt, f in (("common_value_first", "first"), ("common_value_second", "second")):
            s, b, v, win, pi = load(fmt, key).T
            win = win.astype(bool)
            d = np.abs(b - bstar[f](s))
            out.append(dict(bidder=name, format=f, n_bids=len(b),
                            smad_bid=100 * d.mean() / (2 * EPS),
                            se=100 * d.std(ddof=1) / np.sqrt(len(d)) / (2 * EPS),
                            mean_bid=b.mean(), mean_bid_minus_signal=np.mean(b - s),
                            n_winners=int(win.sum()), winner_profit=pi[win].mean(),
                            winner_profit_se=pi[win].std(ddof=1) / np.sqrt(win.sum()),
                            winner_loss_share=100 * np.mean(pi[win] < 0)))
    df = pd.DataFrame(out)
    dst = ROOT / "results" / "analysis" / "cv_bid_deviation.csv"
    df.to_csv(dst, index=False)
    print(df.round(2).to_string(index=False))
    print(f"\nWrote {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

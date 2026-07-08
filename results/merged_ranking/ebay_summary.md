# eBay closing-rule figures: regeneration summary (plan E5/E10)

Produced by `scripts/plots/regenerate_ebay_figures.py` (deterministic; numpy seed 1299
used only for point jitter in the revenue plot). All statistics below are also in
`results/merged_ranking/ebay_figure_stats.json`.

## Outputs

| File | Content |
|---|---|
| `writeup/figures/ebay-winning-bid-non-closing.png` | Histogram of final-winning-bid time, **hard close** (T1 + T3 pooled, N=120) |
| `writeup/figures/ebay-final-winning-closing.png` | Same, **soft close** (T2 + T4 pooled, N=119) |
| `writeup/figures/ebay_cdf_final_bid.png` | Empirical CDF of final-winning-bid time, four treatments (T3/T4 pool r ∈ {40,50,60}) |
| `writeup/figures/ebay_revenue_by_type.png` | Seller revenue (final price) by all 8 auction types |
| `results/merged_ranking/ebay_figure_stats.json` | All statistics (timing, tests, pairwise revenue t-tests, reserve audit) |

## Data provenance and treatment coverage

The recovered directory `recovered_logs/old/experiment_logs_old/V10/ebay_closing_rule/`
contains **only T2** (soft close, no reserve; all 30 prompts verified soft-close, reserve 0).
The full 4-treatment grid survives in git commit `734c0e88` under `experiment_logs/V10/ebay_*`.
The 7 missing treatment folders were restored from that commit into
`recovered_logs/old/experiment_logs_old/V10/` (result CSVs only; raw `*.jsonl` for those
7 dirs remain retrievable from the same commit). The 30 already-recovered T2 CSVs are
**byte-identical** to the git versions.

| Treatment (appendix name) | Directory | Close | Reserve | N runs |
|---|---|---|---|---|
| T1 `basic_proxy` | `ebay_proxy` | hard | — | 30 |
| T2 `closing_rule` | `ebay_closing_rule` | soft | — | 30 |
| T3 `hidden_reserve_40/50/60` | `ebay_proxy_with_hidden_reserve_*` | hard | 40/50/60 | 30 each |
| T4 `closing_rule_hidden_40/50/60` | `ebay_closing_rule_with_hidden_reserve_*` | soft | 40/50/60 | 30/30/**29** |

**No treatment is missing**; the only gap is one run in T4 r=60 (29 instead of 30).
GPT-4o, temperature 0.5, n=3 bidders, IPV values Unif[0,99], 10 scheduled days (periods 0–9);
soft-close runs extend to period 10–14.

## Statistic definition (matters!)

Figures use the **paper definition** (05_validation.tex): final-winning-bid time = the
*last period in which the eventual winner changes her maximum bid* (winner = final
`highest_bidder`; max bids tracked from the `max_bids` column). The old notebooks
(`notebooks/ebay_analysis.ipynb`) used a *price-based proxy* (first period at which
`current_price` reaches its final value). The two agree in only 29.7% of runs
(Spearman ρ = 0.48), so the regenerated histograms will not match the lost originals
bar-for-bar. Headline shares under both definitions:

| Share of decisive bids on/after scheduled final day (day 9) | paper def. | price proxy |
|---|---|---|
| Hard close pooled (N=120) | **50.0%** | 25.8% |
| Soft close pooled (N=119) | **18.5%** | 7.6% |

The qualitative result is the same under either definition.

## Headline findings

1. **Sniping under hard close reproduces.** 50% of hard-close auctions have the winner's
   last max-bid change on the scheduled final day (T1 alone: 63.3%); median timing day
   8.5 (T1: 9). The histogram is deadline-spiked, as in the eBay field evidence
   (Roth & Ockenfels 2002).
2. **Soft-close attenuation reproduces.** Under the extension rule the day-9 spike
   collapses (7.6% exactly at day 9; 18.5% at day ≥ 9) and the distribution shifts
   earlier (mean 5.0 vs 6.7). Hard vs soft pooled: Mann-Whitney p = 3.5e-05,
   KS D = 0.315, p = 7.2e-06; T1 vs T2 alone: MW p = 1.5e-04. A quarter of soft-close
   winners place their decisive bid on **day 0** (bid-early-and-hold), consistent with
   "spreads competition earlier in time."
3. **CAVEAT for the text — T4 does *not* dampen last-period activity beyond T2.**
   discussion.tex (old draft, line 27) claims "Adding a hidden reserve on top of soft
   close (T4) further dampens last-period activity." Under the paper definition T4 is
   *later* than T2 (share ≥ day 9: 21.3% vs 10.0%; mean 5.4 vs 4.0; MW p = 0.048), and
   under the price proxy they are indistinguishable (7.9% vs 6.7%). Recommend softening
   that sentence: both soft-close treatments show strong attenuation relative to hard
   close, but T4 is not below T2.
4. **Revenue is flat — the reused appendix table is validated.** Means range
   57.3–58.0 across all 8 types. Recomputed pairwise Welch t-tests **match
   `tab:ebay-revenue` exactly** (e.g., basic_proxy vs closing_rule t = 0.020, p = 0.984;
   max |t| = 0.144, min p = 0.886; df ≈ 57–58, N = 30 per cell). Nonparametric checks
   agree: pairwise Mann-Whitney min p = 0.82; Kruskal-Wallis H = 0.11, p ≈ 1.0.
5. **Reserve audit (answers appendix TODO items (i)–(ii)).**
   - *Binding frequency*: the reserve blocked the sale (highest max bid < r) in 0/30,
     2/30, 4/30 runs (hard close, r = 40/50/60) and 0/30, 2/30, 3/29 (soft close) —
     at or below the truthful-bidding predictions of 6.6% / 12.9% / 22.2%.
   - *Price-lift audit*: the simulator does **not** lift the standing price to the
     reserve once met, unlike eBay proper. In runs where second-max < r ≤ highest-max
     ("liftable": 6, 8, 13 of 30 at r = 40/50/60 hard; same pattern soft), the final
     price reached the reserve in 0, 0, and 2 cases — and those 2 are mechanical
     (second max 59 → price 60). Revenue is pinned at second-highest max + 1 throughout,
     so the revenue null partly reflects a *mechanical* channel being switched off, not
     only bidder insensitivity. This should be stated when interpreting Figure
     `ebay_revenue_by_type` / `tab:ebay-revenue`.
   - *Strict revenue* (unsold ⇒ 0, the economically correct notion): means fall to 54.9
     (r=50) and 51.7 (r=60) under hard close, but no comparison vs T1 is significant
     (Welch p ≥ 0.37). The figure keeps the original final-price convention to stay
     consistent with the reused t-test table; both conventions are in the JSON.

## Data-quality caveats

- 10 of 30 T2 CSVs (the 2025-02-03 batches) lack the per-agent `value` column (values
  were not logged in the earliest runs). Not needed for these figures; would bias any
  efficiency/bid-vs-value analysis of T2 toward the 2025-02-04 batches.
- One T4 r=60 run is missing (29/30) — already missing in git, not a recovery loss.
- In reserve-blocked runs the log still records a `highest_bidder` and a final price;
  the timing figures treat that bidder as the "eventual winner" (the original analysis
  did the same implicitly).
- Small cells: 30 runs/treatment; pooled panels have N = 120 (hard) / 119 (soft).
- All runs are GPT-4o at temperature 0.5; no other model was run through the eBay
  environment.

## LaTeX integration notes

Filenames match the references in `writeup/contents/discussion.tex` (commented figure
block + active `figures/ebay-winning-bid-non-closing.png`, `ebay-final-winning-closing.png`,
`ebay_cdf_final_bid.png`) and the `\MISSINGFIG` placeholders in
`writeup/contents_v2/05_validation.tex` (fig:ebay-sniping) and
`writeup/contents_v2/appendix_ebay.tex` (fig:ebay-revenue, `ebay_revenue_by_type.png`).
PNGs are 200 dpi (~1400 px wide); prefer `width=0.9\linewidth` (or `scale≈0.3`) over the
old `scale=0.45`. Each PNG already carries a title/subtitle, so LaTeX captions can stay
short. For `tab:ebay-revenue`'s TODO: per-treatment N = 30 (29 for T4 r=60), Welch df in
the JSON (≈57–58), nonparametric Mann-Whitney p-values included per pair.

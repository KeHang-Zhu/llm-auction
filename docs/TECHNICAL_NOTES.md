# Technical notes: LLM auction (TEAC submission)

Everything the paper leaves out on purpose: version history, implementation details, and open items. Sentences moved from the paper keep their wording and say where they came from.

## Scope and limitations

- Author `\email{}` and `\orcid{}` entries are not filled in `TEAC_submission/main.tex`.
- The CCSXML block was written by hand for the three listed concepts (2026-11-20); regenerate it with the ACM tool (https://dl.acm.org/ccs) before the camera-ready.
- Table 7 lists p_eq = 0.75 for KL93 FPSB without a source.

## Human benchmark anchors: what was checked against the sources (2026-11-20)

Sentences moved out of Appendix "Benchmark Records and Mappings" (main.tex) during the final check, word for word:
- "[TODO before submission: fill every table and page reference from the original articles and confirm each number against the print.]"
- "[TODO: the stored values 24.76 and 5.65 are not reproduced by the current script, which returns 14.1 and 18.3 without a fixed seed; reconcile before submission.]"
- "The stored value 5.83 (95% interval [2.57, 9.09]) implies MAD = 3.79 at E[v] = 65. [TODO: confirm E[v]; the authors' working notes use 70.]"

Status of each anchor:
- **Li (2017), SP-APV 9.31 and AC 3.54: reproduced.** Table 3, auction rows: SP 8.04 (1.25) and 4.99 (1.18); OSP 3.19 (1.05) and 1.77 (0.33), for rounds 1-5 and 6-10. Block means 6.515 and 2.48, divided by E[v] = 70, give 9.31 and 3.54. Standard errors combined as independent blocks (0.86, 0.55) give the stored intervals [6.91, 11.70] and [2.00, 5.09].
- **Breitmoser and Schweighofer-Kodritsch, AC-B 5.83: E[v] settled, value not reproduced.** The value distribution is the same as Li's (group draw U[10,110] plus private adjustment U[0,20]), so E[v] = 70, not 65; `analysis/reconstruction_bands.py` now uses 70 (the bands in SMAD units do not change). In the working paper (WZB SP II 2019-203), Figure 1 shows only the shares of the 2P-to-AC reduction (49% presentation, 12% dynamic bidding, 39% dropout information); the mean absolute deviations are in Figure 2 (by round) and Appendix Table 2 (AC-B: 6.03, 3.70, 2.26 for rounds 1-3, 4-6, 7-10). The round-weighted mean of Table 2 is 3.82, i.e. 5.46 at E[v] = 70. Applying the 39% share from Figure 1 to Li's 2P-AC gap gives 5.79. Neither equals 5.83, and the source of the interval [2.57, 9.09] was not found. With 5.46 the human ordering of AC-B (5.46) and SPSB IPV (5.65) would flip.
- **Kagel and Levin (1986), FP-CV 47.59: not reproduced.** Table 2 gives average actual profits and RNNE profits for 11 auction series. Pooling all series, 100*|mean actual - mean RNNE|/mean RNNE is 66.1 with equal weights and 65.9 weighted by periods. No natural subset or weighting gives 47.59.
- **Levin, Kagel and Richard (1996), SP-CV 18.23: not reproduced.** Table 2 (inexperienced bidders) gives actual and theoretical profits for first-price and English auctions. For the English auction the same formula gives more than 100% (131% for n = 4, pooled over signal ranges), because predicted profits are small. In dollar terms the first-price deviation is larger (about 6.5 vs 2.4 for n = 4).
- **Kagel and Levin (1993), FPSB 24.76 and SPSB 5.65:** not reproduced by `analysis/moment_matching_kagel_levin_1993.py` (see the moved sentence above).
- No derivation code for the stored common-value and AC-B anchors exists in the repository; `data/auction_human.csv` holds the values as entered on 2026-02-04.

### Follow-up on the unreproduced anchors (2026-11-21)

Author recollection: the common-value anchors were pooled across group sizes (4 and 7 bidders). Checked against everything in the repository:

- **Method note found.** `data/Auction_human_data_collection.pdf` (compiled 2026-01-22) documents the common-value mapping: draw the mean profit and the predicted profit from normals with the reported standard errors, compute 100*|pi - pi*|/pi* for 100 draws, report the mean; signal ranges pooled. It also states E[v] = 70 for both Li and Breitmoser and Schweighofer-Kodritsch.
- **That method on the supplied tables does not give the stored values** (pooled first, then 100 draws, repeated 4000 times):
  - Kagel and Levin (1986) Table 2: all 11 series 66; N = 3-4 (5 series) 42 pooled, 54 when each series is simulated and then averaged; N = 6-7 105; N = 7 124-131. Stored: 47.59.
  - Levin, Kagel and Richard (1996) Table 2 (inexperienced), first price: n = 4 116, n = 7 281-303, both 142-146.
  - Same table, English: n = 4 132-135, n = 7 226-249, both 163-171. Stored: 18.23. Realized profits are negative in four of five cells while predicted profits are positive, so no pooling of this table gives a value below 100.
- **Second reconstruction route in the repository.** `analysis/moment_matching_kagel_levin_1986_cv.py` and `analysis/moment_matching_levin_kagel_richard_1996_english_cv.py` (2026-01-29) build synthetic bids from the reported bid regressions, pooled over experience, for eps = 12, 18, 24 and N = 4, 6 (first price) or 4, 7 (English). Outputs in `results/v12_interventions/moment_matching/`. Their signal-range-normalized deviation, 100*MAD/(2*eps), is 18.9 (first price) and 18.4 (English) at N = 4, eps = 12, and 16.1 and 14.8 over all cells. No single definition gives 47.59 and 18.23 together.
- **Table 3 of Levin, Kagel and Richard (1996) (one-time-experienced bidders, eps = $12), supplied by the author on 2026-11-21: does not give the stored values either.** First price: 68 (n = 4), 111 (n = 7), 74 pooled by periods. English: 116 (n = 4), 128 (n = 7), 122 pooled. Pooling Table 3 with Table 2 in any subset, equal or period weights, gives nothing within 0.5 of 47.59 or 18.23 for the English rows.
- **AC-B explained.** 5.83 = 3.79/65: the stored value divides the all-round mean absolute deviation (Appendix Table 2 of the working paper gives 3.82 round-weighted) by E[v] = 65. The value distribution implies E[v] = 70, which gives 5.46 (5.41 with 3.79). Appendix Table 2 has no standard errors, so the source of the interval is still unknown.
  - Effect of 5.46 on the human ordering: AC-B falls below SPSB IPV (5.65). Kendall tau_b over the five private-value formats (one-LLM clock cells) changes from 0.80 to 1.00 for GPT-4o and Gemini 2.0 Flash, 0.40 to 0.60 for Claude 3.5 Haiku, 0.00 to 0.20 for Llama-3-8B, and -0.20 to -0.40 for GPT-5-mini.
  - main.tex is inconsistent on this point: Appendix A.1 and Table 1 say E[v] = 70, the mapping paragraph later in the appendix still says 65.
- **Human direction shares for the clock formats.** `data/auction_human.csv` stores below / at / above shares of 16 / 44 / 40 for AC-B, shown in the direction figure as 71% overbids among deviating bids with the label "reported (source)". Appendix Table 2 of the working paper reports, for AC-B, overbidding (b - v > 1) in 1-3% of bids and underbidding (b - v < -1) in 33-69% across round blocks. The stored shares for SP-APV (10 / 50 / 40) and AC (15 / 67 / 18) attributed to Li (2017) were not located in Li's Table 3.

### Changes applied on 2026-11-21 (author decision: AC-B at E[v] = 70)

- `data/auction_human.csv`: AC-B 5.83 [2.57, 9.09] -> 5.46 [2.43, 8.49]; AC-B direction shares 16/44/40 -> 49/49/2 (below / within $1 / above, round-weighted from Appendix Table 2 of the working paper: underbidding 0.69, 0.49, 0.33 and overbidding 0.01, 0.03, 0.02 for rounds 1-3, 4-6, 7-10). SP-APV 10/50/40 -> 22/39/39 and AC 15/67/18 -> 11/70/19, read off Li (2017) Figure 2(a) by measuring bar heights (bins of $4; middle bin within $2). Panel (b) of the same figure (+X auctions) gives SP 12/43/44 and OSP 16/71/13; not used.
- The AC-B interval keeps the standard error on the MAD implied by the old interval at E[v] = 65 (1.08). The source of that standard error is still unknown; Appendix Table 2 reports none.
- `analysis/reconstruction_bands.py`: mixture weights for SP-APV, AC and AC-B updated to the shares above. New 95% bands: SP-APV [6.82, 11.74], AC [2.00, 5.37], AC-B [2.37, 8.72]. AC-B < SP-APV now holds in 96.5% of re-draws (was 92.6%); crosscheck asserts in the concordance scripts updated.
- Kendall tau_b over five private-value formats: GPT-4o 0.80 -> 1.00, Gemini 2.0 Flash 0.80 -> 1.00, Claude 3.5 Haiku 0.40 -> 0.60, Llama-3-8B 0.00 -> 0.20, GPT-5-mini -0.20 -> -0.40; GPT-4o at T = 0.1 / 0.5 / 1.0: 0.80 / 1.00 / 0.80. The human AC-B (5.46) and SPSB IPV (5.65) anchors are 0.19 apart and the AC-B band covers 5.65, so this pair's human order is the least certain one; the joint draws in Table `tab:concordance` include it.
- Human direction in SP-APV: 64% of deviating bids are overbids (was 80%); the scorecard row "Sealed SP-APV errors are mostly overbids" still holds. Human AC-B deviations are now 96% underbids.
- `tables/bands.tex` and `tables/scorecard.tex` are hand-maintained and were updated by hand.
- Row removed from Table `tab:mixture_fit` (main.tex, Appendix "Mixture Model Fitting Details"), word for word: "Breitmoser (2022) & 2P & 0.44 & 0.40 & 0.283 & Mean ratio = 1.10". No benchmark uses it, and the source's Appendix Table 2 gives different 2P shares (round-weighted: overbidding 0.30, underbidding 0.28). The lambda values of the Li and AC-B rows ("0.219", "0.198", "0.154", matched to mean bid/value ratios 1.08, 1.02, 1.01) were replaced by "--": those anchors are the reported MAD and the bands do not use lambda; the mean ratios have no source.
- Moved from the mixture-fit itemize, word for word: "For \citet{li2017obviously} and \citet{breitmoser2022obviousness}: the mean bid-to-value ratio (e.g., $\mathbb{E}[b/v] \approx 1.08$)."
- Common-value anchors 47.59 and 18.23 unchanged; still not reproduced.

### Common-value anchors: denominator check (2026-11-21)

Author recollection: the common-value anchors used a different denominator. Findings:

- **SP-CV 18.23 matches the bid-based reconstruction with the signal-range denominator.** `analysis/moment_matching_levin_kagel_richard_1996_english_cv.py` simulates first-dropout prices from the Levin, Kagel and Richard (1996) regressions (pooled over experience) and reports 100*E|d - d*|/(2*eps). The script has no fixed seed. Over 30 seeds, the cell n = 4, eps = $12 gives 18.32 (range 18.00-18.65); 18.23 lies inside. Other cells: n = 4: 12.25 (eps 18), 9.15 (eps 24); n = 7: 22.82, 15.22, 11.42. So 18.23 is most likely this one cell, a dropout-price deviation over the signal range, not a profit deviation over predicted profit.
- **FP-CV 47.59: still not found.** The first-price script (`moment_matching_kagel_levin_1986_cv.py`, regression b = x - 0.74 eps + 0.65 N, residual SD 4.94) gives 100*E|b - b*|/(2*eps) between 6.6 and 49.8 over N = 3-7 and eps = 6-30; the KL86 cells it runs (eps 12-24, N = 4, 6) give 9.6-24.2. With denominator eps instead of 2*eps, the cell N = 6, eps = 12 gives 48.5 (seed range 47.8-49.5), close to but not matching 47.59, and it would use a different denominator from the English value. Profit deviations from Kagel and Levin (1986) Table 2 divided by |pi| + pi*, pi* - strategic-discount profit, or pi* give 49.4, 37-39, and 66 for all series.
- **LLM common-value cells use yet another denominator.** `scripts/plots/model_comparison_main.py` computes 100*mean|pi - pi*|/20 over winners, with pi* = 2*eps_w/(n+1) (first price) or eps_w/(n+1) (second price), eps_w = winner signal minus common value, and 20 = the half-width of the signal noise (eta ~ U[-20, 20]). This is a profit deviation over the noise half-width.
- **main.tex is inconsistent with all of this.** Appendix "Benchmark Records and Mappings" and Table 1 describe both human anchors as 100*|pi-bar - pi-bar*|/pi-bar* from the cited Table 2s; the LLM formula is not written out in the paper.

### Common-value cells under the bid-based convention (2026-11-21, not yet applied to the paper)

Author decision: common-value deviations are bid deviations over the signal range, 100*mean|b - b*(s)|/(2*eps). The older appendix text in main.tex ("Because there is a very large common part in each players' valuation, we take the following normalization factor", with b* = x - eps + Y for first price and b* = x for second price) already states this; the later "Kagel and Levin (1986) and Levin, Kagel, and Richard (1996): common values" paragraph and Table 1 describe a profit ratio instead and contradict it.

Computed in `analysis/cv_bid_deviation.py` (output `results/analysis/cv_bid_deviation.csv`; not wired into `reproduce_one_llm.py`):

- **Where the stored human values sit under this convention.** English first dropout against d* = x, n = 4, eps = $12: 18.33 in closed form (stored 18.23; the old script has no seed). First price against b* = x - eps + Y: 47.2 at N = 5, eps = $6 and 47.5 averaged over N = 3-7 at eps = $6 (stored 47.59). The two stored anchors therefore use different signal ranges. At a fixed residual SD the measure scales as 1/eps, so the choice of eps drives the level: at the matched cell n = 4, eps = $12 the first-price value is 25.92 against 18.33 for English. First price exceeds English at every matched cell (eps 6: 43.7 vs 36.7; 18: 20.3 vs 12.2; 24: 17.5 vs 9.2).
- **Inputs not checked against the print.** First-price regression b = 1.00x - 0.74 eps + 0.65 N, residual SD 4.94 (script cites Kagel and Levin 1986, Table 4). English first-dropout regressions by experience (script cites Levin, Kagel and Richard 1996, Tables 5 and 6); the pooled intercept 0.40 is their average, and the residual SDs (8.0, 4.0, 4.0; pooled 5.5) are marked "approximated" in the script. The English anchor is essentially 0.8 * SD / (2 eps), so it rests on that approximation.
- **LLM cells are not on this convention.** `model_comparison_main.py`, `appendix2_temperature.py` and `temperature_concordance.py` compute 100*mean|pi_w - pi*|/20 over winners with pi* = 2(s_w - V)/(n+1) or (s_w - V)/(n+1); s_w - V is the winner's realized noise, so pi* is not an equilibrium profit.
- **Equilibrium for the LLM design.** V ~ U[20, 29], noise U[-20, 20], N = 3: the value range is narrower than the signal range, the interior formulas do not apply, and signals between 9 and 40 carry no information about V. The numerical equilibrium bid is nearly flat: 23.3-24.3 (second price) and 22.5-24.1 (first price) for signals from 10 to 40. Expected winner profit in equilibrium is 0.45 in both formats.
- **LLM cells recomputed on bids (all three bidders per auction, divided by 40), first price / second price:** GPT-4o 20.7 / 21.8, Claude 3.5 Haiku 11.8 / 13.9, Gemini 2.0 Flash 17.3 / 18.4, GPT-5-mini 3.8 / 2.3, Llama-3-8B 25.0 / 20.0 (standard errors 0.7-2.1). Current paper values: 60.0 / 40.6, 54.1 / 27.2, 59.5 / 30.9, 30.2 / 14.8, 53.7 / 32.3.
  - The first-price > second-price ordering in SMAD is no longer reproduced by the three non-reasoning large models (the two formats are within about one standard error); it holds for GPT-5-mini and Llama-3-8B.
  - GPT-5-mini is close to equilibrium in both formats, so the sentence "unlike in the private-value settings, GPT-5-mini makes substantial errors in common-value auctions" does not hold on bids.
  - The models bid about the same in the two formats (GPT-4o mean bid 21.0 vs 20.3); the formats differ in what the winner pays.
- **Winner profits (N = 3), first price / second price:** GPT-4o -4.91 / +4.42, Claude 3.5 Haiku -5.26 / -1.27, Gemini 2.0 Flash -5.11 / +1.71, GPT-5-mini +0.71 / +1.61, Llama-3-8B -1.20 / +4.56; share of winners with a loss 79% / 38%, 69% / 59%, 73% / 33%, 33% / 27%, 47% / 23%. Winner profit is lower in first price for all five models. Humans, Levin, Kagel and Richard (1996) Table 2 (inexperienced), first price / English: -2.13 / -0.58, -1.32 / -0.78, +1.20 / +0.11 (n = 4; eps 6, 12, 24), -3.85 / -1.87, -3.75 / -1.80 (n = 7; eps 6, 12).

## Implementation details

- Analysis environment: Python 3.9 with `requirements-analysis.txt` (newer Python cannot install the pinned versions). One-LLM clock outputs: `python scripts/reproduce_one_llm.py`.
- Small-cell flag removed (2026-11-19, author decision): no dagger or hatching for cells below 30. The smallest cells are Claude 3.5 Haiku's common-value cells, 29 of 30 planned rounds each (one failed round; the model is no longer served, so it cannot be topped up). The n >= 30 rule still decides which formats enter Kendall's tau; every private-value cell passes.
- Four one-LLM closed-clock auctions (GPT-4o T=0.5: 2; Claude Haiku 5.5: 1; Gemini 2.5 Flash: 1) hung on the remote side for about 8 hours and were stopped on 2026-11-15; they are counted as failed in Table 2.

## Changelog

### 2026-11-19 (moved out of the paper during the final formal check)
- "An earlier version of this section reported a per-auction statistic (the deviation of the second-highest bid from the second-highest value) on a separate GPT-4o run, and correspondingly larger effect sizes; the qualitative pattern is unchanged." (moved from: main.tex, Section "Clock framing" intervention, footnote on the per-bid scaled deviation)
- "This section was part of the Methods in an earlier version; it is moved here because the eBay-style environment is separate from the laboratory benchmarks." (moved from: main.tex, eBay appendix, first paragraph)
- "An earlier version of this paper also varied a hidden reserve price; we omit it here to keep the environment minimal, and because it had no detectable effect on outcomes in our setting." (moved from: main.tex, eBay appendix, treatments paragraph)
- "the clock cells were rerun under the one-LLM design" (moved from: main.tex, models appendix, "Two cautions" paragraph; now reads "the clock cells use the one-LLM design")
- "Earlier versions reported no clock bids for GPT-5-mini; under the one-LLM design it completes every clock auction." (moved from: main.tex, models appendix, "Two cautions" paragraph)
- "Two wording differences between the earlier GPT-4o run used in a previous version of this paper and the cells reported here should be noted: the earlier run stated that bids must lie between $0 and the bidder's value in $0.1 increments (the current templates say only that bids must be in $0.1 increments), and it limited the bidder's written plan to 50 rather than 100 words." (moved from: main.tex, Gemma clock-framing appendix)

### 2026-11-15
- Clock cells rerun under the one-LLM design; replacement models for Claude (Haiku 5.5), Gemini (2.5 Flash), Llama (3.1-8B).

# Data Map for LLM Auction Experiments

Last updated: 2026-09-28. This map describes the data used by the current manuscript and by `scripts/reproduce_paper.py`. Older experiments remain in the repository, but are not automatically pooled into the published comparisons.

## Directory Structure Overview

| Location | Contents and use |
| --- | --- |
| `experiment_logs/V10/` | GPT-4o baseline auctions, clock auctions, common-value runs, and the released eBay closing-rule exports |
| `robustness_logs/` | Cross-model baselines, GPT-4o temperature checks, and repeated-auction experiments |
| `experiment_logs/paper_interventions/` | Four-model baseline export, original menu/clock-framing result JSONs, and archived configurations and rule texts |
| `plots/auction_human.csv` | Human summary-statistic anchors and source-reported direction shares |
| `results/v12_interventions/moment_matching/` | Synthetic bids reconstructed from published human statistics; used for the first-price direction comparison |
| `results/reconstruction_bands/` | Recomputed human reconstruction uncertainty |
| `results/analysis/` | Model deviations, direction shares, rank concordance, intervention effects, and closing-rule summaries |
| `writeup/figures/`, `writeup/tables/` | Current manuscript figures and LaTeX tables |

## 1. Laboratory baselines

The seven settings are first-price IPV, second-price IPV, sealed second-price APV, open and closed ascending-clock APV, and first- and second-price common-value auctions. IPV means independent private values; APV means affiliated private values.

The reference GPT-4o private-value cells are fixed explicitly in `analysis/difficulty_concordance.py`:

| Format | Source below `experiment_logs/V10/` | Usable bids in the rank analysis |
| --- | --- | ---: |
| FPSB IPV | `fpsb_ipv/run_2026-01-12_21-59-13-724783/results/fpsb_ipv_results.csv` | 285 |
| SPSB IPV | `spsb_ipv/run_2026-01-12_21-59-13-727690/results/spsb_ipv_results.csv` | 270 |
| SP-APV | `spsb_apv/run_2026-01-12_22-28-06-038405/results/spsb_apv_results.csv` | 291 |
| Open clock | `ascending_clock_apv/ascending_clock_apv_merged_results.csv` | 106 |
| Closed clock | `ascending_clock_apv_closed/ascending_clock_apv_closed_merged_results.csv` | 114 |

Clock counts exclude winners because the winner's exit price is censored. The baseline raw result JSONs, exported CSVs, configuration snapshots, and available prompt snapshots remain in their original run directories.

Other model cells are in `robustness_logs/<format>_<suffix>/`:

| Path suffix | Recorded model |
| --- | --- |
| `claude_sonnet` | **Claude 3.5 Haiku**, `claude-3-5-haiku-20241022`; the directory name is historical |
| `gemini` | `gemini-2.0-flash` |
| `gpt5mini` | `gpt-5-mini` |
| `llama` | `meta-llama/Meta-Llama-3-8B-Instruct` |

The analysis excludes the duplicated `robustness_logs/V10/` tree. GPT-5-mini's clock runs produce no usable tick-by-tick bids; they are missing observations, not zero-error measurements. Other thin clock cells are flagged. Rank comparisons require at least 30 usable bids per format.

`model_smad_results.csv` has 42 rows: seven formats by the human benchmark and five models. For each model cell it reports the scaled mean absolute deviation (SMAD), confidence interval, standard error, and sample count. `direction_shares_models.csv` has 30 rows: five private-value formats by those same six sources.

## 2. Human benchmark reconstructions

`plots/auction_human.csv` collects summary-statistic anchors from the experimental literature. The source reconstruction scripts are `analysis/moment_matching_*.py`; the current uncertainty calculation is `analysis/reconstruction_bands.py`.

These are **synthetic reconstructions, not observed individual human records**. The first-price direction comparison uses the Kagel–Levin reconstruction with five human bidders and the benchmark `0.8 * value`. The truthful formats use source-reported under/equal/over shares. Those human categories need not use the same tolerance as the LLM classification, which excludes bids within 2% of the theoretical benchmark.

Private-value model SMAD uses `100 * mean(abs(bid - benchmark_bid)) / 25`. For the three-bidder first-price runs, the benchmark is `2 * value / 3`; it is value in the truthful formats. Common-value results instead measure winner-profit deviations, normalized by 20. Consequently, common-value cells are compared within their own information structure and do not enter the private-value Kendall rank calculation.

The reconstruction bootstrap uses 2,000 draws and seed 1299. Its bands measure calibration/reconstruction uncertainty, not sampling uncertainty from individual human records. Rank reports also distinguish within-cell LLM resampling, human reconstruction re-draws, and joint resampling; bids are treated as independent within cells.

## 3. Description interventions

`experiment_logs/paper_interventions/` releases exactly the inputs needed by `scripts/plots/interventions_models.py`:

- `baselines.csv`: 1,188 bid rows from the original combined export, restricted to the two standard-description experiments `axis1_contingent_baseline` and `axis3_beliefs_baseline` and the four reported models. Model identifiers are canonicalized; free-text plans are omitted. `source_row` identifies the one-based line in the original CSV, including its header.
- `<model>/<experiment>/result_*.json`: 389 original result files across GPT-4o, Claude 3.5 Haiku, Gemini 2.0 Flash, and Gemma-3-27B, for `intervention_menu` and `intervention_proxy_breitmoser`.
- `protocols.json`: archived configurations and rule text for each baseline and intervention, plus the original baseline CSV's relative source name and SHA-256 checksum. Configuration output paths describe historical runs; the analysis reads only the released files.

The original material came from the local `Engineering_simplicity/engineer_simplicity-main` research archive. That archive is not required to run the released analysis. The JSON parser preserves its bidder-name-to-value mapping and file ordering. Results were checked against the original analysis for every model and treatment.

`interventions_models.csv` has 12 rows: four models by pooled baseline, menu framing, and clock framing. The paper emphasizes clock framing for the three non-reasoning large models, with Gemma as an appendix check. Menu results are included for completeness. The outputs include deviations, sample sizes, near-truthful shares, Welch and Mann–Whitney tests, and Cohen's d.

`results/analysis/cell_crosschecks.csv` contains 37 relevant rows from the earlier aggregated analysis for diagnostic cross-checks. It is not the bid-level input to the new estimates. Its private-value SMAD uses a 24.5 normalizer, so the framing analysis explicitly rescales it to the paper's 25 convention. Historical source paths in that reference file describe provenance, not additional dependencies.

## 4. eBay-style closing rules

The two archived datasets are now available directly under the existing experiment-log layout:

| Treatment | Directory | Auction runs |
| --- | --- | ---: |
| Hard close, no reserve | `experiment_logs/V10/ebay_proxy/` | 30 |
| Soft close, no reserve | `experiment_logs/V10/ebay_closing_rule/` | 30 |

Each `result_*.csv` is a complete auction trajectory. These files were copied unchanged from the archived `recovered_logs/old/experiment_logs_old/V10/` datasets. `scripts/plots/ebay_closing_rule_only.py` reads the new repository-relative locations.

The scheduled periods are stored as 0–9 and reported as 1–10; soft-close extensions continue beyond period 10. The plotted timing statistic is the last period in which the eventual winner increases their maximum bid. The summary also reports two distinct alternatives: the first period at the final price, and the last bid by any participant. `ebay_closing_rule_summary.csv` therefore has six rows, two treatments by three timing definitions. The reported 63% versus 7% comparison concerns period 10 under the winner-last definition.

## 5. Temperature and repeated-auction checks

Temperature 0.5 uses the published GPT-4o V10 cells. Temperatures 0.1 and 1.0 use `robustness_logs/<format>_gpt4o_temp01/` and `..._gpt4o_temp10/`. `analysis/temperature_concordance.py` records usable counts, source paths, run dates, seed bases, direction shares, and rank uncertainty. Some clock cells are missing or very small, so the set of usable formats differs across temperatures.

The legacy temperature figure is retained for comparison with the manuscript. Its table generator renders missing cells as zero; those entries are not observations. Use the current `temperature_concordance.csv` and `temperature_robustness.tex`, which explicitly distinguish missing data and thin cells, for interpretation.

The repeated-auction figure uses `robustness_logs/fpsb_ipv_15_rounds/` and `robustness_logs/spsb_ipv_15_round/`. These data contain outcome feedback across auctions and are separate from the one-shot baseline.

## Reproduction and historical files

Run `python scripts/reproduce_paper.py --check` from the root after installing `requirements-analysis.txt`. It regenerates the analyses from released inputs without network calls and compares the five principal CSV outputs with their saved versions. The current manuscript source is `writeup/main.tex`; older sources and notebooks remain as historical material.

Raw EDSL cache JSONL files are excluded from Git. Their absence does not prevent offline reproduction, which uses the exported CSVs and result JSONs described above. Generating new model responses requires the simulator dependencies and provider credentials and is distinct from reproducing the reported results.

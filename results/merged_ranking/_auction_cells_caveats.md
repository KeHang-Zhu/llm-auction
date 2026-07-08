## Baseline mapping used for inference (documentation)

| Cell family | Treatment cells | Baseline used |
|---|---|---|
| ES V12 (`es_v12_csv` + `es_v12_raw`, 4 models) | `axisK_*` treatments | same model's `axisK_*_baseline` |
| | `loss_aversion_*` | `loss_aversion_baseline` |
| | `risk_averse` / `risk_seeking` | `risk_neutrality` |
| | `intervention_*` (menu, proxy_breitmoser, NE/wrong strat reveal, nash_deviation), `spsb`, `private_second_price`, `ascending_clock_closed`, `risk_neutrality`, `loss_aversion_baseline` | POOLED axis baseline (axis1+axis2+axis3 `*_baseline` concatenated, same model) |
| | `axis{1,2,3}_*_baseline` | none (constituents of the pooled baseline; `is_baseline=True`) |
| Recovered V12 GPT-4o (`v12_gpt4o_recovered`) | same rules, applied within price-order suffix (`_first`/`_third`/unsuffixed=second); risk personas map to `intervention_risk_neutral_<suffix>` | suffix-matched baselines |
| V10-style (`v10_gpt4o_anchor`, `v10_recovered_expl`) and `robustness` (per model/temperature group) | `fpsb_ipv`, `third_price_ipv*`, `all_pay_ipv`, `intervention_*` | same-family `spsb_ipv` |
| | `spsb_apv` | `spsb_ipv` |
| | `ascending_clock_apv{,_closed}` | `spsb_apv` |
| | `fpsb_ipv_15_rounds` | `spsb_ipv_15_round` |
| | `common_value_*` | none (no canonical truthful baseline; deviation = bid − private signal, descriptive) |

Pooled-axis-baseline rows are included in the CSV as derived cells named `POOLED_axis_baseline{,_first,_third}`.

## Data-quality caveats

1. **`robustness_logs/*_claude_sonnet` is NOT Claude Sonnet.** Every `config.yaml` in those dirs says `model: claude-3-5-haiku-20241022`. Plot scripts (e.g. `analysis/smad_all_auctions_v2.py`) label these cells "Claude Sonnet" — the paper should either relabel or rerun. The CSV carries the config model.
2. **`recovered_logs/experiment_logs_with_explanation/V10` is gpt-4o, not gpt-5-mini** (all 22 configs), and shares 14/22 run timestamps with `experiment_logs/V10`. Kept as a separate `v10_recovered_expl` source; never pool it with `v10_gpt4o_anchor`.
3. **Empty cells (NA rows, no data anywhere):** `robustness_logs/ascending_clock_apv_gpt5mini` (2 runs, no raw_data/results), `robustness_logs/ascending_clock_apv_closed_gpt5mini` (1 run, empty; its config also says `model: gpt-4-mini`, an apparent typo), `robustness_logs/ascending_clock_apv_gpt4o_temp01` (1 run, empty). So there is **no gpt-5-mini ascending-clock data** and **no temp-0.1 open-clock GPT-4o data**.
4. **Cells reconstructed from raw JSON** (no results CSV in the run dir; parsed with the same logic as `src/export_results.py`): all `es_v12_raw` cells (flat `result_*.json` dirs; env metadata from `configs_auction/interventions_<model>/*.yaml`, all sealed second-price private, seed 1299, n=3), plus single runs inside `ascending_clock_apv_claude_sonnet`, `ascending_clock_apv_closed_gemini`, `ascending_clock_apv_llama`, and `ascending_clock_apv_closed_gpt4o_temp01` (the latter has only 2 repetitions ⇒ n=6 bids; treat with caution — flagged in `notes`).
5. **ES raw dirs have ragged rep counts** (19–50 result files per cell; e.g. `gemini/intervention_wrong_strat_reveal` has only 19 ⇒ n=57 bids). n_bids per cell is in the CSV.
6. **`robustness_logs/V10/` duplicates** two top-level dirs (`common_value_first_gpt4o_temp01/10`); the duplicate copies are excluded.
7. **Common-value cells:** `player_value` is the private *signal*; deviation = bid − signal is descriptive (winner's-curse analysis needs the realized common value, not covered here). SMAD% for CV cells uses the same 24.5 normalizer for comparability but is not an RNE-referenced quantity.
8. **Multiple seeds pooled within cells** where present (e.g. V10 `ascending_clock_apv` runs with seed_base 1299/1319/1399 — all affiliated per config; the `seed_base` column lists every seed pooled). Env (`private`/`affiliated`/`common`) is taken from each run's config/CSV `private_value` field, consistent with the seed convention (1299=private/ipv runs, 1399=affiliated) but authoritative where they differ.
9. **Clock cells:** `bid` is the recorded exit/drop-out price from the results CSVs; deviations are exit − value, so SMAD is comparable to sealed-bid cells only as a dominance-deviation measure.
10. **Rounding/NaN hygiene:** rows with non-numeric or missing bids are dropped and counted in `n_rows_dropped_nan_bid` (0 almost everywhere).
11. **TPSB RNE benchmark** b\*=v·(n−1)/(n−2) exceeds the $49 endowment for v>24.5 when n=3; `mean_dev_rne_capped` uses min(b\*, 49). For n=5 cells the benchmark (4/3·v) is always feasible.
12. **`fpsb_ipv_15_rounds` / `spsb_ipv_15_round`** are multi-round GPT-4o cells (all rounds pooled); they sit in group `gpt4o_15round` and are only compared to each other.

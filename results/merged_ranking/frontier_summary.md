# Frontier-model evidence: what exists, what it shows, what is missing

Generated 2026-07 from `results/merged_ranking/auction_cells.csv` (seed 1299 pipeline;
see `_auction_cells_caveats.md` for provenance rules). Companion to
`plan/FRONTIER_RUNBOOK.md`, which specifies the not-yet-run frontier intervention
battery.

## 1. The only genuine gpt-5-mini data: 7 robustness mechanism cells

**No gpt-5-mini intervention cells exist anywhere in the repo.** The source
previously billed as gpt-5-mini interventions
(`recovered_logs/experiment_logs_with_explanation/V10/`) is **GPT-4o** in every
run's `config.yaml` (all 22 configs), and 14 of its 22 run timestamps duplicate
`experiment_logs/V10/`. Any paper claim built on that source as "gpt-5-mini" is
wrong and must be removed. The genuine gpt-5-mini data are exactly the seven
mechanism cells below (`robustness_logs/*_gpt5mini`, source `robustness` in
`auction_cells.csv`). Both ascending-clock gpt-5-mini directories are empty
shells (no raw data, no results CSV) — **there is no gpt-5-mini clock data.**

| Cell | Format | n bids | Mean dev vs truthful ($) | SMAD (%) | Equilibrium benchmark | Dev vs benchmark |
|---|---|---:|---:|---:|---|---|
| `spsb_ipv_gpt5mini` | SPSB, IPV, n=3 | 87 | −0.05 | 0.2 | truthful (dominant) | — |
| `spsb_apv_gpt5mini` | SPSB, APV, n=3 | 87 | −0.34 | 1.4 | truthful (dominant) | — |
| `fpsb_ipv_gpt5mini` | FPSB, IPV, n=3 | 87 | −8.53 | 34.8 | RNE b\*=(n−1)/n·v | mean +0.002, SMAD_RNE 0.11% |
| `third_price_ipv_gpt5mini` | TPSB, IPV, n=5 | 130 | +4.39 | 26.5 | RNE b\*=(n−1)/(n−2)·v | mean −4.11 (capped −2.28), SMAD_RNE 18.2% |
| `third_price_ipv_gpt5mini_3player` | TPSB, IPV, n=3 | 87 | +14.76 | 60.2 | RNE b\*=2v (capped at $49) | mean −10.87 (capped −0.22), SMAD_RNE 22.5% |
| `common_value_first_gpt5mini` | CV first-price, n=3 | 90 | −2.91 | 36.6 | none (descriptive; dev = bid − signal) | — |
| `common_value_second_gpt5mini` | CV second-price, n=3 | 90 | −2.60 | 36.9 | none (descriptive) | — |

All contrasts vs the same-family `spsb_ipv` baseline are in `auction_cells.csv`
(FPSB and both TPSB cells differ from SPSB at p < 0.001, Welch and MW; TPSB n=3
Cohen's d = 1.72).

## 2. Interpretation (canonical, per the merged-ranking pass)

gpt-5-mini **masters the dominant-strategy sealed-bid auction** — SPSB-IPV is
near-perfect (mean dev −$0.05, SMAD 0.2%; 98.9% of bids within 2% of value) and
FPSB bids sit almost exactly on the risk-neutral equilibrium shading rule
(deviation from b\* of +$0.002 on average, SMAD_RNE 0.11%) — **yet it still
fails the harder third-price format**: at n=3 it overbids value by +$14.76 on
average (SMAD 60.2%, 78% of bids above value) while remaining well short of the
equilibrium b\*=2v, and the n=5 cell shows the same pattern at smaller scale.
Common-value cells are noisy (SMAD ≈ 37%) with the usual dispersion.

**Scope-condition story:** frontier reasoning does **not** uniformly dissolve
the bounded-rationality constraints the paper studies; it dissolves them where
the dominant (or textbook equilibrium) strategy is standard training-corpus
material, and leaves large deviations where the equilibrium logic is
non-textbook (third-price). The constraints migrate rather than vanish. This
replaces the older framing of gpt-5-mini as uniformly "near-optimal".

## 3. Claims that do NOT survive this accounting (integrator checks)

1. **"mean SMAD 6.68%" for gpt-5-mini** (currently in `01_intro.tex` fn.,
   `08_discussion.tex`, `appendix_ablations.tex`): not reproducible from the
   seven genuine cells. Their unweighted mean SMAD is **28.1%**, and the
   fidelity-battery average cannot be formed at all because the two clock cells
   have no data. Table `tab:models`' gpt-5-mini column needs recomputation from
   the rows above (or the clock cells rerun; see runbook §5).
2. **"near-perfect performance in the ascending-clock ... formats"**
   (`appendix_ablations.tex`): no gpt-5-mini clock data exists. The
   near-perfect claim is supportable only for SPSB and (vs RNE) FPSB.
3. **Anything sourced to `recovered_logs/experiment_logs_with_explanation`
   as gpt-5-mini**: that source is GPT-4o (see §1).
4. Note for the facts-sheet record: the CSV's RNE columns put gpt-5-mini's FPSB
   *at* the RNE benchmark (mean dev vs b\* = +$0.002), i.e. shading is
   equilibrium-consistent rather than excessive; the −$8.53 figure is the
   deviation from truthful bidding.

## 4. Frontier intervention cells: do not exist yet

No intervention/scaffold cells (menu, safety, tree, beliefs, clock-framing,
OSP-format) have been run on gpt-5-mini or any newer frontier model, and no
frontier DA cells exist. This machine has no API keys, so nothing was launched.
A complete, ready-to-launch battery is prepared:

- Configs: `Engineering_simplicity/engineer_simplicity-main/configs_auction/frontier/`
  and `configs_da/frontier/` — {claude-sonnet-5, gpt-5-mini, gpt-5,
  gemini-2.5-flash} × {spsb, ascending-clock-closed, payoff safety, payoff
  tree, 2nd-order beliefs, menu, clock-framing (+3 axis baselines)} and
  × {direct_null, osp_choice_fixed, direct_menu_property, textbook_sp}, K=50.
- Launch, key setup, cost estimates, and fold-in commands:
  `plan/FRONTIER_RUNBOOK.md`.

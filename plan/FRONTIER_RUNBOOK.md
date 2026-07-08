# FRONTIER RUNBOOK — intervention battery on frontier models

Status (2026-07): **prepared, not launched.** This machine has no API keys, and
`edsl` is not installed here. Everything below is ready to execute on a
key-provisioned machine. No frontier intervention data exists yet anywhere in
the repo (see `results/merged_ranking/frontier_summary.md`); the only genuine
gpt-5-mini data are the 7 robustness mechanism cells in
`results/merged_ranking/auction_cells.csv`. Do **not** treat
`recovered_logs/experiment_logs_with_explanation/` as gpt-5-mini — it is GPT-4o.

All commands run from
`Engineering_simplicity/engineer_simplicity-main/` (configs use relative paths:
`Prompt/`, `rule_template/`, `experiment_logs/`).

---

## 1. What is prepared

### Auction battery — `configs_auction/frontier/<model>/*.yaml`

4 models × 10 cells, K=50 repetitions, 3 bidders, seeds as in the canonical
grid (1299 private / 1399 affiliated). Cells per model:

| Config | Cell (merged-ranking rung) | Cloned from |
|---|---|---|
| `spsb_apv.yaml` | dedicated `spsb` baseline (OSP-comparison baseline, F3 convention) | `configs_auction/sealedbid/` |
| `ascending_clock_closed.yaml` | OSP extensive form (rung A); reps 40→50 | `configs_auction/acb/` |
| `axis2_forward_onestep.yaml` | Payoff Safety (rung B2) | `interventions_gpt4o/` |
| `axis2_forward_tree.yaml` | Payoff Tree (rung C1) | `interventions_gpt4o/` |
| `axis3_beliefs_secondorder.yaml` | second-order beliefs | `interventions_gpt4o/` |
| `intervention_menu.yaml` | Menu restatement (rung B1) | `interventions_gpt4o/` |
| `intervention_proxy_breitmoser.yaml` | Clock-framing (rung B3) | `interventions_gpt4o/` |
| `axis1_contingent_baseline.yaml` | axis-1 baseline (contrast cell) | `interventions_gpt4o/` |
| `axis2_forward_baseline.yaml` | axis-2 baseline (contrast cell) | `interventions_gpt4o/` |
| `axis3_beliefs_baseline.yaml` | axis-3 baseline (contrast cell) | `interventions_gpt4o/` |

The three axis-baseline cells go beyond the minimal 7-cell spec **on purpose**:
`analysis/build_auction_cells.py` contrasts `axisK_*` treatments against the
same model's `axisK_*_baseline`, and menu / clock-framing /
ascending-clock-closed against the same model's `POOLED_axis_baseline`
(concatenated axis1+2+3 baselines). Without them the frontier treatment cells
would land in `auction_cells.csv` with empty baseline/contrast columns. If
budget forces a cut, drop `axis1_contingent_baseline` first (no axis-1
treatment is in this battery; it only sharpens the pooled baseline).

Rule templates: all referenced `special_name` templates resolve under
`rule_template/auctions/` per `docs/INTERVENTION_TAXONOMY.md` conventions;
`axis2_forward_*` prompt text ships inside the run pipeline the same way the
four existing model grids were produced (the V12 cells in
`experiment_logs/{claude,gemini,gemma,gpt4o}/axis2_forward_*` were generated
from these very config patterns).

### DA battery — `configs_da/frontier/<model>/*.yaml`

4 models × 4 cells, K=50 markets, 4×4 students/schools, seed_base 3000,
`global_ranking.strategy: fixed`:

| Config | Cell | Cloned from |
|---|---|---|
| `da_direct_null.yaml` | direct-revelation null baseline | `configs_da/gpt4o/da_direct_null.yaml` |
| `da_osp_choice_fixed.yaml` | pick-protocol OSP (experiment/condition name kept as `osp_baseline` for alignment with existing cells) | `configs_da/gpt4o/da_osp_baseline.yaml` |
| `da_direct_menu_property.yaml` | menu WITH invariance statement (E7 improver) | `configs_da/gpt4o/` |
| `da_direct_textbook_sp.yaml` | textbook strategy-proofness description (0.0% cell for all four incumbent models) | `configs_da/gpt4o/` |

### Models

| Config dir | `llm:` block | Status |
|---|---|---|
| `claude_sonnet5/` | `model: claude-sonnet-5`, `service_name: anthropic` | exact current Anthropic API id (no date suffix) |
| `gpt5mini/` | `model: gpt-5-mini` (edsl default service = openai) | matches existing `configs/robustness/*_gpt5mini.yaml`; API ignores temperature |
| `gpt5/` | `model: gpt-5` | **VERIFY-MODEL-ID** before launch (bare id vs dated snapshot; edsl support) |
| `gemini25flash/` | `model: gemini-2.5-flash`, `service_name: google` | **VERIFY-MODEL-ID** before launch |

---

## 2. Environment / API keys

The runner code reads **no** keys directly; every call goes through
`edsl.Model(model, temperature, service_name=...)`
(`src/util_plan.py:1317-1323`, `src/util_da.py:1291-1294`). edsl resolves
credentials from the environment (or a `.env` in the working directory):

```bash
export OPENAI_API_KEY=...      # gpt-5 / gpt-5-mini cells — AND required for EVERY battery:
                               # the answer-extraction model is hard-coded gpt-4o-mini
                               # (src/util_plan.py extraction_model_name, src/util_da.py Model("gpt-4o-mini"))
export ANTHROPIC_API_KEY=...   # claude-sonnet-5 cells (service_name: anthropic)
export GOOGLE_API_KEY=...      # gemini-2.5-flash cells (service_name: google)
```

Verify the exact key-name mapping of the installed edsl version before spending
budget (edsl is not installed on the machine this runbook was written on):

```bash
pip install edsl pandas pyyaml            # if missing
python3 -c "from edsl.enums import service_to_api_keyname; print(service_to_api_keyname)"
python3 -c "from edsl import Model; print([s for s in Model.services()])"
```

Smoke-test one repetition per provider before the full battery:

```bash
cd Engineering_simplicity/engineer_simplicity-main
python3 new/main.py --config configs_auction/frontier/gpt5mini/spsb_apv.yaml --repetitions 1
python3 new/main.py --config configs_auction/frontier/claude_sonnet5/spsb_apv.yaml --repetitions 1
python3 new/main.py --config configs_auction/frontier/gemini25flash/spsb_apv.yaml --repetitions 1
```

---

## 3. Launch commands

### Auction (batch controller: `new/task_controller.py`)

One battery per model; the controller skips already-completed cells
(`--force-rerun` to override) and writes a JSON report:

```bash
cd Engineering_simplicity/engineer_simplicity-main
for M in gpt5mini claude_sonnet5 gemini25flash gpt5; do
  python3 new/task_controller.py \
    --configs "configs_auction/frontier/${M}/*.yaml" \
    --max-workers 2 \
    --report-output "batch_report_frontier_auction_${M}.json"
done
```

Single-cell form (equivalent to what the controller invokes internally):

```bash
python3 new/main.py --config configs_auction/frontier/claude_sonnet5/intervention_menu.yaml
```

Each run writes
`experiment_logs/<model_dir>/<experiment>/run_<timestamp>/{config.yaml,raw_data/,results/*.csv}`
and auto-exports the results CSV (`new/main.py` → `export_experiment_results`).

### DA (batch runner: `src/run_da_batch.py`)

```bash
cd Engineering_simplicity/engineer_simplicity-main
for M in gpt5mini claude_sonnet5 gemini25flash gpt5; do
  python3 src/run_da_batch.py configs_da/frontier/${M}/*.yaml
done
```

Output: `experiment_logs/da/<model_dir>/<condition>/` (JSON per market),
matching the layout `analysis/build_da_cells.py` walks.

Run order recommendation: `gpt5mini` first (cheapest; validates plumbing and
**fills the two empty gpt-5-mini clock cells** flagged in
`_auction_cells_caveats.md` §3), then `gemini25flash`, `claude_sonnet5`, `gpt5`.

---

## 4. Call counts and cost (order-of-magnitude)

Mechanics: `plan_reflection` issues **one** free-text completion per
bidder-decision (plan+action in a single response; a retry call only on parse
failure), plus a `gpt-4o-mini` extraction call on some paths. The clock cell
uses survey mode (15 price points in one survey per bidder).

Per model:

| Battery | Primary completions | + extraction/retry margin |
|---|---:|---:|
| Auction: 9 sealed cells × 50 reps × 3 bidders | 1,350 | ~×2 |
| Auction: 1 clock cell × 50 reps × 3 bidders | 150 | ~×2 |
| DA: 3 direct cells × 50 markets × 4 students | 600 | ~×2 |
| DA: 1 pick-protocol OSP cell (~350 informative picks per 50 markets, cf. E9) | ~400–800 | ~×2 |
| **Total per model** | **~2,500–3,000** | **~5,000–6,000 calls** |

Token assumption: ~2.5K input / ~0.6K output per primary call → ≈7M in / 1.7M
out per model across both domains (with margin). Rough cost per model at
mid-2026 list prices (**verify current price sheets before launch**):

| Model | $/M in / out (assumed) | Est. cost, both batteries |
|---|---|---:|
| gpt-5-mini | 0.25 / 2 | ~$5 |
| gemini-2.5-flash | 0.30 / 2.50 | ~$6 |
| gpt-5 | 1.25 / 10 (VERIFY) | ~$26 |
| claude-sonnet-5 | 3 / 15 (intro 2 / 10 through 2026-08-31) | ~$38 (intro ~$26) |
| gpt-4o-mini extraction (all models) | 0.15 / 0.60 | ~$3 total |

**Full battery, all four models, both domains: roughly $75–120 including
retries.** Wall-clock: hours, not days (max_workers 2–4; providers rate-limit
the reasoning models hardest).

---

## 5. Fold-in

1. **One-time edit** — register the frontier log folders in
   `analysis/build_auction_cells.py` (`ES_MODEL_DIRS`, ~line 84):

   ```python
   ES_MODEL_DIRS = {
       "claude": "claude-3-5-haiku-20241022",
       "gemini": "gemini-2.0-flash",
       "gemma": "google/gemma-3-27b-it",
       "gpt4o": "gpt-4o",
       # frontier battery (plan/FRONTIER_RUNBOOK.md):
       "claude_sonnet5": "claude-sonnet-5",
       "gpt5mini": "gpt-5-mini",
       "gpt5": "gpt-5",
       "gemini25flash": "gemini-2.5-flash",
   }
   ```

   Optionally add pretty labels to `MODEL_LABELS` in
   `analysis/build_da_cells.py` (~line 51); unknown folders fall back to the
   folder name, so this is cosmetic.

2. **Rebuild the cells** (from the repo root):

   ```bash
   python3 analysis/build_auction_cells.py   # -> results/merged_ranking/auction_cells.csv + auction_cells_summary.md
   python3 analysis/build_da_cells.py        # -> results/merged_ranking/da_cells.csv + da_cells_summary.md
   ```

   Sanity check: `grep -c "claude-sonnet-5" results/merged_ranking/auction_cells.csv`
   should return ≥10; frontier treatment rows must have non-empty
   `baseline_experiment` / `welch_p` columns (if empty, the axis-baseline cells
   did not complete).

3. **Downstream figures**: `results/merged_ranking/ranking_forest_data.csv`,
   `concordance.md`, and `scripts/plots/ranking_forest.py` (Figure
   `fig:ranking`) were produced by the merged-ranking analysis pass, not by the
   two build scripts — extending the forest to frontier models requires
   regenerating those inputs after step 2.

4. Update `results/merged_ranking/frontier_summary.md` with the new cells and
   retire its "do not exist yet" section.

---

## 6. Paper items these results retire

- **plan/plan.md §Experiments (line ~231)** — "gpt-5-mini on 3–4 key levers
  (ranking flattens at the frontier — measured scope condition)": directly
  executed (and extended to three additional frontier models).
- **`08_discussion.tex` frontier-compression scope paragraph** — currently
  argues from *baseline* play only that "at the frontier, the gaps that the
  design levers close have largely vanished". The intervention cells turn this
  from an assertion into a measurement, and per the F6 accounting the expected
  headline is *constraints migrate, not vanish* (SPSB solved; third-price
  fails), which the section's own scratch notes already anticipate.
- **`appendix_ablations.tex` / `01_intro.tex` fn. "mean SMAD 6.68%"** — the
  gpt-5-mini clock reruns (`ascending_clock_closed` cell) fill the two empty
  cells flagged in `_auction_cells_caveats.md` §3 and allow `tab:models`'
  gpt-5-mini column (and the 6.68% average) to be recomputed from data that
  actually exists.
- **`09_conclusion.tex` "frontier tracking" direction** — the claude-sonnet-5 /
  gpt-5 / gemini-2.5-flash batteries are the first re-estimation point.
- Any residual claim sourced to `recovered_logs/experiment_logs_with_explanation`
  as gpt-5-mini stays dead regardless of these runs (that source is GPT-4o).

## 7. Blocked / open items

- **No API keys on this machine** — nothing launched; §2 smoke tests are the
  first action on a provisioned machine.
- **VERIFY-MODEL-ID** comments in `configs_auction/frontier/{gpt5,gemini25flash}/`
  and `configs_da/frontier/{gpt5,gemini25flash}/` must be resolved against the
  providers' current model lists and the installed edsl version.
- edsl version pin: the incumbent grids were run on an older edsl; confirm the
  installed version still accepts `service_name` and the `Cache.write_jsonl`
  API used by `new/main.py` before the full battery.

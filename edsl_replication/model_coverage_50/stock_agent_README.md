# Stock-agent coverage

The archive identifies six distinct models from prior work. A new shared-state EDSL run completed one sealed first-price private-value auction for each of 50 unique model IDs. Every auction had three valid numeric bids, for 150 bidder interviews total. Three model IDs overlap with the archived set, giving 53 distinct model IDs across the archived and new evidence.

The final run covers OpenAI, Anthropic, Google, DeepInfra, Meta, and xAI models. Two Bedrock entries from the initial roster were not run because AWS credentials were unavailable; they were replaced with catalog-listed models from configured services. Two DeepInfra entries that timed out or returned incomplete bids were also replaced. Original and intermediate rosters and summaries are retained with the run artifacts.

Recorded model spend, including resumed calls and failed attempts retained in the cumulative cost column, is $0.691622. See `model_coverage_50/README.md` for the method, final roster, raw results, and attempt history.

## Included files

- `recorded_models.csv`
- `allocative_efficiency_summary.csv`
- `phase1_evidence_assessment.pdf`
- `model_coverage_50/`: final roster, completion summary, raw results, configurations, and archived attempts
- `run_model_coverage_50.py`

## Provenance

The archived model coverage is described in the assessment and comes from https://github.com/expectedparrot/llm-auction. The new run uses the shared-state auction code; its full method and result record are in `model_coverage_50/`.

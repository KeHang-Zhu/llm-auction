# 50-model shared-state auction coverage

## Result

The final roster contains 50 unique model IDs, and every model completed one sealed first-price private-value auction with three valid numeric bids. That is 50 auctions and 150 bidder interviews. This demonstrates that the shared-state auction can run across a broad model roster; it is not a comparison of model performance.

Final provider counts are 9 OpenAI, 5 Anthropic, 7 Google, 26 DeepInfra, 2 Meta, and 1 xAI model. The two Bedrock entries from the initial roster were omitted because AWS credentials were unavailable. Slow or incomplete DeepInfra entries were replaced with other catalog-listed models. `models_initial_roster.csv` and `summary_initial_attempt.csv` preserve the original roster and first attempt; `models_deepinfra_alternates.csv` and `summary_deepinfra_alternates.csv` preserve the intermediate alternatives. The final roster is `models.csv`, and its final outcomes are in `summary.csv`.

Recorded model spend, including resumed calls and failed attempts retained in the cumulative cost column, is **$0.691622**. The runner enforced a $50 cap. The final roster's conservative pre-run estimate was $1.52.

## Method

Each model played the same single-auction setup with three bidders using that model. The auction values were seeded and shared across models. The bidding prompts and auction mechanism came from the existing FPSB IPV experiment configuration and shared-state EDSL runner. Each model had to return three numeric bids for its roster row to count as complete.

## Files

- `models.csv`: final 50-model roster and cost assumptions.
- `summary.csv`: final status, valid bidder count, cost, and result file for each model.
- `runs/`: serialized results for final runs and retained attempts.
- `models_initial_roster.csv`, `summary_initial_attempt.csv`: original roster and first run record.
- `models_deepinfra_alternates.csv`, `summary_deepinfra_alternates.csv`: intermediate replacement roster and results.
- Numbered YAML files: per-model experiment configurations.
- `../run_model_coverage_50.py`: resumable runner, `.env` loading, xAI key alias, $50 spend cap, and per-model timeout.

From the repository root, the runner preserves already completed rows and skips previously failed rows unless `--retry-failed` is supplied:

```sh
python edsl_replication/run_model_coverage_50.py --max-spend 50
```

The repository `.env` is loaded before EDSL initializes. `GROK_API_KEY` is mapped to the `XAI_API_KEY` name expected by EDSL. Keep `.env` private and out of version control.

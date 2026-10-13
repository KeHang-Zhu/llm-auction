# EDSL shared-state auction studies

`shared_state_auctions.py` builds the EDSL machine and interview schedule for
each archived auction YAML. Sealed-bid auctions use concurrent interviews with
snapshot state; eBay/Amazon proxy auctions use serial interviews with live
public-price updates. Each repetition gets its own shared-state scope.

## Prepare the per-condition folders and papers

The setup command creates one folder per YAML condition under
`edsl_replication/studies/`, copies the configuration, writes the Python machine
factory, and renders the state diagram through EDSL's
`Machine.show_diagram()`. Where result data does not exist, it creates a
standalone setup PDF marked as awaiting inference. This command does not run
interviews or call a model.

```bash
python -m edsl_replication.setup_auction_studies
```

Each folder contains `config.yaml`, `machine_definition.py`,
`figures/state_machine.png`, `paper.tex`, and `paper.pdf`. Result-backed papers
also include raw EDSL results and auction/bidder CSV exports.

## Run a condition when ready

The individual runner uses the provider configured in the YAML and requires its
API key in `.env`. For example, run two auctions of the SPSB-IPV condition:

```bash
python -m edsl_replication.shared_state_auctions \
  configs/experiments/01_01_spsb_ipv.yaml \
  --repetitions 2 \
  --output edsl_replication/studies/spsb_ipv/raw_results.json
```

After a result file is available, generate the result-backed standalone report:

```bash
python -m edsl_replication.write_auction_paper \
  configs/experiments/01_01_spsb_ipv.yaml
```

## Run pilots for every paper condition

The pilot runner executes each of the 27 archived YAML conditions sequentially,
with two auction repetitions per condition by default. It writes results and a
standalone report under each condition's `pilot_02_auctions/` folder, keeping
previous full-run outputs in the condition folder intact. It resumes from a
condition's saved raw results if interrupted.

```bash
python -m edsl_replication.run_auction_pilots
```

Use `--repetitions N` to change the pilot size or `--only condition_slug` to run
selected conditions. Progress and failures are recorded in
`edsl_replication/pilot_status.json`.

The shared-state port preserves the archived configurations and seeded value
draws while changing some details of elicitation and execution. The result
papers record these limits, including two-question plan/bid elicitation for
sealed bids, numeric increment validation, and deterministic tie-breaking.

"""Finish the pilot's malformed terminal forecasts without new model calls.

The archived raw responses remain untouched. When EDSL parsed a literal null for
a forecast beyond the last period, this utility fills that field with the market
rule's known $14 redemption amount, records the repair, submits the accepted
decision, and lets the ordinary EDSL workflow run complete the settlement.
"""

import json
from pathlib import Path

from edsl.sharedstate import SQLiteStateBackend
from edsl.workflows import WorkflowExperiment
from edsl.workflows.coordinator import WorkflowCoordinator
from edsl.workflows.store import SQLiteWorkflowStore


def raw_decision(result):
    response = result["raw_model_response"]["decision_raw_model_response"]
    content = response["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(content)


def main():
    output = Path(__file__).parent / "pilot_01"
    experiment = WorkflowExperiment.load(output / "experiment.json")
    store = SQLiteWorkflowStore(output / "workflow.sqlite")
    backends = {
        state.state_id: SQLiteStateBackend(
            state, output / f"state-{i}.sqlite", runtime=experiment.runtime
        )
        for i, state in enumerate(experiment.states)
    }
    coordinator = WorkflowCoordinator.restore(
        "experiment", store, state_backends=backends
    )
    coordinator.recover("experiment", max_attempts=3)

    latest = {}
    for line in (output / "model-calls.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["step"] == "orders-30":
            latest[row["participant"]] = row["result"]

    recovery_path = output / "recovery.json"
    previous_repairs = (
        json.loads(recovery_path.read_text()).get("repairs", [])
        if recovery_path.exists()
        else []
    )
    repaired = list(previous_repairs)
    known_repairs = {(r["participant"], r["field"]) for r in repaired}
    for participant, result in latest.items():
        decision = result.get("answer", {}).get("decision")
        if decision is None:
            decision = raw_decision(result)
        for key in ("forecast_2", "forecast_5", "forecast_10"):
            pair = (participant, key)
            if decision.get(key) is None and pair not in known_repairs:
                repaired.append({"participant": participant, "field": key, "value": 14.0})
                known_repairs.add(pair)

    pending = store.pending_outbox("experiment")
    for outbox in pending:
        opened = coordinator.open(outbox["work_item_id"])
        if opened.step_name != "orders-30":
            raise RuntimeError(f"unexpected pending step: {opened.step_name}")
        result = latest[opened.participant_id]
        decision = result.get("answer", {}).get("decision")
        if decision is None:
            decision = raw_decision(result)
        for key in ("forecast_2", "forecast_5", "forecast_10"):
            if decision.get(key) is None:
                decision[key] = 14.0
        if decision.get("forecast_0") is None:
            raise ValueError(f"current-price forecast missing for {opened.participant_id}")
        coordinator.submit(
            opened.id,
            {"decision": decision},
            idempotency_key=f"midpoint-news-terminal-repair:{opened.participant_id}",
        )

    completion = experiment.run(output, resume=True)
    (output / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    (output / "recovery.json").write_text(
        json.dumps(
            {
                "status": "completed" if completion["status"] == "completed" else completion["status"],
                "method": "imputed only terminal-horizon forecasts from the fixed redemption rule; no new model calls",
                "repairs": repaired,
                "completion": completion,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"completion": completion, "repairs": repaired}, indent=2))


if __name__ == "__main__":
    main()

# Deferred acceptance in a school-choice market

This study uses a new EDSL `Machine` to test a market mechanism that has no
prices or trades. Twelve students rank four schools; each school has three
seats and a strict priority ranking over students. Each preference profile is
run twice, once with student-proposing deferred acceptance and once with
school-proposing deferred acceptance.

The deterministic pilot uses seeded synthetic preferences and priorities to
check the transition rules independently of model output. The LLM pilot adds a
structured EDSL `QuestionRank` interview for twelve student personas, saves
the resulting rankings, and runs both proposer sides on the same LLM profile.
School priorities remain seeded with `42017` for a controlled comparison.

## Mechanism

In student-proposing deferred acceptance, an unassigned student proposes to
their highest-ranked school they have not yet approached. Each school tentatively
holds its highest-priority applicants up to capacity and rejects the rest.
Rejected students continue down their lists. The process stops when every
student is held or has exhausted their list.

In school-proposing deferred acceptance, a school with an open seat proposes to
the next student on its priority list. Each student tentatively keeps their
most-preferred offer and rejects any lower-ranked offer. A school whose offer
is rejected continues to its next student. With 12 seats and complete strict
rankings on both sides, both processes fill all seats.

The full proposal loop is an EDSL `iterate` expression in each Machine's
`close_effects`. The expression selects the next eligible student or school,
forms a proposal, updates the allocation record, appends a proposal event, and
checks its stop condition. The loop has a finite explicit step bound. The
Python pilot initializes the generic EDSL Runtime and invokes the standard
Machine close transition; it no longer selects proposers or calls proposal
commands. Both Machines declare `algorithms=()`.

The allocation record contains assignments, school holds, proposer cursors,
the student proposal queue, the proposal log, and a terminal flag. A matching
is stable when there is no student-school pair where the student prefers that
school to their assignment and that school has a free seat or prefers the
student to one of its current assignees. The iteration runs atomically inside
the close transition, so intermediate matching states appear in the final
proposal log rather than as separately persisted snapshots.

## Pilot result

Both mechanisms were run on the same preference and priority profile. Each
filled all 12 seats, stayed within capacity, and had zero blocking pairs.

| Outcome | Student-proposing | School-proposing |
|---|---:|---:|
| Students assigned their first choice | 11 of 12 | 10 of 12 |
| Mean student choice rank (1 = best) | 1.17 | 1.42 |
| Proposal transitions | 14 | 32 |
| Blocking pairs | 0 | 0 |

The deterministic pilot results above are from the synthetic profile. The LLM
pilot is documented in [`pilot_llm_01/report.pdf`](pilot_llm_01/report.pdf),
with its complete preference profile and Machine outcomes in
[`pilot_llm_01/results.json`](pilot_llm_01/results.json). In that run, the
student-proposing result assigns 12 of 12 first choices and the school-proposing
result assigns 7 of 12. Both are stable. This is a mechanism and data-path
demonstration, not evidence that LLM personas represent real student choice.
For a code-level account of Machine state, serialization, runtime semantics,
and the Machine-declared iteration, see
[`machine_technical_note.pdf`](machine_technical_note.pdf).

## Files

- `machine_definition.py`: both callback-free EDSL Machines and seeded profiles.
- `run_pilot.py`: generic Runtime initialization, Machine close, results, and stability check.
- `test_machine_conformance.py`: independent Python DA references and conformance tests.
- `pilot_01/results.json`: complete pilot preferences, priorities, assignments, metrics, and stability checks.
- `llm_pilot.py`: LLM persona interviews, preference validation, and both Machine runs.
- `pilot_llm_01/`: elicited rankings, results, EDSL local object-store output, and standalone PDF writeup.

## Run and test

Run the deterministic pilot from the repository root:

```sh
PYTHONPATH=edsl_replication/studies/school_choice_deferred_acceptance \
  python3 edsl_replication/studies/school_choice_deferred_acceptance/run_pilot.py
```

Run the LLM pilot (requires provider credentials in the local environment):

```sh
PYTHONPATH=edsl_replication/studies/school_choice_deferred_acceptance \
  python3 edsl_replication/studies/school_choice_deferred_acceptance/llm_pilot.py
```

Reuse already saved rankings without making new model calls by adding
`--reuse-preferences`.

Run the conformance suite from the repository root:

```sh
PYTHONPATH=edsl_replication/studies/school_choice_deferred_acceptance \
  python3 -m unittest -v test_machine_conformance
```

The tests compare Machine assignments with independent textbook reference
implementations, verify stability and capacity, check student-optimality for
this pair of proposer-side outcomes, confirm that the same profile is used for
both mechanisms, and round-trip each serialized Machine through JSON. The
serialized Machine includes the bounded loop as EDSL `iterate` expressions.

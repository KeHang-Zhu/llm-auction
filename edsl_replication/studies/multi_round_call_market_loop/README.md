# Multi-round call market loop pilot

This small runner-capability pilot puts the repeated market transition inside
one EDSL `Machine` close expression. A generic caller initializes the machine
and invokes `Runtime.close_result` once. The machine's bounded `iterate`
selects the current round's orders, identifies the best bid and ask, determines
whether they cross, settles a one-unit midpoint trade when they do, appends a
round record, and carries balances into the next iteration.

The three fixed rounds deliberately include two trades and one no-trade round:

| Round | Best bid | Best ask | Result |
|---|---:|---:|---|
| 1 | 1,100 cents | 1,000 cents | Trade at 1,050 cents |
| 2 | 900 cents | 1,200 cents | No trade; balances carry forward |
| 3 | 1,300 cents | 1,200 cents | Trade at 1,250 cents |

The fixed order schedule is held in the Machine constants. That makes the
pilot deterministic and isolates whether the EDSL expression can drive a
multi-round mechanism itself. It does not yet test LLM decision-making or a
workflow that gathers fresh model decisions between rounds. The existing
30-round market covers model decisions but schedules its phases in Python.

Run the pilot from this directory:

```sh
PYTHONPATH=. python run_pilot.py
```

The output reports the tape and ending accounts. The expected ending cash is
2,200 cents for trader A, 1,800 cents for trader B, and 2,000 cents each for C
and D. Total cash remains 8,000 cents and total inventory remains four shares.

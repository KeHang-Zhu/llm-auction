"""Run student- and school-proposing DA through each Machine's DSL loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edsl.sharedstate import Runtime

from machine_definition import CAPACITY, SCHOOLS, STUDENTS, build_machine


def run_machine(proposer_side: str, seed: int = 42017, student_preferences=None):
    machine = build_machine(
        seed=seed,
        proposer_side=proposer_side,
        student_preferences_override=student_preferences,
    )
    runtime = Runtime()
    state = runtime.initial_state(machine)
    result = runtime.close_result(machine, state)
    if result.event["status"] != "applied":
        raise RuntimeError(f"Machine close did not apply: {result.event}")
    state = result.state
    return machine, state


def blocking_pairs(assignments, student_preferences, school_priority_ranks, capacities):
    holds = {school: [] for school in SCHOOLS}
    for student, school in assignments.items():
        if school is not None:
            holds[school].append(student)
    violations = []
    for student, assigned_school in assignments.items():
        for school in student_preferences[student]:
            if school == assigned_school:
                break
            incumbents = holds[school]
            has_room = len(incumbents) < capacities[school]
            school_prefers_student = bool(incumbents) and (
                school_priority_ranks[school][student]
                < max(school_priority_ranks[school][other] for other in incumbents)
            )
            if has_room or school_prefers_student:
                violations.append((student, school))
    return violations


def summarize(proposer_side: str, seed: int, student_preferences=None):
    machine, state = run_machine(proposer_side, seed, student_preferences)
    allocation = state["allocation"]
    assignments = allocation["assignments"]
    preferences = machine.constants["student_preferences"]
    student_ranks = machine.constants["student_ranks"]
    priority_ranks = machine.constants["school_priority_ranks"]
    capacities = machine.constants["capacities"]
    rank_by_student = {
        student: student_ranks[student][school]
        for student, school in assignments.items()
    }
    school_counts = {
        school: len(allocation["school_holds"][school]) for school in SCHOOLS
    }
    blocking = blocking_pairs(assignments, preferences, priority_ranks, capacities)
    if blocking:
        raise RuntimeError(f"Machine output is unstable: blocking pairs {blocking}")
    if any(count > capacities[school] for school, count in school_counts.items()):
        raise RuntimeError("Machine output exceeds a school capacity")
    if any(school is None for school in assignments.values()):
        raise RuntimeError("Machine ended with unassigned students")

    priority_rank_by_school = {
        school: {
            student: priority_ranks[school][student]
            for student in allocation["school_holds"][school]
        }
        for school in SCHOOLS
    }
    mean_priority_rank = {
        school: sum(ranks.values()) / len(ranks) if ranks else None
        for school, ranks in priority_rank_by_school.items()
    }
    return {
        "proposer_side": proposer_side,
        "seed": seed,
        "student_preferences": preferences,
        "school_priorities": machine.constants["school_priorities"],
        "assignments": assignments,
        "students_by_school": allocation["school_holds"],
        "proposal_log": allocation["proposal_log"],
        "student_rank_by_assignment": rank_by_student,
        "first_choice_assignments": sum(rank == 0 for rank in rank_by_student.values()),
        "mean_student_rank_zero_based": sum(rank_by_student.values()) / len(STUDENTS),
        "mean_student_rank_one_based": sum(rank + 1 for rank in rank_by_student.values()) / len(STUDENTS),
        "school_counts": school_counts,
        "mean_school_priority_rank_zero_based": mean_priority_rank,
        "proposal_count": len(allocation["proposal_log"]),
        "blocking_pair_count": len(blocking),
        "finished": allocation["finished"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42017)
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).parent / "pilot_01" / "results.json",
    )
    args = parser.parse_args()
    student = summarize("student", args.seed)
    school = summarize("school", args.seed)
    if student["student_preferences"] != school["student_preferences"]:
        raise RuntimeError("proposer-side comparison changed student preferences")
    if student["school_priorities"] != school["school_priorities"]:
        raise RuntimeError("proposer-side comparison changed school priorities")
    result = {
        "market": {"students": len(STUDENTS), "schools": len(SCHOOLS), "capacity_each": CAPACITY},
        "profile_seed": args.seed,
        "student_proposing": student,
        "school_proposing": school,
        "same_profile": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

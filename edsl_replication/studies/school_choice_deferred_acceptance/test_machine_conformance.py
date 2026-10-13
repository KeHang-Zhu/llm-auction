"""Conformance tests against independent deferred-acceptance references."""

from __future__ import annotations

import unittest
import json

from machine_definition import CAPACITY, SCHOOLS, STUDENTS, build_machine
from run_pilot import blocking_pairs, run_machine


def student_proposing_reference(preferences, priorities):
    """Small textbook reference: unmatched students propose in queue order."""
    held = {school: [] for school in SCHOOLS}
    assignment = {student: None for student in STUDENTS}
    next_choice = {student: 0 for student in STUDENTS}
    priority_rank = {
        school: {student: rank for rank, student in enumerate(priorities[school])}
        for school in SCHOOLS
    }
    queue = list(STUDENTS)
    while queue:
        student = queue.pop(0)
        if assignment[student] is not None:
            continue
        if next_choice[student] == len(preferences[student]):
            continue
        school = preferences[student][next_choice[student]]
        next_choice[student] += 1
        candidates = held[school] + [student]
        candidates.sort(key=priority_rank[school].__getitem__)
        held[school] = candidates[:CAPACITY]
        for candidate in candidates:
            assignment[candidate] = school if candidate in held[school] else None
            if assignment[candidate] is None and next_choice[candidate] < len(preferences[candidate]):
                queue.append(candidate)
    return assignment, held


def school_proposing_reference(preferences, priorities):
    """Textbook college-proposing DA with unit-demand students."""
    held = {school: [] for school in SCHOOLS}
    assignment = {student: None for student in STUDENTS}
    next_student = {school: 0 for school in SCHOOLS}
    rank = {
        student: {school: index for index, school in enumerate(preferences[student])}
        for student in STUDENTS
    }
    while True:
        eligible = [
            school for school in SCHOOLS
            if len(held[school]) < CAPACITY
            and next_student[school] < len(priorities[school])
        ]
        if not eligible:
            break
        school = eligible[0]
        student = priorities[school][next_student[school]]
        next_student[school] += 1
        old_school = assignment[student]
        if old_school is None or rank[student][school] < rank[student][old_school]:
            if old_school is not None:
                held[old_school].remove(student)
            assignment[student] = school
            held[school].append(student)
    return assignment, held


class DeferredAcceptanceConformanceTests(unittest.TestCase):
    seed = 42017

    def test_machine_definitions_are_callback_free_and_json_serializable(self):
        for side in ("student", "school"):
            machine = build_machine(self.seed, side)
            self.assertEqual(machine.algorithms, ())
            serialized = machine.to_json()
            self.assertIn('"op": "iterate"', serialized)
            self.assertIn("school_priority_ranks", serialized)
            restored = type(machine).from_json(serialized)
            self.assertEqual(json.loads(restored.to_json()), json.loads(serialized))
            self.assertEqual(set(restored.commands), set(machine.commands))

    def test_student_proposing_matches_reference_and_is_stable(self):
        machine, state = run_machine("student", self.seed)
        allocation = state["allocation"]
        reference_assignment, reference_holds = student_proposing_reference(
            machine.constants["student_preferences"],
            machine.constants["school_priorities"],
        )
        self.assertTrue(allocation["finished"])
        self.assertEqual(allocation["assignments"], reference_assignment)
        self.assertEqual(allocation["school_holds"], reference_holds)
        self.assertEqual(len(allocation["proposal_log"]), 14)
        self.assertEqual(
            blocking_pairs(
                allocation["assignments"],
                machine.constants["student_preferences"],
                machine.constants["school_priority_ranks"],
                machine.constants["capacities"],
            ),
            [],
        )

    def test_school_proposing_matches_reference_and_is_stable(self):
        machine, state = run_machine("school", self.seed)
        allocation = state["allocation"]
        reference_assignment, reference_holds = school_proposing_reference(
            machine.constants["student_preferences"],
            machine.constants["school_priorities"],
        )
        self.assertTrue(allocation["finished"])
        self.assertEqual(allocation["assignments"], reference_assignment)
        self.assertEqual(allocation["school_holds"], reference_holds)
        self.assertEqual(len(allocation["proposal_log"]), 32)
        self.assertEqual(
            blocking_pairs(
                allocation["assignments"],
                machine.constants["student_preferences"],
                machine.constants["school_priority_ranks"],
                machine.constants["capacities"],
            ),
            [],
        )

    def test_proposer_side_changes_outcome_but_uses_same_profile(self):
        student_machine, student_state = run_machine("student", self.seed)
        school_machine, school_state = run_machine("school", self.seed)
        student_allocation = student_state["allocation"]
        school_allocation = school_state["allocation"]
        self.assertEqual(
            student_machine.constants["student_preferences"],
            school_machine.constants["student_preferences"],
        )
        self.assertEqual(
            student_machine.constants["school_priorities"],
            school_machine.constants["school_priorities"],
        )
        student_ranks = student_machine.constants["student_ranks"]
        for student in STUDENTS:
            self.assertLessEqual(
                student_ranks[student][student_allocation["assignments"][student]],
                student_ranks[student][school_allocation["assignments"][student]],
            )
        self.assertNotEqual(
            student_allocation["assignments"], school_allocation["assignments"]
        )
        self.assertEqual(
            sum(len(held) for held in student_allocation["school_holds"].values()),
            len(STUDENTS),
        )
        self.assertEqual(
            sum(len(held) for held in school_allocation["school_holds"].values()),
            len(STUDENTS),
        )

    def test_closed_machine_is_idempotent(self):
        machine, state = run_machine("student", self.seed)
        from edsl.sharedstate import Runtime

        runtime = Runtime()
        result = runtime.close_result(machine, state)
        self.assertEqual(result.event["status"], "noop")
        self.assertEqual(result.state, state)


if __name__ == "__main__":
    unittest.main()

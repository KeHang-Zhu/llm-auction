"""Callback-free EDSL Machines for student- or school-proposing DA.

The complete bounded proposal loop is an EDSL ``iterate`` expression in the
Machine's close effects. A generic Runtime can therefore execute the matching
without an experiment-specific Python proposal loop.
"""

from __future__ import annotations

import random

from edsl.sharedstate import (
    Machine,
    StateType,
    assign,
    choose,
    constant,
    current,
    field,
    filter_items,
    iterate,
    let,
    local,
    map_items,
    map_sequence,
    record,
    reduce,
    state_field,
    take,
)


STUDENTS = tuple(f"student-{index:02d}" for index in range(12))
SCHOOLS = tuple(f"school-{index:02d}" for index in range(4))
CAPACITY = 3


def make_preferences(seed: int = 42017, student_preferences_override=None):
    """Generate complete strict rankings, deterministically, at author time."""
    student_preferences = {}
    for student in STUDENTS:
        ranking = list(SCHOOLS)
        random.Random(f"{seed}:student:{student}").shuffle(ranking)
        student_preferences[student] = ranking

    if student_preferences_override is not None:
        if set(student_preferences_override) != set(STUDENTS):
            raise ValueError("student preference profile must include each student exactly once")
        for student, ranking in student_preferences_override.items():
            if len(ranking) != len(SCHOOLS) or set(ranking) != set(SCHOOLS):
                raise ValueError(
                    f"{student} must rank each school exactly once: {tuple(SCHOOLS)}"
                )
            student_preferences[student] = list(ranking)

    school_priorities = {}
    for school in SCHOOLS:
        ranking = list(STUDENTS)
        random.Random(f"{seed}:school:{school}").shuffle(ranking)
        school_priorities[school] = ranking

    student_ranks = {
        student: {school: rank for rank, school in enumerate(ranking)}
        for student, ranking in student_preferences.items()
    }
    school_priority_ranks = {
        school: {student: rank for rank, student in enumerate(ranking)}
        for school, ranking in school_priorities.items()
    }
    return student_preferences, student_ranks, school_priorities, school_priority_ranks


def _allocation_type():
    return StateType.record(
        {
            "queue": StateType.sequence(StateType.text()),
            "assignments": StateType.map(
                StateType.text(), StateType.optional(StateType.text())
            ),
            "school_holds": StateType.map(
                StateType.text(), StateType.sequence(StateType.text())
            ),
            "student_next_choice": StateType.map(
                StateType.text(), StateType.integer(minimum=0)
            ),
            "school_next_student": StateType.map(
                StateType.text(), StateType.integer(minimum=0)
            ),
            "proposal_log": StateType.sequence(),
            "finished": StateType.boolean(),
        }
    )


def _initial_allocation():
    return {
        "queue": list(STUDENTS),
        "assignments": {student: None for student in STUDENTS},
        "school_holds": {school: [] for school in SCHOOLS},
        "student_next_choice": {student: 0 for student in STUDENTS},
        "school_next_student": {school: 0 for school in SCHOOLS},
        "proposal_log": [],
        "finished": False,
    }


def _student_proposing_loop():
    """Return the serialized bounded DA iteration for student proposers."""
    state = local("matching")
    student = local("student")
    school = local("school")
    ranking = constant("student_preferences").get(student)
    cursor = state.get("student_next_choice").get(student)

    candidates = state.get("school_holds").get(school).appended(student)
    ranked_candidates = reduce(
        "sort_records",
        map_sequence(
            candidates,
            item="candidate",
            value_expr=record(
                student=local("candidate"),
                priority=constant("school_priority_ranks")
                .get(school)
                .get(local("candidate")),
            ),
        ),
        fields=("priority",),
        descending=(False,),
    )
    sorted_students = map_sequence(
        ranked_candidates,
        item="candidate",
        value_expr=local("candidate").get("student"),
    )
    retained = take(sorted_students, constant("capacities").get(school))
    rejected = map_sequence(
        filter_items(
            sorted_students,
            item="candidate",
            predicate=~retained.contains(local("candidate")),
        ),
        item="candidate",
        value_expr=local("candidate"),
    )

    proposal_state = let(
        "retained",
        retained,
        let(
            "rejected",
            rejected,
            record(
                queue=state.get("queue").drop_first() + local("rejected"),
                assignments=map_items(
                    state.get("assignments"),
                    key="candidate",
                    value="old_assignment",
                    key_expr=local("candidate"),
                    value_expr=choose(
                        candidates.contains(local("candidate")),
                        choose(
                            local("retained").contains(local("candidate")),
                            school,
                            None,
                        ),
                        local("old_assignment"),
                    ),
                ),
                school_holds=state.get("school_holds").with_item(
                    school, local("retained")
                ),
                student_next_choice=state.get("student_next_choice").with_item(
                    student, cursor + 1
                ),
                school_next_student=state.get("school_next_student"),
                proposal_log=state.get("proposal_log").appended(
                    record(
                        side=constant("proposer_side"),
                        proposer=student,
                        school=school,
                        outcome=choose(
                            local("retained").contains(student), "held", "rejected"
                        ),
                    )
                ),
                finished=False,
            ),
        ),
    )
    proposal = let(
        "school",
        ranking.at(cursor),
        let(
            "ranked_candidates",
            ranked_candidates,
            let("sorted_students", sorted_students, proposal_state),
        ),
    )
    step = let(
        "student",
        state.get("queue").first(),
        let(
            "ranking",
            constant("student_preferences").get(local("student")),
            let(
                "cursor",
                state.get("student_next_choice").get(local("student")),
                choose(
                    local("cursor") >= local("ranking").length(),
                    state.with_item("queue", state.get("queue").drop_first()),
                    proposal,
                ),
            ),
        ),
    )
    max_steps = (
        reduce(
            "sum",
            map_sequence(
                constant("students"),
                item="student_id",
                value_expr=constant("student_preferences")
                .get(local("student_id"))
                .length(),
            ),
        )
        + constant("students").length()
    )
    allocation = iterate(
        constant("initial_allocation"),
        state="matching",
        state_type=_allocation_type(),
        until=state.get("queue").length() == 0,
        step=step,
        max_steps=max_steps,
    )
    return allocation.with_item("finished", True)


def _school_proposing_loop():
    """Return the serialized bounded DA iteration for school proposers."""
    state = local("matching")
    school = local("school")
    student = local("student")
    active_schools = filter_items(
        constant("schools"),
        item="candidate_school",
        predicate=(
            state.get("school_holds")
            .get(local("candidate_school"))
            .length()
            < constant("capacities").get(local("candidate_school"))
        )
        & (
            state.get("school_next_student").get(local("candidate_school"))
            < constant("school_priorities").get(local("candidate_school")).length()
        ),
    )
    priority_list = constant("school_priorities").get(school)
    cursor = state.get("school_next_student").get(school)
    current_school = state.get("assignments").get(student)
    accepted = choose(
        current_school == None,
        True,
        constant("student_ranks").get(student).get(school)
        < constant("student_ranks").get(student).get(current_school),
    )

    next_state = record(
        queue=[],
        assignments=state.get("assignments").with_item(
            student, choose(accepted, school, current_school)
        ),
        school_holds=map_items(
            state.get("school_holds"),
            key="school_key",
            value="held_students",
            key_expr=local("school_key"),
            value_expr=choose(
                local("school_key") == school,
                choose(
                    accepted,
                    local("held_students").appended(student),
                    local("held_students"),
                ),
                choose(
                    accepted & (local("school_key") == current_school),
                    filter_items(
                        local("held_students"),
                        item="held_student",
                        predicate=local("held_student") != student,
                    ),
                    local("held_students"),
                ),
            ),
        ),
        student_next_choice=state.get("student_next_choice"),
        school_next_student=state.get("school_next_student").with_item(
            school, cursor + 1
        ),
        proposal_log=state.get("proposal_log").appended(
            record(
                side=constant("proposer_side"),
                proposer=school,
                student=student,
                outcome=choose(accepted, "held", "rejected"),
            )
        ),
        finished=False,
    )
    step = let(
        "school",
        active_schools.first(),
        let(
            "student",
            priority_list.at(cursor),
            next_state,
        ),
    )
    max_steps = constant("schools").length() * constant("students").length()
    allocation = iterate(
        constant("initial_allocation"),
        state="matching",
        state_type=_allocation_type(),
        until=active_schools.length() == 0,
        step=step,
        max_steps=max_steps,
    )
    return allocation.with_item("finished", True)


def build_machine(
    seed: int = 42017,
    proposer_side: str = "student",
    student_preferences_override=None,
) -> Machine:
    """Build a Machine whose close transition runs DA entirely in the DSL."""
    if proposer_side not in {"student", "school"}:
        raise ValueError("proposer_side must be 'student' or 'school'")

    preferences, student_ranks, priorities, priority_ranks = make_preferences(
        seed, student_preferences_override
    )
    side_name = f"{proposer_side}-proposing"
    capacities = {school: CAPACITY for school in SCHOOLS}
    initial = _initial_allocation()
    machine = Machine(
        name=f"SchoolChoiceDeferredAcceptance_{proposer_side.title()}Proposing",
        constants={
            "seed": seed,
            "proposer_side": side_name,
            "students": list(STUDENTS),
            "schools": list(SCHOOLS),
            "capacities": capacities,
            "initial_allocation": initial,
            "student_preferences": preferences,
            "student_ranks": student_ranks,
            "school_priorities": priorities,
            "school_priority_ranks": priority_ranks,
            "total_capacity": sum(capacities.values()),
        },
        fields={"allocation": state_field(_allocation_type(), initial)},
        commands={},
        view={
            "proposer_side": constant("proposer_side"),
            "assignments": field("allocation").get("assignments"),
            "school_holds": field("allocation").get("school_holds"),
            "proposal_log": field("allocation").get("proposal_log"),
            "finished": field("allocation").get("finished"),
            "current_identity": current("name"),
        },
        close_effects=(
            assign(
                "allocation",
                _student_proposing_loop()
                if proposer_side == "student"
                else _school_proposing_loop(),
            ),
        ),
        complete_when=field("allocation").get("finished"),
        algorithms=(),
    )
    machine.validate()
    return machine

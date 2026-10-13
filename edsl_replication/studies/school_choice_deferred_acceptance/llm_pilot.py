"""Elicit student rankings locally with an LLM, then run both DA Machines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edsl import Agent, Model, QuestionRank, Survey
from edsl.agents import AgentList
from dotenv import load_dotenv

from machine_definition import SCHOOLS, STUDENTS
from run_pilot import summarize


SEED = 42017
DEFAULT_MODEL = "gpt-4o-mini"
SERVICE = "openai"

SCHOOL_DESCRIPTIONS = {
    "school-00": (
        "Cedar STEM Academy (north): strong mathematics, computer science, labs, "
        "and robotics; structured classes and a competitive academic culture."
    ),
    "school-01": (
        "Harbor Arts and Humanities (south-central): writing, theater, visual arts, "
        "and small seminars; expressive projects and discussion-based classes."
    ),
    "school-02": (
        "Summit College Preparatory (west): broad rigorous academics, individual "
        "advising, and college preparation; organized classes and a quiet campus."
    ),
    "school-03": (
        "Riverside Community School (east): project-based learning, environmental "
        "science, outdoor activities, and arts; collaborative and flexible classes."
    ),
}

STUDENT_PROFILES = {
    "student-00": "Lives north. Loves robotics and algebra, prefers structured lessons, and values a short commute.",
    "student-01": "Lives south-central. Enjoys theater and creative writing, learns through discussion, and wants a welcoming campus.",
    "student-02": "Lives east. Interested in ecology and outdoor projects, prefers collaborative learning, and values flexible electives.",
    "student-03": "Lives west. Wants strong college advising, likes history and biology, and prefers an organized academic routine.",
    "student-04": "Lives south-central. Enjoys drawing and literature, values small classes, and wants room for creative projects.",
    "student-05": "Lives north. Interested in computers and engineering, likes hands-on labs, and prefers clear academic expectations.",
    "student-06": "Lives east. Enjoys science and community volunteering, prefers group projects, and would like outdoor activities.",
    "student-07": "Lives west. Likes mathematics and debate, values academic challenge, and wants personalized guidance about college.",
    "student-08": "Lives east. Interested in visual arts and environmental issues, prefers project-based classes, and values a collaborative school.",
    "student-09": "Lives north. Enjoys physics and coding, wants access to advanced labs, and prefers a focused learning environment.",
    "student-10": "Lives west. Enjoys writing and social studies, values supportive teachers, and wants a broad college-preparatory program.",
    "student-11": "Lives south-central. Interested in music and theater, prefers seminar discussion, and wants a school with a strong arts community.",
}


def ranking_survey():
    catalog = "\n".join(
        f"- {school}: {description}"
        for school, description in SCHOOL_DESCRIPTIONS.items()
    )
    prompt = (
        "You are choosing a public high school for yourself. Use the profile below "
        "to rank all four schools from most preferred to least preferred. Treat the "
        "listed characteristics as the available information; do not invent other "
        "school features. Rank by your own fit, not by which school you think is "
        "most selective or most likely to admit you. Make a strict ranking with no "
        "ties.\n\n"
        "YOUR STUDENT PROFILE\n{{ agent.profile }}\n\n"
        "SCHOOL CATALOG\n" + catalog
    )
    question = QuestionRank(
        question_name="school_ranking",
        question_text=prompt,
        question_options=list(SCHOOLS),
        num_selections=len(SCHOOLS),
        use_code=False,
        include_comment=False,
    )
    agents = AgentList(
        [
            Agent(
                name=student,
                traits={"student_id": student, "profile": STUDENT_PROFILES[student]},
                instruction=(
                    "You are a student making a school choice. State preferences "
                    "according to the priorities in your profile. Do not try to "
                    "game the deferred-acceptance algorithm."
                ),
            )
            for student in STUDENTS
        ]
    )
    return Survey([question]), agents


def normalize_ranking(value, student):
    if isinstance(value, dict):
        # Some QuestionRank result adapters retain a named ranking wrapper.
        value = value.get("ranking", value.get("school_ranking", value))
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{student} returned a non-list ranking: {value!r}")
    ranking = [str(choice).strip() for choice in value]
    if len(ranking) != len(SCHOOLS) or set(ranking) != set(SCHOOLS):
        raise ValueError(f"{student} did not rank each school exactly once: {ranking!r}")
    return ranking


def collect_preferences(model_name: str, object_store_root: Path):
    load_dotenv()
    # The Runner streams results into EDSL's local object store. Keep that
    # store alongside this pilot so it works in restricted environments and
    # leaves a reproducible local artifact.
    from edsl.object_store.store import ObjectStore

    object_store_root.mkdir(parents=True, exist_ok=True)
    ObjectStore.default_root = staticmethod(lambda: object_store_root)
    survey, agents = ranking_survey()
    results = (
        survey.by(agents)
        .by(Model(model_name, service_name=SERVICE, temperature=0.2))
        .run(
            cache=False,
            disable_remote_cache=True,
            disable_remote_inference=True,
            max_concurrency=4,
            stop_on_exceptions=True,
        )
    )
    if results.has_unfixed_exceptions:
        raise RuntimeError("One or more student ranking interviews failed validation")
    rankings = {}
    for result in results:
        student = result.agent.name
        rankings[student] = normalize_ranking(
            result.answer["school_ranking"], student
        )
    if set(rankings) != set(STUDENTS):
        raise RuntimeError(f"Expected rankings from all 12 students, got {len(rankings)}")
    return rankings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "pilot_llm_01",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reuse-preferences", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    preference_path = args.output_dir / "preferences.json"
    if args.reuse_preferences:
        if not preference_path.exists():
            raise FileNotFoundError(f"No saved LLM rankings found at {preference_path}")
        preferences = json.loads(preference_path.read_text())
    else:
        if preference_path.exists():
            raise FileExistsError(
                f"{preference_path} exists; use --reuse-preferences or a fresh output directory"
            )
        preferences = collect_preferences(args.model, args.output_dir / "edsl_objects")
        preference_path.write_text(json.dumps(preferences, indent=2) + "\n")

    output = {
        "market": {"students": len(STUDENTS), "schools": len(SCHOOLS), "capacity_each": 3},
        "preference_source": "LLM ranking interviews" if not args.reuse_preferences else "saved LLM ranking interviews",
        "model": args.model,
        "service": SERVICE,
        "temperature": 0.2,
        "profile_seed_for_school_priorities": SEED,
        "school_descriptions": SCHOOL_DESCRIPTIONS,
        "student_profiles": STUDENT_PROFILES,
        "student_preferences": preferences,
        "student_proposing": summarize("student", SEED, preferences),
        "school_proposing": summarize("school", SEED, preferences),
    }
    results_path = args.output_dir / "results.json"
    results_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({
        "status": "complete",
        "preferences": str(preference_path),
        "results": str(results_path),
        "student_proposing": {
            key: output["student_proposing"][key]
            for key in ("first_choice_assignments", "mean_student_rank_one_based", "proposal_count", "blocking_pair_count")
        },
        "school_proposing": {
            key: output["school_proposing"][key]
            for key in ("first_choice_assignments", "mean_student_rank_one_based", "proposal_count", "blocking_pair_count")
        },
    }, indent=2))


if __name__ == "__main__":
    main()

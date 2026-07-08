"""
Test script for DA algorithm correctness.
Verifies DA algorithm with known rankings before running with LLMs.
"""

from util_da import Rule_DA, Student, DA_Direct, DA_plan
from edsl import Model, Cache


def test_da_algorithm_basic():
    """Test DA algorithm with known rankings."""
    print("="*70)
    print("TEST 1: Basic DA Algorithm with Known Rankings")
    print("="*70)

    # Create rule
    rule = Rule_DA(
        mechanism_type="direct",
        intervention_type="baseline",
        common_range=[40, 70],
        private_range=20
    )

    # Create students with known values and priorities
    students = [
        Student(
            value_dict={"w": 100, "x": 80, "y": 60, "z": 40},
            priority_dict={"w": 1, "x": 2, "y": 1, "z": 2},  # High priority at w, y
            name="A",
            rule=rule
        ),
        Student(
            value_dict={"w": 90, "x": 100, "y": 70, "z": 50},
            priority_dict={"w": 2, "x": 1, "y": 2, "z": 1},  # High priority at x, z
            name="B",
            rule=rule
        ),
        Student(
            value_dict={"w": 70, "x": 60, "y": 80, "z": 50},
            priority_dict={"w": 3, "x": 3, "y": 3, "z": 3},  # Low priority everywhere
            name="C",
            rule=rule
        ),
        Student(
            value_dict={"w": 60, "x": 50, "y": 70, "z": 90},
            priority_dict={"w": 4, "x": 4, "y": 4, "z": 4},  # Lowest priority everywhere
            name="D",
            rule=rule
        ),
    ]

    # Create DA_Direct mechanism (without LLM calls)
    da = DA_Direct(students=students, rule=rule, model=None, cache=None)

    # Test with truthful rankings (students rank by their true values)
    print("\nScenario 1: Truthful Rankings")
    truthful_rankings = {
        "Student A": ["w", "x", "y", "z"],  # 100 > 80 > 60 > 40
        "Student B": ["x", "w", "y", "z"],  # 100 > 90 > 70 > 50
        "Student C": ["y", "w", "x", "z"],  # 80 > 70 > 60 > 50
        "Student D": ["z", "y", "w", "x"],  # 90 > 70 > 60 > 50
    }

    matches = da._run_da_algorithm(truthful_rankings)
    da._record_outcomes(matches)

    print("\nExpected behavior:")
    print("  - Student A proposes to w (top choice), has priority 1 → gets w")
    print("  - Student B proposes to x (top choice), has priority 1 → gets x")
    print("  - Student C proposes to y (top choice), but A and B take w,x")
    print("  - Student D proposes to z (top choice)")

    print(f"\nActual matches: {matches}")
    assert matches["Student A"] == "w", "Student A should get w"
    assert matches["Student B"] == "x", "Student B should get x"
    print("✓ Test passed: Truthful rankings produce expected stable matching")

    # Test with strategic ranking
    print("\n" + "="*70)
    print("Scenario 2: Strategic Ranking (Student C lies)")
    print("="*70)
    strategic_rankings = {
        "Student A": ["w", "x", "y", "z"],
        "Student B": ["x", "w", "y", "z"],
        "Student C": ["w", "y", "x", "z"],  # Lies: ranks w first instead of y
        "Student D": ["z", "y", "w", "x"],
    }

    # Reset students
    for s in students:
        s.matched_school = None
        s.utility = 0

    da2 = DA_Direct(students=students, rule=rule, model=None, cache=None)
    matches2 = da2._run_da_algorithm(strategic_rankings)
    da2._record_outcomes(matches2)

    print(f"\nActual matches: {matches2}")
    print("\nNote: Strategic misreporting can harm the student in DA")
    print("(DA is strategy-proof, so lying shouldn't help)")

    print("\n" + "="*70)
    print("TEST 1 PASSED ✓")
    print("="*70)


def test_da_plan_value_generation():
    """Test DA_plan value generation and student building."""
    print("\n" + "="*70)
    print("TEST 2: DA_plan Value Generation")
    print("="*70)

    rule = Rule_DA(
        mechanism_type="direct",
        common_range=[40, 70],
        private_range=20
    )

    da_plan = DA_plan(
        number_students=4,
        number_schools=4,
        rule=rule,
        output_dir="test_output",
        model="gpt-4o",
        temperature=0.5
    )

    # Test value generation
    da_plan.draw_values(seed=1234)

    # Verify values structure
    assert len(da_plan.values_list) == 4, "Should have 4 schools"
    for school in ["w", "x", "y", "z"]:
        assert school in da_plan.values_list, f"Missing school {school}"
        assert len(da_plan.values_list[school]) == 4, f"School {school} should have 4 student values"

    # Verify priorities structure
    assert da_plan.priorities_structure is not None
    for school in ["w", "x", "y", "z"]:
        assert school in da_plan.priorities_structure
        assert len(da_plan.priorities_structure[school]) == 4

    # Build students
    da_plan.build_students()
    assert len(da_plan.students) == 4, "Should have 4 students"

    for student in da_plan.students:
        assert len(student.values) == 4, f"{student.name} should have 4 school values"
        assert len(student.priorities) == 4, f"{student.name} should have 4 school priorities"

    print("\n✓ Value generation test passed")
    print("✓ Student building test passed")

    print("\n" + "="*70)
    print("TEST 2 PASSED ✓")
    print("="*70)


def test_priority_structure():
    """Test fixed acyclic priority structure."""
    print("\n" + "="*70)
    print("TEST 3: Acyclic Priority Structure")
    print("="*70)

    rule = Rule_DA(mechanism_type="direct")
    da_plan = DA_plan(
        number_students=4,
        number_schools=4,
        rule=rule,
        output_dir="test_output"
    )

    priorities = da_plan._generate_acyclic_priorities()

    # Verify structure matches readme
    expected = {
        "w": {"Student A": 1, "Student B": 2, "Student C": 3, "Student D": 4},
        "x": {"Student B": 1, "Student A": 2, "Student C": 3, "Student D": 4},
        "y": {"Student A": 1, "Student B": 2, "Student D": 3, "Student C": 4},
        "z": {"Student B": 1, "Student A": 2, "Student D": 3, "Student C": 4}
    }

    assert priorities == expected, "Priority structure doesn't match expected"

    print("\nFixed acyclic priority structure:")
    for school, prios in priorities.items():
        priority_order = sorted(prios.items(), key=lambda x: x[1])
        order_str = " > ".join([name.split()[-1] for name, _ in priority_order])
        print(f"  {school}: {order_str}")

    print("\n✓ Priority structure matches readme specification")

    print("\n" + "="*70)
    print("TEST 3 PASSED ✓")
    print("="*70)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("DA IMPLEMENTATION TESTS")
    print("="*70)

    try:
        test_da_algorithm_basic()
        test_da_plan_value_generation()
        test_priority_structure()

        print("\n" + "="*70)
        print("ALL TESTS PASSED ✓✓✓")
        print("="*70)
        print("\nThe DA implementation is ready for LLM experiments!")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

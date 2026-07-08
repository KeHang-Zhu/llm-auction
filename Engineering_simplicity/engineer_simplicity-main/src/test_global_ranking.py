"""
Test script for global_ranking feature.
Verifies that global_ranking is correctly computed and passed to templates.
"""

from util_da import Rule_DA, DA_plan


def test_global_ranking_strategies():
    """Test different global ranking strategies."""
    print("="*70)
    print("TEST: Global Ranking Strategies")
    print("="*70)

    # Test each strategy
    strategies = ["average", "fixed", "random", "misleading"]

    for strategy in strategies:
        print(f"\n{'='*70}")
        print(f"Testing strategy: {strategy}")
        print(f"{'='*70}")

        rule = Rule_DA(
            mechanism_type="direct",
            intervention_type="baseline",
            common_range=[40, 70],
            private_range=20,
            global_ranking_strategy=strategy
        )

        da_plan = DA_plan(
            number_students=4,
            number_schools=4,
            rule=rule,
            output_dir="test_output"
        )

        # Generate values (this will compute global_ranking)
        da_plan.draw_values(seed=1234)

        # Verify global_ranking was generated
        assert hasattr(da_plan, 'global_ranking'), "global_ranking not generated"
        assert da_plan.global_ranking is not None, "global_ranking is None"
        assert ">" in da_plan.global_ranking, "global_ranking format incorrect"

        print(f"\n✓ Strategy '{strategy}' generated: {da_plan.global_ranking}")


def test_global_ranking_in_prompt():
    """Test that global_ranking is passed to prompt templates."""
    print(f"\n{'='*70}")
    print("TEST: Global Ranking in Prompt")
    print(f"{'='*70}")

    rule = Rule_DA(
        mechanism_type="direct",
        global_ranking_strategy="average"
    )

    da_plan = DA_plan(
        number_students=4,
        number_schools=4,
        rule=rule,
        output_dir="test_output"
    )

    # Generate values and build students
    da_plan.draw_values(seed=1234)
    da_plan.build_students()

    # Create DA mechanism (without running LLM)
    from util_da import DA_Direct
    da_direct = DA_Direct(
        students=da_plan.students,
        rule=rule,
        model=None,
        cache=None,
        global_ranking=da_plan.global_ranking
    )

    # Build prompt for first student
    student = da_plan.students[0]
    prompt = da_direct._build_student_prompt(student)

    # Verify global_ranking appears in prompt
    assert da_plan.global_ranking in prompt, "global_ranking not in prompt"
    print(f"\n✓ Global ranking appears in prompt")
    print(f"\nPrompt excerpt:")
    lines = prompt.split('\n')
    for i, line in enumerate(lines):
        if 'most applicants' in line.lower():
            print(f"  {lines[i-1] if i > 0 else ''}")
            print(f"  {line}")
            print(f"  {lines[i+1] if i < len(lines)-1 else ''}")
            break


def test_average_strategy_correctness():
    """Test that 'average' strategy computes correct ranking."""
    print(f"\n{'='*70}")
    print("TEST: Average Strategy Correctness")
    print(f"{'='*70}")

    rule = Rule_DA(
        mechanism_type="direct",
        global_ranking_strategy="average"
    )

    da_plan = DA_plan(
        number_students=4,
        number_schools=4,
        rule=rule,
        output_dir="test_output"
    )

    # Generate values with fixed seed
    da_plan.draw_values(seed=1234)

    # Manually compute expected ranking
    avg_values = {}
    for school in ["w", "x", "y", "z"]:
        avg_values[school] = sum(da_plan.values_list[school]) / 4

    print(f"\nAverage values: {avg_values}")

    # Sort by value
    sorted_schools = sorted(avg_values.items(), key=lambda x: x[1], reverse=True)
    expected_ranking = " > ".join([s for s, _ in sorted_schools])

    print(f"Expected ranking: {expected_ranking}")
    print(f"Generated ranking: {da_plan.global_ranking}")

    assert da_plan.global_ranking == expected_ranking, "Average ranking incorrect"
    print(f"\n✓ Average strategy produces correct ranking")


def test_misleading_strategy():
    """Test that 'misleading' strategy reverses the ranking."""
    print(f"\n{'='*70}")
    print("TEST: Misleading Strategy (Reversed)")
    print(f"{'='*70}")

    # Generate with average strategy
    rule_avg = Rule_DA(
        mechanism_type="direct",
        global_ranking_strategy="average"
    )
    da_avg = DA_plan(4, 4, rule_avg, "test_output")
    da_avg.draw_values(seed=1234)

    # Generate with misleading strategy (same seed)
    rule_mislead = Rule_DA(
        mechanism_type="direct",
        global_ranking_strategy="misleading"
    )
    da_mislead = DA_plan(4, 4, rule_mislead, "test_output")
    da_mislead.draw_values(seed=1234)

    avg_schools = da_avg.global_ranking.split(" > ")
    mislead_schools = da_mislead.global_ranking.split(" > ")

    print(f"\nAverage ranking: {da_avg.global_ranking}")
    print(f"Misleading ranking: {da_mislead.global_ranking}")

    # Verify it's reversed
    assert avg_schools == list(reversed(mislead_schools)), "Misleading not reversed"
    print(f"\n✓ Misleading strategy correctly reverses ranking")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("GLOBAL RANKING FEATURE TESTS")
    print("="*70)

    try:
        test_global_ranking_strategies()
        test_global_ranking_in_prompt()
        test_average_strategy_correctness()
        test_misleading_strategy()

        print("\n" + "="*70)
        print("ALL TESTS PASSED ✓✓✓")
        print("="*70)
        print("\nGlobal ranking feature is working correctly!")
        print("You can now run experiments with social information effects.")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

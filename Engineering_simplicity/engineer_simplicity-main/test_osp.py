#!/usr/bin/env python3
"""
Test script for the new True OSP mechanism implementation.
"""
import sys
sys.path.insert(0, 'src')

from util_da import Rule_DA, DA_plan
from edsl import Cache, Model

def test_osp_mechanism():
    """
    Test the new OSP mechanism with Ashlagi-Gonczarowski tree.
    """
    print("=" * 70)
    print("Testing True OSP Mechanism (Ashlagi-Gonczarowski tree)")
    print("=" * 70)

    # Initialize cache
    cache = Cache()

    # Create rule
    rule = Rule_DA(
        mechanism_type="osp",
        special_name="da_osp_yesno_guaranteed.txt",  # Use yes/no template
        templates_dir="rule_template/DA/",
        common_range=[40, 70],
        private_range=20,
        global_ranking_strategy="fixed"
    )

    # Create DA plan
    da = DA_plan(
        number_students=4,
        number_schools=4,
        rule=rule,
        output_dir="test_output/osp_tree",
        cache=cache,
        model="gpt-4o",
        temperature=0.5
    )

    # Draw values
    print("\nDrawing values with seed=3001...")
    da.draw_values(seed=3001)

    # Build students
    print("Building students...")
    da.build_students()

    # Print student information
    print("\nStudent Information:")
    for student in da.students:
        sorted_schools = sorted(student.values.items(), key=lambda x: x[1], reverse=True)
        pref_order = " > ".join([s for s, _ in sorted_schools])
        print(f"\n{student.name}:")
        print(f"  Preference order: {pref_order}")
        print(f"  Values: {student.values}")
        print(f"  Priorities: {student.priorities}")

    # Run OSP mechanism
    print("\n" + "=" * 70)
    print("Running OSP Mechanism...")
    print("=" * 70)

    results = da.run()

    # Print results
    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)

    print("\nOSP Tree Trace:")
    # Use 'osp_tree_trace' if available, otherwise 'osp_history'
    tree_trace = results.get('osp_tree_trace', results.get('osp_history', []))
    for i, node in enumerate(tree_trace):
        print(f"\nNode {i}:")
        print(f"  Type: {node['type']}")
        print(f"  Student: {node.get('student', 'N/A')}")
        if node['type'] in ['yes_no_a', 'yes_no_b']:
            print(f"  Candidate: {node.get('candidate')}")
            print(f"  Fallback: {node.get('fallback')}")
            print(f"  Answer: {node.get('answer')}")
        else:
            print(f"  Choice: {node.get('choice')}")
        print(f"  Reasoning: {node.get('reasoning', 'N/A')[:100]}...")

    print("\n" + "=" * 70)
    print("Final Matches:")
    print("=" * 70)
    for student_name, school in results['matches'].items():
        print(f"{student_name} → {school}")

    print("\n" + "=" * 70)
    print("Truthfulness:")
    print("=" * 70)
    for student_name, is_truthful in results['truthfulness'].items():
        status = "✓ TRUTHFUL" if is_truthful else "✗ MISREPORTED"
        print(f"{student_name}: {status}")

    print(f"\nTruthfulness Rate: {results['truthfulness_rate']:.1%}")

    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)

    return results

if __name__ == "__main__":
    try:
        results = test_osp_mechanism()
        print("\n✓ Test passed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

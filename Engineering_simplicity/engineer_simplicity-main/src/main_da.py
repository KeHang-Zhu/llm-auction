"""
Main entry point for Deferred Acceptance (DA) experiments.

Runs DA simulation with LLM agents, supporting both:
- Direct revelation mechanism (full ranking submission)
- OSP mechanism (sequential local queries)
"""

from edsl import Cache
import os
from util_da import Rule_DA, DA_plan
import concurrent.futures


def run_da_experiment(i, mechanism_type, intervention_type, number_students,
                     number_schools, rule, output_dir, c, model='gpt-4o',
                     temperature=0.5, seed_base=3000, config_dict=None):
    """
    Run single DA experiment instance.

    Args:
        i: Experiment index (for seed generation)
        mechanism_type: "direct" or "osp"
        intervention_type: Cognitive intervention type
        number_students: Number of students (fixed at 4)
        number_schools: Number of schools (fixed at 4)
        rule: Rule_DA instance
        output_dir: Output directory for results
        c: Cache instance
        model: Model name
        temperature: LLM temperature
        seed_base: Base seed for value generation
        config_dict: Configuration dictionary to save
    """
    # Create DA plan (will auto-create run_{timestamp} folder)
    da = DA_plan(
        number_students=number_students,
        number_schools=number_schools,
        rule=rule,
        output_dir=output_dir,
        timestring=None,  # Will be auto-generated
        cache=c,
        model=model,
        temperature=temperature,
        config_dict=config_dict
    )

    # Run experiment
    da.draw_values(seed=seed_base + i)
    da.build_students()
    da.run()
    da.data_to_json()

    print(f"\nExperiment {i} completed successfully")


if __name__ == "__main__":
    c = Cache()

    # DA Configuration
    mechanism_type = "direct"  # "direct" or "osp"
    intervention_type = "baseline"  # "baseline", "axis1_enumerate", etc.
    number_students = 4
    number_schools = 4

    # Template selection
    special_name = "da_direct_traditional.txt"  # Override template if needed
    # special_name = "da_osp_choice.txt"  # For OSP mechanism

    # Value generation parameters
    common_range = [40, 70]
    private_range = 20

    # Global ranking strategy (social information)
    # Options: "average", "fixed", "random", "misleading"
    global_ranking_strategy = "fixed"  # Default: based on average values

    # LLM parameters
    model = "gpt-4o"
    temperature = 0.5

    # Output directory
    output_dir = f"experiment_logs/da/{mechanism_type}_{intervention_type}"
    os.makedirs(output_dir, exist_ok=True)

    # Create rule
    rule = Rule_DA(
        mechanism_type=mechanism_type,
        intervention_type=intervention_type,
        special_name=special_name,
        templates_dir="rule_template/DA/",
        common_range=common_range,
        private_range=private_range,
        global_ranking_strategy=global_ranking_strategy  # Add strategy
    )
    rule.describe()
    print(f"\nGlobal ranking strategy: {global_ranking_strategy}")

    # Number of experiment repetitions
    N = 5

    # Run experiments sequentially (for debugging)
    for i in range(N):
        run_da_experiment(
            i, mechanism_type, intervention_type,
            number_students, number_schools,
            rule, output_dir, c,
            model=model, temperature=temperature
        )

    # # Run experiments in parallel (uncomment for production)
    # with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    #     futures = [
    #         executor.submit(
    #             run_da_experiment,
    #             i, mechanism_type, intervention_type,
    #             number_students, number_schools,
    #             rule, output_dir, c,
    #             model=model, temperature=temperature
    #         )
    #         for i in range(N)
    #     ]
    #
    #     for future in concurrent.futures.as_completed(futures):
    #         try:
    #             future.result()
    #         except Exception as e:
    #             print(f"Experiment failed: {e}")

    print(f"\n{'='*70}")
    print(f"All {N} experiments completed!")
    print(f"Results saved to: {output_dir}")
    print(f"{'='*70}")

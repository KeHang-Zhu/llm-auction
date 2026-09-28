#!/usr/bin/env python3
"""Regenerate the September 2026 paper outputs without LLM API calls."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ["analysis/reconstruction_bands.py"],
    ["scripts/plots/model_comparison_main.py"],
    ["scripts/plots/figure1_bands_models.py", "gp"],
    ["scripts/plots/figure2_models.py"],
    ["analysis/difficulty_concordance.py"],
    ["analysis/difficulty_concordance_models.py"],
    ["analysis/temperature_concordance.py"],
    ["scripts/plots/interventions_models.py"],
    ["scripts/plots/ebay_closing_rule_only.py"],
    ["scripts/plots/appendix1_learning.py"],
    ["scripts/plots/appendix2_temperature.py"],
]
CHECK_FILES = [
    "model_smad_results.csv",
    "direction_shares_models.csv",
    "interventions_models.csv",
    "ebay_closing_rule_summary.csv",
    "temperature_concordance.csv",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Compare regenerated principal CSVs with the saved results.")
    args = parser.parse_args()
    expected = {}
    if args.check:
        import pandas as pd
        for name in CHECK_FILES:
            expected[name] = pd.read_csv(ROOT / "results" / "analysis" / name)
    env = {**os.environ, "MPLBACKEND": "Agg"}
    for step in STEPS:
        print(f"\n==> {' '.join(step)}", flush=True)
        subprocess.run([sys.executable, *step], cwd=ROOT, env=env, check=True)
    if args.check:
        from pandas.testing import assert_frame_equal
        for name, reference in expected.items():
            actual = pd.read_csv(ROOT / "results" / "analysis" / name)
            # Reports serialize some values to six significant figures.
            assert_frame_equal(actual, reference, check_exact=False,
                               rtol=1e-5, atol=1e-6)
            print(f"Verified {name}")
    print("\nOffline reproduction completed.")


if __name__ == "__main__":
    main()

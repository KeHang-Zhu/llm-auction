#!/usr/bin/env python3
"""Regenerate every clock-dependent output with the one-LLM clock design and
install it in TEAC_submission/.

Runs the analysis scripts with CLOCK_DESIGN=one_llm (outputs carry the suffix
_one_llm, so the legacy outputs that scripts/reproduce_paper.py --check
verifies stay untouched), builds the attempt-and-exclusion table, then copies
the new figures and tables over the corresponding files in TEAC_submission/.

    python scripts/reproduce_one_llm.py            # analysis + install
    python scripts/reproduce_one_llm.py --no-install
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEAC = ROOT / "TEAC_submission"
STEPS = [
    ["scripts/plots/model_comparison_main.py"],
    ["scripts/plots/figure1_bands_models.py", "gp"],
    ["scripts/plots/figure2_models.py"],
    ["analysis/difficulty_concordance.py"],
    ["analysis/difficulty_concordance_models.py"],
    ["analysis/temperature_concordance.py"],
    ["scripts/plots/appendix2_temperature.py"],
    ["scripts/plots/figure_profiles.py"],
    ["analysis/clock_attrition.py"],
    ["analysis/clock_macros.py"],
    ["analysis/data_inventory.py"],
]
# one-LLM output (relative to ROOT) -> file in TEAC_submission/
INSTALL = {
    "results/figures/smad_profiles_gp_one_llm.png": "figures/smad_profiles_gp.png",
    "results/figures/smad_profiles_all_one_llm.png": "figures/smad_profiles_all.png",
    "results/figures/direction_grid_one_llm.png": "figures/direction_grid.png",
    "results/figures/smad_profiles_temperature_one_llm.png": "figures/smad_profiles_temperature.png",
    "results/tables/model_comparison_one_llm.tex": "tables/model_comparison.tex",
    "results/tables/concordance_one_llm.tex": "tables/concordance.tex",
    "results/tables/temperature_robustness_one_llm.tex": "tables/temperature_robustness.tex",
    "results/tables/direction_shares_one_llm.tex": "tables/direction_shares.tex",
    "results/tables/data_inventory_lab.tex": "tables/data_inventory_lab.tex",
    "results/tables/data_inventory_other.tex": "tables/data_inventory_other.tex",
    "results/tables/data_inventory_numbers.tex": "tables/data_inventory_numbers.tex",
    "results/tables/clock_numbers_one_llm.tex": "tables/clock_numbers.tex",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-install", action="store_true")
    args = ap.parse_args()
    env = {**os.environ, "MPLBACKEND": "Agg", "CLOCK_DESIGN": "one_llm"}
    for step in STEPS:
        print(f"\n==> CLOCK_DESIGN=one_llm {' '.join(step)}", flush=True)
        subprocess.run([sys.executable, *step], cwd=ROOT, env=env, check=True)
    if args.no_install:
        return
    for src, dst in INSTALL.items():
        s, d = ROOT / src, TEAC / dst
        if not s.exists():
            raise FileNotFoundError(s)
        shutil.copy2(s, d)
        print(f"installed {dst}")
    print("\nOne-LLM outputs installed in TEAC_submission/.")


if __name__ == "__main__":
    main()

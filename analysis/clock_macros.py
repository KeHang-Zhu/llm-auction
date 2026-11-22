#!/usr/bin/env python3
"""LaTeX macros for every clock-dependent number quoted in the paper text.

Reads the one-LLM analysis outputs (run after model_comparison_main.py,
figure2_models.py, difficulty_concordance*.py, temperature_concordance.py and
clock_attrition.py) plus the one-LLM clock cells themselves, and writes
\\newcommand definitions, so the prose updates when the data do.

Output: results/tables/clock_numbers_one_llm.tex
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CLOCK_DESIGN", "one_llm")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_data as cd  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = cd.PROJECT_ROOT
RES = ROOT / "results" / "analysis"
INCREMENT = 0.5
# macro tag -> (model_key in model_smad_results, display name in other outputs, one-LLM suffix)
MODELS = {
    "Gpt": ("gpt4o", "GPT-4o", ""),
    "Claude": ("claude_sonnet", "Claude 3.5 Haiku", "claude_sonnet"),
    "Gemini": ("gemini", "Gemini 2.0 Flash", "gemini"),
    "Mini": ("gpt5mini", "GPT-5-mini", "gpt5mini"),
    "Llama": ("llama", "Llama-3-8B", "llama"),
}
FORMATS = {  # macro tag -> (model_smad auction label, direction label, one-LLM format key)
    "AC": ("Ascending Clock APV", "AC", "ascending_clock_apv"),
    "ACB": ("AC-Closed (AC-B) APV", "AC-B", "ascending_clock_apv_closed"),
}


def num(x: float, signed: bool = False) -> str:
    d = 2 if abs(x) < 1 else 1
    s = f"{x:+.{d}f}" if signed else f"{x:.{d}f}"
    return s.replace("-", r"\ensuremath{-}")


WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def tick_both(a: str, b: str) -> str:
    """'all' when every open- and closed-clock exit is within one increment, else 'a\\% and b\\%'."""
    return "all" if a == b == "100" else f"{a}\\% and {b}\\%"


def tau(x: float) -> str:
    return f"{x:.2f}".replace("-", r"\ensuremath{-}")


def main() -> None:
    out: dict[str, str] = {}
    smad = pd.read_csv(RES / cd.out_name("model_smad_results.csv"))
    dirs = pd.read_csv(RES / cd.out_name("direction_shares_models.csv"))
    conc = pd.read_csv(RES / cd.out_name("difficulty_concordance_models.csv"))
    five = json.loads((RES / cd.out_name("difficulty_concordance.json")).read_text())
    temp = pd.read_csv(RES / cd.out_name("temperature_concordance.csv"))
    attr = pd.read_csv(RES / cd.out_name("clock_attrition.csv"))

    for mt, (mkey, mname, suffix) in MODELS.items():
        for ft, (alabel, dlabel, fkey) in FORMATS.items():
            r = smad[(smad["auction"] == alabel) & (smad["model_key"] == mkey)].iloc[0]
            out[f"Smad{ft}{mt}"] = num(r["smad"])
            out[f"N{ft}{mt}"] = str(int(r["n"]))
            df = cd.load_one_llm(fkey, "" if mkey == "gpt4o" else suffix)
            u = cd.usable_clock_rows(df)
            gap = (u["bid"] - pd.to_numeric(u["player_value"])).abs()
            out[f"Tick{ft}{mt}"] = f"{100 * (gap <= INCREMENT + 1e-9).mean():.0f}"
            d = dirs[(dirs["format"] == dlabel) & (dirs["source"] == mname)].iloc[0]
            out[f"Under{ft}{mt}"] = f"{d['under_share']:.0f}"
            out[f"Over{ft}{mt}"] = f"{d['over_share']:.0f}"
            out[f"Ndev{ft}{mt}"] = str(int(d["n_deviating"]))
        out[f"TickBoth{mt}"] = tick_both(out[f"TickAC{mt}"], out[f"TickACB{mt}"])
        for fs, tag in (("all_usable", "All"), ("sealed3", "Sealed")):
            c = conc[(conc["model"] == mname) & (conc["format_set"] == fs)].iloc[0]
            out[f"Tau{tag}{mt}"] = tau(c["tau_point"])
            out[f"TauK{tag}{mt}"] = WORDS.get(int(c["n_formats"]), str(int(c["n_formats"])))
            out[f"TauCI{tag}{mt}"] = f"[{tau(c['ci_joint_lo'])}, {tau(c['ci_joint_hi'])}]"
            out[f"TauP{tag}{mt}"] = f"{100 * c['p_tau_pos_joint']:.0f}"

    # GPT-4o over all five private-value formats (single-model script)
    out["TauFiveGpt"] = tau(five["tau_point"])
    out["TauFiveCIGpt"] = f"[{tau(five['layer_c_joint']['ci95'][0])}, {tau(five['layer_c_joint']['ci95'][1])}]"
    out["TauFiveLlmCIGpt"] = f"[{tau(five['layer_a_llm_bootstrap']['ci95'][0])}, {tau(five['layer_a_llm_bootstrap']['ci95'][1])}]"
    out["TauFivePGpt"] = f"{100 * five['layer_c_joint']['frac_tau_positive']:.0f}"
    h, l = np.array(five["human_smad"]), np.array(five["llm_smad"])
    conc_n = disc_n = 0
    disc_pairs = []
    for i in range(len(h)):
        for j in range(i + 1, len(h)):
            s = np.sign(h[i] - h[j]) * np.sign(l[i] - l[j])
            if s > 0:
                conc_n += 1
            elif s < 0:
                disc_n += 1
                disc_pairs.append(f"{five['formats'][i]}/{five['formats'][j]}")
    out["TauFiveConc"] = str(conc_n)
    out["TauFiveDisc"] = str(disc_n)
    out["TauFiveDiscPairs"] = ", ".join(disc_pairs)

    for t, tag in ((0.1, "Lo"), (0.5, "Mid"), (1.0, "Hi")):
        r = temp[temp["temperature"] == t].iloc[0]
        out[f"TempTauAll{tag}"] = tau(r["tau_all_usable"])
        out[f"TempTauK{tag}"] = str(int(r["k_all_usable"]))
        out[f"TempTauP{tag}"] = f"{100 * r['p_tau_pos_joint_all_usable']:.0f}"
    tj = json.loads((RES / cd.out_name("temperature_concordance.json")).read_text())
    rhos = [c["spearman_rho"] for c in tj["between_temperature_rank_correlation"]]
    out["TempSpearmanMin"] = f"{min(rhos):.2f}"

    out["ClockAttempted"] = str(int(attr["attempted"].sum()))
    out["ClockFailed"] = str(int(attr["failed"].sum()))
    out["ClockCensored"] = str(int(attr["censored"].sum()))
    op = attr[attr["format"].str.startswith("AC (open)")]
    cl = attr[~attr["format"].str.startswith("AC (open)")]
    out["ClockOpenUsableMin"] = str(int(op["usable"].min()))
    out["ClockOpenUsableMax"] = str(int(op["usable"].max()))
    out["ClockClosedUsableMin"] = str(int(cl["usable"].min()))
    out["ClockClosedUsableMax"] = str(int(cl["usable"].max()))
    out["ClockOpenCensoredPct"] = f"{100 * op['censored'].sum() / op['completed'].sum():.0f}"

    lines = ["% Auto-generated by analysis/clock_macros.py -- do not edit by hand.",
             "% Clock-dependent numbers quoted in the text (one-LLM clock design)."]
    lines += [f"\\providecommand{{\\{k}}}{{}}\\renewcommand{{\\{k}}}{{{v}}}" for k, v in out.items()]
    path = ROOT / "results" / "tables" / cd.out_name("clock_numbers.tex")
    path.write_text("\n".join(lines) + "\n")
    for k, v in out.items():
        print(f"{k:24s} {v}")
    print(f"\nSaved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

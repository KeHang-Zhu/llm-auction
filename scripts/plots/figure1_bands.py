"""
figure1_bands.py -- Human vs LLM SMAD comparison (fig:smad-comparison) WITH
Monte-Carlo reconstruction-uncertainty bands on the human bars.

This is the `_bands` companion to `scripts/plots/figure1.py`.  It reproduces the
existing figure exactly (same seaborn theme, same horizontal layout, same blue
Human / orange LLM(GPT-4o) bars, same ordering by human SMAD) and replaces the
black-star "no CI available" markers on the human bars with 95% Monte-Carlo
percentile bands from the parametric bootstrap over the reconstruction's
calibration parameters (`analysis/reconstruction_bands.py`,
`results/reconstruction_bands/bands.csv`).

It does NOT overwrite figure1.png; it writes figure1_bands.png/.pdf next to it.

Run (from repo root):
    .venv/bin/python scripts/plots/figure1_bands.py
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import seaborn as sns
    _HAVE_SNS = True
except ImportError:                    # venv has no seaborn -- replicate its look
    _HAVE_SNS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLOTS_DIR = PROJECT_ROOT / "plots"
BANDS_CSV = PROJECT_ROOT / "results" / "reconstruction_bands" / "bands.csv"
FIG_OUT = PROJECT_ROOT / "writeup" / "figures" / "figure1_bands.png"
FIG_OUT_LOCAL = PLOTS_DIR / "figure1_bands.png"


def _apply_style():
    """Match figure1.py's seaborn whitegrid/talk theme (with a matplotlib
    fallback that reproduces the same light-gray panel + white gridlines and
    the enlarged 'talk'-context fonts, so the _bands figure is visually
    identical whether or not seaborn is installed)."""
    if _HAVE_SNS:
        sns.set_theme(style="whitegrid", context="talk")
        plt.rcParams["font.size"] = 10
        return
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#EAEAF2",     # seaborn whitegrid panel gray
        "axes.edgecolor": "white",
        "axes.linewidth": 1.25,
        "axes.grid": True,
        "grid.color": "white",
        "grid.linewidth": 1.1,
        "axes.axisbelow": True,
        "xtick.color": "#555555",
        "ytick.color": "#555555",
        "text.color": "#111111",
        "axes.labelcolor": "#111111",
        "font.size": 13,                 # 'talk' context base
        "axes.titlesize": 15,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "font.family": "sans-serif",
    })


_apply_style()

HUMAN_COLOR = "#2E86AB"   # blue  (identical to figure1.py)
LLM_COLOR = "#F18F01"     # orange

# Map the figure's format labels to the reconstruction-band anchor names.
# Formats without a reconstruction band (CV: profit-based metric) keep the
# existing "no reconstruction band" star marker.
FORMAT_TO_ANCHOR = {
    "First-Price IPV": "FPSB IPV",
    "Second-Price IPV": "SPSB IPV",
    "Second-Price APV": "SP-APV",
    "Ascending Clock APV": "AC",
    "AC-Closed (AC-B) APV": "AC-B",
    # First-Price CV / Second-Price CV: no reconstruction band (profit-based).
}


def parse_ci_string(ci_str):
    if pd.isna(ci_str) or "no CI" in str(ci_str):
        return None, None
    m = re.search(r"\[([0-9.]+),\s*([0-9.]+)\]", str(ci_str))
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def load_data():
    human_df = pd.read_csv(PLOTS_DIR / "auction_human.csv")
    llm_df = pd.read_csv(PLOTS_DIR / "theoretical_deviation_results_updated.csv")
    bands = pd.read_csv(BANDS_CSV).set_index("anchor")

    format_mapping = {
        "First-Price IPV": "First-Price IPV",
        "Second-Price IPV": "Second-Price IPV",
        "AC-B (Breitmoser2022)": "AC-Closed (AC-B) APV",
        "SPSB (Li 2017)": "Second-Price APV",
        "Ascending Clock (Li 2017)": "Ascending Clock APV",
        "First-Price Common Value": "First-Price CV",
        "Second-Price Common Value (English proxy)": "Second-Price CV",
        "Second-Price Common Value": "Second-Price CV",
    }

    human = []
    for _, row in human_df.iterrows():
        if pd.isna(row["Auction"]):
            continue
        name = format_mapping.get(row["Auction"].strip(), row["Auction"].strip())
        smad = float(row["SMAD"])
        # Prefer the reconstruction-uncertainty band where we have one.
        anchor = FORMAT_TO_ANCHOR.get(name)
        if anchor is not None and anchor in bands.index:
            lo = float(bands.loc[anchor, "lo95"])
            hi = float(bands.loc[anchor, "hi95"])
            band_kind = "mc"
        else:
            # fall back to any published CI already in the CSV, else none
            lo, hi = parse_ci_string(row["CI"])
            band_kind = "pub" if lo is not None else "none"
        human.append(dict(auction=name, source="Human", smad=smad,
                          lo=lo, hi=hi, band_kind=band_kind))
    human_df2 = pd.DataFrame(human)

    llm = llm_df[["auction", "smad", "ci_lower", "ci_upper"]].copy()
    llm["source"] = "LLM (GPT-4o)"
    llm["lo"] = llm["ci_lower"]
    llm["hi"] = llm["ci_upper"]
    llm["band_kind"] = "pub"

    combined = pd.concat(
        [human_df2, llm[["auction", "source", "smad", "lo", "hi", "band_kind"]]],
        ignore_index=True,
    )
    matched = set(human_df2["auction"]) & set(llm["auction"])
    combined = combined[combined["auction"].isin(matched)]
    return combined


def main():
    combined = load_data()

    # order by human SMAD (ascending), identical to figure1.py
    auction_order = (combined[combined["source"] == "Human"]
                     .sort_values("smad")["auction"].tolist())

    fig, ax = plt.subplots(figsize=(12, 10))
    n = len(auction_order)
    y = np.arange(n)
    height = 0.35

    star_used = False
    for i, auction in enumerate(auction_order):
        adata = combined[combined["auction"] == auction]
        for j, source in enumerate(["Human", "LLM (GPT-4o)"]):
            sd = adata[adata["source"] == source]
            if len(sd) == 0:
                continue
            row = sd.iloc[0]
            y_pos = i + (j - 0.5) * height
            color = HUMAN_COLOR if source == "Human" else LLM_COLOR
            ax.barh(y_pos, row["smad"], height, color=color, alpha=0.7,
                    label=source if i == 0 else "")
            if pd.notna(row["lo"]) and pd.notna(row["hi"]):
                xerr = [[row["smad"] - row["lo"]], [row["hi"] - row["smad"]]]
                ax.errorbar(row["smad"], y_pos, xerr=xerr, fmt="none",
                            ecolor="black", capsize=4, capthick=1.5, linewidth=1.5)
            else:
                ax.plot(row["smad"], y_pos, "k*", markersize=10)
                star_used = True

    ax.set_ylabel("Auction Format", fontsize=13, fontweight="bold")
    ax.set_xlabel("Scaled Mean Absolute Deviation (SMAD) from Theoretical Optimum (%)",
                  fontsize=13, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(auction_order)
    ax.legend(loc="lower right", frameon=True, fontsize=11)
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2, alpha=0.5)
    ax.grid(axis="x", alpha=0.3, linestyle="--")

    note = ("Human whiskers: 95% Monte-Carlo reconstruction bands "
            "(parametric bootstrap over calibration parameters).")
    if star_used:
        note += "  ★: no reconstruction band (CV, profit-based)."
    ax.text(0.98, -0.02, note, transform=ax.transAxes, fontsize=8.5,
            verticalalignment="bottom", horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3))

    plt.tight_layout()
    FIG_OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(FIG_OUT, dpi=300, bbox_inches="tight")
    plt.savefig(FIG_OUT.with_suffix(".pdf"), bbox_inches="tight")
    plt.savefig(FIG_OUT_LOCAL, dpi=300, bbox_inches="tight")
    print(f"Saved: {FIG_OUT}")
    print(f"Saved: {FIG_OUT.with_suffix('.pdf')}")
    print(f"Saved: {FIG_OUT_LOCAL}")
    plt.close()


if __name__ == "__main__":
    main()

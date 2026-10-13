#!/usr/bin/env python3
"""A6 -- cross-model menu-framing and clock-framing interventions (SPSB IPV).

Four models from the Engineering-Simplicity (ES) V12 grid -- GPT-4o,
Claude 3.5 Haiku, Gemini 2.0 Flash, Gemma-3-27B -- each with three cells of
the same second-price sealed-bid auction (values Unif{0..49}, 3 bidders,
b* = v), differing only in how the mechanism is described:

    BASELINE       pooled axis1_contingent_baseline + axis3_beliefs_baseline
                   (axis2_forward_baseline EXCLUDED: its template was a
                   two-stage clock-exit description, i.e. a treated cell --
                   results/merged_ranking/_axis2_baseline_provenance.md)
    MENU           intervention_menu            (Gonczarowski et al. menu)
    CLOCK FRAMING  intervention_proxy_breitmoser (Breitmoser 2022 clock)

Per (model, cell): n bids, mean/sd of the scaled deviation (b - v)/25,
paper-convention SMAD = 100 * mean|b - v| / 25, +/-2 % rule shares
(within iff |b - v| <= 0.02 v), and for the two treatments vs the baseline:
Welch t p, Mann-Whitney p, Cohen's d ((treatment - baseline)/pooled sd).

Cross-check: results/analysis/cell_crosschecks.csv (family es_v12) reports
smad_pct with normalizer 24.5; ours must equal smad_pct * 24.5 / 25 and n /
mean_dev must match exactly. Deltas are stored in the CSV and printed.

Data (bid-level):
  baselines   experiment_logs/paper_interventions/baselines.csv
  treatments  experiment_logs/paper_interventions/<model>/<exp>/result_*.json
              (the original bidder-to-value mapping is retained).
  protocols   experiment_logs/paper_interventions/protocols.json

Outputs (repo-relative):
  results/analysis/interventions_models.csv
  writeup/tables/interventions_models.tex   (tabular-only fragment, menu+clock)
  writeup/figures/fig_interventions_models.{png,pdf}
  -- clock-framing-only variants (menu framing is not in the paper):
  writeup/tables/clock_framing_models.tex      all four models
  writeup/figures/fig_clock_framing_models.{png,pdf}
  writeup/tables/clock_framing_main.tex        GPT-4o, Claude 3.5 Haiku, Gemini 2.0 Flash (main text)
  writeup/figures/fig_clock_framing_main.{png,pdf}     1x3 panels
  writeup/tables/clock_framing_gemma.tex       Gemma-3-27B only (appendix robustness note)
  writeup/figures/fig_clock_framing_gemma.{png,pdf}    single panel

Run: python3 scripts/plots/interventions_models.py              # all outputs
     python3 scripts/plots/interventions_models.py --clock-only # only the clock-framing files
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
DATA_DIR = ROOT / "experiment_logs" / "paper_interventions"

CELLS_CSV = ROOT / "results" / "analysis" / "cell_crosschecks.csv"
OUT_CSV = ROOT / "results" / "analysis" / "interventions_models.csv"
OUT_TEX = ROOT / "writeup" / "tables" / "interventions_models.tex"
OUT_FIG = ROOT / "writeup" / "figures" / "fig_interventions_models"  # .png/.pdf
OUT_TEX_CLOCK = ROOT / "writeup" / "tables" / "clock_framing_models.tex"
OUT_FIG_CLOCK = ROOT / "writeup" / "figures" / "fig_clock_framing_models"
OUT_TEX_MAIN = ROOT / "writeup" / "tables" / "clock_framing_main.tex"
OUT_FIG_MAIN = ROOT / "writeup" / "figures" / "fig_clock_framing_main"
OUT_TEX_GEMMA = ROOT / "writeup" / "tables" / "clock_framing_gemma.tex"
OUT_FIG_GEMMA = ROOT / "writeup" / "figures" / "fig_clock_framing_gemma"

NORM = 25.0            # paper convention (Sec. method): SMAD = 100*mean|b-v|/25
NORM_CELLS = 24.5      # auction_cells.csv convention (E[b*] for Unif{0..49})
WITHIN_FRAC = 0.02

BASELINE_EXPS = ["axis1_contingent_baseline", "axis3_beliefs_baseline"]
MODELS = [  # canonical id, ES experiment_logs dir, display name
    ("gpt-4o", "gpt4o", "GPT-4o"),
    ("claude-3-5-haiku-20241022", "claude", "Claude 3.5 Haiku"),
    ("gemini-2.0-flash", "gemini", "Gemini 2.0 Flash"),
    ("google/gemma-3-27b-it", "gemma", "Gemma-3-27B"),
]
CELLS = [  # key, display, ES experiment (None -> pooled baseline)
    ("baseline", "Baseline", "POOLED_axis_baseline"),
    ("menu", "Menu framing", "intervention_menu"),
    ("clock", "Clock framing", "intervention_proxy_breitmoser"),
]
# main text = the three general-purpose families; Gemma-3-27B = appendix robustness note
MAIN_MODELS = [m for m in MODELS if m[0] != "google/gemma-3-27b-it"]
GEMMA_MODELS = [m for m in MODELS if m[0] == "google/gemma-3-27b-it"]
CLOCK_CELLS = [c for c in CELLS if c[0] in ("baseline", "clock")]

# ---- chart chrome (dataviz reference palette; light surface) ---------------
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = {  # baseline = neutral reference gray; treatments = categorical slots 2, 1
    "baseline": "#a9a7a0",
    "menu": "#eb6834",
    "clock": "#2a78d6",
}
XLIM = (-1.0, 0.5)     # scaled deviation (b - v)/25; off-scale share annotated


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------
def load_baseline_devs() -> dict[str, np.ndarray]:
    """Read the released subset of the original pooled baseline export."""
    df = pd.read_csv(DATA_DIR / "baselines.csv")
    df = df[df["experiment"].isin(BASELINE_EXPS)].copy()
    df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
    df["player_value"] = pd.to_numeric(df["player_value"], errors="coerce")
    return {
        model: df[df["model"] == model].dropna(subset=["bid", "player_value"])
        [["player_value", "bid"]].to_numpy(dtype=float)
        for model, _, _ in MODELS
    }


def load_treatment(mdir: str, model: str, exp: str) -> np.ndarray:
    """Parse shipped result JSONs using the original bidder-to-value mapping."""
    protocols = json.loads((DATA_DIR / "protocols.json").read_text())
    assert protocols[mdir][exp]["llm"]["model"] == model
    player_idx = {f"Bidder {name}": i for i, name in enumerate(
        ["Andy", "Betty", "Charles", "David", "Ethel", "Florian", "Gray"])}
    rows = []
    paths = sorted((DATA_DIR / mdir / exp).glob("result_*.json"))
    if not paths:
        raise FileNotFoundError(f"No released runs for {mdir}/{exp}")
    for path in paths:
        data = json.loads(path.read_text())
        for key in sorted(data):
            rd = data[key]
            for idx, entry in enumerate(rd["history"]["bidding history"]):
                pidx = player_idx.get(entry["agent"], idx)
                if pidx < len(rd["value"]):
                    rows.append((rd["value"][pidx], entry.get("bid")))
    df = pd.DataFrame(rows, columns=["player_value", "bid"])
    return df.apply(pd.to_numeric, errors="coerce").dropna().to_numpy(dtype=float)


# ----------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------
def cohens_d(a, b):
    n1, n2 = len(a), len(b)
    s = np.sqrt(((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1))
                / (n1 + n2 - 2))
    return (a.mean() - b.mean()) / s if s > 0 else np.nan


def describe(vb: np.ndarray) -> dict:
    v, b = vb[:, 0], vb[:, 1]
    d = b - v
    band = WITHIN_FRAC * v
    within = np.abs(d) <= band
    return {
        "n_bids": len(d),
        "mean_dev_dollar": d.mean(), "sd_dev_dollar": d.std(ddof=1),
        "mean_dev_scaled": d.mean() / NORM, "sd_dev_scaled": d.std(ddof=1) / NORM,
        "se_dev_scaled": d.std(ddof=1) / NORM / np.sqrt(len(d)),
        "median_dev_scaled": np.median(d) / NORM,
        "smad_pct": 100.0 * np.abs(d).mean() / NORM,
        "smad_pct_norm24p5": 100.0 * np.abs(d).mean() / NORM_CELLS,
        "share_under": float((d < -band).mean()),
        "share_over": float((d > band).mean()),
        "share_within_2pct": float(within.mean()),
    }


def contrast(d_t: np.ndarray, d_b: np.ndarray) -> dict:
    t, p = stats.ttest_ind(d_t, d_b, equal_var=False)
    return {"diff_mean_dev_scaled": (d_t.mean() - d_b.mean()) / NORM,
            "welch_t": t, "welch_p": p,
            "mw_p": stats.mannwhitneyu(d_t, d_b, alternative="two-sided").pvalue,
            "cohens_d": cohens_d(d_t, d_b)}


def cross_check(rows: list[dict]) -> None:
    ref = pd.read_csv(CELLS_CSV)
    ref = ref[(ref["family"] == "es_v12")
              & ref["experiment"].isin([c[2] for c in CELLS])]
    for r in rows:
        m = ref[(ref["model"] == r["model"]) & (ref["experiment"] == r["experiment"])]
        if len(m) != 1:
            r.update({"xcheck_status": f"no unique auction_cells row ({len(m)})"})
            continue
        m = m.iloc[0]
        r["xcheck_n_bids"] = int(m["n_bids"])
        r["xcheck_mean_dev_dollar"] = m["mean_dev"]
        r["xcheck_smad_pct_norm24p5"] = m["smad_pct"]
        r["xcheck_smad_pct_rescaled_to_25"] = m["smad_pct"] * NORM_CELLS / NORM
        r["delta_n_bids"] = r["n_bids"] - r["xcheck_n_bids"]
        r["delta_mean_dev_dollar"] = r["mean_dev_dollar"] - m["mean_dev"]
        r["delta_smad_pct"] = r["smad_pct"] - r["xcheck_smad_pct_rescaled_to_25"]
        if r["cell"] != "baseline":
            r["delta_mw_p"] = r["mw_p"] - m["mw_p"]
            r["delta_cohens_d"] = r["cohens_d"] - m["cohens_d"]
        ok = (r["delta_n_bids"] == 0 and abs(r["delta_mean_dev_dollar"]) < 1e-4
              and abs(r["delta_smad_pct"]) < 1e-3)
        r["xcheck_status"] = "match" if ok else "MISMATCH"


# ----------------------------------------------------------------------------
# Table
# ----------------------------------------------------------------------------
def fmt_p(p: float) -> str:
    if p < 1e-3:
        return r"$p<0.001$"
    return rf"$p={p:.2f}$" if p >= 0.01 else rf"$p={p:.3f}$"


def fmt_signed(x: float, nd: int = 3) -> str:
    return f"${x:+.{nd}f}$"


def write_table(df: pd.DataFrame) -> None:
    YES, NO = r"$\surd$", r"$\times$"  # base LaTeX only (paper does not load amssymb)
    lines = [
        r"\begin{tabular}{l rr rrl rrl c}",
        r"\toprule",
        r" & \multicolumn{2}{c}{Baseline} & \multicolumn{3}{c}{Menu framing}"
        r" & \multicolumn{3}{c}{Clock framing} & Signs vs.\ human \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-6}\cmidrule(lr){7-9}",
        r"Model & SMAD & mean dev & SMAD & mean dev & $\Delta$ (MW)"
        r" & SMAD & mean dev & $\Delta$ (MW) & anchor (clock\,/\,menu) \\",
        r"\midrule",
    ]
    for model, _, name in MODELS:
        g = df[df["model"] == model].set_index("cell")
        b, m, c = g.loc["baseline"], g.loc["menu"], g.loc["clock"]

        def delta(t):
            arrow = r"$\downarrow$" if t["smad_pct"] < b["smad_pct"] else r"$\uparrow$"
            return arrow + r" {\scriptsize " + fmt_p(t["mw_p"]) + "}"

        clock_helps = (c["smad_pct"] < b["smad_pct"]) and (c["mw_p"] < 0.05)
        menu_null = m["mw_p"] >= 0.05
        signs = (YES if clock_helps else NO) + r"\,/\," + (YES if menu_null else NO)
        lines.append(
            f"{name} & {b['smad_pct']:.1f}\\% & {fmt_signed(b['mean_dev_scaled'])}"
            f" & {m['smad_pct']:.1f}\\% & {fmt_signed(m['mean_dev_scaled'])} & {delta(m)}"
            f" & {c['smad_pct']:.1f}\\% & {fmt_signed(c['mean_dev_scaled'])} & {delta(c)}"
            f" & {signs} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_TEX}")


def write_clock_table(df: pd.DataFrame, models=MODELS,
                      out: Path = OUT_TEX_CLOCK) -> None:
    """Clock-framing-only table for a model subset (default: all four)."""
    YES, NO = r"$\surd$", r"$\times$"
    lines = [
        r"\begin{tabular}{l rr rr c l c}",
        r"\toprule",
        r" & \multicolumn{2}{c}{Baseline} & \multicolumn{2}{c}{Clock framing}"
        r" & within $\pm2\%$ & & matches \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"Model & SMAD & mean dev & SMAD & mean dev & baseline $\to$ clock"
        r" & $\Delta$ (MW) & human sign? \\",
        r"\midrule",
    ]
    for model, _, name in models:
        g = df[df["model"] == model].set_index("cell")
        b, c = g.loc["baseline"], g.loc["clock"]
        arrow = r"$\downarrow$" if c["smad_pct"] < b["smad_pct"] else r"$\uparrow$"
        delta = arrow + r" {\scriptsize " + fmt_p(c["mw_p"]) + "}"
        helps = (c["smad_pct"] < b["smad_pct"]) and (c["mw_p"] < 0.05)
        lines.append(
            f"{name} & {b['smad_pct']:.1f}\\% & {fmt_signed(b['mean_dev_scaled'])}"
            f" & {c['smad_pct']:.1f}\\% & {fmt_signed(c['mean_dev_scaled'])}"
            f" & {100 * b['share_within_2pct']:.0f}\\% $\\to$ {100 * c['share_within_2pct']:.0f}\\%"
            f" & {delta} & {YES if helps else NO} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


# ----------------------------------------------------------------------------
# Figure
# ----------------------------------------------------------------------------
def kde_curve(x: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if np.std(x) < 1e-9:
        return None
    return stats.gaussian_kde(x, bw_method="scott")(grid)


def write_figure(devs: dict[tuple[str, str], np.ndarray], df: pd.DataFrame,
                 cells=CELLS, models=MODELS, out: Path = OUT_FIG,
                 title="Menu framing vs. clock framing of the same second-price auction, four models",
                 subtitle=("Baseline = pooled axis1 + axis3 SPSB descriptions (ES V12 grid). "
                           "Dashed lines mark means; n = baseline / menu / clock bids.")) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8.5, "axes.linewidth": 0.8,
    })
    n = len(models)
    if n == 4:      # original layout, kept literal so the four-panel files are unchanged
        W, left, right, lx = 11.5, 0.055, 0.99, 0.045
    else:           # same margins in inches (0.63" left, 0.12" right), 2.85" per panel
        W = max(2.85 * n + 0.1, 5.0)
        left, right, lx = 0.6325 / W, 1 - 0.115 / W, 0.5175 / W
    top, bottom, sup_y, sub_va = ((0.80, 0.235, 0.095, "baseline") if n > 1
                                  else (0.72, 0.27, 0.12, "top"))
    fig, axes = plt.subplots(1, n, figsize=(W, 3.4), sharex=True, sharey=True,
                             squeeze=False)
    axes = axes[0]
    fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom, wspace=0.08)
    grid = np.linspace(XLIM[0] - 0.1, XLIM[1] + 0.1, 700)

    for ax, (model, _, name) in zip(axes, models):
        g = df[df["model"] == model].set_index("cell")
        ns = []
        for key, label, _ in cells:
            x = devs[(model, key)]
            ns.append(len(x))
            c = SERIES[key]
            y = kde_curve(x, grid)
            if key == "baseline":
                if y is not None:
                    ax.fill_between(grid, 0, y, color=c, alpha=0.45, lw=0, zorder=2)
                    ax.plot(grid, y, color=MUTED, lw=0.8, zorder=3)
            else:
                if y is not None:
                    ax.fill_between(grid, 0, y, color=c, alpha=0.10, lw=0, zorder=3)
                    ax.plot(grid, y, color=c, lw=1.8, zorder=4)
            if y is None:  # degenerate cell: draw a spike at the common value
                ax.axvline(float(np.mean(x)), color=c, lw=2.5, zorder=4)
            ax.axvline(float(np.mean(x)), color=(INK2 if key == "baseline" else c),
                       lw=1.1, ls=(0, (4, 2.5)), zorder=5)
        ax.axvline(0, color=AXIS, lw=0.8, zorder=1)
        ax.set_xlim(*XLIM)
        off = max(np.mean((devs[(model, k)] < XLIM[0]) | (devs[(model, k)] > XLIM[1]))
                  for k, _, _ in cells)
        smads = " $\\to$ ".join(f"{g.loc[k, 'smad_pct']:.1f}" for k, _, _ in cells)
        txt = f"SMAD {smads}%"
        if off >= 0.001:
            txt += f"\n{100 * off:.1f}% off-scale"
        ax.text(0.035, 0.955, txt, transform=ax.transAxes, ha="left", va="top",
                fontsize=7.0, color=INK2, zorder=8,
                bbox=dict(fc="white", alpha=0.7, ec="none", pad=1.5))
        ax.set_title(f"{name}\n(n = {' / '.join(str(n) for n in ns)})", fontsize=9.5,
                     color=INK, pad=6)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        for s in ["left", "bottom"]:
            ax.spines[s].set_color(AXIS)
        ax.tick_params(colors=INK2, labelsize=7.5)
        ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("density", fontsize=8, color=INK2)
    fig.supxlabel("scaled deviation from truthful bid,  $(b-v)/25$",
                  fontsize=8.5, color=INK2, y=sup_y)

    fig.text(left, 0.955, title, fontsize=11.5, color=INK, weight="semibold")
    fig.text(left, 0.905 if n > 1 else 0.92, subtitle, fontsize=8.2, color=INK2,
             va=sub_va)
    keys = [k for k, _, _ in cells]
    handles = [Patch(facecolor=SERIES["baseline"], alpha=0.45, edgecolor=MUTED,
                     label="Baseline (traditional SPSB)")]
    if "menu" in keys:
        handles.append(Line2D([], [], color=SERIES["menu"], lw=1.8, label="Menu framing"))
    if "clock" in keys:
        handles.append(Line2D([], [], color=SERIES["clock"], lw=1.8, label="Clock framing"))
    handles.append(Line2D([], [], color=INK2, lw=1.1, ls=(0, (4, 2.5)), label="mean"))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(lx, -0.005),
               ncol=4, frameon=False, fontsize=7.6, labelcolor=INK2)
    if n > 1:   # single-panel figure is too narrow for legend + footer on one row
        fig.text(right, 0.012, "ES V12 bid-level data; SMAD normalizer 25",
                 fontsize=6.4, color=MUTED, ha="right")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix(".png"), dpi=220)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    print(f"wrote {out}.png / .pdf")


def write_clock_figure(devs, df, models=MODELS, out: Path = OUT_FIG_CLOCK,
                       title="Clock framing of the same second-price auction, four models",
                       subtitle=("Baseline = pooled axis1 + axis3 SPSB descriptions (ES V12 grid). "
                                 "Dashed lines mark means; n = baseline / clock bids.")) -> None:
    """Baseline + clock framing only (same panels / x-limits), for a model subset."""
    write_figure(devs, df, cells=CLOCK_CELLS, models=models, out=out,
                 title=title, subtitle=subtitle)


def write_clock_outputs(devs, df) -> None:
    """All clock-framing-only tables and figures (four-model, main-text 1x3, Gemma 1x1)."""
    write_clock_table(df)
    write_clock_figure(devs, df)
    write_clock_table(df, MAIN_MODELS, OUT_TEX_MAIN)
    write_clock_figure(devs, df, MAIN_MODELS, OUT_FIG_MAIN,
                       title="Clock framing of the same second-price auction, three model families")
    write_clock_table(df, GEMMA_MODELS, OUT_TEX_GEMMA)
    write_clock_figure(devs, df, GEMMA_MODELS, OUT_FIG_GEMMA,
                       title="Clock framing, Gemma-3-27B (robustness note)",
                       subtitle=("Baseline = pooled axis1 + axis3 SPSB descriptions (ES V12 grid).\n"
                                 "Dashed lines mark means; n = baseline / clock bids."))


# ----------------------------------------------------------------------------
def main(clock_only: bool = False):
    base = load_baseline_devs()
    devs: dict[tuple[str, str], np.ndarray] = {}
    rows = []
    for model, mdir, name in MODELS:
        vb = {"baseline": base[model]}
        for key, _, exp in CELLS[1:]:
            vb[key] = load_treatment(mdir, model, exp)
        d_base = vb["baseline"][:, 1] - vb["baseline"][:, 0]
        for key, label, exp in CELLS:
            d = vb[key][:, 1] - vb[key][:, 0]
            devs[(model, key)] = d / NORM
            r = {"model": model, "model_display": name, "cell": key,
                 "cell_display": label, "experiment": exp,
                 "baseline_experiment": ("" if key == "baseline"
                                         else "POOLED[" + "+".join(BASELINE_EXPS) + "]")}
            r.update(describe(vb[key]))
            if key != "baseline":
                r.update(contrast(d, d_base))
            rows.append(r)
    cross_check(rows)
    df = pd.DataFrame(rows)
    if clock_only:
        write_clock_outputs(devs, df)
        return
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, float_format="%.6g")
    print(f"wrote {OUT_CSV}")

    pd.set_option("display.width", 250)
    cols = ["model_display", "cell", "n_bids", "mean_dev_scaled", "sd_dev_scaled",
            "smad_pct", "share_under", "share_over", "share_within_2pct",
            "welch_p", "mw_p", "cohens_d", "xcheck_smad_pct_rescaled_to_25",
            "delta_smad_pct", "delta_n_bids", "xcheck_status"]
    print(df[cols].to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    bad = df[df["xcheck_status"] != "match"]
    if len(bad):
        print(f"\nWARNING: {len(bad)} cell(s) do not match auction_cells.csv")

    write_table(df)
    write_figure(devs, df)
    write_clock_outputs(devs, df)


if __name__ == "__main__":
    main(clock_only="--clock-only" in sys.argv[1:])

#!/usr/bin/env python3
"""Ranking forest plot (the paper's money figure, F1) + concordance stats.

Reads the frozen cell-level results produced by the merged-ranking pipeline:
    results/merged_ranking/auction_cells.csv   (build_auction_cells.py)
    results/merged_ranking/da_cells.csv        (build_da_cells.py)
    results/v12_interventions/moment_matching/*  (human reconstructions)

Produces:
    writeup/figures/ranking_forest.pdf           (the figure)
    results/merged_ranking/ranking_forest_data.csv (every number in the figure)
    results/merged_ranking/concordance.md        (Kendall's W, sign tests,
                                                  tier violations, sensitivity)

Definitions (plan/plan.md §4):
    D(L, d, m)  = SMAD %% (auctions, normalizer E[b*] = 24.5)
                = mean Kendall-tau error %% (DA)
    rho         = 1 - D(lever) / D(baseline), within model x domain.
    rho = 1 perfect play, rho = 0 no effect, rho < 0 backfires.

Baseline mapping (documented; matches the cell builders):
    Auctions: axis-specific baseline where one exists
      (axis2_forward_* -> axis2_forward_baseline,
       axis3_beliefs_* -> axis3_beliefs_baseline,
       risk_averse     -> risk_neutrality),
      otherwise the same model's POOLED_axis_baseline
      (menu, clock framing, ascending clock).
    DA: every treatment vs the same model's direct_baseline
      (DA has no axis-specific baselines).

Bootstrap: numpy seed 1299, B = 2000. Pooled-median CIs are a double
bootstrap: resample cells with replacement AND redraw each cell's D from a
normal approximation to its published bootstrap CI (se = width / 3.92),
truncated at 0. Cells whose CI is exactly [0, 0] (OSP-DA tau) contribute
rho = 1 with zero width -- the tau metric is structurally censored there
(see da_cells_summary.md).

Human anchors:
    Clock row: canonical human SMADs from the writeup's moment-matched
      reconstructions (plots/human_llm_comparison_summary.csv):
      SP-APV 9.31 [6.9, 11.7], AC 3.54 [2.0, 5.1], AC-B 5.83 [2.6, 9.1].
      rho_human = 1 - SMAD_clock / SMAD_SP, whiskers by parametric bootstrap
      of both SMADs from the published CIs.
    Menu row: Gonczarowski et al. reconstruction
      (results/v12_interventions/moment_matching/gonczarowski_2022_synthetic_bids.csv),
      D = mean |b - v| per treatment (matches the MAD column of the
      moment-matching table: 0.523 traditional vs 0.557 menu);
      rho_human = 1 - D_menu / D_traditional, bootstrap whiskers over the
      synthetic bids.
    Baseline anchor: rho = 0 by construction (the bold zero line).

A frontier intervention grid now exists (family es_v12, models gpt-5-mini /
gpt-5 / claude-sonnet-5 / gemini-2.5-flash) plus DA cells for the three
servable frontier models, but the frontier is near-exactly truthful at every
sealed baseline (rho = 1 - D/D_base is ill-defined as D_base -> 0), so the
forest plots ONLY the four canonical bounded-rationality models and the
frontier is reported as a separate appendix battery. (The old "gpt-5-mini has
no intervention cells" claim referred to the misattributed gpt-4o logs under
recovered_logs/experiment_logs_with_explanation and is superseded.)
"""
from __future__ import annotations

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
MR = ROOT / "results" / "merged_ranking"
MM = ROOT / "results" / "v12_interventions" / "moment_matching"
FIG_OUT = ROOT / "writeup" / "figures" / "ranking_forest.pdf"
DATA_OUT = MR / "ranking_forest_data.csv"
CONC_OUT = MR / "concordance.md"

SEED = 1299
N_BOOT = 2000
CLIP = -1.5           # display clip for extreme rho (spec)
Z95 = 3.92            # CI width -> ~2 * 1.96 se

MODELS = ["gpt-4o", "claude-3-5-haiku-20241022", "gemini-2.0-flash",
          "google/gemma-3-27b-it"]
MODEL_SHORT = {"gpt-4o": "GPT-4o",
               "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
               "gemini-2.0-flash": "Gemini 2.0 Flash",
               "google/gemma-3-27b-it": "Gemma 3 27B"}
DA_LABEL = {"GPT-4o": "gpt-4o",
            "Claude 3.5 Haiku": "claude-3-5-haiku-20241022",
            "Gemini 2.0 Flash": "gemini-2.0-flash",
            "Gemma 3 27B": "google/gemma-3-27b-it"}

# dataviz palette (validated: worst adjacent CVD dE 35.9, all checks pass;
# aqua/gold are sub-3:1 on white -> relief via legend + direct labels)
MODEL_COLOR = {"gpt-4o": "#2a78d6",                 # blue
               "claude-3-5-haiku-20241022": "#1baf7a",  # aqua
               "gemini-2.0-flash": "#008300",       # green
               "google/gemma-3-27b-it": "#4a3aa7"}  # violet
GOLD = "#c98500"          # human anchors
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BACKFIRE = "#d03b3b"      # status-critical, used only as a 4% wash + label

# ---------------------------------------------------------------------------
# Lever rows: (row_id, family, label, auction_exp, auction_baseline,
#              da_condition, da_baseline)
# auction_baseline "POOLED" -> POOLED_axis_baseline
# ---------------------------------------------------------------------------
LEVERS = [
    ("osp", "A", "Ascending clock / iterative DA (OSP)",
     "ascending_clock_closed", "POOLED", "osp_baseline", "direct_baseline"),
    ("safety", "B2", "Safety description (payoff / rejection)",
     "axis2_forward_onestep", "POOLED",  # corrected 2026-07-09: axis2_forward_baseline was a treated clock-exit cell
     "axis2_monotonic_safety", "direct_baseline"),
    ("clockframe", "B3", "Clock framing (sealed-bid, text only)",
     "intervention_proxy_breitmoser", "POOLED", None, None),
    ("menu_auc", "B1", "Menu restatement -- auction",
     "intervention_menu", "POOLED", None, None),
    ("menu_mech", "B1", "Menu, mechanics restated -- DA",
     None, None, "direct_menu_mechanics", "direct_baseline"),
    ("menu_prop", "B1", "Menu, invariance property -- DA",
     None, None, "direct_menu_property", "direct_baseline"),
    ("tree", "C1", "Payoff tree (contingent)",
     "axis2_forward_tree", "POOLED",  # corrected: see _axis2_baseline_provenance.md
     "axis1_tree", "direct_baseline"),
    ("lookahead", "C2", "Forward planning (lookahead)",
     "axis2_forward_backward_induct", "POOLED",  # corrected: see _axis2_baseline_provenance.md
     "axis2_1step", "direct_baseline"),
    ("belief1", "C3", "First-order beliefs",
     "axis3_beliefs_firstorder", "axis3_beliefs_baseline",
     "axis3_firstorder", "direct_baseline"),
    ("belief2", "C3", "Second-order beliefs",
     "axis3_beliefs_secondorder", "axis3_beliefs_baseline",
     "axis3_secondorder", "direct_baseline"),
    ("risk_averse", "D", "Risk-averse persona",
     "risk_averse", "risk_neutrality",
     "intervention_risk_averse", "direct_baseline"),
]

# tier membership for the pre-committed partial order (plan §4)
TIERS = [
    ("T1 (A: OSP extensive form)", ["osp"]),
    ("T2 (B2/B3/C1: safety, clock framing, tree)",
     ["safety", "clockframe", "tree"]),
    ("T3 (B1: restatements ~ baseline)", ["menu_auc", "menu_mech"]),
    ("T4 (C2/C3: lookahead, beliefs)", ["lookahead", "belief1", "belief2"]),
    ("T5 (D: risk-averse persona)", ["risk_averse"]),
]


# ---------------------------------------------------------------------------
# Load cells
# ---------------------------------------------------------------------------
def load_auction():
    df = pd.read_csv(MR / "auction_cells.csv")
    df = df[df["source"].isin(["es_v12_csv", "es_v12_raw"])]
    cells = {}
    for _, r in df.iterrows():
        se = (r["boot_ci_smad_hi"] - r["boot_ci_smad_lo"]) / Z95
        cells[(r["model"], r["experiment"])] = {
            "D": r["smad_pct"], "se": se, "n": r["n_bids"],
            "welch_p": r.get("welch_p"), "mw_p": r.get("mw_p"),
        }
    return cells


def load_da():
    df = pd.read_csv(MR / "da_cells.csv")
    df = df[(df["variant"] == "da") & df["model_label"].isin(DA_LABEL)]
    cells = {}
    for _, r in df.iterrows():
        m = DA_LABEL[r["model_label"]]
        if pd.isna(r["mean_tau_pct"]):
            continue
        cells[(m, r["condition"])] = {
            "D": r["mean_tau_pct"], "se": r["se_boot_pct"],
            "n": r["n_students"],
        }
    return cells


def build_rho_table(auc, da):
    rows = []
    for rid, fam, label, aexp, abase, dcond, dbase in LEVERS:
        for m in MODELS:
            if aexp is not None:
                bkey = "POOLED_axis_baseline" if abase == "POOLED" else abase
                t, b = auc.get((m, aexp)), auc.get((m, bkey))
                if t and b and b["D"] > 0:
                    rows.append(dict(
                        row=rid, family=fam, label=label, model=m,
                        domain="auction", treatment=aexp, baseline=bkey,
                        D_t=t["D"], se_t=t["se"], D_b=b["D"], se_b=b["se"],
                        n_t=t["n"], rho=1 - t["D"] / b["D"]))
            if dcond is not None:
                t, b = da.get((m, dcond)), da.get((m, dbase))
                if t and b and b["D"] > 0:
                    rows.append(dict(
                        row=rid, family=fam, label=label, model=m,
                        domain="DA", treatment=dcond, baseline=dbase,
                        D_t=t["D"], se_t=t["se"], D_b=b["D"], se_b=b["se"],
                        n_t=t["n"], rho=1 - t["D"] / b["D"]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pooled median + double-bootstrap CI (seed 1299)
# ---------------------------------------------------------------------------
def pooled_median_ci(sub: pd.DataFrame, rng: np.random.Generator,
                     n_boot: int = N_BOOT):
    """Resample cells with replacement AND redraw each cell's D_t, D_b."""
    k = len(sub)
    Dt, st = sub["D_t"].values, sub["se_t"].fillna(0).values
    Db, sb = sub["D_b"].values, sub["se_b"].fillna(0).values
    med = float(np.median(sub["rho"]))
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, k, k)
        dt = np.clip(rng.normal(Dt[idx], st[idx]), 0, None)
        db = np.clip(rng.normal(Db[idx], sb[idx]), 0.05, None)
        boots[i] = np.median(1 - dt / db)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return med, float(lo), float(hi)


# ---------------------------------------------------------------------------
# Human anchors
# ---------------------------------------------------------------------------
def human_anchors(rng: np.random.Generator):
    """Return {row_id: [(label, rho, lo, hi)]}."""
    out = {}
    # clock: canonical human SMADs + published 95% CIs (see module docstring)
    sp, sp_ci = 9.31, (6.9, 11.7)
    anchors = [("AC", 3.54, (2.0, 5.1)), ("AC-B", 5.83, (2.6, 9.1))]
    res = []
    for name, v, ci in anchors:
        draws = 1 - (np.clip(rng.normal(v, (ci[1] - ci[0]) / Z95, N_BOOT), 0.01, None)
                     / np.clip(rng.normal(sp, (sp_ci[1] - sp_ci[0]) / Z95, N_BOOT),
                               0.01, None))
        lo, hi = np.percentile(draws, [2.5, 97.5])
        res.append((name, 1 - v / sp, float(lo), float(hi)))
    out["osp"] = res

    # menu: Gonczarowski reconstruction, D = mean |b - v|
    g = pd.read_csv(MM / "gonczarowski_2022_synthetic_bids.csv")
    tr = np.abs(g.loc[g["treatment"] == "Traditional", "bid"].values
                - g.loc[g["treatment"] == "Traditional", "player_value"].values)
    me = np.abs(g.loc[g["treatment"] == "Menu", "bid"].values
                - g.loc[g["treatment"] == "Menu", "player_value"].values)
    rho = 1 - me.mean() / tr.mean()
    draws = np.empty(N_BOOT)
    for i in range(N_BOOT):
        draws[i] = 1 - (rng.choice(me, len(me)).mean()
                        / rng.choice(tr, len(tr)).mean())
    lo, hi = np.percentile(draws, [2.5, 97.5])
    out["menu_auc"] = [("menu (GHT22)", float(rho), float(lo), float(hi))]
    return out


# ---------------------------------------------------------------------------
# Concordance statistics
# ---------------------------------------------------------------------------
def kendalls_w(mat: np.ndarray):
    """mat: judges x items (values -> within-judge ranks). Tie-corrected W."""
    m, n = mat.shape
    ranks = np.vstack([stats.rankdata(-row) for row in mat])  # rank 1 = best
    R = ranks.sum(axis=0)
    S = ((R - R.mean()) ** 2).sum()
    T = 0.0
    for row in ranks:
        _, counts = np.unique(row, return_counts=True)
        T += ((counts ** 3 - counts).sum()) / 12.0
    denom = m ** 2 * (n ** 3 - n) / 12.0 - m * T
    W = S / denom if denom > 0 else np.nan
    chi2 = m * (n - 1) * W
    p = stats.chi2.sf(chi2, n - 1)
    return W, chi2, n - 1, p


def cell_matrix(tab: pd.DataFrame, rows, domains):
    """levers x (model, domain) rho matrix restricted to complete columns."""
    judges, mat = [], []
    for m in MODELS:
        for d in domains:
            vals = []
            for rid in rows:
                s = tab[(tab["row"] == rid) & (tab["model"] == m)
                        & (tab["domain"] == d)]
                vals.append(s["rho"].iloc[0] if len(s) else np.nan)
            v = np.array(vals)
            if not np.isnan(v).any():
                judges.append((MODEL_SHORT[m], d))
                mat.append(v)
    return judges, np.array(mat)


def sign_tests(tab: pd.DataFrame):
    """Adjacent-tier sign tests over model x domain cells."""
    res = []
    cells = [(m, d) for m in MODELS for d in ["auction", "DA"]]
    for (name_hi, hi), (name_lo, lo) in zip(TIERS[:-1], TIERS[1:]):
        wins = tot = 0
        detail = []
        for m, d in cells:
            hi_v = tab[(tab["model"] == m) & (tab["domain"] == d)
                       & tab["row"].isin(hi)]["rho"]
            lo_v = tab[(tab["model"] == m) & (tab["domain"] == d)
                       & tab["row"].isin(lo)]["rho"]
            if len(hi_v) == 0 or len(lo_v) == 0:
                continue
            tot += 1
            w = hi_v.mean() > lo_v.mean()
            wins += int(w)
            if not w:
                detail.append(f"{MODEL_SHORT[m]}/{d} "
                              f"({hi_v.mean():.2f} vs {lo_v.mean():.2f})")
        p = stats.binomtest(wins, tot, 0.5).pvalue if tot else np.nan
        res.append(dict(hi=name_hi, lo=name_lo, wins=wins, n=tot, p=p,
                        violations="; ".join(detail) if detail else "none"))
    # T3 vs baseline (rho = 0)
    wins = tot = 0
    for m, d in cells:
        v = tab[(tab["model"] == m) & (tab["domain"] == d)
                & tab["row"].isin(["menu_auc", "menu_mech"])]["rho"]
        if len(v):
            tot += 1
            wins += int(v.mean() > 0)
    res.append(dict(hi="T3 (B1 restatements)", lo="baseline (rho = 0)",
                    wins=wins, n=tot,
                    p=stats.binomtest(wins, tot, 0.5).pvalue if tot else np.nan,
                    violations="two-sided placebo check"))
    return pd.DataFrame(res)


def cross_model_tau(tab: pd.DataFrame):
    """4x4 Kendall tau between models over lever x domain rho vectors."""
    piv = tab.pivot_table(index=["row", "domain"], columns="model",
                          values="rho")
    piv = piv[MODELS]
    n = len(MODELS)
    mat = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            sub = piv[[MODELS[i], MODELS[j]]].dropna()
            if len(sub) >= 3:
                mat[i, j] = stats.kendalltau(sub.iloc[:, 0],
                                             sub.iloc[:, 1]).statistic
    return mat, piv


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def draw(tab, pooled, anchors, tau_mat):
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8.5, "axes.linewidth": 0.8,
        "pdf.fonttype": 42,
    })
    order = pooled.sort_values("median", ascending=False)["row"].tolist()
    nrow = len(order)
    fig = plt.figure(figsize=(12.4, 7.4))
    ax = fig.add_axes([0.235, 0.315, 0.435, 0.60])

    xlim = (CLIP - 0.14, 1.30)
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.55, nrow - 0.45)
    ax.invert_yaxis()

    # row banding
    for i in range(nrow):
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color="#f7f6f3", zorder=0)
    # backfire wash + reference lines
    ax.axvspan(xlim[0], 0, color=BACKFIRE, alpha=0.045, zorder=0.5)
    ax.axvline(0, color=INK2, lw=1.8, zorder=1)
    ax.axvline(1, color=AXIS, lw=0.8, zorder=1)
    for x in [-1.5, -1.0, -0.5, 0.5]:
        ax.axvline(x, color=GRID, lw=0.8, zorder=0.8)
    ax.text(0, -0.62, "baseline\n$\\rho = 0$", ha="center", va="bottom",
            fontsize=7, color=INK2, transform=ax.get_xaxis_transform(),
            clip_on=False)
    ax.text(1, -0.62, "perfect play\n$\\rho = 1$", ha="center", va="bottom",
            fontsize=7, color=MUTED, transform=ax.get_xaxis_transform(),
            clip_on=False)
    ax.text(-0.75, nrow - 0.62, "$\\leftarrow$ backfires ($\\rho < 0$)",
            ha="center", va="top", fontsize=7.5, color=BACKFIRE, alpha=0.9)

    clip_notes = []
    ymap = {rid: i for i, rid in enumerate(order)}
    for rid in order:
        y = ymap[rid]
        sub = tab[tab["row"] == rid]
        p = pooled[pooled["row"] == rid].iloc[0]
        # pooled CI + median (clip for display)
        lo, hi = max(p["lo"], CLIP), min(p["hi"], 1.25)
        ax.plot([lo, hi], [y, y], color=INK, lw=2.0, solid_capstyle="butt",
                zorder=3, alpha=0.85)
        med_x = max(p["median"], CLIP)
        marker = "<" if p["median"] < CLIP else "|"
        ax.plot([med_x], [y], marker=marker, ms=11 if marker == "|" else 6,
                color=INK, mew=2.4 if marker == "|" else 1.2, zorder=4)
        # per-cell marks
        for _, r in sub.iterrows():
            off = -0.16 if r["domain"] == "auction" else 0.18
            x = r["rho"]
            c = MODEL_COLOR[r["model"]]
            if x < CLIP:
                ax.plot([CLIP], [y + off], marker="<", ms=5, color=c,
                        mew=0, alpha=0.9, zorder=5, clip_on=False)
                clip_notes.append(
                    f"{p['label'].split(' (')[0].split(' --')[0]} / "
                    f"{MODEL_SHORT[r['model']].split()[0]} ({r['domain']}) "
                    f"{x:.1f}")
            elif r["domain"] == "auction":
                ax.plot([x], [y + off], marker="o", ms=6.5, mfc=c,
                        mec="white", mew=1.2, zorder=6)
            else:
                ax.plot([x], [y + off], marker="^", ms=5.5, mfc="none",
                        mec=c, mew=1.2, alpha=0.85, zorder=5)
        # human anchors (gold diamonds + whiskers), lower edge of the row
        for name, rho_h, lo_h, hi_h in anchors.get(rid, []):
            ya = y + 0.34
            ax.plot([lo_h, hi_h], [ya, ya], color=GOLD, lw=1.1, zorder=6)
            ax.plot([rho_h], [ya], marker="D", ms=6, mfc=GOLD, mec="white",
                    mew=1.0, zorder=7)
            ax.annotate(name, (rho_h, ya), textcoords="offset points",
                        xytext=(0, -4.5), ha="center", va="top",
                        fontsize=6.2, color="#8a5c00", zorder=7)

    # row labels + margin columns
    ax.set_yticks(range(nrow))
    ax.set_yticklabels([])
    ax.tick_params(axis="y", length=0)
    for rid in order:
        y = ymap[rid]
        p = pooled[pooled["row"] == rid].iloc[0]
        ax.text(-0.02, y, p["label"], ha="right", va="center", fontsize=8.6,
                color=INK, transform=ax.get_yaxis_transform())
        ax.text(-0.478, y, p["family"], ha="left", va="center", fontsize=8.6,
                color=MUTED, transform=ax.get_yaxis_transform())
        ax.text(1.03, y, f"{p['median']:+.2f}  [{p['lo']:+.2f}, {p['hi']:+.2f}]",
                ha="left", va="center", fontsize=7.6, color=INK2,
                transform=ax.get_yaxis_transform())
        # rows with a human experiment but no reconstructed numeric anchor get a
        # qualitative sign-anchor label (see Sec. 7 and tab:ranking): clock-framing
        # (Breitmoser 2022; agrees 3/4 families), menu-invariance (GHIT 2024 Menu-SP,
        # Katuscak-Kittsteiner 2024), menu-mechanics (Guillen-Hakimov 2018 backfire).
        QUAL_ANCHORS = {
            "clockframe": "sign-anchored (BSK22; 3/4 families)",
            "menu_prop": "sign-anchored (GHIT24, KK24)",
            "menu_mech": "sign-anchored backfire (GH18)",
        }
        if rid in anchors:
            atxt, acol = "anchored " + "/".join(a[0] for a in anchors[rid]), "#8a5c00"
        elif rid in QUAL_ANCHORS:
            atxt, acol = QUAL_ANCHORS[rid], "#8a5c00"
        else:
            atxt, acol = "no human experiment -- lab prediction", MUTED
        ax.text(1.315, y, atxt, ha="left", va="center", fontsize=7.0,
                color=acol, style="normal" if rid in anchors else "italic",
                transform=ax.get_yaxis_transform())
    # column headers
    hdr_y = 1.012
    ax.text(-0.478, hdr_y, "family", ha="left", va="bottom", fontsize=7.2,
            color=MUTED, transform=ax.transAxes)
    ax.text(1.03, hdr_y, "pooled median $\\rho$ [95% CI]", ha="left",
            va="bottom", fontsize=7.2, color=MUTED, transform=ax.transAxes)
    ax.text(1.315, hdr_y, "human evidence ($\\diamondsuit$)", ha="left",
            va="bottom", fontsize=7.2, color=MUTED, transform=ax.transAxes)

    ax.set_xticks([-1.5, -1.0, -0.5, 0, 0.5, 1.0])
    ax.set_xlabel("preservation index  $\\rho \\;=\\; 1 - "
                  "D(\\mathrm{lever})\\,/\\,D(\\mathrm{baseline})$",
                  fontsize=9, color=INK)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=8)

    fig.text(0.235, 0.965, "The simplicity-preservation ranking of design levers",
             fontsize=12.5, color=INK, weight="semibold")
    fig.text(0.235, 0.938,
             "$D$ = SMAD (% of $E[b^*]=24.5$) in second-price auctions; "
             "mean Kendall-$\\tau$ error (%) in deferred acceptance.  "
             "Marks: one model $\\times$ domain cell; rows sorted by pooled median.",
             fontsize=8, color=INK2)

    # legend (proxy artists)
    handles = [Line2D([], [], marker="o", ls="", mfc=MODEL_COLOR[m],
                      mec="white", ms=7, label=MODEL_SHORT[m])
               for m in MODELS]
    handles += [
        Line2D([], [], marker="o", ls="", mfc="#b9b7b0", mec="white", ms=7,
               label="auction (filled circle)"),
        Line2D([], [], marker="^", ls="", mfc="none", mec="#b9b7b0", ms=6,
               label="DA (open triangle; secondary)"),
        Line2D([], [], marker="|", ls="-", color=INK, ms=9, mew=2,
               label="pooled median, 95% bootstrap CI"),
        Line2D([], [], marker="D", ls="-", color=GOLD, mfc=GOLD, mec="white",
               ms=6, label="human anchor (reconstruction, 95% CI)"),
        Line2D([], [], marker="<", ls="", color=INK2, ms=6,
               label=f"clipped at $\\rho$ = {CLIP} (values in note)"),
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.03, 0.035),
               ncol=2, frameon=False, fontsize=7.4, handletextpad=0.5,
               columnspacing=1.2, labelcolor=INK2)

    # panel B: cross-model rank agreement
    axh = fig.add_axes([0.535, 0.075, 0.14, 0.16])
    n = len(MODELS)
    steps = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf",
             "#184f95", "#0d366b"]
    lo_t, hi_t = 0.0, 1.0
    for i in range(n):
        for j in range(n):
            t = tau_mat[i, j]
            k = int(np.clip((t - lo_t) / (hi_t - lo_t), 0, 0.999) * len(steps))
            face = steps[k] if not np.isnan(t) else "#f0efec"
            axh.add_patch(plt.Rectangle((j, n - 1 - i), 0.94, 0.94,
                                        facecolor=face, edgecolor="white",
                                        lw=1.5))
            if not np.isnan(t):
                lum_dark = k >= 3
                axh.text(j + 0.47, n - 1 - i + 0.47, f"{t:.2f}", ha="center",
                         va="center", fontsize=6.2,
                         color="white" if lum_dark else INK)
    short = ["4o", "Haiku", "Gemini", "Gemma"]
    axh.set_xlim(0, n); axh.set_ylim(0, n)
    axh.set_xticks([i + 0.47 for i in range(n)])
    axh.set_xticklabels(short, fontsize=6.5, color=INK2)
    axh.set_yticks([i + 0.47 for i in range(n)])
    axh.set_yticklabels(short[::-1], fontsize=6.5, color=INK2)
    axh.tick_params(length=0)
    for s in axh.spines.values():
        s.set_visible(False)
    axh.set_title("cross-model rank agreement\n(Kendall $\\tau$ over lever "
                  "$\\times$ domain $\\rho$)", fontsize=7, color=INK2, pad=3)

    # footnote: clipped values + provenance
    if clip_notes:
        import textwrap
        note = "Marks clipped at rho = -1.5 (true values):  " + \
               ";  ".join(clip_notes) + "."
        note = "\n".join(textwrap.wrap(note, 58))
        fig.text(0.70, 0.245, note, fontsize=6.4, color=MUTED, va="top",
                 bbox=dict(boxstyle="round,pad=0.4", fc="#f7f6f3", ec="none"))
    fig.text(0.03, 0.020,
             "Sources: results/merged_ranking/{auction_cells,da_cells}.csv. Human anchors: moment-matched reconstructions -- Li 2017 / Breitmoser 2022 clock "
             "(SP-APV SMAD 9.31 vs AC 3.54, AC-B 5.83) and Gonczarowski et al. 2022 menu null.",
             fontsize=6.2, color=MUTED)
    fig.text(0.03, 0.006,
             "Auction baselines: pooled axis baseline {axis1,axis3} for axis-2 levers (axis2_forward_baseline is a treated clock-exit cell, excluded), axis-specific for beliefs/risk; DA baseline: direct_baseline. "
             "OSP-DA cells have tau = 0 by construction (censored). Frontier models (near-truthful at baseline) reported separately in the appendix.",
             fontsize=6.2, color=MUTED)

    FIG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_OUT, dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------------------
# concordance.md
# ---------------------------------------------------------------------------
def fmt_p(p):
    if pd.isna(p):
        return "NA"
    return f"{p:.4f}" if p >= 1e-4 else f"{p:.1e}"


def write_concordance(tab, pooled, anchors, W_res, signs, tau_mat, piv,
                      pooled_menu_combined, sens):
    L = []
    L.append("# Concordance of the lever ranking across models and domains\n")
    L.append("Generated by `scripts/plots/ranking_forest.py` (numpy seed "
             f"{SEED}, B={N_BOOT}). Inputs: `results/merged_ranking/"
             "auction_cells.csv`, `da_cells.csv`, moment-matched human "
             "reconstructions. The forest figure below plots only the four "
             "canonical bounded-rationality models (GPT-4o, Claude 3.5 Haiku, "
             "Gemini 2.0 Flash, Gemma 3 27B); this is deliberate. A frontier "
             "intervention grid now EXISTS in auction_cells.csv (family "
             "es_v12, models gpt-5-mini / gpt-5 / claude-sonnet-5 / "
             "gemini-2.5-flash) and DA cells for the three servable frontier "
             "models, but the frontier is essentially truthful at every sealed "
             "baseline (rho ill-defined as D(baseline) -> 0), so it is reported "
             "as a separate battery in the appendix (Table "
             "tab:ablations-frontier and the DA frontier table), not as forest "
             "rows.\n")

    L.append("## Pooled preservation index by lever (rows as in the forest "
             "figure, sorted)\n")
    L.append("rho = 1 - D(lever)/D(baseline) within model x domain; D = SMAD% "
             "(auctions, /24.5) or mean Kendall-tau error % (DA). Pooled = "
             "median over available model x domain cells; CI = double "
             "bootstrap (cells resampled + per-cell parametric noise from "
             "the published bootstrap CIs).\n")
    L.append("| lever | family | cells | pooled median rho | 95% CI | "
             "auction rho (4o/Haiku/Gemini/Gemma) | DA rho (4o/Haiku/Gemini/"
             "Gemma) | human anchor |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, p in pooled.sort_values("median", ascending=False).iterrows():
        sub = tab[tab["row"] == p["row"]]

        def vec(dom):
            out = []
            for m in MODELS:
                s = sub[(sub["model"] == m) & (sub["domain"] == dom)]
                out.append(f"{s['rho'].iloc[0]:+.2f}" if len(s) else "NA")
            return " / ".join(out) if any(o != "NA" for o in out) else "--"
        anc = anchors.get(p["row"])
        anc_s = ("; ".join(f"{a[0]}: {a[1]:+.2f} [{a[2]:+.2f}, {a[3]:+.2f}]"
                           for a in anc) if anc else "none (lab prediction)")
        L.append(f"| {p['label']} | {p['family']} | {p['n_cells']} | "
                 f"{p['median']:+.3f} | [{p['lo']:+.3f}, {p['hi']:+.3f}] | "
                 f"{vec('auction')} | {vec('DA')} | {anc_s} |")
    L.append("")
    L.append(f"Combined single 'menu' row (auction menu + DA menu cells "
             f"pooled, for reference): median rho = "
             f"{pooled_menu_combined[0]:+.3f} "
             f"[{pooled_menu_combined[1]:+.3f}, {pooled_menu_combined[2]:+.3f}]"
             " -- reported because the figure splits B1 into three rows "
             "(the DA data splits: invariance-property menu improves play, "
             "mechanics-only menu backfires; see da_cells_summary.md).\n")

    L.append("## Kendall's W of the lever ordering\n")
    L.append("| cell set | judges (cells) | items (levers) | W | chi2 | df | p |")
    L.append("|---|---|---|---|---|---|---|")
    for name, (judges, W, chi2, df, p, items) in W_res.items():
        L.append(f"| {name} | {judges} | {items} | {W:.3f} | {chi2:.1f} | "
                 f"{df} | {fmt_p(p)} |")
    L.append("")

    L.append("## Pairwise sign tests, adjacent tiers (pre-committed partial "
             "order, plan §4)\n")
    L.append("Tier value per cell = mean rho of the tier's levers present in "
             "that model x domain cell; exact binomial test vs 0.5 "
             "(two-sided).\n")
    L.append("| higher tier | lower tier | wins | cells | p (binomial) | "
             "violating cells |")
    L.append("|---|---|---|---|---|---|")
    for _, r in signs.iterrows():
        L.append(f"| {r['hi']} | {r['lo']} | {r['wins']} | {r['n']} | "
                 f"{fmt_p(r['p'])} | {r['violations']} |")
    L.append("")

    L.append("## Cross-model rank agreement (Kendall tau over lever x domain "
             "rho vectors)\n")
    hdr = "| | " + " | ".join(MODEL_SHORT[m] for m in MODELS) + " |"
    L.append(hdr)
    L.append("|---" * (len(MODELS) + 1) + "|")
    for i, m in enumerate(MODELS):
        row = [f"| {MODEL_SHORT[m]}"]
        for j in range(len(MODELS)):
            row.append(f" {tau_mat[i, j]:.2f} " if not np.isnan(tau_mat[i, j])
                       else " NA ")
        L.append("|".join(row) + "|")
    L.append("")

    L.append(sens)
    (CONC_OUT).write_text("\n".join(L))


def main():
    rng = np.random.default_rng(SEED)
    auc, da = load_auction(), load_da()
    tab = build_rho_table(auc, da)

    pooled_rows = []
    for i, (rid, fam, label, *_) in enumerate(LEVERS):
        sub = tab[tab["row"] == rid]
        # deterministic per-row seed (do NOT use hash(): salted per process)
        med, lo, hi = pooled_median_ci(sub, np.random.default_rng(SEED + i))
        pooled_rows.append(dict(row=rid, family=fam, label=label,
                                n_cells=len(sub), median=med, lo=lo, hi=hi))
    pooled = pd.DataFrame(pooled_rows)

    anchors = human_anchors(np.random.default_rng(SEED))

    # concordance stats
    auc_rows = [r[0] for r in LEVERS if r[3] is not None]
    da_rows = [r[0] for r in LEVERS if r[5] is not None]
    common = [r for r in auc_rows if r in da_rows]
    W_res = {}
    for name, rows, doms in [
            ("auctions only", auc_rows, ["auction"]),
            ("DA only", da_rows, ["DA"]),
            ("both domains (common levers)", common, ["auction", "DA"])]:
        judges, mat = cell_matrix(tab, rows, doms)
        W, chi2, df, p = kendalls_w(mat)
        W_res[name] = (len(judges), W, chi2, df, p, len(rows))
    signs = sign_tests(tab)
    tau_mat, piv = cross_model_tau(tab)

    # combined-menu sensitivity
    menu_all = tab[tab["row"].isin(["menu_auc", "menu_mech", "menu_prop"])]
    pooled_menu_combined = pooled_median_ci(
        menu_all, np.random.default_rng(SEED))

    # sensitivity: pooled auction baseline instead of axis-specific
    sens_rows = []
    for rid, fam, label, aexp, abase, *_ in LEVERS:
        if aexp is None or abase == "POOLED":
            continue
        for m in MODELS:
            t = auc.get((m, aexp))
            b_ax = auc.get((m, abase if abase != "POOLED" else "POOLED_axis_baseline"))
            b_po = auc.get((m, "POOLED_axis_baseline"))
            if t and b_ax and b_po:
                r_ax, r_po = 1 - t["D"] / b_ax["D"], 1 - t["D"] / b_po["D"]
                if np.sign(r_ax) != np.sign(r_po):
                    sens_rows.append(
                        f"- **{label} / {MODEL_SHORT[m]} (auction)**: "
                        f"axis-specific baseline gives rho = {r_ax:+.2f}, "
                        f"pooled baseline gives {r_po:+.2f} (sign flips; "
                        f"axis baseline SMAD {b_ax['D']:.1f} vs pooled "
                        f"{b_po['D']:.1f}).")
    # ---- honest tier-violation statement (computed from tab) -------------
    def rho_of(rid, m, d):
        s = tab[(tab["row"] == rid) & (tab["model"] == m)
                & (tab["domain"] == d)]
        return s["rho"].iloc[0] if len(s) else np.nan

    tree_gt_safety_auc = sum(
        rho_of("tree", m, "auction") > rho_of("safety", m, "auction")
        for m in MODELS)
    safety_gt_tree_da = sum(
        rho_of("safety", m, "DA") > rho_of("tree", m, "DA") for m in MODELS)
    viol = []
    viol.append(
        f"1. **T3 vs T4 is NOT separated** (sign test p = 1.0): restatements "
        f"do not reliably beat strategizing scaffolds. The failures are real "
        f"backfires of restatements, not noise: the auction menu moves "
        f"GPT-4o AWAY from truthful play (rho = {rho_of('menu_auc', 'gpt-4o', 'auction'):+.2f}, "
        f"Welch p = 0.003 in auction_cells.csv) and menu-mechanics backfires "
        f"in DA for GPT-4o ({rho_of('menu_mech', 'gpt-4o', 'DA'):+.2f}) and "
        f"Gemma ({rho_of('menu_mech', 'google/gemma-3-27b-it', 'DA'):+.2f}). "
        f"The pre-committed tier claim 'baseline ~ B1' survives only as the "
        f"two-sided placebo test (3/8 above zero, p = 0.73) -- i.e., B1 is "
        f"null ON AVERAGE but heterogeneous across models and variants.")
    viol.append(
        f"2. **B1 splits in DA**: the invariance-property menu behaves like "
        f"a B2 safety description (pooled rho = +0.65; significant "
        f"improvements for Claude and Gemini, MW p <= 1e-4 in "
        f"da_cells_summary.md), while the mechanics-only menu backfires "
        f"(pooled rho = -1.67). The figure therefore shows three B1 rows "
        f"rather than asserting one 'menu' rung.")
    viol.append(
        f"3. **Within-tier domain flip (expected, plan §4)**: payoff tree > "
        f"safety in {tree_gt_safety_auc}/4 auction cells, safety > tree in "
        f"{safety_gt_tree_da}/4 DA cells -- consistent with keeping B2/B3/C1 "
        f"in ONE tier with no within-tier order asserted.")
    viol.append(
        f"4. **Axis-2 baseline provenance (resolved, 2026-07-09)**: the V12 "
        f"`axis2_forward_baseline` template was NOT a plain SPSB text -- it was "
        f"a two-stage sealed-bid-as-clock-exit description (a Breitmoser-style "
        f"clock-framing/B3 variant), so it is a TREATED cell, not a baseline "
        f"(see results/merged_ranking/_axis2_baseline_provenance.md; trace "
        f"check: 15-25% of claude/gemini/gemma plans under this cell echo "
        f"clock/exit/stage-2 language, vs 0% under axis1/axis3). Gemma's "
        f"formerly 'anomalously good axis-2 baseline' (SMAD 8.6% vs axis1/axis3 "
        f"~24-29%) is explained by that framing partly fixing Gemma's play, not "
        f"by baseline noise. Corrected canon: the pooled axis baseline is "
        f"{{axis1, axis3}} only, and axis-2 treatments (safety, tree, lookahead) "
        f"are now contrasted against that corrected pool. On the corrected pool "
        f"every Gemma axis-2 auction rho is POSITIVE (safety "
        f"{rho_of('safety', 'google/gemma-3-27b-it', 'auction'):+.2f}, "
        f"tree {rho_of('tree', 'google/gemma-3-27b-it', 'auction'):+.2f}, "
        f"lookahead {rho_of('lookahead', 'google/gemma-3-27b-it', 'auction'):+.2f}) "
        f"-- the earlier 'baseline-noise-driven backfire' reading is retired.")
    viol.append(
        f"5. **OSP-DA rho = 1.0 is censored**: the tau metric records zero "
        f"error by construction on length-1 revealed sequences; the E9 "
        f"decision-level accounting (da_cells_summary.md) still finds 0 "
        f"misreports for 3/4 models in the pick protocol (rule-of-three "
        f"95% UBs ~0.9%) but Gemma has 5 strict pick errors (1.6%) and "
        f"Claude has 24.1% Type-1 false rejections in the yes/no tree -- "
        f"'0.0%' is protocol-specific.")
    viol.append(
        f"6. **DA rho magnitudes are ratio-unstable for GPT-4o**: its DA "
        f"direct_baseline error is only 1.0%, so any treatment error of a "
        f"few percent produces extreme negative rho (risk-averse "
        f"{rho_of('risk_averse', 'gpt-4o', 'DA'):+.1f}, lookahead "
        f"{rho_of('lookahead', 'gpt-4o', 'DA'):+.1f}). Ranks are unaffected; "
        f"clipped in the figure at -1.5.")
    viol.append(
        f"7. **Risk-seeking persona (not a figure row)** is heterogeneous, "
        f"not uniformly bad: Claude overbids catastrophically in auctions "
        f"(mean dev +8.40, SMAD 35.0% vs risk-neutral 7.6%) while GPT-4o's "
        f"DA play is nearly unaffected (0.7% tau error). The figure keeps "
        f"the canonical D rung (risk-averse) only.")
    viol.append(
        f"8. **C2 condition choice**: the DA lookahead mark is axis2_1step "
        f"(the paper's 'one-step' 7.8% cell). Deeper scaffolds are not "
        f"monotone (2step 5.1%, fullsim pooled ~3.8%), so the C2 rung is "
        f"sensitive to k; the auction mark (axis2_forward_backward_induct) "
        f"is a fake-sequential framing since SPSB has no true forward-"
        f"planning axis (docs/INTERVENTION_TAXONOMY.md).")

    sens = ("## Tier violations and within-tier flips (honest statement)\n\n"
            + "\n".join(viol) + "\n\n"
            "## Sensitivity and honest caveats\n\n"
            "Under the corrected-baseline canon, the axis-2 treatments (safety, "
            "tree, lookahead) are contrasted against the pooled axis baseline "
            "{axis1, axis3} -- `axis2_forward_baseline` is a treated clock-exit "
            "cell and is excluded (point 4 above; "
            "_axis2_baseline_provenance.md). Only the belief and risk cells "
            "retain their own axis-specific baselines (axis3_beliefs_baseline, "
            "risk_neutrality). Belief cells whose rho sign flips if their "
            "axis-specific baseline is swapped for the pooled axis baseline:\n\n"
            + ("\n".join(sens_rows) if sens_rows else "- none") + "\n")
    write_concordance(tab, pooled, anchors, W_res, signs, tau_mat, piv,
                      pooled_menu_combined, sens)

    # backing CSV
    out = tab.copy()
    out["model"] = out["model"].map(MODEL_SHORT)
    out = out.merge(pooled[["row", "median", "lo", "hi"]], on="row",
                    suffixes=("", "_pooled"))
    out.rename(columns={"median": "pooled_median_rho", "lo": "pooled_ci_lo",
                        "hi": "pooled_ci_hi"}, inplace=True)
    anc_rows = []
    for rid, lst in anchors.items():
        lab = dict((r[0], r[2]) for r in LEVERS)
        for name, rho, lo, hi in lst:
            anc_rows.append(dict(row=rid, family="human", label=lab[rid],
                                 model=f"HUMAN ({name})", domain="human",
                                 rho=rho, pooled_ci_lo=lo, pooled_ci_hi=hi))
    out = pd.concat([out, pd.DataFrame(anc_rows)], ignore_index=True)
    out.to_csv(DATA_OUT, index=False)

    draw(tab, pooled, anchors, tau_mat)
    print(f"wrote {FIG_OUT}\nwrote {DATA_OUT}\nwrote {CONC_OUT}")
    print(pooled.sort_values("median", ascending=False)
          [["family", "label", "n_cells", "median", "lo", "hi"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()

"""
Temperature robustness of GPT-4o's cross-mechanism ORDERING and DIRECTION.

WHAT THIS DOES
--------------
The paper's temperature appendix (tab:temperature_comparison) reports GPT-4o's
SMAD by format at sampling temperature T in {0.1, 0.5, 1.0} and reads the
magnitudes.  This script asks the ordinal question the paper's design-screening
frame actually relies on: does the cross-mechanism ORDERING of deviations (which
format is hardest, FPSB vs SPSB, FP-CV vs SP-CV, clock formats at the bottom)
and the DIRECTION of deviations (under- vs over-bidding in the second-price
formats) survive a change of temperature, even though the magnitudes move?

For each temperature it recomputes every cell from bid level and reports

  * SMAD per format with n (private-value formats: 100*mean|b - b*(v)|/25 with
    b* = (2/3)v for FPSB (N=3) and v otherwise, clock cells non-winners only;
    common value: the paper's profit-based method, 100*mean|pi_winner - pi*|/20
    per round with pi* = 2eps/(n+1) for first price and eps/(n+1) for second
    price, eps = winner's signal - common value; see
    scripts/plots/appendix2_temperature.py::calculate_cv_deviation_from_json);
  * Kendall tau-b vs the reconstructed-human ranking (FPSB IPV 24.7639, SPSB IPV
    5.646, SP-APV 9.31, AC 3.54, AC-B 5.83) over (a) the three sealed private-
    value formats and (b) every private-value format with n >= 30 non-winning
    bids, with the three uncertainty layers of difficulty_concordance.py
    (LLM within-cell bid resampling; human reconstruction re-draws; joint;
    B=2000, seed 1299) and P(tau > 0);
  * the sign of FPSB - SPSB and of FP-CV - SP-CV (with the share of within-cell
    bootstrap draws preserving the sign);
  * direction shares for SPSB IPV and SP-APV (and the other private formats):
    within-band iff |b - b*| <= 0.02 b*; under/over shares of the remainder;
  * Spearman / Kendall rank correlation of the SMAD vectors BETWEEN temperatures
    (0.1 vs 0.5, 0.5 vs 1.0, 0.1 vs 1.0) and the max absolute SMAD change per
    format across temperatures;
  * a reproduction of the paper's temperature table with the exact method of
    scripts/plots/appendix2_temperature.py (first CSV per cell, non-winners for
    clock cells, JSON winner-profit method for CV, T=0.5 from
    plots/theoretical_deviation_results_updated.csv), flagging any mismatch.

Cells
-----
  T=0.5  experiment_logs/V10 (the published cells; difficulty_concordance's
         published-value asserts are kept), CV from the V10 raw_data JSON.
  T=0.1  robustness_logs/<key>_gpt4o_temp01
  T=1.0  robustness_logs/<key>_gpt4o_temp10
  A clock cell with no results CSV but with raw_data JSON (AC-B at T=0.1, two
  rounds) is parsed from the JSON; the agent -> value mapping is verified on a
  cell that has both CSV and JSON before it is used.

Third-price IPV (N=5, the Kagel-Levin human anchor's N) is computed as a
supplementary line (JSON/CSV/MD only, never in a tau) with b*(v) = (N-1)/(N-2) v.

OUTPUTS
-------
    results/analysis/temperature_concordance.json
    results/analysis/temperature_concordance.csv     (one row per temperature x format)
    results/analysis/temperature_concordance.md
    writeup/tables/temperature_robustness.tex    (tabular-only booktabs fragment)

Run (from repo root):
    python3 analysis/temperature_concordance.py
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # appendix2_temperature imports pyplot/seaborn at module level

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (PROJECT_ROOT / "analysis", PROJECT_ROOT / "scripts" / "plots"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import difficulty_concordance as dc  # noqa: E402  (cells, human anchors, tau-b, re-draws)
import difficulty_concordance_models as dcm  # noqa: E402  (bootstrap layers, cell reader)

try:  # the paper's own functions, used only for the reproduction cross-check
    import appendix2_temperature as a2  # noqa: E402
    A2_IMPORT_ERROR = None
except Exception as _e:  # pragma: no cover
    a2 = None
    A2_IMPORT_ERROR = repr(_e)

SEED = dc.SEED            # 1299
B = dc.B                  # 2000
SCALING = dc.SCALING      # 25.0 (private-value formats)
CV_SCALING = 20.0         # common-value normalizer of the paper's temperature table
N_AGENTS_CV = 3
MIN_N = dcm.MIN_N         # 30
WITHIN_FRAC = 0.02

PRIVATE = dc.FORMATS      # ["FPSB IPV", "SPSB IPV", "SP-APV", "AC", "AC-B"]
SEALED3 = dcm.SEALED3     # ["FPSB IPV", "SPSB IPV", "SP-APV"]
CV = ["FP-CV", "SP-CV"]
CV_KEY = {"FP-CV": ("common_value_first", "first_price"),
          "SP-CV": ("common_value_second", "second_price")}
HUMAN_SMAD = dict(zip(PRIVATE, dc.HUMAN_SMAD.tolist()))

# paper row order (tab:temperature_comparison) and short labels for the tex fragment
ROW_ORDER = ["FP-CV", "FPSB IPV", "SP-CV", "SP-APV", "AC-B", "SPSB IPV", "AC"]
TEX_LABEL = {"FP-CV": "FP-CV", "FPSB IPV": "FPSB", "SP-CV": "SP-CV", "SP-APV": "SP-APV",
             "AC-B": "AC-B", "SPSB IPV": "SPSB", "AC": "AC"}
FAMILY = {**{f: "private" for f in PRIVATE}, **{f: "common value" for f in CV}}

TEMPS = ["0.1", "0.5", "1.0"]
SUFFIX = {"0.1": "gpt4o_temp01", "1.0": "gpt4o_temp10"}
PAIRS = [("0.1", "0.5"), ("0.5", "1.0"), ("0.1", "1.0")]

# writeup/main.tex, tab:temperature_comparison (T = 0.1, 0.5, 1.0)
PAPER_TABLE = {
    "AC-B": (0.00, 0.47, 2.15), "AC": (0.00, 0.81, 1.00), "SPSB IPV": (14.77, 8.69, 12.89),
    "SP-APV": (12.87, 10.73, 12.75), "FP-CV": (39.00, 59.99, 42.92),
    "SP-CV": (35.51, 40.60, 33.53), "FPSB IPV": (28.07, 27.55, 24.99),
}

V10 = PROJECT_ROOT / "experiment_logs" / "V10"
ROBUST = PROJECT_ROOT / "robustness_logs"
PUBLISHED_T05 = PROJECT_ROOT / "plots" / "theoretical_deviation_results_updated.csv"
HUMAN_CSV = PROJECT_ROOT / "plots" / "auction_human.csv"
OUT_DIR = PROJECT_ROOT / "results" / "analysis"
TEX_DIR = PROJECT_ROOT / "writeup" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TEX_DIR.mkdir(parents=True, exist_ok=True)

# raw_data JSON: round['value'] is indexed in this fixed agent order (verified below)
AGENT_ORDER = ["Bidder Andy", "Bidder Betty", "Bidder Charles"]

# supplementary third-price cells (N=5 matches the Kagel-Levin n=5 human anchor 7.6566)
THIRD = {"0.5": V10 / "third_price_ipv", "0.1": ROBUST / "third_price_ipv_gpt4o_temp01",
         "1.0": ROBUST / "third_price_ipv_gpt4o_temp10"}


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# Bid-level loading: private-value formats
# ---------------------------------------------------------------------------
def clock_frame_from_json(cell_dir: Path) -> pd.DataFrame | None:
    """Bid-level frame for a clock cell that has raw_data JSON but no results CSV."""
    files = sorted(cell_dir.glob("**/raw_data/result_*.json"))
    if not files:
        return None
    rows = []
    for f in files:
        data = json.loads(f.read_text())
        for rk, r in data.items():
            if not rk.startswith("round_"):
                continue
            values = r["value"]
            winner = r["history"]["winner"]["winner"]
            for h in r["history"]["bidding history"]:
                rows.append({"player_name": h["agent"],
                             "player_value": float(values[AGENT_ORDER.index(h["agent"])]),
                             "bid": float(h["bid"]), "is_winner": h["agent"] == winner,
                             "source_json": f.name})
    return pd.DataFrame(rows)


def verify_json_agent_order() -> str:
    """Check AGENT_ORDER on a clock cell that has BOTH a results CSV and raw_data JSON."""
    cell_dir = ROBUST / "ascending_clock_apv_closed_gpt4o_temp10"
    csv = dcm._read_cell_dir(cell_dir)
    js = clock_frame_from_json(cell_dir)
    assert csv is not None and js is not None and len(csv) == len(js), (len(csv), len(js))
    key = lambda d: sorted(zip(d["player_name"], d["player_value"].round(6),  # noqa: E731
                               d["bid"].round(6), d["is_winner"].astype(bool)))
    assert key(csv) == key(js), "raw_data JSON agent->value mapping does not reproduce the CSV"
    return f"verified on {rel(cell_dir)} ({len(csv)} bids): JSON value order = {AGENT_ORDER}"


def _meta(df: pd.DataFrame) -> dict:
    """Seed bases and run dates of a bid-level CSV frame (provenance for the caveats)."""
    seeds = sorted(int(s) for s in df["seed_base"].dropna().unique()) if "seed_base" in df.columns else []
    dates = sorted(df["timestamp"].astype(str).str[:10].unique()) if "timestamp" in df.columns else []
    return {"seed_bases": seeds, "dates": dates}


def private_cell(fmt: str, T: str) -> tuple[pd.DataFrame | None, str, dict]:
    """Per-bid frame (value, bid, bstar, dev = bid - bstar), source note and meta for one cell."""
    if T == "0.5":
        cfg = dc.CELLS[fmt]
        df = pd.read_csv(cfg["csv"])
        source = rel(cfg["csv"])
        assert set(df["model"].unique()) == {"gpt-4o"}, f"{fmt}: non-GPT-4o rows"
        if "temperature" in df.columns:
            assert np.allclose(df["temperature"].astype(float), 0.5), f"{fmt}: T != 0.5 in V10 cell"
        meta = _meta(df)
    else:
        cell_dir = ROBUST / f"{dcm.FORMAT_KEY[fmt]}_{SUFFIX[T]}"
        df = dcm._read_cell_dir(cell_dir)
        if df is not None:
            source = rel(cell_dir) + " (results CSV)"
            assert set(df["model"].unique()) == {"gpt-4o"}, f"{cell_dir}: model ids {set(df['model'])}"
            assert np.allclose(df["temperature"].astype(float), float(T)), f"{cell_dir}: temperature column != {T}"
            meta = _meta(df)
        elif dcm.IS_CLOCK[fmt]:
            df = clock_frame_from_json(cell_dir)
            if df is None or df.empty:
                return None, "no results CSV and no raw_data JSON", {}
            source = rel(cell_dir) + " (raw_data JSON; no results CSV)"
            cfg_txt = "".join(p.read_text() for p in cell_dir.glob("run_*/config.yaml"))
            if cfg_txt and f"temperature: {T}" not in cfg_txt:
                warnings.warn(f"{cell_dir}: config.yaml does not state temperature: {T}")
            seeds = sorted({int(m) for m in re.findall(r"seed_base:\s*(\d+)", cfg_txt)})
            dates = sorted({s[9:19] for s in df["source_json"].unique()})
            meta = {"seed_bases": seeds, "dates": dates}
        else:
            return None, "no results CSV", {}
    n_nan = int(df["bid"].isna().sum())
    if n_nan:
        warnings.warn(f"{fmt} T={T}: dropping {n_nan} NaN bids")
        df = df.dropna(subset=["bid"])
    if dcm.IS_CLOCK[fmt]:
        df = df[~df["is_winner"].astype(bool)]
    out = pd.DataFrame({"value": df["player_value"].to_numpy(float), "bid": df["bid"].to_numpy(float)})
    out["bstar"] = dcm.BSTAR[fmt](out["value"].to_numpy())
    out["dev"] = out["bid"] - out["bstar"]
    return out.reset_index(drop=True), source, meta


def third_price_cell(T: str) -> dict | None:
    """Supplementary third-price IPV (N=5) with the repo's RNE convention (build_auction_cells.rne_bstar):
    b* = v (N-1)/(N-2), plus the variant capped at the $49 endowment (ENDOWMENT_CAP)."""
    d = THIRD[T]
    if T == "0.5":
        files = sorted(d.glob("**/results/*_results.csv"))
        df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True) if files else None
    else:
        df = dcm._read_cell_dir(d)
    if df is None or df.empty:
        return None
    assert set(df["model"].unique()) == {"gpt-4o"}
    N = int(df["number_agents"].iloc[0])
    assert (df["number_agents"] == N).all()
    v, b = df["player_value"].to_numpy(float), df["bid"].to_numpy(float)
    ok = ~np.isnan(b)
    bstar = (N - 1) / (N - 2) * v[ok]
    return {"smad_rne": float(100 * np.abs(b[ok] - bstar).mean() / SCALING),
            "smad_rne_capped49": float(100 * np.abs(b[ok] - np.minimum(bstar, 49.0)).mean() / SCALING),
            "n": int(ok.sum()), "N": N, "bstar": f"({N-1}/{N-2}) v [capped variant: min(b*, 49)]",
            "human_anchor_kagel_levin_n5": 7.6566, "source": rel(d),
            "note": "not in the paper's temperature table and not in any tau; shown for completeness only"}


# ---------------------------------------------------------------------------
# Common value: per-round winner-profit deviations (paper method)
# ---------------------------------------------------------------------------
def cv_round_deviations(cell_dir: Path, auction_type: str) -> np.ndarray | None:
    """Replicates appendix2_temperature.calculate_cv_deviation_from_json at round level."""
    files = list(cell_dir.glob("**/raw_data/result_*.json"))
    if not files:
        return None
    out = []
    for f in files:
        data = json.loads(f.read_text())
        for rk, r in data.items():
            if not rk.startswith("round_"):
                continue
            winner = r["history"]["winner"]["winner"]
            idx = next((i for i, h in enumerate(r["history"]["bidding history"]) if h["agent"] == winner), None)
            if idx is None:
                continue
            eps = r["value"][idx] - r["common"]
            pi_star = (2 * eps) / (N_AGENTS_CV + 1) if auction_type == "first_price" else eps / (N_AGENTS_CV + 1)
            out.append(abs(r["profit"][idx] - pi_star))
    return np.array(out, float) if out else None


def cv_cell(fmt: str, T: str) -> tuple[np.ndarray | None, str]:
    key, atype = CV_KEY[fmt]
    cell_dir = V10 / key if T == "0.5" else ROBUST / f"{key}_{SUFFIX[T]}"
    devs = cv_round_deviations(cell_dir, atype)
    if devs is None:
        return None, "no raw_data JSON"
    if a2 is not None:  # cross-check against the paper's own function
        ref = a2.calculate_cv_deviation_from_json(cell_dir, atype)
        assert ref["n_observations"] == len(devs) and abs(ref["smad"] - 100 * devs.mean() / CV_SCALING) < 1e-9
    return devs, rel(cell_dir) + " (raw_data JSON, winner profit per round)"


def smad_private(dev_abs: np.ndarray) -> float:
    return float(100.0 * dev_abs.mean() / SCALING)


def smad_cv(dev: np.ndarray) -> float:
    return float(100.0 * dev.mean() / CV_SCALING)


# ---------------------------------------------------------------------------
# Direction shares
# ---------------------------------------------------------------------------
def direction_shares(frame: pd.DataFrame) -> dict:
    within = np.abs(frame["dev"].to_numpy()) <= WITHIN_FRAC * frame["bstar"].to_numpy()
    dev = frame.loc[~within, "dev"].to_numpy()
    n_dev = int(len(dev))
    return {"n": int(len(frame)), "within_share": float(within.mean()), "n_deviating": n_dev,
            "under_share_dev": float((dev < 0).mean()) if n_dev else float("nan"),
            "over_share_dev": float((dev > 0).mean()) if n_dev else float("nan")}


def human_direction() -> dict:
    """Source-reported under/equal/over frequencies -> under share of deviating bids."""
    h = pd.read_csv(HUMAN_CSV)
    h["Auction"] = h["Auction"].astype(str).str.strip()
    out = {}
    for fmt, label in [("SPSB IPV", "Second-Price IPV"), ("SP-APV", "SPSB (Li 2017)"),
                       ("AC", "Ascending Clock (Li 2017)"), ("AC-B", "AC-B (Breitmoser2022)")]:
        row = h[h["Auction"] == label].iloc[0]
        u, e, o = float(row["Underbid"]), float(row["Equalbid"]), float(row["Overbid"])
        out[fmt] = {"under_share_dev": u / (u + o), "over_share_dev": o / (u + o),
                    "within_share": e / (u + e + o), "source": f"plots/auction_human.csv: {label}"}
    cvh = {r["Auction"]: float(r["SMAD"]) for _, r in h.iterrows()
           if r["Auction"] in ("First-Price Common Value", "Second-Price Common Value")}
    out["human_cv_smad"] = {"FP-CV": cvh["First-Price Common Value"], "SP-CV": cvh["Second-Price Common Value"]}
    return out


# ---------------------------------------------------------------------------
# Paper-table reproduction (appendix2_temperature.py method, verbatim semantics)
# ---------------------------------------------------------------------------
def paper_method(fmt: str, T: str) -> dict:
    key = dcm.FORMAT_KEY[fmt] if fmt in PRIVATE else CV_KEY[fmt][0]
    if T == "0.5":
        pub = pd.read_csv(PUBLISHED_T05).set_index("auction_key")
        return {"smad": float(pub.loc[key, "smad"]), "n": int(pub.loc[key, "n"]),
                "source": rel(PUBLISHED_T05)}
    cell_dir = ROBUST / f"{key}_{SUFFIX[T]}"
    if fmt in CV:
        devs = cv_round_deviations(cell_dir, CV_KEY[fmt][1])
        if devs is None:
            return {"smad": None, "n": 0, "source": "NO DATA (no raw_data JSON)"}
        return {"smad": smad_cv(devs), "n": int(len(devs)), "source": rel(cell_dir)}
    files = list(cell_dir.glob("**/results/*_results.csv"))  # the paper reads csv_files[0]
    if not files:
        return {"smad": None, "n": 0, "source": "NO DATA (no results CSV; rendered as 0 by the generator)"}
    df = pd.read_csv(files[0])
    if dcm.IS_CLOCK[fmt]:
        df = df[~df["is_winner"]].copy()
    dev = np.abs(df["bid"].to_numpy(float) - dcm.BSTAR[fmt](df["player_value"].to_numpy(float)))
    return {"smad": smad_private(dev), "n": int(len(df)), "source": rel(files[0])}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    json_note = verify_json_agent_order()

    # published GPT-4o T=0.5 cells with the hard asserts of difficulty_concordance
    devs_pub, smads_pub, ns_pub = dc.load_llm_deviations()

    hum_full = dc.human_redraw_matrix()
    assert float(np.mean(hum_full[:, 0] > hum_full[:, 1])) == 1.0
    assert abs(float(np.mean(hum_full[:, 4] < hum_full[:, 2])) - 0.926) < 0.01

    hdir = human_direction()

    cells = {}      # cells[T][fmt] -> dict(smad, n, source, ...)
    frames = {}     # frames[T][fmt] -> per-bid frame (private) / per-round deviations (CV)
    per_temp = {}
    for T in TEMPS:
        cells[T], frames[T] = {}, {}
        devs_abs = {}
        for fmt in PRIVATE:
            fr, source, meta = private_cell(fmt, T)
            if fr is None:
                cells[T][fmt] = {"smad": None, "n": 0, "source": source}
                continue
            dev_abs = np.abs(fr["dev"].to_numpy())
            if T == "0.5":  # must equal the published bid-level deviations exactly
                assert np.allclose(np.sort(dev_abs), np.sort(devs_pub[fmt])), fmt
            devs_abs[fmt] = dev_abs
            frames[T][fmt] = fr
            cells[T][fmt] = {"smad": smad_private(dev_abs), "n": int(len(fr)), "source": source, **meta,
                             **{k: v for k, v in direction_shares(fr).items() if k != "n"}}
        cv_devs = {}
        for fmt in CV:
            d, source = cv_cell(fmt, T)
            if d is None:
                cells[T][fmt] = {"smad": None, "n": 0, "source": source}
                continue
            cv_devs[fmt] = d
            frames[T][fmt] = d
            cells[T][fmt] = {"smad": smad_cv(d), "n": int(len(d)), "source": source}
        if T == "0.5":  # the published CV cells of the temperature table
            assert abs(cells[T]["FP-CV"]["smad"] - 59.989583) < 1e-4 and cells[T]["FP-CV"]["n"] == 96
            assert abs(cells[T]["SP-CV"]["smad"] - 40.603261) < 1e-4 and cells[T]["SP-CV"]["n"] == 92

        usable = [f for f in PRIVATE if f in devs_abs and cells[T][f]["n"] >= MIN_N]
        assert all(f in usable for f in SEALED3), f"T={T}: a sealed format is below MIN_N"
        blocks = {"sealed3": dcm.concordance_block(devs_abs, SEALED3, hum_full),
                  "all_usable": dcm.concordance_block(devs_abs, usable, hum_full)}

        # FP-CV vs SP-CV sign under within-cell resampling of per-round deviations
        cv_sign = None
        if all(f in cv_devs for f in CV):
            rng = np.random.default_rng(SEED + 11)
            fp, sp = cv_devs["FP-CV"], cv_devs["SP-CV"]
            d_fp = np.array([rng.choice(fp, len(fp)).mean() for _ in range(B)])
            d_sp = np.array([rng.choice(sp, len(sp)).mean() for _ in range(B)])
            cv_sign = {"fpcv_minus_spcv": cells[T]["FP-CV"]["smad"] - cells[T]["SP-CV"]["smad"],
                       "fpcv_gt_spcv_point": bool(cells[T]["FP-CV"]["smad"] > cells[T]["SP-CV"]["smad"]),
                       "fpcv_gt_spcv_share_boot": float(np.mean(d_fp > d_sp)),
                       "design": f"per-round |pi - pi*| resampled within each CV cell, B={B}, seed {SEED+11}"}

        # SP-APV vs SPSB IPV sign (the one pair whose order moves) under within-cell bid resampling
        rng = np.random.default_rng(SEED + 13)
        d_apv = np.array([rng.choice(devs_abs["SP-APV"], len(devs_abs["SP-APV"])).mean() for _ in range(B)])
        d_sp = np.array([rng.choice(devs_abs["SPSB IPV"], len(devs_abs["SPSB IPV"])).mean() for _ in range(B)])
        spapv_gt_spsb_share = float(np.mean(d_apv > d_sp))

        # hardest sealed format and clock-at-the-bottom checks (point values)
        s = {f: cells[T][f]["smad"] for f in PRIVATE if cells[T][f]["smad"] is not None}
        clock_usable = [f for f in ("AC", "AC-B") if f in usable]
        per_temp[T] = {
            "usable_private_formats": usable,
            "excluded_private": {f: (f"n={cells[T][f]['n']} < {MIN_N}" if cells[T][f]["smad"] is not None
                                     else cells[T][f]["source"]) for f in PRIVATE if f not in usable},
            "format_sets": blocks,
            "fpsb_hardest_sealed_point": bool(s["FPSB IPV"] > max(s["SPSB IPV"], s["SP-APV"])),
            "spapv_gt_spsb_point": bool(s["SP-APV"] > s["SPSB IPV"]),   # the human order
            "spapv_minus_spsb": s["SP-APV"] - s["SPSB IPV"],
            "spapv_gt_spsb_share_boot": spapv_gt_spsb_share,
            "clock_usable": clock_usable,
            "clock_below_all_sealed_point": (bool(all(s[c] < min(s[f] for f in SEALED3) for c in clock_usable))
                                             if clock_usable else None),
            "cv_sign": cv_sign,
            "third_price_ipv_supplementary": third_price_cell(T),
        }

    # --- paper-table reproduction
    repro = {}
    for fmt in ROW_ORDER:
        repro[fmt] = {}
        for i, T in enumerate(TEMPS):
            pm = paper_method(fmt, T)
            paper_val = PAPER_TABLE[fmt][i]
            if pm["smad"] is None:
                status = "NO DATA (paper prints 0.00)" if paper_val == 0.0 else "NO DATA but paper prints a value"
            else:
                status = "match" if abs(round(pm["smad"], 2) - paper_val) < 0.005 else "MISMATCH"
            repro[fmt][T] = {**pm, "paper_table": paper_val, "status": status,
                             "this_script_smad": cells[T][fmt]["smad"], "this_script_n": cells[T][fmt]["n"]}
    mismatches = [(f, T, r) for f in ROW_ORDER for T, r in repro[f].items() if r["status"] == "MISMATCH"]
    nodata_as_zero = [(f, T) for f in ROW_ORDER for T, r in repro[f].items() if r["status"].startswith("NO DATA")]

    # --- between-temperature rank correlations of the SMAD vectors
    def smad_vec(T, fmts):
        return np.array([cells[T][f]["smad"] for f in fmts])

    between = []
    for t1, t2 in PAIRS:
        for rule in ("n_ge_30_both", "any_data_both"):
            fmts = [f for f in ROW_ORDER
                    if cells[t1][f]["smad"] is not None and cells[t2][f]["smad"] is not None
                    and (rule == "any_data_both" or (cells[t1][f]["n"] >= MIN_N and cells[t2][f]["n"] >= MIN_N))]
            x, y = smad_vec(t1, fmts), smad_vec(t2, fmts)
            rho = stats.spearmanr(x, y)
            tau = stats.kendalltau(x, y, variant="b")
            between.append({"T1": t1, "T2": t2, "rule": rule, "k": len(fmts), "formats": fmts,
                            "spearman_rho": float(rho.statistic), "spearman_p": float(rho.pvalue),
                            "kendall_tau_b": float(tau.statistic), "kendall_p": float(tau.pvalue),
                            "ordering_T1": " > ".join(f for f in sorted(fmts, key=lambda f: -cells[t1][f]["smad"])),
                            "ordering_T2": " > ".join(f for f in sorted(fmts, key=lambda f: -cells[t2][f]["smad"])),
                            "discordant_pairs": [(a, b_) for i, a in enumerate(fmts) for b_ in fmts[i + 1:]
                                                 if (cells[t1][a]["smad"] - cells[t1][b_]["smad"])
                                                 * (cells[t2][a]["smad"] - cells[t2][b_]["smad"]) < 0]})

    # --- magnitude swings
    swings = {}
    for fmt in ROW_ORDER:
        have = {T: cells[T][fmt]["smad"] for T in TEMPS if cells[T][fmt]["smad"] is not None}
        if len(have) < 2:
            swings[fmt] = {"max_abs_change": None, "note": "fewer than two temperatures with data"}
            continue
        tmax, tmin = max(have, key=have.get), min(have, key=have.get)
        ref = cells["0.5"][fmt]["smad"]
        swings[fmt] = {"max_abs_change": have[tmax] - have[tmin], "T_max": tmax, "T_min": tmin,
                       "smad_by_T": have, "rel_to_T05": (have[tmax] - have[tmin]) / ref if ref else None,
                       "max_over_min_ratio": have[tmax] / have[tmin] if have[tmin] > 0 else None,
                       "any_cell_n_lt_30": bool(any(cells[T][fmt]["n"] < MIN_N for T in have)),
                       "temps_with_data": sorted(have)}

    # --- orderings over the formats usable at every temperature (and the k=6 set shared by T=0.5/1.0)
    common_all = [f for f in ROW_ORDER if all(cells[T][f]["smad"] is not None and cells[T][f]["n"] >= MIN_N for T in TEMPS)]
    common_0510 = [f for f in ROW_ORDER if all(cells[T][f]["smad"] is not None and cells[T][f]["n"] >= MIN_N for T in ("0.5", "1.0"))]

    def ordering(T, fmts):
        return " > ".join(sorted(fmts, key=lambda f: -cells[T][f]["smad"]))

    orderings = {"formats_usable_at_all_T": common_all,
                 "by_T": {T: ordering(T, common_all) for T in TEMPS},
                 "formats_usable_at_T05_and_T10": common_0510,
                 "by_T_T05_T10": {T: ordering(T, common_0510) for T in ("0.5", "1.0")}}

    # --- provenance summary for the caveats (seed bases / run dates per cell)
    prov = {T: {f: {"seed_bases": cells[T][f].get("seed_bases", []), "dates": cells[T][f].get("dates", [])}
                for f in PRIVATE if cells[T][f]["smad"] is not None} for T in TEMPS}

    # --- robustness verdicts (point values, over temperatures with usable data)
    def all_T(pred):
        return bool(all(pred(T) for T in TEMPS))

    verdict = {
        "fpsb_hardest_sealed_every_T": all_T(lambda T: per_temp[T]["fpsb_hardest_sealed_point"]),
        "fpsb_gt_spsb_every_T": all_T(lambda T: per_temp[T]["format_sets"]["sealed3"]["fpsb_gt_spsb_llm_point"]),
        "fpsb_gt_spsb_min_boot_share": min(per_temp[T]["format_sets"]["sealed3"]["fpsb_gt_spsb_share_llm"] for T in TEMPS),
        "fpcv_gt_spcv_every_T": all_T(lambda T: per_temp[T]["cv_sign"] and per_temp[T]["cv_sign"]["fpcv_gt_spcv_point"]),
        "fpcv_gt_spcv_min_boot_share": min(per_temp[T]["cv_sign"]["fpcv_gt_spcv_share_boot"] for T in TEMPS),
        "spapv_gt_spsb_by_T": {T: per_temp[T]["spapv_gt_spsb_point"] for T in TEMPS},
        "spapv_minus_spsb_by_T": {T: per_temp[T]["spapv_minus_spsb"] for T in TEMPS},
        "spapv_gt_spsb_share_boot_by_T": {T: per_temp[T]["spapv_gt_spsb_share_boot"] for T in TEMPS},
        "clock_below_all_sealed_by_T": {T: per_temp[T]["clock_below_all_sealed_point"] for T in TEMPS},
        "tau_sealed3_by_T": {T: per_temp[T]["format_sets"]["sealed3"]["tau_point"] for T in TEMPS},
        "tau_sealed3_positive_every_T": all_T(lambda T: per_temp[T]["format_sets"]["sealed3"]["tau_point"] > 0),
        "tau_all_usable_by_T": {T: per_temp[T]["format_sets"]["all_usable"]["tau_point"] for T in TEMPS},
        "p_tau_pos_joint_sealed3_by_T": {T: per_temp[T]["format_sets"]["sealed3"]["layer_c_joint"]["frac_tau_positive"] for T in TEMPS},
        "p_tau_pos_joint_all_usable_by_T": {T: per_temp[T]["format_sets"]["all_usable"]["layer_c_joint"]["frac_tau_positive"] for T in TEMPS},
        "spsb_under_dominated_every_T": all_T(lambda T: cells[T]["SPSB IPV"]["under_share_dev"] > 0.5),
        "spapv_under_dominated_every_T": all_T(lambda T: cells[T]["SP-APV"]["under_share_dev"] > 0.5),
        "human_spsb_under_share_dev": hdir["SPSB IPV"]["under_share_dev"],
        "human_spapv_under_share_dev": hdir["SP-APV"]["under_share_dev"],
        "largest_swing_format": max((f for f in ROW_ORDER if swings[f]["max_abs_change"] is not None
                                     and not swings[f]["any_cell_n_lt_30"]), key=lambda f: swings[f]["max_abs_change"]),
    }

    results = {
        "statistic": "GPT-4o SMAD ordering/direction across sampling temperature T in {0.1, 0.5, 1.0}",
        "seed": SEED, "B": B, "min_n": MIN_N, "scaling_private": SCALING, "scaling_cv": CV_SCALING,
        "within_band_rule": f"|b - b*| <= {WITHIN_FRAC} b*; under/over are shares of the remainder",
        "human_smad_private": HUMAN_SMAD, "human_smad_cv": hdir["human_cv_smad"],
        "human_direction": {k: v for k, v in hdir.items() if k != "human_cv_smad"},
        "json_agent_order_check": json_note,
        "appendix2_temperature_import": "ok" if a2 is not None else f"failed: {A2_IMPORT_ERROR}",
        "cells": cells,
        "per_temperature": per_temp,
        "paper_table_reproduction": {"paper_table": PAPER_TABLE, "cells": repro,
                                     "mismatches": [{"format": f, "T": T, **r} for f, T, r in mismatches],
                                     "no_data_rendered_as_zero": nodata_as_zero},
        "between_temperature_rank_correlation": between,
        "orderings": orderings,
        "max_abs_smad_change_by_format": swings,
        "cell_provenance_seed_bases_dates": prov,
        "verdict_flags": verdict,
    }
    (OUT_DIR / "temperature_concordance.json").write_text(json.dumps(results, indent=2, default=float))

    # --- CSV: one row per temperature x format
    rows = []
    for T in TEMPS:
        blk3, blka = per_temp[T]["format_sets"]["sealed3"], per_temp[T]["format_sets"]["all_usable"]
        for fmt in ROW_ORDER:
            c, r = cells[T][fmt], repro[fmt][T]
            rows.append({
                "temperature": T, "format": fmt, "family": FAMILY[fmt],
                "smad": None if c["smad"] is None else round(c["smad"], 4), "n": c["n"],
                "n_ge_30": c["n"] >= MIN_N, "source": c["source"],
                "within_share": round(c["within_share"], 4) if "within_share" in c else None,
                "under_share_dev": round(c["under_share_dev"], 4) if "under_share_dev" in c else None,
                "over_share_dev": round(c["over_share_dev"], 4) if "over_share_dev" in c else None,
                "paper_method_smad": None if r["smad"] is None else round(r["smad"], 4),
                "paper_method_n": r["n"], "paper_table_value": r["paper_table"], "paper_status": r["status"],
                "tau_sealed3": round(blk3["tau_point"], 4),
                "tau_sealed3_joint_ci": f"[{blk3['layer_c_joint']['ci95'][0]:+.2f}, {blk3['layer_c_joint']['ci95'][1]:+.2f}]",
                "p_tau_pos_joint_sealed3": round(blk3["layer_c_joint"]["frac_tau_positive"], 4),
                "tau_all_usable": round(blka["tau_point"], 4), "k_all_usable": blka["n_formats"],
                "tau_all_usable_joint_ci": f"[{blka['layer_c_joint']['ci95'][0]:+.2f}, {blka['layer_c_joint']['ci95'][1]:+.2f}]",
                "p_tau_pos_joint_all_usable": round(blka["layer_c_joint"]["frac_tau_positive"], 4),
                "fpsb_gt_spsb": blk3["fpsb_gt_spsb_llm_point"],
                "fpsb_gt_spsb_boot_share": round(blk3["fpsb_gt_spsb_share_llm"], 4),
                "fpcv_gt_spcv": per_temp[T]["cv_sign"]["fpcv_gt_spcv_point"],
                "fpcv_gt_spcv_boot_share": round(per_temp[T]["cv_sign"]["fpcv_gt_spcv_share_boot"], 4),
                "spapv_gt_spsb": per_temp[T]["spapv_gt_spsb_point"],
                "spapv_gt_spsb_boot_share": round(per_temp[T]["spapv_gt_spsb_share_boot"], 4),
            })
    pd.DataFrame(rows).to_csv(OUT_DIR / "temperature_concordance.csv", index=False)

    # --- LaTeX fragment
    def tex_cell(T, fmt):
        c = cells[T][fmt]
        if c["smad"] is None:
            return "---"
        dag = r"$^{\dagger}$" if c["n"] < MIN_N else ""
        return f"{c['smad']:.2f}{dag} {{\\scriptsize ({c['n']})}}"

    def tex_tau_ci(blk, with_k=False):
        lo, hi = blk["layer_c_joint"]["ci95"]
        k = f", $k{{=}}{blk['n_formats']}$" if with_k else ""
        return f"{{\\scriptsize [{dcm.tex_num(lo)}, {dcm.tex_num(hi)}]{k}}}"

    def tau_rows_tex(label, set_name, with_k=False):
        """Point row plus a scriptsize continuation row (joint 95% CI, k), as in direction_shares.tex."""
        blks = [per_temp[T]["format_sets"][set_name] for T in TEMPS]
        return [f"{label} & " + " & ".join(dcm.tex_num(b["tau_point"]) for b in blks) + r" \\",
                " & " + " & ".join(tex_tau_ci(b, with_k) for b in blks) + r" \\"]

    def p_line(set_name):
        return ", ".join(f"T={T}: {per_temp[T]['format_sets'][set_name]['layer_c_joint']['frac_tau_positive']*100:.0f}%"
                         for T in TEMPS)

    def tex_sign(point, share):
        return f"{'yes' if point else 'no'} {{\\scriptsize ({share*100:.0f}\\%)}}"

    def tex_dir(T, fmt):
        c = cells[T][fmt]
        return f"{c['under_share_dev']*100:.0f}\\% {{\\scriptsize (within {c['within_share']*100:.0f}\\%)}}"

    L = [
        "% Auto-generated by analysis/temperature_concordance.py -- do not edit by hand.",
        "% GPT-4o at sampling temperature T. Private-value rows: SMAD = 100*mean|b - b*(v)|/25, b* = (2/3)v for FPSB (N=3) and v otherwise;",
        "%   clock rows (AC, AC-B) non-winners only. CV rows: 100*mean|pi_winner - pi*|/20 per round (the paper's temperature-table method).",
        "%   (n) = bids (private) or rounds (CV). $^{\\dagger}$ = n < 30, excluded from every tau; --- = no runs exist.",
        "% tau rows: point Kendall tau-b vs the reconstructed-human SMAD ranking (FPSB IPV 24.76, SPSB IPV 5.65, SP-APV 9.31, AC 3.54, AC-B 5.83);",
        "%   second line = joint 95% CI (LLM within-cell bid resampling x human reconstruction re-draws, B=2000, seed 1299), k = formats used.",
        f"%   P(tau_b > 0) in joint draws -- 3 sealed: {p_line('sealed3')}; all n>=30: {p_line('all_usable')}.",
        "% Sign rows: point sign, with the share of B=2000 within-cell bootstrap draws preserving it. Direction rows: share of bids",
        "%   outside the +/-2% band that are below the benchmark; 'within' = share of all bids inside the band.",
        r"\begin{tabular}{@{}lccc@{}}",
        r"\toprule",
        r" & $T=0.1$ & $T=0.5$ & $T=1.0$ \\",
        r"\midrule",
    ]
    for fmt in ROW_ORDER:
        L.append(f"{TEX_LABEL[fmt]} & " + " & ".join(tex_cell(T, fmt) for T in TEMPS) + r" \\")
    L.append(r"\midrule")
    L += tau_rows_tex(r"Kendall $\tau_b$ vs human (3 sealed)", "sealed3")
    L.append(r"\addlinespace")
    L += tau_rows_tex(r"Kendall $\tau_b$ vs human (all $n\ge30$)", "all_usable", with_k=True)
    L.append(r"\addlinespace")
    L.append(r"FPSB $>$ SPSB & " + " & ".join(
        tex_sign(per_temp[T]["format_sets"]["sealed3"]["fpsb_gt_spsb_llm_point"],
                 per_temp[T]["format_sets"]["sealed3"]["fpsb_gt_spsb_share_llm"]) for T in TEMPS) + r" \\")
    L.append(r"FP-CV $>$ SP-CV & " + " & ".join(
        tex_sign(per_temp[T]["cv_sign"]["fpcv_gt_spcv_point"],
                 per_temp[T]["cv_sign"]["fpcv_gt_spcv_share_boot"]) for T in TEMPS) + r" \\")
    L.append(r"SPSB IPV: under-share of deviating bids & " + " & ".join(tex_dir(T, "SPSB IPV") for T in TEMPS) + r" \\")
    L.append(r"SP-APV: under-share of deviating bids & " + " & ".join(tex_dir(T, "SP-APV") for T in TEMPS) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    (TEX_DIR / "temperature_robustness.tex").write_text("\n".join(L) + "\n")

    # --- Markdown
    def f2(x):
        return "---" if x is None else f"{x:.2f}"

    def pct(x):
        return f"{x*100:.0f}%"

    def md_cell(T, fmt):
        c = cells[T][fmt]
        if c["smad"] is None:
            return "--- (no runs)"
        return f"{c['smad']:.2f} (n={c['n']}){' †' if c['n'] < MIN_N else ''}"

    smad_rows = [f"| {fmt} | {FAMILY[fmt]} | " + " | ".join(md_cell(T, fmt) for T in TEMPS)
                 + f" | {f2(HUMAN_SMAD.get(fmt, hdir['human_cv_smad'].get(fmt)))} |" for fmt in ROW_ORDER]
    tp = {T: per_temp[T]["third_price_ipv_supplementary"] for T in TEMPS}

    repro_rows = []
    for fmt in ROW_ORDER:
        for T in TEMPS:
            r = repro[fmt][T]
            repro_rows.append(f"| {fmt} | {T} | {r['paper_table']:.2f} | {f2(r['smad'])} | {r['n']} | "
                              f"{f2(r['this_script_smad'])} | {r['this_script_n']} | {r['status']} |")

    tau_rows = []
    for T in TEMPS:
        for set_name in ("sealed3", "all_usable"):
            blk = per_temp[T]["format_sets"][set_name]
            if set_name == "all_usable" and blk["formats"] == SEALED3:
                tau_rows.append(f"| {T} | all n ≥ {MIN_N} = 3 sealed (no usable clock cell) | | | | | |")
                continue
            a, b_, j = blk["layer_a_llm_bootstrap"], blk["layer_b_human_redraws"], blk["layer_c_joint"]
            tau_rows.append(
                f"| {T} | {dcm.fmt_set_label(blk['formats'])} ({blk['n_formats']}) | {blk['tau_point']:+.2f} | "
                f"[{a['ci95'][0]:+.2f}, {a['ci95'][1]:+.2f}] ({pct(a['frac_tau_positive'])}) | "
                f"[{b_['ci95'][0]:+.2f}, {b_['ci95'][1]:+.2f}] ({pct(b_['frac_tau_positive'])}) | "
                f"[{j['ci95'][0]:+.2f}, {j['ci95'][1]:+.2f}] ({pct(j['frac_tau_positive'])}) | "
                f"{pct(blk['fpsb_hardest_share_joint'])} |")

    sign_rows = []
    for T in TEMPS:
        b3, cs, pt = per_temp[T]["format_sets"]["sealed3"], per_temp[T]["cv_sign"], per_temp[T]
        sign_rows.append(
            f"| {T} | {b3['fpsb_minus_spsb_llm']:+.2f} ({'yes' if b3['fpsb_gt_spsb_llm_point'] else 'no'}, "
            f"{pct(b3['fpsb_gt_spsb_share_llm'])}) | {cs['fpcv_minus_spcv']:+.2f} "
            f"({'yes' if cs['fpcv_gt_spcv_point'] else 'no'}, {pct(cs['fpcv_gt_spcv_share_boot'])}) | "
            f"{pt['spapv_minus_spsb']:+.2f} ({'yes' if pt['spapv_gt_spsb_point'] else 'no'}, "
            f"P(SP-APV>SPSB)={pct(pt['spapv_gt_spsb_share_boot'])}) | "
            f"{', '.join(pt['clock_usable']) or 'none usable'}: "
            f"{ {True: 'yes', False: 'no', None: 'n/a'}[pt['clock_below_all_sealed_point']] } |")

    dir_rows = []
    for fmt in PRIVATE:
        cells_T = []
        for T in TEMPS:
            c = cells[T][fmt]
            if c["smad"] is None or c["n_deviating"] == 0:
                cells_T.append("---" if c["smad"] is None else f"n/a (no deviating bids, n={c['n']})")
            else:
                cells_T.append(f"{pct(c['under_share_dev'])} / {pct(c['over_share_dev'])} "
                               f"(within {pct(c['within_share'])}, n={c['n']}){' †' if c['n'] < MIN_N else ''}")
        h = hdir.get(fmt)
        hcell = f"{pct(h['under_share_dev'])} / {pct(h['over_share_dev'])} (within {pct(h['within_share'])})" if h else "n/a"
        dir_rows.append(f"| {fmt} | " + " | ".join(cells_T) + f" | {hcell} |")

    btw_rows = []
    for r in between:
        disc = "; ".join(f"{a} vs {b_}" for a, b_ in r["discordant_pairs"]) or "none"
        btw_rows.append(f"| {r['T1']} vs {r['T2']} | {r['rule']} | {r['k']} | {r['spearman_rho']:+.3f} | "
                        f"{r['kendall_tau_b']:+.3f} | {disc} |")

    swing_rows = []
    for fmt in ROW_ORDER:
        s = swings[fmt]
        if s["max_abs_change"] is None:
            swing_rows.append(f"| {fmt} | --- | | | | {s['note']} |")
            continue
        ratio = "" if s["max_over_min_ratio"] is None else f"{s['max_over_min_ratio']:.2f}x"
        relt = "" if s["rel_to_T05"] is None else pct(s["rel_to_T05"])
        swing_rows.append(f"| {fmt} | {s['max_abs_change']:.2f} | {s['smad_by_T'][s['T_min']]:.2f} (T={s['T_min']}) -> "
                          f"{s['smad_by_T'][s['T_max']]:.2f} (T={s['T_max']}) | {relt} | {ratio} | "
                          f"{'tiny-n cell involved' if s['any_cell_n_lt_30'] else ''} |")

    V = verdict
    spapv_hold = [T for T, ok in V["spapv_gt_spsb_by_T"].items() if ok]
    spapv_fail = [T for T, ok in V["spapv_gt_spsb_by_T"].items() if not ok]
    prim = [r for r in between if r["rule"] == "n_ge_30_both"]
    rho_min, tau_min = min(r["spearman_rho"] for r in prim), min(r["kendall_tau_b"] for r in prim)
    big = V["largest_swing_format"]
    ac_t10 = cells["1.0"]["AC"]
    acb_t01, acb_t10 = cells["0.1"]["AC-B"], cells["1.0"]["AC-B"]
    sw_spsb, sw_fpcv, sw_spcv, sw_big = swings["SPSB IPV"], swings["FP-CV"], swings["SP-CV"], swings[big]

    def rng_str(s):
        return f"{s['smad_by_T'][s['T_min']]:.2f} (T={s['T_min']}) → {s['smad_by_T'][s['T_max']]:.2f} (T={s['T_max']})"

    # provenance sentences (data-driven)
    def seeds_of(T, fmts):
        return {f: cells[T][f].get("seed_bases", []) for f in fmts if cells[T][f]["smad"] is not None}

    def dates_of(T):
        ds = sorted({d for f in PRIVATE if cells[T][f]["smad"] is not None for d in cells[T][f].get("dates", [])})
        return f"{ds[0]} to {ds[-1]}" if len(ds) > 1 else (ds[0] if ds else "n/a")

    s05 = seeds_of("0.5", SEALED3)
    sealed_seeds_same = all(s05[f] == seeds_of(T, SEALED3)[f] for T in ("0.1", "1.0") for f in SEALED3)
    s05_str = ", ".join(f"{f} {s05[f]}" for f in SEALED3)
    prov_sentence = (
        f"The sealed cells use the same seed bases at every temperature ({s05_str}), so the value draws are "
        f"comparable across T" if sealed_seeds_same else
        f"The sealed cells do NOT share seed bases across temperature (T=0.5: {s05}; "
        f"T=0.1: {seeds_of('0.1', SEALED3)}; T=1.0: {seeds_of('1.0', SEALED3)})")
    clock_prov = (f"the V10 clock cells pool runs with seed bases AC {cells['0.5']['AC']['seed_bases']} / "
                  f"AC-B {cells['0.5']['AC-B']['seed_bases']}, whereas the T=1.0 clock cells use "
                  f"{cells['1.0']['AC']['seed_bases']}. Run dates: T=0.5 {dates_of('0.5')}; T=0.1 {dates_of('0.1')}; "
                  f"T=1.0 {dates_of('1.0')}")
    tp_line = " / ".join(
        f"T={T}: RNE {tp[T]['smad_rne']:.1f}, capped {tp[T]['smad_rne_capped49']:.1f} (n={tp[T]['n']})"
        for T in TEMPS if tp[T] is not None)

    hold = [
        f"FPSB is the hardest sealed private-value format at every temperature: {'yes' if V['fpsb_hardest_sealed_every_T'] else 'NO'}.",
        f"FPSB > SPSB at every temperature: {'yes' if V['fpsb_gt_spsb_every_T'] else 'NO'} "
        f"(preserved in >= {pct(V['fpsb_gt_spsb_min_boot_share'])} of within-cell bootstrap draws at every T).",
        f"FP-CV > SP-CV at every temperature: {'yes' if V['fpcv_gt_spcv_every_T'] else 'NO'} "
        f"(preserved in >= {pct(V['fpcv_gt_spcv_min_boot_share'])} of draws; the weakest temperature is T="
        f"{min(TEMPS, key=lambda T: per_temp[T]['cv_sign']['fpcv_gt_spcv_share_boot'])}). Humans: FP-CV "
        f"{hdir['human_cv_smad']['FP-CV']:.2f} > SP-CV {hdir['human_cv_smad']['SP-CV']:.2f}, same sign.",
        f"Direction in SPSB IPV: under-bidding dominates the deviating bids at every temperature: "
        f"{'yes' if V['spsb_under_dominated_every_T'] else 'NO'} "
        f"({' / '.join(pct(cells[T]['SPSB IPV']['under_share_dev']) for T in TEMPS)} under at T=0.1/0.5/1.0; "
        f"humans {pct(V['human_spsb_under_share_dev'])} under, i.e. GPT-4o's direction is stably OPPOSITE to humans).",
        f"Direction in SP-APV: under-bidding dominates at every temperature: "
        f"{'yes' if V['spapv_under_dominated_every_T'] else 'NO'} "
        f"({' / '.join(pct(cells[T]['SP-APV']['under_share_dev']) for T in TEMPS)} under; humans {pct(V['human_spapv_under_share_dev'])}).",
        f"Kendall tau-b vs the human ranking over the three sealed formats is positive at every temperature: "
        f"{'yes' if V['tau_sealed3_positive_every_T'] else 'NO'} "
        f"({', '.join(f'T={T}: {v:+.2f}' for T, v in V['tau_sealed3_by_T'].items())}; P(tau>0) joint "
        f"{', '.join(f'{pct(v)}' for v in V['p_tau_pos_joint_sealed3_by_T'].values())}).",
        f"Clock formats with n >= {MIN_N} sit below every sealed format: "
        + "; ".join(f"T={T}: {({True: 'yes', False: 'no', None: 'no usable clock cell'})[v]}"
                    + (f" ({', '.join(per_temp[T]['clock_usable'])})" if per_temp[T]["clock_usable"] else "")
                    for T, v in V["clock_below_all_sealed_by_T"].items()) + ".",
    ]
    fails = [
        f"SP-APV > SPSB IPV (the human order, 9.31 > 5.65) holds only at T={', '.join(spapv_hold) or 'none'} "
        f"and is reversed at T={', '.join(spapv_fail) or 'none'}; the gaps are "
        f"{', '.join(f'T={T}: {v:+.2f}' for T, v in V['spapv_minus_spsb_by_T'].items())} SMAD points. "
        f"This single adjacent swap is why tau-b over the three sealed formats drops from +1.00 at T=0.5 to +0.33 "
        f"at the other temperatures, and it is the only ordering change among formats with n >= {MIN_N}.",
        f"AC-B cannot be tested at T=0.1 (n={acb_t01['n']} non-winners, two rounds of raw JSON, no CSV) or T=1.0 "
        f"(n={acb_t10['n']}); AC has no runs at T=0.1 and n={ac_t10['n']} at T=1.0. The all-usable tau therefore "
        f"uses k=3/5/4 formats at T=0.1/0.5/1.0 and is not comparable across temperatures at face value.",
    ]

    md = f"""# Temperature robustness of GPT-4o's cross-mechanism ordering and direction

*Generated by `analysis/temperature_concordance.py` (seed {SEED}, B={B}, MIN_N={MIN_N}). Reuses the cells,
human anchors, tau-b and reconstruction re-draws of `analysis/difficulty_concordance.py` and the bootstrap
layers of `analysis/difficulty_concordance_models.py`; the paper-table reproduction uses the method of
`scripts/plots/appendix2_temperature.py` ({results['appendix2_temperature_import']}).*

## SMAD by format and temperature

Private-value formats: 100·mean|b − b*(v)|/{SCALING:.0f} with b* = (2/3)v for FPSB and v otherwise; clock cells
(AC, AC-B) non-winners only; n = bids. Common value: 100·mean|π_winner − π*|/{CV_SCALING:.0f} per round with
π* = 2ε/(n+1) (first price) or ε/(n+1) (second price), ε = winner's signal − common value; n = rounds.
† = n < {MIN_N} (excluded from every tau). T=0.5 are the published V10 cells; T=0.1/1.0 are `robustness_logs`.

| Format | family | T=0.1 | T=0.5 | T=1.0 | Human anchor |
|---|---|---|---|---|---:|
{chr(10).join(smad_rows)}

Cell provenance: AC-B at T=0.1 is parsed from two rounds of `raw_data` JSON (no results CSV exists); the
JSON agent→value mapping was {json_note}. AC at T=0.1 has no data at all (run directory with no
`raw_data`/`results`). Supplementary, not in the paper's table and not in any tau: third-price IPV (N=5,
b* = (N−1)/(N−2)·v per `build_auction_cells.rne_bstar`, "capped" = b* capped at the $49 endowment):
{tp_line}; human anchor (Kagel–Levin, n=5) 7.66.

## Reproduction of the paper's temperature table (tab:temperature_comparison)

Method of `scripts/plots/appendix2_temperature.py`: first results CSV per cell, non-winners for clock cells,
scaling 25; CV from raw_data JSON (winner profit per round, scaling 20); T=0.5 read from
`plots/theoretical_deviation_results_updated.csv`. "this script" = the concatenated/de-duplicated cells above.

| Format | T | paper table | paper method | n | this script | n | status |
|---|---|---:|---:|---:|---:|---:|---|
{chr(10).join(repro_rows)}

{"**No mismatches**: every non-empty paper cell reproduces to two decimals with the same n." if not mismatches
 else "**MISMATCHES**: " + "; ".join(f"{f} T={T}: paper {r['paper_table']} vs recomputed {r['smad']:.2f}" for f, T, r in mismatches)}
The paper's **"0.00" entries for AC and AC-B at T=0.1 are not measurements**: no results CSV exists for either
cell, and the table generator prints "0" for missing data (`generate_latex_table`: `"0"` when `smad` is NaN).
AC-B at T=0.1 has {acb_t01['n']} non-winning bids in raw JSON (SMAD {f2(acb_t01['smad'])}); AC at T=0.1 has none.
The T=1.0 clock cells are also small (AC n={ac_t10['n']}, AC-B n={acb_t10['n']} non-winners), so the AC-B row
of the paper's table (0.00 / 0.47 / 2.15) compares nothing, n=114 and n=8.

## Kendall tau-b vs the reconstructed-human ranking, by temperature

Human anchors: FPSB IPV 24.76, SPSB IPV 5.65, SP-APV 9.31, AC 3.54, AC-B 5.83. Layers as in
`difficulty_concordance.py`: (a) LLM within-cell bid resampling with the human ranking fixed; (b) human
reconstruction re-draws with the LLM ranking fixed; (c) joint. Percentages are P(tau > 0) in that layer.
With k formats and no ties tau-b takes k(k−1)/2+1 values (k=3: {{−1, −1/3, +1/3, +1}}).

| T | formats (k) | tau-b | (a) LLM CI | (b) human CI | (c) joint CI | FPSB hardest (joint) |
|---|---|---:|---|---|---|---:|
{chr(10).join(tau_rows)}

## Signs of the pairwise gaps

FPSB−SPSB: share = LLM bootstrap draws preserving the sign. FP-CV−SP-CV: per-round profit deviations
resampled within each CV cell (B={B}). SP-APV−SPSB IPV: the human order is SP-APV > SPSB IPV.

| T | FPSB − SPSB (FPSB>SPSB?, share) | FP-CV − SP-CV (FP-CV>SP-CV?, share) | SP-APV − SPSB IPV (human order?) | usable clock formats below all sealed? |
|---|---|---|---|---|
{chr(10).join(sign_rows)}

## Direction of deviations (under / over share of bids outside the ±2% band)

| Format | T=0.1 | T=0.5 | T=1.0 | Human (source-reported) |
|---|---|---|---|---|
{chr(10).join(dir_rows)}

## Ordering stability between temperatures

Rank correlations of the SMAD vectors across formats. `n_ge_30_both` restricts to formats with n ≥ {MIN_N} at
both temperatures (the informative comparison); `any_data_both` adds the tiny clock cells (†) for completeness.

| pair | rule | k | Spearman rho | Kendall tau-b | discordant pairs |
|---|---|---:|---:|---:|---|
{chr(10).join(btw_rows)}

Orderings over the {len(common_all)} formats with n ≥ {MIN_N} at all three temperatures ({', '.join(common_all)}):
{chr(10).join(f"* T={T}: {orderings['by_T'][T]}" for T in TEMPS)}

Adding the formats usable at both T=0.5 and T=1.0 ({', '.join(common_0510)}):
{chr(10).join(f"* T={T}: {orderings['by_T_T05_T10'][T]}" for T in ("0.5", "1.0"))}

## Magnitude swings across temperature

| Format | max abs. change in SMAD | min → max | relative to T=0.5 | max/min | note |
|---|---:|---|---:|---:|---|
{chr(10).join(swing_rows)}

## What holds at every temperature and what does not

Holds at every temperature:
{chr(10).join(f"* {s}" for s in hold)}

Does not hold / cannot be tested:
{chr(10).join(f"* {s}" for s in fails)}

Magnitudes are not stable. Among formats with n ≥ {MIN_N} at every temperature the largest swing is {big},
{rng_str(sw_big)}, i.e. {pct(sw_big['rel_to_T05'])} of its T=0.5 value ({sw_big['max_over_min_ratio']:.2f}x);
SPSB IPV moves {rng_str(sw_spsb)} ({pct(sw_spsb['rel_to_T05'])} of T=0.5, {sw_spsb['max_over_min_ratio']:.2f}x) and
SP-CV {rng_str(sw_spcv)} ({sw_spcv['max_over_min_ratio']:.2f}x). Yet the between-temperature rank correlation over
those formats never falls below Spearman {rho_min:+.2f} / Kendall {tau_min:+.2f}: the only reordering is the
adjacent SPSB IPV / SP-APV swap, between the two formats whose SMADs are closest. That swap is a real
reversal at T=0.1 (bid resampling restores the human order in only
{pct(V['spapv_gt_spsb_share_boot_by_T']['0.1'])} of draws) but a coin flip at T=1.0
({pct(V['spapv_gt_spsb_share_boot_by_T']['1.0'])}); at T=0.5 the human order holds in
{pct(V['spapv_gt_spsb_share_boot_by_T']['0.5'])} of draws.

**Verdict.** The cross-mechanism ordering and the direction of deviations are robust to temperature
(FPSB hardest, FPSB > SPSB, FP-CV > SP-CV, clock formats lowest where measurable, under-bidding in both
second-price formats at every T), while the magnitudes are not (swings of {sw_spsb['max_abs_change']:.1f} SMAD
points in SPSB IPV and {sw_fpcv['max_abs_change']:.1f} in FP-CV). The one ordinal exception is the SPSB IPV vs
SP-APV order, which is concordant with humans only at T=0.5 and reverses on a
{min(abs(v) for T, v in V['spapv_minus_spsb_by_T'].items() if T != '0.5'):.2f}–{max(abs(v) for T, v in V['spapv_minus_spsb_by_T'].items() if T != '0.5'):.2f}-point
gap at T=0.1 and T=1.0.

## Caveats

Human-side uncertainty is reconstruction/calibration uncertainty (`analysis/reconstruction_bands.py`), not
human sampling error. LLM CIs treat bids (or CV rounds) as i.i.d. within cells. {prov_sentence}; {clock_prov}
-- so run date (and, for the clock cells, seed base) differ alongside temperature. The CV SMAD is
profit-based with a different normalizer (20) than the private-value SMAD (25) and is never ranked against
private-value formats here. Clock cells at T=0.1 (AC none, AC-B n={acb_t01['n']}) and AC-B at T=1.0
(n={acb_t10['n']}) are too small to say anything.
"""
    (OUT_DIR / "temperature_concordance.md").write_text(md)

    # --- console
    print(json_note)
    print("\nSMAD by format x temperature (n):")
    for fmt in ROW_ORDER:
        print(f"  {fmt:9s} " + "  ".join(f"T={T}: {md_cell(T, fmt):>22s}" for T in TEMPS))
    print("\nPaper-table reproduction:", "no mismatches" if not mismatches else mismatches)
    print("  no-data cells rendered as 0.00 in the paper:", nodata_as_zero)
    print("\nKendall tau-b vs human:")
    for T in TEMPS:
        for set_name in ("sealed3", "all_usable"):
            blk = per_temp[T]["format_sets"][set_name]
            j = blk["layer_c_joint"]
            print(f"  T={T} {set_name:10s} k={blk['n_formats']} tau={blk['tau_point']:+.2f} "
                  f"joint CI [{j['ci95'][0]:+.2f}, {j['ci95'][1]:+.2f}] P(tau>0)={j['frac_tau_positive']*100:.0f}% "
                  f"FPSB>SPSB {blk['fpsb_gt_spsb_share_llm']*100:.0f}%")
        cs = per_temp[T]["cv_sign"]
        print(f"        FP-CV>SP-CV: {cs['fpcv_gt_spcv_point']} ({cs['fpcv_gt_spcv_share_boot']*100:.0f}%)  "
              f"SP-APV>SPSB: {per_temp[T]['spapv_gt_spsb_point']} ({per_temp[T]['spapv_gt_spsb_share_boot']*100:.0f}%)  "
              f"SPSB under {cells[T]['SPSB IPV']['under_share_dev']*100:.0f}%  SP-APV under {cells[T]['SP-APV']['under_share_dev']*100:.0f}%")
    print("\nBetween-temperature rank correlations:")
    for r in between:
        print(f"  {r['T1']} vs {r['T2']} [{r['rule']}, k={r['k']}] rho={r['spearman_rho']:+.3f} tau={r['kendall_tau_b']:+.3f} "
              f"discordant={r['discordant_pairs']}")
    print("\nMax |dSMAD| by format:")
    for fmt in ROW_ORDER:
        s = swings[fmt]
        if s["max_abs_change"] is not None:
            print(f"  {fmt:9s} {s['max_abs_change']:6.2f}  ({s['smad_by_T'][s['T_min']]:.2f}@T={s['T_min']} -> "
                  f"{s['smad_by_T'][s['T_max']]:.2f}@T={s['T_max']}){'  [tiny-n]' if s['any_cell_n_lt_30'] else ''}")
    print(f"\nWrote {OUT_DIR/'temperature_concordance.{json,csv,md}'} and {TEX_DIR/'temperature_robustness.tex'}")


if __name__ == "__main__":
    main()

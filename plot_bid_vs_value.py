"""
Generate bid vs. value scatter plots for recent auction runs.

Creates one plot per run (with a dotted y=x reference line), saves
individual PNGs, and bundles everything into a multi-page PDF.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
import yaml


VALUE_COLUMNS = ["player_value", "value", "Value"]
BID_COLUMNS = ["bid", "Bid", "offer"]
RUN_GLOBS = [
    ("experiment_logs", Path("experiment_logs/V10")),
    ("robustness_logs", Path("robustness_logs/V10")),
]
OUTPUT_DIR = Path("results/bid_vs_value_plots/V10")
ORDER_AUCTION = ["FP", "SP", "Clock", "TP", "All-pay", "Other"]
ORDER_ENV = [
    "IPV",
    "IPV (clock)",
    "APV",
    "APV (clock, open)",
    "APV (clock, closed)",
    "Common value (first)",
    "Common value (second)",
    "Intervention",
    "Other",
]


def pick_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Return the first matching column from candidates."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def axis_limits(series_a: pd.Series, series_b: pd.Series) -> tuple[float, float]:
    """Compute symmetric limits around the data with a small margin."""
    finite_a = pd.to_numeric(series_a, errors="coerce")
    finite_b = pd.to_numeric(series_b, errors="coerce")
    combined_min = min(finite_a.min(), finite_b.min())
    combined_max = max(finite_a.max(), finite_b.max())
    if pd.isna(combined_min) or pd.isna(combined_max):
        return 0.0, 1.0
    span = combined_max - combined_min
    pad = max(span * 0.05, 1e-3)
    return combined_min - pad, combined_max + pad


def plot_scatter(df: pd.DataFrame, run_label: str, title: str) -> plt.Figure:
    """Return a standardized scatter plot figure."""
    value_col = pick_column(df, VALUE_COLUMNS)
    bid_col = pick_column(df, BID_COLUMNS)
    if not value_col or not bid_col:
        raise ValueError(f"Missing required columns in {run_label}")

    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df[bid_col] = pd.to_numeric(df[bid_col], errors="coerce")
    df = df.dropna(subset=[value_col, bid_col])
    if df.empty:
        raise ValueError(f"No numeric bid/value data in {run_label}")

    low, high = axis_limits(df[value_col], df[bid_col])

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#222222",
            "axes.labelcolor": "#222222",
            "xtick.color": "#444444",
            "ytick.color": "#444444",
            "axes.titleweight": "bold",
        }
    )

    fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=240)
    ax.scatter(
        df[value_col],
        df[bid_col],
        s=32,
        alpha=0.7,
        color="#1f78b4",
        edgecolors="none",
        label="Bids",
    )
    ax.plot(
        [low, high],
        [low, high],
        linestyle="--",
        color="#666666",
        linewidth=1.0,
        label="y = x",
    )

    # Add a simple OLS regression line if we have at least two points.
    if len(df) >= 2:
        x = df[value_col].to_numpy()
        y = df[bid_col].to_numpy()
        try:
            slope, intercept = np.polyfit(x, y, deg=1)
            x_line = np.array([low, high])
            y_line = slope * x_line + intercept
            ax.plot(
                x_line,
                y_line,
                color="#e15759",
                linewidth=1.35,
                label="OLS fit",
            )
        except np.linalg.LinAlgError:
            pass

    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Value", labelpad=6)
    ax.set_ylabel("Bid", labelpad=6)
    ax.set_title(title, loc="left", fontsize=13)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    return fig


def pretty_model_name(raw: Optional[str]) -> str:
    if not raw:
        return "Unknown model"
    raw = raw.lower()
    mapping = {
        "gpt-4o": "GPT-4o",
        "gpt4o": "GPT-4o",
        "gpt5mini": "GPT-5 mini",
        "claude-sonnet": "Claude Sonnet",
        "claude_sonnet": "Claude Sonnet",
        "gemini": "Gemini",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "llama": "Llama",
    }
    return mapping.get(raw, raw)


def auction_type_label(seal_clock: str, price_order: str, special_name: Optional[str]) -> str:
    if seal_clock == "clock":
        return "Clock"

    special = (special_name or "").lower()
    if "spsb" in special or "second_price" in special:
        return "SP"
    if "fpsb" in special or "first_price" in special:
        return "FP"
    if "third_price" in special:
        return "TP"
    if "all_pay" in special or "allpay" in special:
        return "All-pay"

    mapping = {
        "first": "FP",
        "second": "SP",
        "third": "TP",
        "allpay": "All-pay",
    }
    return mapping.get(price_order, "Other")


def environment_label(experiment_name: str, private_value: str, seal_clock: str, open_blind: str) -> str:
    name = (experiment_name or "").lower()
    pv = (private_value or "").lower()
    clock = seal_clock == "clock"
    blind = (open_blind or "").lower() == "blind"

    if "common_value_first" in name:
        return "Common value (first)"
    if "common_value_second" in name:
        return "Common value (second)"
    if "intervention" in name:
        return "Intervention"
    if "apv" in name or pv == "affiliated":
        if clock:
            return "APV (clock, closed)" if blind else "APV (clock, open)"
        return "APV"
    if "ipv" in name or pv == "private":
        if clock:
            return "IPV (clock)"
        return "IPV"
    return "Other"


def ordering_value(value: str, order: List[str]) -> Tuple[int, str]:
    try:
        return (order.index(value), value)
    except ValueError:
        return (len(order), value)


def load_config(run_dir: Path) -> Dict:
    cfg_path = run_dir / "config.yaml"
    if cfg_path.exists():
        try:
            return yaml.safe_load(cfg_path.read_text()) or {}
        except Exception:
            return {}
    return {}


def build_titles(meta: Dict, base_label: str, run_dir: Path) -> Tuple[str, str, str]:
    """Return (main_title, subtitle, footnote) for the plot."""
    main_parts = [
        meta.get("auction_type_label", "Auction"),
        meta.get("environment_label", "Env"),
        pretty_model_name(meta.get("model")),
    ]
    main_title = " · ".join(filter(None, main_parts))

    details = []
    temp = meta.get("temperature")
    if temp is not None:
        details.append(f"T={temp}")
    agents = meta.get("number_agents")
    if agents:
        details.append(f"agents={agents}")
    rounds = meta.get("rounds")
    if rounds:
        details.append(f"rounds={rounds}")
    version = meta.get("version")
    if version:
        details.append(version)
    special = meta.get("special_name")
    if special:
        details.append(str(special))
    subtitle = " | ".join(details)

    footnote = f"{base_label}/{run_dir.parent.name}/{run_dir.name}"
    return main_title, subtitle, footnote


def collect_meta(csv_path: Path, run_dir: Path) -> Dict:
    df = pd.read_csv(csv_path)
    row = df.iloc[0].to_dict()
    cfg = load_config(run_dir)

    rule_cfg = cfg.get("rule", {})
    auction_cfg = cfg.get("auction", {})
    llm_cfg = cfg.get("llm", {})
    experiment_cfg = cfg.get("experiment", {})

    seal_clock = rule_cfg.get("seal_clock") or row.get("seal_clock")
    price_order = rule_cfg.get("price_order") or row.get("price_order")
    private_value = rule_cfg.get("private_value") or row.get("private_value")
    open_blind = rule_cfg.get("open_blind") or row.get("open_blind")

    meta = {
        "experiment_name": row.get("experiment_name") or experiment_cfg.get("name"),
        "version": row.get("version") or experiment_cfg.get("version"),
        "model": row.get("model") or llm_cfg.get("model"),
        "temperature": row.get("temperature") if not pd.isna(row.get("temperature", np.nan)) else llm_cfg.get("temperature"),
        "special_name": row.get("special_name") or rule_cfg.get("special_name"),
        "number_agents": row.get("number_agents") or auction_cfg.get("number_agents"),
        "rounds": row.get("total_rounds") or auction_cfg.get("rounds"),
        "seal_clock": seal_clock,
        "price_order": price_order,
        "private_value": private_value,
        "open_blind": open_blind,
    }

    meta["auction_type_label"] = auction_type_label(seal_clock, price_order, meta["special_name"])
    meta["environment_label"] = environment_label(meta["experiment_name"], private_value, seal_clock, open_blind)
    meta["df"] = df
    return meta


def collect_runs() -> List[Dict]:
    """Return a list of run metadata dicts."""
    runs: List[Dict] = []
    for base_label, base_path in RUN_GLOBS:
        if not base_path.exists():
            continue
        for run_dir in base_path.rglob("run_*"):
            if not run_dir.is_dir():
                continue
            for csv_path in sorted((run_dir / "results").glob("*.csv")):
                meta = collect_meta(csv_path, run_dir)
                meta["base_label"] = base_label
                meta["csv_path"] = csv_path
                meta["run_dir"] = run_dir
                runs.append(meta)
    return runs


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / "bid_vs_value_plots.pdf"

    runs = collect_runs()
    if not runs:
        print("No run CSVs found. Nothing to plot.")
        return

    def sort_key(meta: Dict) -> Tuple:
        auction_rank = ordering_value(meta.get("auction_type_label", "Other"), ORDER_AUCTION)
        env_rank = ordering_value(meta.get("environment_label", "Other"), ORDER_ENV)
        model_name = pretty_model_name(meta.get("model") or "")
        return (auction_rank, env_rank, model_name, meta.get("experiment_name") or "", meta.get("run_dir").name)

    runs = sorted(runs, key=sort_key)

    generated = []
    with PdfPages(pdf_path) as pdf:
        for meta in runs:
            base_label = meta["base_label"]
            csv_path = meta["csv_path"]
            run_dir = meta["run_dir"]
            run_label = f"{base_label}/{csv_path.relative_to(csv_path.parents[2])}"
            df = meta["df"]

            main_title, subtitle, footnote = build_titles(meta, base_label, run_dir)
            title_lines = [main_title]
            if subtitle:
                title_lines.append(subtitle)
            fig = plot_scatter(df, run_label, "\n".join(title_lines))
            # Add footnote near bottom-left
            fig.text(0.0, 0.01, footnote, fontsize=8, color="#555555", ha="left", va="bottom")
            pdf.savefig(fig, bbox_inches="tight")

            png_name = f"{base_label}_{run_dir.parent.name}_{run_dir.name}.png"
            png_path = OUTPUT_DIR / png_name
            fig.savefig(png_path, bbox_inches="tight", dpi=300)
            plt.close(fig)
            generated.append((run_label, png_path))

    print(f"Wrote {len(generated)} plots.")
    print(f"PDF: {pdf_path}")
    if generated:
        print("Sample PNG:", generated[0][1])


if __name__ == "__main__":
    main()

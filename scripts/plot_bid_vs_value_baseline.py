"""
Generate bid vs. value scatter plots for recent auction runs.

Creates one plot per run (with a dotted y=x reference line), saves
individual PNGs, and bundles everything into a multi-page PDF.
"""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


VALUE_COLUMNS = ["player_value", "value", "Value"]
BID_COLUMNS = ["bid", "Bid", "offer"]
RUN_GLOBS = [
    ("experiment_logs", Path("experiment_logs/V10")),
    ("robustness_logs", Path("robustness_logs/V10")),
]
OUTPUT_DIR = Path("results/bid_vs_value_plots/V10")


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
    fig, ax = plt.subplots(figsize=(6, 6), dpi=200)
    ax.scatter(
        df[value_col],
        df[bid_col],
        s=28,
        alpha=0.75,
        color="#1f77b4",
        edgecolors="none",
        label="Bids",
    )
    ax.plot(
        [low, high],
        [low, high],
        linestyle="--",
        color="#666666",
        linewidth=1.1,
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
                color="#ff7f0e",
                linewidth=1.3,
                label="OLS fit",
            )
        except np.linalg.LinAlgError:
            pass

    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Private value")
    ax.set_ylabel("Bid")
    ax.set_title(title)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return fig


def build_title(df: pd.DataFrame, run_dir: Path, base_label: str) -> str:
    """Assemble an informative title from CSV metadata plus path context."""
    meta = df.iloc[0].to_dict()
    experiment = meta.get("experiment_name") or run_dir.parent.name
    version = meta.get("version")
    model = meta.get("model")
    temp = meta.get("temperature")
    special = meta.get("special_name")
    run_id = run_dir.name

    parts = [experiment]
    if version:
        parts.append(f"{version}")
    if model:
        parts.append(f"model={model}")
    if temp is not None:
        parts.append(f"T={temp}")
    if special:
        parts.append(str(special))
    parts.append(f"{base_label}/{run_dir.parent.name}/{run_id}")
    return " | ".join(parts)


def collect_runs() -> List[tuple[str, Path]]:
    """Return (base_label, csv_path) pairs for all run outputs."""
    run_files: List[tuple[str, Path]] = []
    for base_label, base_path in RUN_GLOBS:
        if not base_path.exists():
            continue
        for run_dir in base_path.rglob("run_*"):
            if not run_dir.is_dir():
                continue
            for csv_path in sorted((run_dir / "results").glob("*.csv")):
                run_files.append((base_label, csv_path))
    return sorted(run_files)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / "bid_vs_value_plots.pdf"

    runs = collect_runs()
    if not runs:
        print("No run CSVs found. Nothing to plot.")
        return

    generated = []
    with PdfPages(pdf_path) as pdf:
        for base_label, csv_path in runs:
            run_dir = csv_path.parent.parent
            run_label = f"{base_label}/{csv_path.relative_to(csv_path.parents[2])}"
            df = pd.read_csv(csv_path)
            title = build_title(df, run_dir, base_label)
            fig = plot_scatter(df, run_label, title)
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

"""Create publication-ready figures from the exported SPSB-IPV CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import correlation

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


COLORS = {
    "ink": "#243247",
    "blue": "#2C6E9B",
    "teal": "#2A9D8F",
    "orange": "#E08E45",
    "red": "#C44949",
    "grid": "#DCE3EA",
    "muted": "#637286",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_figures(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    bidders = _read_csv(input_dir / "spsb_ipv_bidder_results.csv")
    auctions = _read_csv(input_dir / "spsb_ipv_auction_results.csv")
    summary = json.loads((input_dir / "spsb_ipv_summary.json").read_text())

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.labelcolor": COLORS["ink"],
            "axes.edgecolor": COLORS["grid"],
            "axes.titlecolor": COLORS["ink"],
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "text.color": COLORS["ink"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.7,
            "grid.alpha": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    values = [float(row["value"]) for row in bidders]
    bids = [float(row["bid"]) for row in bidders]
    deviations = [float(row["bid_minus_value"]) for row in bidders]

    # Figure 1: density shows where bids concentrate, with truthful bidding as reference.
    fig, ax = plt.subplots(figsize=(7.1, 5.2), constrained_layout=True)
    density = ax.hexbin(
        values,
        bids,
        gridsize=19,
        extent=(0, 49, 0, 49),
        mincnt=1,
        cmap="Blues",
        linewidths=0.25,
        edgecolors="white",
    )
    ax.plot([0, 49], [0, 49], color=COLORS["orange"], linewidth=1.8, linestyle="--", label="Truthful bid: bid = value")
    ax.set(xlim=(0, 49), ylim=(0, 49), xlabel="Private value", ylabel="Submitted bid")
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.set_title("Bids closely track values, with systematic shading", loc="left", weight="bold", pad=12)
    ax.text(
        0.03,
        0.96,
        f"N = {len(bidders)} bidder observations\nPearson r = {correlation(values, bids):.3f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": COLORS["grid"], "alpha": 0.95},
    )
    ax.legend(frameon=False, loc="lower right")
    colorbar = fig.colorbar(density, ax=ax, pad=0.02)
    colorbar.set_label("Number of observations")
    _save(fig, output_dir, "spsb_ipv_bid_value_density")

    # Figure 2: negative bid-minus-value values represent shading.
    fig, ax = plt.subplots(figsize=(7.1, 4.3), constrained_layout=True)
    ax.hist(deviations, bins=25, range=(-12.5, 0.5), color=COLORS["blue"], edgecolor="white", linewidth=0.8)
    ax.axvline(0, color=COLORS["ink"], linewidth=1.2, linestyle="-", label="No shading (bid = value)")
    ax.axvline(summary["mean_bid_minus_value"], color=COLORS["red"], linewidth=2, label=f"Mean = {summary['mean_bid_minus_value']:.2f}")
    ax.axvline(summary["median_bid_minus_value"], color=COLORS["orange"], linewidth=2, linestyle="--", label=f"Median = {summary['median_bid_minus_value']:.2f}")
    ax.set(xlabel="Bid minus private value", ylabel="Bidder observations")
    ax.set_title("Bid shading is common; a few larger reductions extend the left tail", loc="left", weight="bold", pad=12)
    ax.text(
        0.98,
        0.95,
        f"Below value: {summary['under_value']}\nAt value: {summary['equal_value']}\nAbove value: {summary['over_value']}",
        transform=ax.transAxes,
        va="top",
        ha="right",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": COLORS["grid"], "alpha": 0.95},
    )
    ax.legend(frameon=False, ncol=1, loc="lower left")
    _save(fig, output_dir, "spsb_ipv_bid_shading_distribution")

    # Figure 3: allocation efficiency and winner utility at auction level.
    max_values = []
    winner_values = []
    efficiencies = []
    profits = []
    for row in auctions:
        values_by_bidder = json.loads(row["bidder_values"])
        max_values.append(max(values_by_bidder.values()))
        winner_values.append(float(row["winner_value"]))
        efficiencies.append(row["allocatively_efficient"].lower() == "true")
        profits.append(float(row["winner_profit"]))

    fig, (allocation_ax, profit_ax) = plt.subplots(1, 2, figsize=(10.4, 4.5), constrained_layout=True)
    for efficient, color, label in ((True, COLORS["teal"], "Efficient (97)"), (False, COLORS["red"], "Inefficient (3)")):
        xs = [x for x, flag in zip(max_values, efficiencies) if flag == efficient]
        ys = [y for y, flag in zip(winner_values, efficiencies) if flag == efficient]
        allocation_ax.scatter(xs, ys, s=38, alpha=0.8, color=color, edgecolor="white", linewidth=0.45, label=label, zorder=3)
    allocation_ax.plot([0, 49], [0, 49], color=COLORS["muted"], linestyle="--", linewidth=1.3)
    for row, x, y, efficient in zip(auctions, max_values, winner_values, efficiencies):
        if not efficient:
            allocation_ax.annotate(
                row["repetition"],
                (x, y),
                xytext=(5, -10),
                textcoords="offset points",
                fontsize=8,
                color=COLORS["red"],
                weight="bold",
            )
    allocation_ax.set(xlim=(0, 49), ylim=(0, 49), xlabel="Highest private value in auction", ylabel="Winner's private value")
    allocation_ax.set_title("Allocation", loc="left", weight="bold")
    allocation_ax.legend(frameon=False, fontsize=8, loc="upper left")
    allocation_ax.xaxis.set_major_locator(MultipleLocator(10))
    allocation_ax.yaxis.set_major_locator(MultipleLocator(10))

    profit_ax.hist(profits, bins=12, color=COLORS["blue"], edgecolor="white", linewidth=0.8)
    profit_ax.axvline(summary["mean_winner_utility"], color=COLORS["red"], linewidth=2, label=f"Mean = {summary['mean_winner_utility']:.2f}")
    profit_ax.set(xlabel="Winner utility (value minus second price)", ylabel="Auctions")
    profit_ax.set_title("Winner utility", loc="left", weight="bold")
    profit_ax.legend(frameon=False, loc="upper right")
    fig.suptitle("Auction outcomes: high allocation efficiency and positive winner surplus", x=0.02, ha="left", weight="bold", fontsize=13)
    _save(fig, output_dir, "spsb_ipv_auction_outcomes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("edsl_replication/runs"))
    parser.add_argument("--output-dir", type=Path, default=Path("writeup/figures"))
    args = parser.parse_args()
    make_figures(args.input_dir, args.output_dir)
    print(f"Wrote figures to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

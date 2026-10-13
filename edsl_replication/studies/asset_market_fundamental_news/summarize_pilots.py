"""Summarize pilot_02 arms and plot forecasts and submitted quote frontiers."""

from collections import Counter
import argparse
import json
from pathlib import Path
import statistics

import matplotlib.pyplot as plt

from edsl.sharedstate import SQLiteStateBackend
from edsl.workflows import WorkflowExperiment


STUDY = Path(__file__).parent
ROOT = STUDY / "pilot_02"
ARMS = ("positive", "negative", "control")
COLORS = {"positive": "#2a7f62", "negative": "#b5413e", "control": "#4e6f91"}


def load_arm(arm, root):
    output = root / arm
    experiment = WorkflowExperiment.load(output / "experiment.json")
    backend = SQLiteStateBackend(
        experiment.states[0], output / "state-0.sqlite", runtime=experiment.runtime
    )
    market = backend.snapshot("session").state["market"]
    return experiment, market


def main(root=ROOT):
    data = {}
    for arm in ARMS:
        experiment, market = load_arm(arm, root)
        orders = market["order_log"]
        prices = [row["price"] for row in market["tape"] if row["volume"]]
        data[arm] = {
            "experiment": experiment,
            "market": market,
            "orders": orders,
            "prices": prices,
            "trade_tape": [
                {"period": row["period"], "price": row["price"], "volume": row["volume"]}
                for row in market["tape"] if row["volume"]
            ],
            "volume": sum(row["volume"] for row in market["tape"]),
            "trade_periods": sum(bool(row["volume"]) for row in market["tape"]),
            "mean_forecast_5": statistics.mean(
                row["decision"]["forecast_0"] for row in orders if row["period"] == 5
            ),
            "mean_forecast_6": statistics.mean(
                row["decision"]["forecast_0"] for row in orders if row["period"] == 6
            ),
            "mean_h10_5": statistics.mean(
                row["decision"]["forecast_10"] for row in orders if row["period"] == 5
            ),
            "mean_h10_6": statistics.mean(
                row["decision"]["forecast_10"] for row in orders if row["period"] == 6
            ),
            "sides": dict(Counter(row["decision"]["side"] for row in orders)),
            "cash_range": [
                min(a["cash_cents"] for a in market["accounts"].values()) / 100,
                max(a["cash_cents"] for a in market["accounts"].values()) / 100,
            ],
            "redemption_cents": market["terminal_redemption_cents"],
            "news_event_count": len(market["fundamental_events"]),
            "redemption_applied": market["redemption_applied"],
        }

    fig, ax = plt.subplots(figsize=(8.3, 4.5))
    periods = range(1, 31)
    for arm in ARMS:
        orders = data[arm]["orders"]
        means = [
            statistics.mean(
                row["decision"]["forecast_0"] for row in orders if row["period"] == period
            )
            for period in periods
        ]
        ax.plot(periods, means, color=COLORS[arm], linewidth=2, label=f"{arm.title()} news")
        value = data[arm]["redemption_cents"] / 100
        ax.step(
            (1, 5, 6, 30),
            (14, 14, value, value),
            where="post",
            color=COLORS[arm],
            linestyle=":",
            linewidth=1,
            alpha=0.65,
        )
    ax.axvline(5.5, color="#555555", linestyle="--", linewidth=1.2)
    ax.set(
        xlabel="Trading period",
        ylabel="Mean forecast of current transaction price ($)",
        xlim=(1, 30), xticks=(1, 5, 6, 10, 15, 20, 25, 30),
        title="Forecast response to payoff-relevant news (after period 5)",
    )
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    fig.tight_layout()
    fig.savefig(root / "forecast_paths.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(8.3, 7.0), sharex=True)
    for ax, arm in zip(axes, ARMS):
        orders = data[arm]["orders"]
        best_bids, best_asks, gaps = [], [], []
        for period in periods:
            rows = [row for row in orders if row["period"] == period]
            bids = [
                row["decision"]["price"] for row in rows
                if row["decision"]["side"] == "buy" and row["accepted_quantity"] > 0
            ]
            asks = [
                row["decision"]["price"] for row in rows
                if row["decision"]["side"] == "sell" and row["accepted_quantity"] > 0
            ]
            best_bids.append(max(bids) if bids else float("nan"))
            best_asks.append(min(asks) if asks else float("nan"))
            gaps.append(min(asks) - max(bids) if asks and bids else float("nan"))
        ax.plot(periods, best_bids, color="#356d9a", label="Best buy limit")
        ax.plot(periods, best_asks, color="#b5413e", label="Best sell limit")
        ax.fill_between(periods, best_bids, best_asks, where=[g > 0 for g in gaps],
                        color="#999999", alpha=0.15, interpolate=True)
        ax.axvline(5.5, color="#555555", linestyle="--", linewidth=1)
        ax.set_ylabel("Limit ($)")
        ax.set_title(f"{arm.title()} arm: highest bid and lowest ask")
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, ncol=2, loc="upper left")
    axes[-1].set_xlabel("Trading period")
    axes[-1].set_xticks((1, 5, 6, 10, 15, 20, 25, 30))
    fig.text(0.12, 0.01, "Shaded gaps indicate the highest buy limit remained below the lowest sell limit.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(root / "order_frontiers.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Direct manipulation check: compare each trader's buy limit immediately
    # before and after the news. Lines connect only traders who submitted a
    # buy order in both periods, keeping the within-trader change visible.
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.6), sharey=True)
    paired_changes = {}
    for ax, arm in zip(axes, ARMS):
        orders = data[arm]["orders"]
        by_period = {
            period: {
                row["trader"]: row["decision"]["price"]
                for row in orders
                if row["period"] == period and row["decision"]["side"] == "buy"
            }
            for period in (5, 6)
        }
        both = sorted(set(by_period[5]) & set(by_period[6]))
        paired_differences = [
            by_period[6][trader] - by_period[5][trader] for trader in both
        ]
        paired_changes[arm] = {
            "n": len(both),
            "mean": statistics.mean(paired_differences) if paired_differences else None,
        }
        for trader in both:
            xs = (0, 1)
            ys = (by_period[5][trader], by_period[6][trader])
            ax.plot(xs, ys, color=COLORS[arm], alpha=0.48, linewidth=1.3, zorder=1)
            ax.scatter(xs, ys, color=COLORS[arm], s=30, zorder=2)
        only_pre = sorted(set(by_period[5]) - set(by_period[6]))
        only_post = sorted(set(by_period[6]) - set(by_period[5]))
        ax.scatter([0] * len(only_pre), [by_period[5][t] for t in only_pre],
                   facecolors="none", edgecolors=COLORS[arm], marker="o", s=48,
                   linewidth=1.5, zorder=3)
        ax.scatter([1] * len(only_post), [by_period[6][t] for t in only_post],
                   facecolors="none", edgecolors=COLORS[arm], marker="s", s=48,
                   linewidth=1.5, zorder=3)
        delta = paired_changes[arm]["mean"]
        delta_label = f"{delta:+.2f}" if delta is not None else "n/a"
        ax.set_title(f"{arm.title()} arm")
        ax.text(0.04, 0.96, f"Paired buyers: n={len(both)}\nMean change: {delta_label}",
                transform=ax.transAxes, va="top", ha="left", fontsize=9,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8})
        ax.set_xticks((0, 1), ("Before\n(period 5)", "After\n(period 6)"))
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Submitted buy limit ($)")
    fig.suptitle("Buy limits changed immediately after payoff news", y=1.02, fontsize=13)
    fig.text(0.5, 0.01,
             "Each line follows the same trader who bought in both periods; open markers indicate a buyer in only one period.",
             ha="center", fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(root / "bids_before_after.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    summary = {
        arm: {key: value for key, value in values.items() if key not in {"experiment", "market", "orders", "prices"}}
        for arm, values in data.items()
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (root / "paired_bid_changes.json").write_text(json.dumps(paired_changes, indent=2) + "\n")
    machine = data["control"]["experiment"].states[0].definition.machines["market"]
    machine.show_diagram(
        filename=str(root / "fundamental_news_machine.png"),
        renderer="pydot", detail=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    main(args.root)

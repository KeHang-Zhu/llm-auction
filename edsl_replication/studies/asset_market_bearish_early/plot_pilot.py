"""Plot market activity and treatment-group forecasts for pilot_01."""

from pathlib import Path
import statistics

import matplotlib.pyplot as plt

from edsl.sharedstate import SQLiteStateBackend
from edsl.workflows import WorkflowExperiment


STUDY = Path(__file__).parent
OUTPUT = STUDY / "pilot_01"


def load_market():
    experiment = WorkflowExperiment.load(OUTPUT / "experiment.json")
    backend = SQLiteStateBackend(
        experiment.states[0], OUTPUT / "state-0.sqlite", runtime=experiment.runtime
    )
    return experiment, backend.snapshot("session").state["market"]


def main():
    experiment, market = load_market()
    periods = list(range(1, 31))

    fig, (price_ax, volume_ax) = plt.subplots(
        2, 1, figsize=(8.3, 5.2), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    price_ax.axhline(14, color="#555555", linestyle="--", linewidth=1.2,
                     label="$14 terminal redemption")
    price_ax.plot(
        periods,
        [r["price"] if r["volume"] else float("nan") for r in market["tape"]],
        color="#356d9a", marker="o", linewidth=1.8, markersize=5,
        label="Transaction price (trade periods only)",
    )
    volume_ax.bar(
        [r["period"] for r in market["tape"]],
        [r["volume"] for r in market["tape"]],
        color="#7294ad", width=0.8,
    )
    price_ax.set_ylabel("Transaction price ($)")
    volume_ax.set_ylabel("Shares")
    volume_ax.set_xlabel("Trading period")
    volume_ax.set_xticks((1, 5, 10, 15, 20, 25, 30))
    price_ax.set_title("Market activity after pre-market bearish news")
    price_ax.legend(frameon=False, loc="upper left")
    for ax in (price_ax, volume_ax):
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT / "market_outcomes.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    updated = set(market["private_updates"])
    groups = {"Bearish news": updated, "No news": set(market["accounts"]) - updated}
    colors = {"Bearish news": "#356d9a", "No news": "#b5413e"}
    fig, ax = plt.subplots(figsize=(8.3, 4.2))
    for label, members in groups.items():
        means, spreads = [], []
        for period in periods:
            rows = [
                row for row in market["order_log"]
                if row["period"] == period and row["trader"] in members
            ]
            forecasts = [row["decision"]["forecast_0"] for row in rows]
            means.append(statistics.mean(forecasts))
            spreads.append(statistics.pstdev(forecasts))
        color = colors[label]
        ax.plot(periods, means, label=label, color=color, linewidth=2)
        ax.fill_between(
            periods, [m - s for m, s in zip(means, spreads)],
            [m + s for m, s in zip(means, spreads)], color=color, alpha=0.15, linewidth=0,
        )
    ax.axvline(0.5, color="#555555", linestyle="--", linewidth=1.2)
    ax.annotate("news delivered before period 1", xy=(0.5, 0.97),
                xycoords=("data", "axes fraction"), xytext=(8, -7),
                textcoords="offset points", ha="left", va="top", fontsize=9)
    ax.set(
        xlabel="Trading period", ylabel="Mean forecast of current transaction price ($)",
        xlim=(1, 30), xticks=(1, 5, 10, 15, 20, 25, 30),
        title="Forecast paths by news assignment (one market session)",
    )
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=2, loc="lower right")
    fig.text(0.12, 0.01, "Shading shows ±1 within-group standard deviation (n=6).",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUTPUT / "forecast_paths.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    machine = experiment.states[0].definition.machines["market"]
    machine.show_diagram(filename=str(OUTPUT / "market_machine.png"), renderer="pydot", detail=True)


if __name__ == "__main__":
    main()

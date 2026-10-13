"""Plot descriptive forecast paths from pilot_01 shared state."""

from pathlib import Path
import statistics

import matplotlib.pyplot as plt

from edsl.sharedstate import SQLiteStateBackend
from edsl.workflows import WorkflowExperiment


STUDY = Path(__file__).parent
OUTPUT = STUDY / "pilot_01"


def main():
    experiment = WorkflowExperiment.load(OUTPUT / "experiment.json")
    backend = SQLiteStateBackend(
        experiment.states[0], OUTPUT / "state-0.sqlite", runtime=experiment.runtime
    )
    market = backend.snapshot("session").state["market"]
    treated = set(market["private_updates"])
    groups = {
        "Private update": treated,
        "Control": set(market["accounts"]) - treated,
    }
    colors = {"Private update": "#b5413e", "Control": "#356d9a"}

    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    for label, members in groups.items():
        means, spreads = [], []
        for period in range(1, 31):
            rows = [
                row for row in market["order_log"]
                if row["period"] == period and row["trader"] in members
            ]
            forecasts = [row["decision"]["forecast_0"] for row in rows]
            means.append(statistics.mean(forecasts))
            spreads.append(statistics.pstdev(forecasts))
        color = colors[label]
        periods = list(range(1, 31))
        ax.plot(periods, means, label=label, color=color, linewidth=2)
        ax.fill_between(
            periods,
            [m - s for m, s in zip(means, spreads)],
            [m + s for m, s in zip(means, spreads)],
            color=color,
            alpha=0.15,
            linewidth=0,
        )

    ax.axvline(15.5, color="#555555", linestyle="--", linewidth=1.3)
    ax.annotate(
        "private estimate delivered\nbefore period 16",
        xy=(15.5, 0.97),
        xycoords=("data", "axes fraction"),
        xytext=(8, -7),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=9,
        color="#444444",
    )
    ax.set(
        xlabel="Trading period",
        ylabel="Mean forecast of current transaction price ($)",
        xlim=(1, 30),
        xticks=(1, 5, 10, 15, 16, 20, 25, 30),
        title="Price forecasts in one market session (no transactions occurred)",
    )
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=2, loc="lower right")
    fig.text(
        0.12,
        0.01,
        "Shading shows ±1 within-group standard deviation (n=6); descriptive only.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUTPUT / "forecast_paths.png", dpi=220, bbox_inches="tight")


if __name__ == "__main__":
    main()

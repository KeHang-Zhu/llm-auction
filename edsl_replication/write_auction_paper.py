"""Export condition-level data, visualizations, and standalone PDF papers."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

from edsl_replication.shared_state_auctions import (
    ROOT, build_proxy_machine, build_sealed_machine, study_slug,
)


def tex(value: Any) -> str:
    text = str(value)
    for char, replacement in (("\\", r"\textbackslash{}"), ("&", r"\&"),
                              ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                              ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
        text = text.replace(char, replacement)
    return text


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def process_results(source: Path, study_dir: Path) -> dict[str, Any]:
    payload = json.loads(source.read_text())
    config, result = payload["config"], payload["results"]
    rows = result["data"]
    bindings = result.get("shared_state", {}).get("bindings", [])
    if len(bindings) != 1:
        raise ValueError(f"expected one machine binding, found {len(bindings)}")
    binding = bindings[0]
    states = {snapshot["scope"]: snapshot["state"]["auction"]
              for snapshot in binding.get("exit_snapshots", [])}
    proxy = config["prompt"].get("strategy_type") == "ebay"
    by_scope: dict[str, list[dict[str, Any]]] = {}
    missing = []
    for row in rows:
        traits, answer = row.get("agent", {}).get("traits", {}), row.get("answer", {})
        bid = answer.get("bid_response")
        if bid is None:
            missing.append({"auction_id": traits.get("auction_id"),
                            "period": traits.get("period"), "answer": answer})
            continue
        by_scope.setdefault(traits["auction_id"], []).append({
            "repetition": int(traits["auction_id"].split("-")[-1]),
            "auction_id": traits["auction_id"], "seed": traits.get("seed"),
            "bidder": traits["bidder_id"], "seat": traits["seat"],
            "period": traits.get("period", 0), "value": traits["value"],
            "bid": float(bid), "plan": answer.get("plan"),
        })
    bidder_rows: list[dict[str, Any]] = []
    auction_rows: list[dict[str, Any]] = []
    for scope, observed in sorted(by_scope.items()):
        state = states.get(scope)
        if not state:
            missing.append({"auction_id": scope, "error": "missing exit snapshot"})
            continue
        winner, price = state.get("winner"), state.get("price")
        if proxy:
            max_bids = state.get("max_bids", {})
            values = state.get("values", {})
            for row in observed:
                bidder_rows.append(row | {
                    "final_max_bid": max_bids.get(row["bidder"], 0),
                    "is_winner": row["bidder"] == winner,
                    "profit": state.get("utilities", {}).get(row["bidder"], 0),
                    "winner": winner, "price": price,
                })
            auction_rows.append({
                "repetition": observed[0]["repetition"], "auction_id": scope,
                "seed": observed[0]["seed"], "winner": winner or "",
                "price": price if price is not None else "",
                "sale": winner is not None,
                "winner_value": values.get(winner, "") if winner else "",
                "winner_max_bid": max_bids.get(winner, "") if winner else "",
                "bidder_values": json.dumps(values, sort_keys=True),
                "final_max_bids": json.dumps(max_bids, sort_keys=True),
                "turn_actions": len(state.get("actions", {})),
            })
        else:
            utilities, payments = state.get("utilities", {}), state.get("payments", {})
            for row in observed:
                bidder_rows.append(row | {
                    "bid_minus_value": row["bid"] - row["value"],
                    "is_winner": row["bidder"] == winner,
                    "payment": payments.get(row["bidder"], 0),
                    "profit": utilities.get(row["bidder"], 0),
                    "winner": winner or "", "price": price if price is not None else "",
                })
            by_seat = {r["bidder"]: r for r in observed}
            winner_value = by_seat.get(winner, {}).get("value") if winner else None
            auction_rows.append({
                "repetition": observed[0]["repetition"], "auction_id": scope,
                "seed": observed[0]["seed"], "winner": winner or "",
                "price": price if price is not None else "",
                "sale": winner is not None, "winner_value": winner_value or "",
                "winner_bid": state.get("winning_bid") or "",
                "winner_profit": utilities.get(winner, 0) if winner else 0,
                "allocatively_efficient": (winner_value == max(r["value"] for r in observed)
                                            if winner else False),
                "bidder_values": json.dumps({r["bidder"]: r["value"] for r in observed}, sort_keys=True),
                "bids": json.dumps({r["bidder"]: r["bid"] for r in observed}, sort_keys=True),
            })

    all_bids = [float(r["bid"]) for r in bidder_rows]
    all_values = [float(r["value"]) for r in bidder_rows]
    final_bids = ([float(r["final_max_bid"]) for r in bidder_rows]
                  if proxy else all_bids)
    sold = sum(bool(row["sale"]) for row in auction_rows)
    settled = [float(row["price"]) for row in auction_rows if row["price"] != ""]
    deviation = [b - v for b, v in zip(final_bids, all_values)]
    summary = {
        "condition": config["experiment"]["name"],
        "description": config["experiment"].get("description", ""),
        "model": config["llm"]["model"], "temperature": config["llm"]["temperature"],
        "mechanism": config["rule"]["price_order"],
        "value_type": config["rule"]["private_value"],
        "bidder_count": config["auction"]["number_agents"],
        "configured_auctions": config["execution"]["repetitions"],
        "requested_auctions": payload.get("run_metadata", {}).get(
            "repetitions", config["execution"]["repetitions"]),
        "interviews": len(rows), "completed_decisions": len(bidder_rows),
        "failed_answers": len(missing), "settled_auctions": len(auction_rows),
        "sale_rate": sold / len(auction_rows) if auction_rows else None,
        "mean_value": statistics.mean(all_values) if all_values else None,
        "mean_bid": statistics.mean(final_bids) if final_bids else None,
        "mean_bid_minus_value": statistics.mean(deviation) if deviation else None,
        "mean_absolute_bid_value_gap": statistics.mean(abs(x) for x in deviation) if deviation else None,
        "mean_price": statistics.mean(settled) if settled else None,
        "efficient_share": (sum(bool(row.get("allocatively_efficient")) for row in auction_rows)
                            / len(auction_rows) if auction_rows and not proxy else None),
        "event_count": len(binding.get("events", [])),
        "read_events": sum(e.get("kind") == "read" for e in binding.get("events", [])),
        "write_events": sum(e.get("kind") == "write" for e in binding.get("events", [])),
        "state_id": binding.get("state_id"),
        "protocol": ("One plan-and-bid decision per bidder per period, serial live state, fixed turn count."
                     if proxy else "Concurrent sealed bids; plan and typed numeric bid are elicited separately."),
        "notes": [],
    }
    if proxy:
        summary["notes"].append("Randomized within-period order is seeded; it is fixed before inference.")
        if config["rule"].get("closing"):
            summary["notes"].append("Soft-close extension is not modeled; archived turn count is fixed.")
        summary["notes"].append("Minimum bid increment is described in prompts; numeric bids are not grid-validated.")
    else:
        summary["notes"].extend([
            "Tie-breaking is deterministic by bidder seat; legacy settlement randomizes among tied high bidders.",
            "Plan and numeric bid are separate questions; legacy elicits a single tagged response.",
            "Numeric bids are not validated against the configured increment.",
        ])
    study_dir.mkdir(parents=True, exist_ok=True)
    write_csv(study_dir / "bidder_results.csv", bidder_rows)
    write_csv(study_dir / "auction_results.csv", auction_rows)
    (study_dir / "summary.json").write_text(json.dumps(summary | {"failures": missing}, indent=2) + "\n")
    return summary


def make_plot(study_dir: Path, summary: dict[str, Any], bidders: list[dict[str, Any]],
              auctions: list[dict[str, Any]], proxy: bool) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    if proxy:
        periods: dict[int, list[float]] = {}
        for row in bidders:
            periods.setdefault(int(row["period"]), []).append(float(row["bid"]))
        xs = sorted(periods)
        means = [statistics.mean(periods[x]) for x in xs]
        ax.plot(xs, means, marker="o", color="#2C6E9B", linewidth=2, label="Mean submitted maximum")
        ax.set(xlabel="Auction period", ylabel="Submitted maximum bid")
        ax.set_title("Proxy bids over the auction timeline")
        ax.legend(frameon=False)
    else:
        values = [float(r["value"]) for r in bidders]
        bids = [float(r["bid"]) for r in bidders]
        if values:
            ax.scatter(values, bids, s=24, alpha=.55, color="#2C6E9B", edgecolors="none")
            lower, upper = min(values + bids), max(values + bids)
            ax.plot([lower, upper], [lower, upper], linestyle="--", color="#E08E45", label="Bid = value")
        ax.set(xlabel="Private or perceived value", ylabel="Submitted bid")
        ax.set_title("Bid levels relative to bidder values")
        ax.legend(frameon=False)
    ax.grid(alpha=.2)
    fig.savefig(study_dir / "figures" / "results.pdf", bbox_inches="tight")
    fig.savefig(study_dir / "figures" / "results.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_report(study_dir: Path, config: dict[str, Any], summary: dict[str, Any],
                config_path_name: str, proxy: bool) -> Path:
    from edsl_replication.shared_state_auctions import build_proxy_machine, build_sealed_machine

    figure = "figures/results.pdf"
    diagram = "figures/state_machine.png"
    mechanism = "Sequential proxy bidding" if proxy else f"Sealed-bid {config['rule']['price_order']}-price"
    notes = "\n".join(r"\item " + tex(note) for note in summary["notes"])
    machine_function = "build_proxy_machine" if proxy else "build_sealed_machine"
    study_folder = str(study_dir.relative_to(ROOT))
    import inspect
    source_code = inspect.getsource(build_proxy_machine if proxy else build_sealed_machine)
    # Control TeX-sensitive characters inside Python listings by writing it as a verbatim file.
    (study_dir / "machine_definition.py").write_text(source_code)
    rows = [
        ("Auction condition", summary["condition"]), ("Model", summary["model"]),
        ("Bidders", summary["bidder_count"]), ("Requested auctions", summary["requested_auctions"]),
        ("Settled auctions", summary["settled_auctions"]), ("Completed decisions", summary["completed_decisions"]),
        ("Failed answers", summary["failed_answers"]), ("State events", summary["event_count"]),
    ]
    table = "\n".join(f"{tex(a)} & {tex(b)} \\\\" for a, b in rows)
    metrics = []
    for key, label in (("mean_value", "Mean bidder value"), ("mean_bid", "Mean bid or final maximum"),
                       ("mean_bid_minus_value", "Mean bid-value gap"), ("mean_price", "Mean transaction price"),
                       ("sale_rate", "Sale rate"), ("efficient_share", "Efficient allocation share")):
        value = summary.get(key)
        if value is not None:
            metrics.append(f"{tex(label)}: {value:.3f}")
    tex_body = rf"""\documentclass[11pt]{{article}}
\usepackage[margin=0.8in]{{geometry}}
\usepackage[T1]{{fontenc}}
\usepackage{{lmodern}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{xcolor}}
\usepackage{{listings}}
\usepackage{{hyperref}}
\usepackage{{float}}
\definecolor{{codebg}}{{HTML}}{{F6F8FA}}
\definecolor{{codekw}}{{HTML}}{{2457A6}}
\definecolor{{codestr}}{{HTML}}{{A31515}}
\definecolor{{codecom}}{{HTML}}{{547547}}
\lstset{{language=Python,basicstyle=\ttfamily\small,backgroundcolor=\color{{codebg}},
  keywordstyle=\color{{codekw}}\bfseries,stringstyle=\color{{codestr}},
  commentstyle=\color{{codecom}}\itshape,showstringspaces=false,breaklines=true,
  frame=single,rulecolor=\color{{black!18}},columns=fullflexible}}
\title{{{tex(config['experiment'].get('description', mechanism))}}}
\author{{EDSL shared-state replication note}}
\date{{\today}}
\begin{{document}}
\maketitle
\begin{{abstract}}
This standalone report documents the {tex(mechanism.lower())} condition from the
archived llm-auction experiment. It gives the auction's shared-state machine,
the local EDSL launch path, and descriptive results from the recorded run.
The result is a new model run, not a replay of archived responses.
\end{{abstract}}
\section{{Auction and run design}}
{tex(config['experiment'].get('description', mechanism))}. The condition uses
{summary['bidder_count']} bidders, {tex(config['rule']['private_value'])} values,
{summary['requested_auctions']} auction repetitions, model {tex(summary['model'])},
and temperature {summary['temperature']}. The archived prompts and rule template
are taken from \path{{{tex(config['prompt']['rule_template_dir'] + config['rule']['special_name'])}}}.

\begin{{table}}[H]\centering\begin{{tabular}}{{lr}}\toprule
Item & Status \\\midrule
{table}
\bottomrule\end{{tabular}}\caption{{Run coverage and state event counts.}}\end{{table}}

\section{{Shared-state machine}}
Each auction repetition has an isolated scope. The machine accepts bidder actions,
exposes only its public view during play, and computes settlement in its close
transition. This prevents actions in concurrent auctions from mixing. The diagram
below was generated by the current EDSL \texttt{{Machine.show\_diagram()}} method.
\begin{{figure}}[H]\centering\includegraphics[width=\linewidth]{{{diagram}}}
\caption{{State, command, view, and close lifecycle for this condition.}}
\end{{figure}}

\subsection{{Mathematical form}}
Write the machine as $M=(C,X,A,V,\delta,\kappa)$, with constants $C$,
internal state $X$, action interface $A$, public view $V$, action transition
$\delta$, and close transition $\kappa$. The scope map assigns independent
states $x_r$ to auction repetitions $r$, so $\delta(x_r,a)$ cannot mutate
$x_{{r'}}$ when $r\ne r'$. For sealed bids, $x=(B,z)$ stores bid records
$B=\{{(i,s_i,v_i,c,b_i)\}}$ by bidder id; the open view reports only the
number of submissions. At close, bids are sorted by $(-b_i,s_i)$, the rule
selects rank $k\in\{{1,2,3\}}$ (or rank one for all-pay), and payments are
$p_i=b_i$ for every bidder in all-pay, otherwise $p_i=q$ for the winner and
zero for others. Utility is $u_i=\tilde v_i-p_i$, where $\tilde v_i$ is
the private or common component specified by the condition.

For proxy bidding, the internal state includes maximum bids $m_i$ and public
price $p$. A submitted amount $a_i$ updates $m_i\leftarrow\max(m_i,a_i)$;
if the two largest maxima are $m_{(1)}\ge m_{(2)}$, then the displayed price
is $\min(m_{(1)},m_{(2)}+\Delta)$ when $m_{(2)}>0$, otherwise the start
price. The winner is the top maximum if the final displayed price reaches the
reserve. Each serial EDSL interview reads the latest public price before
committing its action.

\subsection{{Definition used for this condition}}
The implementation below is the actual Python machine factory. The archived
configuration supplies the number of bidders, payment rule, value model, reserve,
and timing constants. The close transition ranks bids by amount and stable seat,
then records payments and utilities. For proxy auctions, serial live reads expose
the updated public price while each bidder's maximum remains private.
\lstinputlisting{{machine_definition.py}}

\section{{Local EDSL execution}}
The EDSL runner executes on the local machine and calls the provider named in the
YAML using the configured API key. No localhost model server is part of this run.
The launch command for this condition is:
\begin{{lstlisting}}[language=bash]
python -m edsl_replication.shared_state_auctions \\
  {config_path_name} \\
  --output edsl_replication/studies/{tex(study_folder)}/raw_results.json
\end{{lstlisting}}
The raw result contains the EDSL interviews, state map, machine event history, and
exit snapshots. CSV exports retain bidder-turn and auction-level observations.

\section{{Observed results}}
\begin{{figure}}[H]\centering\includegraphics[width=.88\linewidth]{{{figure}}}
\caption{{Descriptive result visualization for this condition.}}
\end{{figure}}
\noindent {"; ".join(metrics)}.

The plotted pattern is descriptive. These runs use the archived prompt and
condition settings but a newly executed EDSL shared-state protocol; differences
in question structure and execution order can affect model responses.

\section{{Protocol limits}}
\begin{{itemize}}
{notes}
\end{{itemize}}
\end{{document}}
"""
    (study_dir / "paper.tex").write_text(tex_body)
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                       cwd=study_dir, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT)
    return study_dir / "paper.pdf"


def write_study(config_path: Path, raw_results: Path | None = None,
                output_dir: Path | None = None) -> Path:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text())
    name = config["experiment"]["name"]
    study_dir = (output_dir.resolve() if output_dir else
                 ROOT / "edsl_replication" / "studies" / study_slug(config_path))
    study_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, study_dir / "config.yaml")
    source = raw_results or study_dir / "raw_results.json"
    summary = process_results(source, study_dir)
    payload = json.loads(source.read_text())
    proxy = config["prompt"].get("strategy_type") == "ebay"
    bidders = list(csv.DictReader((study_dir / "bidder_results.csv").open()))
    auctions = list(csv.DictReader((study_dir / "auction_results.csv").open()))
    figure_dir = study_dir / "figures"
    figure_dir.mkdir(exist_ok=True)
    make_plot(study_dir, summary, bidders, auctions, proxy)
    machine = build_proxy_machine(config) if proxy else build_sealed_machine(config)
    machine.show_diagram(str(figure_dir / "state_machine.png"), renderer="pydot", dpi=250)
    return make_report(study_dir, config, summary,
                       str(config_path.relative_to(ROOT)), proxy)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--raw-results", type=Path)
    args = parser.parse_args()
    print(write_study(args.config, args.raw_results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

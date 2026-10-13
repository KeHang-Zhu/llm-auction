"""Prepare one shared-state study folder and standalone paper per YAML condition.

This setup-only command does not construct EDSL interviews or call a model.
For conditions without result data, it creates a protocol paper explicitly
marked as awaiting inference.
"""

from __future__ import annotations

import argparse
import inspect
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from edsl_replication.shared_state_auctions import (
    ROOT, build_proxy_machine, build_sealed_machine, study_slug,
)
from edsl_replication.write_auction_paper import tex


def write_setup_paper(study_dir: Path, config: dict[str, Any], config_rel: str,
                      proxy: bool) -> Path:
    mechanism = "Sequential proxy bidding" if proxy else (
        f"Sealed-bid {config['rule']['price_order']}-price"
    )
    code_file = "machine_definition.py"
    figure = "figures/state_machine.png"
    reps = config["execution"]["repetitions"]
    interrupted_partial = config["experiment"]["name"] == "ebay_reserve_0"
    run_status = ("Prior 100-auction run interrupted after 32 completed scopes; "
                  "partial state not analyzed"
                  if interrupted_partial else "Not run; this file is a setup paper")
    bidder_count = config["auction"]["number_agents"]
    turns = config["rule"].get("turns", 1)
    if proxy:
        protocol = (f"Each auction has {turns} periods, with bidders acting serially "
                    "within each period. An interview reads the current public price "
                    "and the acting bidder's own maximum before its action is committed.")
        math_text = (r"The state contains maxima $m_i$, private values $v_i$, public "
                     r"actions, period $t$, and current price $p$. A submitted amount "
                     r"$a_i$ updates $m_i\gets\max(m_i,a_i)$. With increment $\Delta$, "
                     r"the price is $\min(m_{(1)},m_{(2)}+\Delta)$ when the second "
                     r"maximum is positive, and the start price otherwise. At close, "
                     r"the top maximum wins if the final price meets the reserve.")
        machine_fn = build_proxy_machine
    else:
        protocol = ("Bidders submit sealed bids concurrently against a shared snapshot. "
                    "The state machine withholds bid records until all required bids "
                    "arrive, then settles the auction in one close transition.")
        math_text = (r"The state stores bid records $B=\{(i,s_i,v_i,c_i,b_i)\}$. "
                     r"At close they are sorted by $(-b_i,s_i)$; the configured order "
                     r"selects the settlement bid. In first-, second-, or third-price "
                     r"auctions only the winner pays that bid; in all-pay every bidder "
                     r"pays their own bid. Utility is value less payment.")
        machine_fn = build_sealed_machine
    source = inspect.getsource(machine_fn)
    (study_dir / code_file).write_text(source)
    rows = [
        ("Condition", config["experiment"]["name"]),
        ("Bidders", bidder_count),
        ("Value model", config["rule"]["private_value"]),
        ("Configured repetitions", reps),
        ("Model", config["llm"]["model"]),
        ("Temperature", config["llm"]["temperature"]),
        ("Inference status", run_status),
        ("Machine", "Defined; diagram generated from EDSL Machine.show_diagram()"),
    ]
    table = "\n".join(f"{tex(k)} & {tex(v)} \\\\" for k, v in rows)
    paper = rf"""\documentclass[11pt]{{article}}
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
\author{{EDSL shared-state experiment setup}}
\date{{\today}}
\begin{{document}}
\maketitle
\begin{{abstract}}
This standalone document specifies the shared-state implementation and planned
execution for this archived llm-auction condition. It does not report model
outcome estimates; any prior partial execution is identified below.
\end{{abstract}}
\section{{Condition and protocol}}
{tex(config['experiment'].get('description', mechanism))}. This condition uses
{bidder_count} bidders, {tex(config['rule']['private_value'])} values, and
{reps} configured auction repetitions with model {tex(config['llm']['model'])}
at temperature {config['llm']['temperature']}. {tex(protocol)}

\begin{{table}}[H]\centering\begin{{tabular}}{{ll}}\toprule
Item & Setup \\\midrule
{table}
\\bottomrule\end{{tabular}}\caption{{Experiment setup; no inference results are included.}}\end{{table}}

\section{{Shared-state machine}}
Each repetition has its own scope in the shared-state map. The machine definition
is $M=(C,X,A,V,\delta,\kappa)$: constants $C$, internal state $X$, action
interface $A$, public view $V$, action transition $\delta$, and close transition
$\kappa$. Separate scopes ensure that a transition in auction $r$ cannot alter
auction $r'$. {math_text}
\begin{{figure}}[H]\centering
\includegraphics[width=\linewidth]{{{figure}}}
\caption{{Diagram generated by EDSL's \texttt{{Machine.show\_diagram()}}.}}
\end{{figure}}
\subsection{{Python machine factory}}
The following is the implementation used to build this condition's machine.
\lstinputlisting{{{code_file}}}

\section{{Launch command}}
The EDSL runner executes locally and uses the model service and key configured
for this experiment. This setup step did not launch interviews. To run the
configured number of repetitions:
\begin{{lstlisting}}[language=bash]
python -m edsl_replication.shared_state_auctions \\
  {tex(config_rel)} \\
  --output edsl_replication/studies/{tex(study_dir.name)}/raw_results.json
\end{{lstlisting}}
\section{{Results}}
{("A prior run was interrupted after 32 of 100 auction scopes completed. The "
  "completed-scope state log is preserved, but it has not been incorporated into "
  "this setup paper. No outcome estimates are reported here."
  if interrupted_partial else
  "Results are pending. After inference, the condition report will be rebuilt "
  "from the EDSL result object, interview answers, machine event history, and "
  "exit snapshots. No outcome estimates or charts are included in this setup paper.")}
\end{{document}}
"""
    (study_dir / "paper.tex").write_text(paper)
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                       cwd=study_dir, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT)
    return study_dir / "paper.pdf"


def setup(config_path: Path, force: bool = False) -> Path:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text())
    study_dir = ROOT / "edsl_replication" / "studies" / study_slug(config_path)
    study_dir.mkdir(parents=True, exist_ok=True)
    (study_dir / "figures").mkdir(exist_ok=True)
    shutil.copy2(config_path, study_dir / "config.yaml")
    proxy = config["prompt"].get("strategy_type") == "ebay"
    machine = build_proxy_machine(config) if proxy else build_sealed_machine(config)
    machine.show_diagram(str(study_dir / "figures" / "state_machine.png"),
                         renderer="pydot", dpi=250)
    paper_pdf = study_dir / "paper.pdf"
    # A result-backed paper is authoritative. Only generate a setup paper when
    # results are absent, or when explicitly requested for a setup refresh.
    if not (study_dir / "raw_results.json").exists() and (force or not paper_pdf.exists()):
        write_setup_paper(study_dir, config,
                          str(config_path.relative_to(ROOT)), proxy)
    return study_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", default=[],
                        help="Set up one condition slug or experiment name; repeatable")
    parser.add_argument("--force", action="store_true",
                        help="Refresh setup paper for conditions without raw results")
    args = parser.parse_args()
    configs = sorted((ROOT / "configs/experiments").glob("*.yaml"))
    selected = 0
    for config_path in configs:
        config = yaml.safe_load(config_path.read_text())
        slug, name = study_slug(config_path), config["experiment"]["name"]
        if args.only and slug not in args.only and name not in args.only:
            continue
        folder = setup(config_path, force=args.force)
        selected += 1
        print(f"SET UP {slug}: {folder / 'paper.pdf'}", flush=True)
    if args.only and selected != len(args.only):
        print(f"Requested {len(args.only)} selector(s); matched {selected} config(s)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

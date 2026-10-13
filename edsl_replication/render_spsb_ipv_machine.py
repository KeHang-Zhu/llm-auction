"""Render the SPSB-IPV machine with EDSL's Machine.show_diagram()."""

from __future__ import annotations

from pathlib import Path

from edsl_replication.spsb_ipv_shared_state import build_machine


OUTPUT_DIR = Path("writeup/figures")
DIAGRAM = OUTPUT_DIR / "spsb_ipv_shared_state_machine.png"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    machine = build_machine(bidder_count=3)
    machine.show_diagram(str(DIAGRAM), renderer="pydot", dpi=300)
    print(f"Rendered machine diagram in {DIAGRAM}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI for the cost-aware routing evaluation.

    python -m evals.cost_aware_routing --example       # run the illustrative sample
    python -m evals.cost_aware_routing runs.json        # score your recorded runs

The runs file schema is documented in ``runsio.py``. Numbers must come from real
run logs; ``--example`` uses bundled illustrative data (clearly labelled) so you
can see the output shape before you have your own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .runsio import report_for_file

_EXAMPLE = Path(__file__).with_name("runs_example.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals.cost_aware_routing")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("runs", nargs="?", help="path to a runs JSON file")
    group.add_argument(
        "--example",
        action="store_true",
        help="score the bundled illustrative sample instead of a runs file",
    )
    args = parser.parse_args(argv)

    path = _EXAMPLE if args.example else Path(args.runs)
    if not path.exists():
        parser.error(f"runs file not found: {path}")
    if args.example:
        print("[illustrative sample — numbers are NOT measured]\n")
    print(report_for_file(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

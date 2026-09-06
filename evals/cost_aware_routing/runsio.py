"""Load recorded runs and render the comparison report.

A runs file is JSON with two arrays, ``baseline`` and ``routed``, each a list of
task runs::

    {
      "note": "...",
      "baseline": [
        {"task_id": "docs-env-parity", "accepted": true,
         "attempts": [{"tier": "opus", "input_tokens": 40000,
                       "output_tokens": 6000, "wall_seconds": 55}]}
      ],
      "routed": [ ... ]
    }

Every number must come from real run logs. The bundled ``runs_example.json`` is
illustrative, not measured — see its ``note`` field.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .scoring import Attempt, SuiteResult, TaskRun, compare


def _parse_runs(entries: list[dict]) -> list[TaskRun]:
    return [
        TaskRun(
            task_id=e["task_id"],
            accepted=bool(e.get("accepted", False)),
            attempts=[
                Attempt(
                    tier=a["tier"],
                    input_tokens=int(a["input_tokens"]),
                    output_tokens=int(a["output_tokens"]),
                    wall_seconds=float(a.get("wall_seconds", 0.0)),
                )
                for a in e.get("attempts", [])
            ],
        )
        for e in entries
    ]


def load_runs(path: str | Path) -> dict[str, list[TaskRun]]:
    """Parse a runs JSON file into ``{"baseline": [...], "routed": [...]}``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "baseline": _parse_runs(data.get("baseline", [])),
        "routed": _parse_runs(data.get("routed", [])),
    }


def _money(value: float) -> str:
    return "inf" if math.isinf(value) else f"${value:.4f}"


def _row(label: str, base: str, routed: str) -> str:
    return f"  {label:<24}{base:>14}{routed:>14}"


def render_report(comparison: dict[str, object]) -> str:
    """Render a `compare()` result as a fixed-width text table."""
    base: SuiteResult = comparison["baseline"]  # type: ignore[assignment]
    routed: SuiteResult = comparison["routed"]  # type: ignore[assignment]
    pct = comparison["savings_pct"]
    lines = [
        "Cost-aware routing evaluation",
        "=" * 52,
        _row("", "baseline", "routed"),
        _row("accepted / total", f"{base.accepted_count}/{base.total_count}",
             f"{routed.accepted_count}/{routed.total_count}"),
        _row("acceptance rate", f"{base.acceptance_rate:.0%}",
             f"{routed.acceptance_rate:.0%}"),
        _row("total cost", _money(base.total_cost), _money(routed.total_cost)),
        _row("cost / accepted task", _money(base.cost_per_accepted_task),
             _money(routed.cost_per_accepted_task)),
        _row("total wall (s)", f"{base.total_wall_seconds:.0f}",
             f"{routed.total_wall_seconds:.0f}"),
        "",
        f"  cost/accepted delta: {_money(comparison['cost_per_accepted_task_delta'])}",  # type: ignore[arg-type]
        f"  savings: {'n/a' if pct is None else f'{pct:.1f}%'}",
    ]
    return "\n".join(lines)


def report_for_file(path: str | Path) -> str:
    """Load a runs file and return its rendered comparison report."""
    runs = load_runs(path)
    return render_report(compare(runs["baseline"], runs["routed"]))

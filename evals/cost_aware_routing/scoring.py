"""Scoring for the cost-aware routing evaluation.

The headline metric is **cost per accepted task**, not raw token cost. A task's
cost is the sum of *every* attempt it took — including rework and retries — so a
cheap model that has to be redone is charged for both tries. The cost of a task
that was never accepted still lands in the numerator but never in the
denominator, so a workflow that fails tasks is penalised, not rewarded, for being
cheap per call. This is the whole point: a cheaper response that needs
substantial rework is not a saving.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .pricing import token_cost


@dataclass(frozen=True)
class Attempt:
    """One model call made while working a task (an initial pass or a redo)."""

    tier: str
    input_tokens: int
    output_tokens: int
    wall_seconds: float = 0.0

    def cost(self) -> float:
        return token_cost(self.tier, self.input_tokens, self.output_tokens)


@dataclass
class TaskRun:
    """One task carried end to end under a given workflow.

    ``accepted`` is the human/eval verdict against the task's pre-defined success
    criteria — it must be decided the same way for the baseline and the routed
    workflow, or the comparison is meaningless.
    """

    task_id: str
    attempts: list[Attempt] = field(default_factory=list)
    accepted: bool = False

    def cost(self) -> float:
        return sum(a.cost() for a in self.attempts)

    def wall_seconds(self) -> float:
        return sum(a.wall_seconds for a in self.attempts)

    def rework_passes(self) -> int:
        """Attempts beyond the first — the redo count."""
        return max(len(self.attempts) - 1, 0)


@dataclass(frozen=True)
class SuiteResult:
    """Aggregate metrics for one workflow over a suite of task runs."""

    accepted_count: int
    total_count: int
    total_cost: float
    cost_per_accepted_task: float
    acceptance_rate: float
    total_wall_seconds: float


def score_suite(runs: list[TaskRun]) -> SuiteResult:
    """Aggregate a suite of task runs into headline metrics.

    ``cost_per_accepted_task`` is ``inf`` when nothing was accepted — infinite
    spend bought zero accepted work — which keeps it comparable rather than
    dividing by zero.
    """
    total = len(runs)
    accepted = sum(1 for r in runs if r.accepted)
    total_cost = sum(r.cost() for r in runs)
    cpat = total_cost / accepted if accepted else math.inf
    return SuiteResult(
        accepted_count=accepted,
        total_count=total,
        total_cost=total_cost,
        cost_per_accepted_task=cpat,
        acceptance_rate=(accepted / total if total else 0.0),
        total_wall_seconds=sum(r.wall_seconds() for r in runs),
    )


def compare(baseline: list[TaskRun], routed: list[TaskRun]) -> dict[str, object]:
    """Compare a baseline workflow against the routed one on the same tasks.

    A negative ``cost_per_accepted_task_delta`` means routing is cheaper per
    accepted task. ``savings_pct`` is that delta as a percentage of the baseline
    (``None`` when the baseline metric is not finite).
    """
    base = score_suite(baseline)
    routed_result = score_suite(routed)
    delta = routed_result.cost_per_accepted_task - base.cost_per_accepted_task
    savings_pct: float | None = None
    if math.isfinite(base.cost_per_accepted_task) and base.cost_per_accepted_task:
        savings_pct = -delta / base.cost_per_accepted_task * 100.0
    return {
        "baseline": base,
        "routed": routed_result,
        "cost_per_accepted_task_delta": delta,
        "savings_pct": savings_pct,
    }

"""Cost-aware routing evaluation harness.

Measures the cost-aware subagent routing (`.claude/agents/*.md`) against a
baseline workflow on a fixed set of representative tasks, scoring **cost per
accepted task** rather than raw token cost. See ``README.md`` for the method.

This package is the *instrument*, not a set of results: it defines the task
catalogue, the pricing, and the scoring. Recording the runs — token counts, wall
time, and the human/eval acceptance verdict — is a manual step per the README.
"""

from __future__ import annotations

from .pricing import MODEL_PRICING, ModelPrice, set_price, token_cost
from .scoring import Attempt, SuiteResult, TaskRun, compare, score_suite
from .tasks import TASKS, EvalTask, load_tasks

__all__ = [
    "MODEL_PRICING",
    "ModelPrice",
    "set_price",
    "token_cost",
    "Attempt",
    "TaskRun",
    "SuiteResult",
    "score_suite",
    "compare",
    "TASKS",
    "EvalTask",
    "load_tasks",
]

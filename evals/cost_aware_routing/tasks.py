"""The representative task catalogue for the routing evaluation.

Tasks live in ``tasks.yaml`` so they can be edited without touching code. Each
task names the tier the routing policy *recommends* and the success criteria that
decide acceptance — criteria are fixed here, before any run, so the baseline and
routed workflows are judged the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_TASKS_FILE = Path(__file__).with_name("tasks.yaml")

_VALID_TIERS = {"haiku", "sonnet", "opus"}
_VALID_CATEGORIES = {
    "documentation",
    "exploration",
    "implementation",
    "difficult",
}


@dataclass(frozen=True)
class EvalTask:
    """One representative task with its pre-defined acceptance criteria."""

    task_id: str
    category: str
    description: str
    recommended_tier: str
    success_criteria: tuple[str, ...]


def load_tasks(path: Path | None = None) -> list[EvalTask]:
    """Load and validate the task catalogue from ``tasks.yaml``."""
    raw = yaml.safe_load((path or _TASKS_FILE).read_text(encoding="utf-8"))
    tasks = [
        EvalTask(
            task_id=entry["id"],
            category=entry["category"],
            description=entry["description"],
            recommended_tier=entry["recommended_tier"],
            success_criteria=tuple(entry["success_criteria"]),
        )
        for entry in raw["tasks"]
    ]
    _validate(tasks)
    return tasks


def _validate(tasks: list[EvalTask]) -> None:
    """Fail loudly on a malformed catalogue rather than at scoring time."""
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            raise ValueError(f"duplicate task id: {task.task_id}")
        seen.add(task.task_id)
        if task.recommended_tier not in _VALID_TIERS:
            raise ValueError(f"{task.task_id}: bad tier {task.recommended_tier!r}")
        if task.category not in _VALID_CATEGORIES:
            raise ValueError(f"{task.task_id}: bad category {task.category!r}")
        if not task.success_criteria:
            raise ValueError(f"{task.task_id}: needs success criteria")


TASKS: list[EvalTask] = load_tasks()

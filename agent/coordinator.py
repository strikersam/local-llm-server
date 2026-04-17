"""agent/coordinator.py — Multi-Agent Coordinator

One coordinator agent breaks a goal into subtasks, dispatches each to a
dedicated worker AgentRunner with a restricted toolset, then assembles the
combined result.  Workers run concurrently up to *max_concurrent*.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agent.loop import AgentRunner

log = logging.getLogger("qwen-coordinator")


@dataclass
class WorkerSpec:
    """Describes a single worker's task and constraints."""

    worker_id: str
    instruction: str
    allowed_tools: list[str] = field(
        default_factory=lambda: ["read_file", "list_files", "search_code"]
    )
    model: str | None = None
    max_steps: int = 3


@dataclass
class CoordinatorResult:
    goal: str
    workers: list[dict[str, Any]]
    completed_at: str
    total_duration_s: float
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "workers": self.workers,
            "completed_at": self.completed_at,
            "total_duration_s": self.total_duration_s,
            "summary": self.summary,
        }


class AgentCoordinator:
    """Run N worker AgentRunners in parallel under a single coordinator.

    Usage::

        coordinator = AgentCoordinator(ollama_base="http://localhost:11434")
        result = await coordinator.run(
            "Refactor the codebase",
            worker_specs=[
                WorkerSpec("w1", "Update router tests"),
                WorkerSpec("w2", "Update agent tests"),
            ],
        )
    """

    def __init__(
        self,
        *,
        ollama_base: str,
        workspace_root: str | None = None,
        github_token: str | None = None,
    ) -> None:
        self.ollama_base = ollama_base
        self.workspace_root = workspace_root
        # Bug 5: Multi-agent tasks previously failed silently on GitHub tool
        # calls because the token was only set on the top-level runner.
        # Forward it to every worker so they can call GitHub tools too.
        self.github_token = github_token

    async def run(
        self,
        goal: str,
        worker_specs: list[WorkerSpec],
        *,
        max_concurrent: int = 3,
        email: str | None = None,
        department: str | None = None,
        key_id: str | None = None,
    ) -> CoordinatorResult:
        started = time.monotonic()
        log.info(
            "Coordinator starting: goal=%r workers=%d max_concurrent=%d",
            goal,
            len(worker_specs),
            max_concurrent,
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_worker(spec: WorkerSpec) -> dict[str, Any]:
            async with semaphore:
                runner = AgentRunner(
                    ollama_base=self.ollama_base,
                    workspace_root=self.workspace_root,
                    email=email,
                    department=department,
                    key_id=key_id,
                    github_token=self.github_token,
                )
                try:
                    result = await runner.run(
                        instruction=spec.instruction,
                        history=[],
                        requested_model=spec.model,
                        auto_commit=False,
                        max_steps=spec.max_steps,
                        user_id=email,
                    )
                    return {"worker_id": spec.worker_id, "status": "ok", "result": result}
                except Exception as exc:
                    log.error("Worker %s failed: %s", spec.worker_id, exc)
                    return {
                        "worker_id": spec.worker_id,
                        "status": "error",
                        "error": str(exc),
                    }

        worker_results: list[dict[str, Any]] = list(
            await asyncio.gather(*[run_worker(s) for s in worker_specs])
        )
        elapsed = time.monotonic() - started

        ok_count = sum(1 for w in worker_results if w.get("status") == "ok")
        summary = (
            f"Coordinator finished: {ok_count}/{len(worker_specs)} workers succeeded "
            f"in {elapsed:.1f}s"
        )
        log.info(summary)

        return CoordinatorResult(
            goal=goal,
            workers=worker_results,
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_duration_s=round(elapsed, 2),
            summary=summary,
        )

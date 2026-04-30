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
from enum import Enum
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
class AgentSpec:
    agent_id: str
    role: str = "worker"
    capabilities: list[str] = field(default_factory=lambda: ["general"])
    model: str | None = None
    max_parallel_tasks: int = 1
    active_tasks: int = 0


@dataclass
class TaskSpec:
    task_id: str
    instruction: str
    task_type: str = "general"
    dependencies: list[str] = field(default_factory=list)
    priority: int = 0
    model: str | None = None
    max_steps: int = 3
    retry_limit: int = 1


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


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
        agents = [
            AgentSpec(
                agent_id=spec.worker_id,
                capabilities=["general"],
                model=spec.model,
                max_parallel_tasks=1,
            )
            for spec in worker_specs
        ]
        tasks = [
            TaskSpec(
                task_id=spec.worker_id,
                instruction=spec.instruction,
                task_type="general",
                model=spec.model,
                max_steps=spec.max_steps,
            )
            for spec in worker_specs
        ]
        swarm = MultiAgentSwarm(
            ollama_base=self.ollama_base,
            workspace_root=self.workspace_root,
            github_token=self.github_token,
        )
        return await swarm.run(
            goal=goal,
            agents=agents,
            tasks=tasks,
            max_concurrent=max_concurrent,
            email=email,
            department=department,
            key_id=key_id,
        )


class MultiAgentSwarm:
    """Dependency-aware multi-agent task runner with capability routing."""

    def __init__(
        self,
        *,
        ollama_base: str,
        workspace_root: str | None = None,
        github_token: str | None = None,
    ) -> None:
        self.ollama_base = ollama_base
        self.workspace_root = workspace_root
        self.github_token = github_token

    async def run(
        self,
        *,
        goal: str,
        agents: list[AgentSpec],
        tasks: list[TaskSpec],
        max_concurrent: int,
        email: str | None = None,
        department: str | None = None,
        key_id: str | None = None,
    ) -> CoordinatorResult:
        started = time.monotonic()
        if not agents:
            agents = [AgentSpec(agent_id="default-worker", capabilities=["general", "code", "research", "writing"])]
        statuses = {task.task_id: TaskStatus.PENDING for task in tasks}
        results: dict[str, dict[str, Any]] = {}
        attempts: dict[str, int] = {task.task_id: 0 for task in tasks}
        tasks_by_id = {task.task_id: task for task in tasks}
        running: dict[str, asyncio.Task[tuple[str, AgentSpec, dict[str, Any]]]] = {}
        global_semaphore = asyncio.Semaphore(max_concurrent)

        async def execute(task: TaskSpec, agent: AgentSpec) -> tuple[str, AgentSpec, dict[str, Any]]:
            async with global_semaphore:
                agent.active_tasks += 1
                try:
                    runner = AgentRunner(
                        ollama_base=self.ollama_base,
                        workspace_root=self.workspace_root,
                        email=email,
                        department=department,
                        key_id=key_id,
                        github_token=self.github_token,
                    )
                    result = await runner.run(
                        instruction=task.instruction,
                        history=self._dependency_history(task, results),
                        requested_model=task.model or agent.model,
                        auto_commit=False,
                        max_steps=task.max_steps,
                        user_id=email,
                        department=department,
                        key_id=key_id,
                    )
                    return task.task_id, agent, {
                        "task_id": task.task_id,
                        "worker_id": agent.agent_id,
                        "agent_role": agent.role,
                        "task_type": task.task_type,
                        "status": "ok",
                        "dependencies": task.dependencies,
                        "result": result,
                    }
                except Exception as exc:
                    log.error("Task %s failed on agent %s: %s", task.task_id, agent.agent_id, exc)
                    return task.task_id, agent, {
                        "task_id": task.task_id,
                        "worker_id": agent.agent_id,
                        "agent_role": agent.role,
                        "task_type": task.task_type,
                        "status": "error",
                        "dependencies": task.dependencies,
                        "error": str(exc),
                    }
                finally:
                    agent.active_tasks = max(0, agent.active_tasks - 1)

        while True:
            for task in sorted(tasks, key=lambda t: t.priority, reverse=True):
                if statuses[task.task_id] != TaskStatus.PENDING or task.task_id in running:
                    continue
                missing = [dep for dep in task.dependencies if dep not in tasks_by_id]
                failed = [dep for dep in task.dependencies if statuses.get(dep) in {TaskStatus.FAILED, TaskStatus.BLOCKED}]
                if missing or failed:
                    statuses[task.task_id] = TaskStatus.BLOCKED
                    results[task.task_id] = {
                        "task_id": task.task_id,
                        "status": "blocked",
                        "dependencies": task.dependencies,
                        "error": f"Unmet dependencies: {missing or failed}",
                    }
                    continue
                if any(statuses.get(dep) != TaskStatus.COMPLETED for dep in task.dependencies):
                    continue
                agent = self._select_agent(agents, task)
                if not agent:
                    continue
                statuses[task.task_id] = TaskStatus.RUNNING
                attempts[task.task_id] += 1
                running[task.task_id] = asyncio.create_task(execute(task, agent))

            if not running:
                pending = [tid for tid, status in statuses.items() if status == TaskStatus.PENDING]
                if pending:
                    for tid in pending:
                        statuses[tid] = TaskStatus.BLOCKED
                        results[tid] = {"task_id": tid, "status": "blocked", "error": "No capable agent available"}
                break

            done, _pending = await asyncio.wait(running.values(), return_when=asyncio.FIRST_COMPLETED)
            for finished in done:
                task_id, _agent, payload = await finished
                running.pop(task_id, None)
                task = tasks_by_id[task_id]
                if payload.get("status") == "ok":
                    statuses[task_id] = TaskStatus.COMPLETED
                    results[task_id] = payload
                elif attempts[task_id] <= task.retry_limit:
                    statuses[task_id] = TaskStatus.PENDING
                else:
                    statuses[task_id] = TaskStatus.FAILED
                    results[task_id] = payload

            if all(status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED} for status in statuses.values()):
                break

        ordered_results = [results.get(task.task_id, {"task_id": task.task_id, "status": statuses[task.task_id]}) for task in tasks]
        elapsed = time.monotonic() - started
        ok_count = sum(1 for item in ordered_results if item.get("status") == "ok")
        summary = f"Coordinator finished: {ok_count}/{len(tasks)} tasks succeeded in {elapsed:.1f}s"
        return CoordinatorResult(
            goal=goal,
            workers=ordered_results,
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_duration_s=round(elapsed, 2),
            summary=summary,
        )

    @staticmethod
    def _select_agent(agents: list[AgentSpec], task: TaskSpec) -> AgentSpec | None:
        capable = [
            agent for agent in agents
            if agent.active_tasks < max(1, agent.max_parallel_tasks)
            and (task.task_type in agent.capabilities or "general" in agent.capabilities)
        ]
        if not capable:
            return None
        capable.sort(key=lambda a: (a.active_tasks, -len(set(a.capabilities) & {task.task_type})))
        return capable[0]

    @staticmethod
    def _dependency_history(task: TaskSpec, results: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for dep in task.dependencies:
            if dep in results:
                history.append({"role": "assistant", "content": f"Dependency {dep} result: {results[dep]}"})
        return history

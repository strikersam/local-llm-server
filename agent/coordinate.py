"""agent/coordinate.py — Multi-Agent Coordination models, helpers, and optional APIRouter.

This module provides:
  - Pydantic request/response models for the /agent/coordinate endpoint
  - build_swarm_from_request() helper
  - An APIRouter (can be included in other apps directly)

The primary /agent/coordinate endpoint in proxy.py imports models from here.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.coordinator import AgentSpec, MultiAgentSwarm, TaskSpec

log = logging.getLogger("qwen-coordinator")

router = APIRouter()


# ─── Request / Response models ─────────────────────────────────────────────────


class AgentConfig(BaseModel):
    """Agent definition for /agent/coordinate requests."""

    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="", max_length=200)
    role: str = Field(default="worker", max_length=64)
    capabilities: list[str] = Field(default_factory=lambda: ["general"])
    model: str | None = None
    max_parallel_tasks: int = Field(default=1, ge=1, le=10)
    llm_provider: str = Field(default="ollama", max_length=64)


class TaskInput(BaseModel):
    """Task definition for /agent/coordinate requests."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    id: str | None = Field(
        default=None, description="Alias for task_id (for compatibility)"
    )
    instruction: str = Field(..., min_length=1, max_length=4000)
    description: str = Field(default="", max_length=4000)
    task_type: str = Field(default="general", max_length=64)
    type: str | None = Field(default=None, description="Alias for task_type")
    priority: int = Field(default=0, ge=0)
    dependencies: list[str] = Field(default_factory=list)
    model: str | None = None
    max_steps: int = Field(default=3, ge=1, le=20)
    retry_limit: int = Field(default=1, ge=0, le=5)

    def resolved_task_id(self) -> str:
        return self.id or self.task_id or str(uuid.uuid4())

    def resolved_task_type(self) -> str:
        return self.type or self.task_type or "general"

    def resolved_instruction(self) -> str:
        return self.instruction or self.description or ""


class CoordinateRequestV2(BaseModel):
    """Extended coordinate request supporting both agents+tasks and legacy workers."""

    goal: str = Field(default="coordinate", min_length=1, max_length=2000)
    agents: list[AgentConfig] = Field(default_factory=list)
    tasks: list[TaskInput] = Field(default_factory=list)
    max_concurrent: int = Field(default=3, ge=1, le=10)


class SwarmSummary(BaseModel):
    total_tasks: int
    completed: int
    failed: int


class CoordinateResponse(BaseModel):
    status: str
    summary: SwarmSummary
    agents_used: list[dict[str, Any]]
    results: dict[str, Any]


# ─── Helpers ───────────────────────────────────────────────────────────────────


def build_agent_specs(agent_configs: list[AgentConfig]) -> list[AgentSpec]:
    """Convert AgentConfig list to AgentSpec list for MultiAgentSwarm."""
    if not agent_configs:
        return [
            AgentSpec(
                agent_id="default-worker",
                role="worker",
                capabilities=["general", "code", "research", "writing"],
                max_parallel_tasks=1,
            )
        ]
    return [
        AgentSpec(
            agent_id=cfg.agent_id or str(uuid.uuid4()),
            role=cfg.role,
            capabilities=list(cfg.capabilities) if cfg.capabilities else ["general"],
            model=cfg.model,
            max_parallel_tasks=cfg.max_parallel_tasks,
        )
        for cfg in agent_configs
    ]


def build_task_specs(task_inputs: list[TaskInput]) -> list[TaskSpec]:
    """Convert TaskInput list to TaskSpec list for MultiAgentSwarm."""
    return [
        TaskSpec(
            task_id=t.resolved_task_id(),
            instruction=t.resolved_instruction(),
            task_type=t.resolved_task_type(),
            dependencies=list(t.dependencies),
            priority=t.priority,
            model=t.model,
            max_steps=t.max_steps,
            retry_limit=t.retry_limit,
        )
        for t in task_inputs
    ]


def build_swarm(
    agent_configs: list[AgentConfig],
    *,
    ollama_base: str = "http://localhost:11434",
    workspace_root: str | None = None,
) -> tuple[MultiAgentSwarm, list[AgentSpec]]:
    """Create a MultiAgentSwarm and agent specs from request configs."""
    import os

    ollama_base = ollama_base or os.environ.get("OLLAMA_BASE", "http://localhost:11434")
    swarm = MultiAgentSwarm(
        ollama_base=ollama_base,
        workspace_root=workspace_root,
    )
    agents = build_agent_specs(agent_configs)
    return swarm, agents


# ─── Standalone APIRouter (optional — proxy.py has its own /agent/coordinate) ──


@router.post("/v2/agent/coordinate")
async def coordinate_v2(body: CoordinateRequestV2) -> dict[str, Any]:
    """
    V2 coordinate endpoint — accepts AgentConfig + TaskInput lists.

    The primary /agent/coordinate in proxy.py supports both legacy workers
    and this newer tasks+agents format. This route is registered separately
    for clients that want the cleaner v2 schema.
    """
    if not body.tasks:
        raise HTTPException(status_code=400, detail="No tasks provided")

    import os
    from pathlib import Path

    try:
        ollama_base = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        workspace_root = str(Path(__file__).resolve().parents[1])

        swarm, agents = build_swarm(
            body.agents,
            ollama_base=ollama_base,
            workspace_root=workspace_root,
        )
        tasks = build_task_specs(body.tasks)

        result = await swarm.run(
            goal=body.goal,
            agents=agents,
            tasks=tasks,
            max_concurrent=body.max_concurrent,
        )

        result_dict = result.as_dict()
        workers = result_dict.get("workers", [])
        completed = sum(1 for w in workers if w.get("status") == "ok")
        failed = sum(
            1 for w in workers if w.get("status") in ("error", "failed", "blocked")
        )

        return {
            "status": "success",
            "summary": {
                "total_tasks": len(tasks),
                "completed": completed,
                "failed": failed,
            },
            "agents_used": [
                {
                    "agent_id": a.agent_id,
                    "role": a.role,
                    "capabilities": a.capabilities,
                }
                for a in agents
            ],
            "results": result_dict,
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Agent coordination v2 failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

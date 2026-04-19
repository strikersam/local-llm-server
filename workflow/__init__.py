"""workflow — CRISPY deterministic workflow engine.

Lifecycle:
  request → context → research → investigate → structure → plan
  → [ApprovalGate] → execute (slices) → review → verify → report

Import the engine and the FastAPI router from this package:

    from workflow import WorkflowEngine, workflow_router
"""
from __future__ import annotations

from workflow.engine import WorkflowEngine
from workflow.api import workflow_router

__all__ = ["WorkflowEngine", "workflow_router"]

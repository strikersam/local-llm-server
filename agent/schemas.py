from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class AcceptedJob(BaseModel):
    session_id: str
    job_id: str
    status: str
    phase: str
    message: str


class RunningJob(BaseModel):
    job_id: str
    session_id: str
    status: str
    phase: str
    progress_events: List[Dict[str, Any]]
    workspace_path: Optional[str]


class CompletedJob(BaseModel):
    job_id: str
    session_id: str
    status: str
    phase: str
    final_message: Optional[str]
    result: Optional[Dict[str, Any]]


class FailedJob(BaseModel):
    job_id: str
    session_id: str
    status: str
    phase: str
    error: Dict[str, Any]


class AgentJobEnvelope(BaseModel):
    accepted: AcceptedJob
    running: Optional[RunningJob]
    completed: Optional[CompletedJob]
    failed: Optional[FailedJob]

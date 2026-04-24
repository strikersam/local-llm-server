"""setup/api.py — First-run Setup Wizard backend.

Five-step wizard:
  Step 1: Provider setup         (select local vs cloud; enter API keys)
  Step 2: Local model detection  (show detected hardware; pick default model)
  Step 3: Runtime configuration  (choose which runtimes to enable)
  Step 4: Default agent          (configure default agent profile)
  Step 5: Policy preferences     (cost / privacy / escalation preferences)

After completion:
  - Settings are persisted per-user in the WizardState store.
  - The wizard is NOT shown again to users who have completed it.
  - Admins can reset any user's wizard state.

Routes:
  GET  /api/setup/state              → current wizard state
  PUT  /api/setup/step/{step_num}    → save a single step
  POST /api/setup/complete           → mark wizard complete
  POST /api/setup/reset              → reset wizard (admin only)
  GET  /api/setup/detect/models      → detect available Ollama models
  GET  /api/setup/detect/hardware    → return hardware profile (delegates to hardware/)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rbac import UserRole, audit, get_user_role, require_admin

log = logging.getLogger("qwen-proxy")

setup_router = APIRouter(prefix="/api/setup", tags=["setup"])

# ── Wizard state model ────────────────────────────────────────────────────────

class WizardState(BaseModel):
    user_id:       str
    completed:     bool  = False
    current_step:  int   = 1
    started_at:    float = Field(default_factory=time.time)
    completed_at:  float | None = None
    # Per-step data (stored as raw dicts for flexibility)
    step1_providers:   dict = Field(default_factory=dict)   # provider selections
    step2_model:       dict = Field(default_factory=dict)   # default model choice
    step3_runtimes:    dict = Field(default_factory=dict)   # runtime enable flags
    step4_agent:       dict = Field(default_factory=dict)   # default agent config
    step5_policy:      dict = Field(default_factory=dict)   # policy preferences

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Step request models ────────────────────────────────────────────────────────

class Step1Request(BaseModel):
    """Provider setup: which providers to use and their API keys."""
    use_ollama:       bool = True
    ollama_base_url:  str  = "http://localhost:11434"
    use_openai:       bool = False
    use_anthropic:    bool = False
    use_groq:         bool = False
    # Note: API key values are stored via secrets_store, not here
    openai_secret_id:    str | None = None
    anthropic_secret_id: str | None = None
    groq_secret_id:      str | None = None


class Step2Request(BaseModel):
    """Local model detection results and default model selection."""
    default_model:      str  = "qwen3-coder:30b"
    coder_model:        str  = "qwen3-coder:30b"
    reviewer_model:     str  = "deepseek-r1:32b"
    embedding_model:    str  = "nomic-embed-text"
    accepted_degraded:  bool = False   # user acknowledges degraded compatibility


class Step3Request(BaseModel):
    """Runtime configuration."""
    enable_hermes:     bool = True
    enable_opencode:   bool = False
    enable_goose:      bool = False
    enable_openhands:  bool = False
    enable_aider:      bool = False
    hermes_base_url:   str  = "http://localhost:4444"


class Step4Request(BaseModel):
    """Default agent configuration."""
    agent_name:        str  = "My Agent"
    agent_model:       str  = "qwen3-coder:30b"
    runtime_id:        str | None = None
    cost_policy:       str  = "local_only"
    system_prompt:     str  = ""


class Step5Request(BaseModel):
    """Policy preferences."""
    never_use_paid_providers:        bool = True
    require_approval_before_paid:    bool = True
    max_paid_escalations_per_day:    int  = 0
    enable_langfuse:                 bool = False
    langfuse_public_key_secret_id:   str | None = None
    langfuse_secret_key_secret_id:   str | None = None
    langfuse_host:                   str  = "https://cloud.langfuse.com"
    send_anonymous_telemetry:        bool = False


# ── In-memory state store ──────────────────────────────────────────────────────

_wizard_states: dict[str, WizardState] = {}


def get_wizard_state(user_id: str) -> WizardState:
    if user_id not in _wizard_states:
        _wizard_states[user_id] = WizardState(user_id=user_id)
    return _wizard_states[user_id]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _uid(request: Request) -> str:
    user = getattr(request.state, "user", None) or {}
    if isinstance(user, dict):
        return user.get("email") or user.get("_id") or "anonymous"
    return str(getattr(user, "email", "anonymous"))


async def _detect_ollama_models(base_url: str = "http://localhost:11434") -> list[dict]:
    """Query Ollama /api/tags to get the list of locally available models."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data   = resp.json()
                models = data.get("models", [])
                return [
                    {
                        "name":     m.get("name", ""),
                        "size_gb":  round(m.get("size", 0) / 1e9, 1),
                        "modified": m.get("modified_at", ""),
                    }
                    for m in models
                ]
    except Exception as e:
        log.debug("Ollama model detection failed: %s", e)
    return []


# ── Routes ────────────────────────────────────────────────────────────────────

@setup_router.get("/state")
async def get_setup_state(request: Request):
    """Return the current wizard state for this user."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    return state.as_dict()


@setup_router.get("/detect/hardware")
async def detect_hardware_for_wizard():
    """Return hardware profile (used in Step 2 of wizard)."""
    from hardware.detector import get_hardware_profile
    import asyncio, functools
    profile = await asyncio.get_event_loop().run_in_executor(None, get_hardware_profile)
    return profile.as_dict()


@setup_router.get("/detect/models")
async def detect_models_for_wizard(ollama_url: str = "http://localhost:11434"):
    """Return list of locally available Ollama models (used in Step 2)."""
    models  = await _detect_ollama_models(ollama_url)
    return {"models": models, "total": len(models), "ollama_url": ollama_url}


@setup_router.put("/step/1")
async def save_step1(request: Request, body: Step1Request):
    """Save Step 1: Provider setup."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step1_providers = body.model_dump()
    state.current_step    = max(state.current_step, 2)
    audit("setup.step1", getattr(request.state, "user", {}), resource="setup")
    return {"step": 1, "saved": True, "next_step": 2}


@setup_router.put("/step/2")
async def save_step2(request: Request, body: Step2Request):
    """Save Step 2: Model selection."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step2_model  = body.model_dump()
    state.current_step = max(state.current_step, 3)
    audit("setup.step2", getattr(request.state, "user", {}), resource="setup")
    return {"step": 2, "saved": True, "next_step": 3}


@setup_router.put("/step/3")
async def save_step3(request: Request, body: Step3Request):
    """Save Step 3: Runtime configuration."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step3_runtimes = body.model_dump()
    state.current_step   = max(state.current_step, 4)
    audit("setup.step3", getattr(request.state, "user", {}), resource="setup")
    return {"step": 3, "saved": True, "next_step": 4}


@setup_router.put("/step/4")
async def save_step4(request: Request, body: Step4Request):
    """Save Step 4: Default agent."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step4_agent  = body.model_dump()
    state.current_step = max(state.current_step, 5)
    audit("setup.step4", getattr(request.state, "user", {}), resource="setup")
    return {"step": 4, "saved": True, "next_step": 5}


@setup_router.put("/step/5")
async def save_step5(request: Request, body: Step5Request):
    """Save Step 5: Policy preferences."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step5_policy = body.model_dump()
    state.current_step = 5
    audit("setup.step5", getattr(request.state, "user", {}), resource="setup")
    return {"step": 5, "saved": True, "next_step": "complete"}


@setup_router.post("/complete")
async def complete_wizard(request: Request):
    """Mark wizard as complete.  Will not be shown again on next login."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.completed    = True
    state.completed_at = time.time()
    audit("setup.complete", getattr(request.state, "user", {}), resource="setup", outcome="success")
    log.info("Setup wizard completed for user %s", uid)
    return {"completed": True, "user_id": uid}


@setup_router.post("/reset")
async def reset_wizard(request: Request):
    """Reset wizard state.  Admin only."""
    require_admin(request)
    target_uid = (await request.json()).get("user_id", _uid(request))
    if target_uid in _wizard_states:
        del _wizard_states[target_uid]
    audit("setup.reset", getattr(request.state, "user", {}), resource="setup", resource_id=target_uid)
    return {"reset": True, "user_id": target_uid}

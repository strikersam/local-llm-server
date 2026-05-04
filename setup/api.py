"""setup/api.py — First-run Setup Wizard backend.

Five-step wizard:
  Step 1: Provider setup         (select local vs cloud; enter API keys)
  Step 2: Local model detection  (show detected hardware; pick default model)
  Step 3: Runtime configuration  (choose which runtimes to enable)
  Step 4: Default agent          (configure default agent profile)
  Step 5: Policy preferences     (cost / privacy / escalation preferences)

After completion:
  - Settings are persisted per-user in the WizardState store.
  - The wizard stops auto-blocking login once complete, but can be reopened later for edits.
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

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rbac import UserRole, audit, get_user_role, require_admin
from secrets_store import get_secrets_store, SecretRecord

log = logging.getLogger("qwen-proxy")

DEFAULT_LANGFUSE_HOST = (
    os.environ.get("LANGFUSE_BASE_URL")
    or os.environ.get("LANGFUSE_HOST")
    or "https://cloud.langfuse.com"
)

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
    use_nvidia_nim:   bool = True   # default ON — free cloud, no local infra needed
    use_ollama:       bool = False  # default OFF — only needed for local inference
    ollama_base_url:  str  = "http://localhost:11434"
    repo_path:        str | None = None   # local-llm-server repo folder
    models_path:      str | None = None   # Ollama models folder
    use_openai:       bool = False
    use_anthropic:    bool = False
    use_google:       bool = False
    use_azure:        bool = False
    use_groq:         bool = False
    use_copilot:      bool = False
    # Note: API key values are stored via secrets_store, not here
    openai_secret_id:    str | None = None
    anthropic_secret_id: str | None = None
    google_secret_id:    str | None = None
    azure_secret_id:     str | None = None
    groq_secret_id:      str | None = None
    copilot_secret_id:   str | None = None


class Step2Request(BaseModel):
    """Local model detection results and default model selection."""
    default_model:      str  = "qwen/qwen2.5-coder-32b-instruct"
    coder_model:        str  = "qwen/qwen2.5-coder-32b-instruct"
    reviewer_model:     str  = "deepseek-ai/deepseek-r1"
    embedding_model:    str  = "nomic-embed-text"
    accepted_degraded:  bool = False   # user acknowledges degraded compatibility
    repo_path:          str | None = None  # path to local-llm-server repo
    models_path:        str | None = None  # path to models directory


class Step3Request(BaseModel):
    """Runtime configuration."""
    enable_hermes:     bool = True
    enable_opencode:   bool = False
    enable_goose:      bool = False
    enable_openhands:  bool = False
    enable_task_harness: bool = False
    enable_aider:      bool = False
    hermes_base_url:   str  = "http://localhost:4444"


class Step4Request(BaseModel):
    """Default agent configuration."""
    agent_name:        str  = "My Agent"
    agent_model:       str  = "qwen/qwen2.5-coder-32b-instruct"
    runtime_id:        str | None = None
    cost_policy:       str  = "free_only"
    system_prompt:     str  = ""


class Step5Request(BaseModel):
    """Policy preferences."""
    never_use_paid_providers:        bool = True
    require_approval_before_paid:    bool = True
    max_paid_escalations_per_day:    int  = 0
    enable_langfuse:                 bool = False
    langfuse_public_key_secret_id:   str | None = None
    langfuse_secret_key_secret_id:   str | None = None
    langfuse_host:                   str  = DEFAULT_LANGFUSE_HOST
    send_anonymous_telemetry:        bool = False


# ── Persistent state store ────────────────────────────────────────────────────

_WIZARD_STATE_DIR = Path.home() / ".local-llm-server" / "wizard-states"
_WIZARD_STATE_DIR.mkdir(parents=True, exist_ok=True)

_wizard_states: dict[str, WizardState] = {}


def _get_state_file(user_id: str) -> Path:
    """Get the file path for a user's wizard state."""
    safe_id = user_id.replace('/', '_').replace('\\', '_')
    return _WIZARD_STATE_DIR / f"{safe_id}.json"


def _load_wizard_state(user_id: str) -> WizardState:
    """Load wizard state from disk, or create a new one if not found."""
    state_file = _get_state_file(user_id)
    if state_file.exists():
        try:
            with open(state_file) as f:
                data = json.load(f)
            return WizardState(**data)
        except Exception as e:
            log.warning("Failed to load wizard state for %s: %s", user_id, e)
    return WizardState(user_id=user_id)


def _save_wizard_state(state: WizardState) -> None:
    """Persist wizard state to disk."""
    state_file = _get_state_file(state.user_id)
    try:
        with open(state_file, 'w') as f:
            json.dump(state.as_dict(), f, indent=2)
    except Exception as e:
        log.error("Failed to save wizard state for %s: %s", state.user_id, e)


def get_wizard_state(user_id: str) -> WizardState:
    """Get wizard state, loading from disk if not already in memory."""
    if user_id not in _wizard_states:
        _wizard_states[user_id] = _load_wizard_state(user_id)
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


@setup_router.get("/detect/providers")
async def detect_configured_providers():
    """Return which providers are already configured server-side via env vars.

    Called by the setup wizard on load so it can show 'already configured'
    indicators (e.g. Nvidia NIM key already set on Render) without exposing
    the actual key values to the browser.
    """
    nvidia_key = (
        os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey") or ""
    ).strip()
    openai_key = (
        os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_COMPAT_API_KEY") or ""
    ).strip()
    anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    langfuse_pk = (os.environ.get("LANGFUSE_PUBLIC_KEY") or "").strip()
    langfuse_sk = (os.environ.get("LANGFUSE_SECRET_KEY") or "").strip()

    return {
        "nvidia_nim": {
            "configured": bool(nvidia_key),
            "base_url": os.environ.get("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
            "default_model": os.environ.get("NVIDIA_DEFAULT_MODEL") or "meta/llama-3.3-70b-instruct",
        },
        "openai": {"configured": bool(openai_key)},
        "anthropic": {"configured": bool(anthropic_key)},
        "langfuse": {
            "configured": bool(langfuse_pk and langfuse_sk),
            "host": DEFAULT_LANGFUSE_HOST,
        },
    }


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
    _save_wizard_state(state)
    audit("setup.step1", getattr(request.state, "user", {}), resource="setup")
    return {"step": 1, "saved": True, "next_step": 2}


@setup_router.put("/step/2")
async def save_step2(request: Request, body: Step2Request):
    """Save Step 2: Model selection."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step2_model  = body.model_dump()
    state.current_step = max(state.current_step, 3)
    _save_wizard_state(state)
    audit("setup.step2", getattr(request.state, "user", {}), resource="setup")
    return {"step": 2, "saved": True, "next_step": 3}


@setup_router.put("/step/3")
async def save_step3(request: Request, body: Step3Request):
    """Save Step 3: Runtime configuration."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step3_runtimes = body.model_dump()
    state.current_step   = max(state.current_step, 4)
    _save_wizard_state(state)
    audit("setup.step3", getattr(request.state, "user", {}), resource="setup")
    return {"step": 3, "saved": True, "next_step": 4}


@setup_router.put("/step/4")
async def save_step4(request: Request, body: Step4Request):
    """Save Step 4: Default agent."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step4_agent  = body.model_dump()
    state.current_step = max(state.current_step, 5)
    _save_wizard_state(state)
    audit("setup.step4", getattr(request.state, "user", {}), resource="setup")
    return {"step": 4, "saved": True, "next_step": 5}


@setup_router.put("/step/5")
async def save_step5(request: Request, body: Step5Request):
    """Save Step 5: Policy preferences."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.step5_policy = body.model_dump()
    state.current_step = 5
    _save_wizard_state(state)
    audit("setup.step5", getattr(request.state, "user", {}), resource="setup")
    return {"step": 5, "saved": True, "next_step": "complete"}


@setup_router.post("/complete")
async def complete_wizard(request: Request):
    """Mark wizard as complete.  Will not be shown again on next login."""
    uid   = _uid(request)
    state = get_wizard_state(uid)
    state.completed    = True
    state.completed_at = time.time()
    _save_wizard_state(state)
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


@setup_router.post("/secret")
async def store_secret_during_setup(request: Request):
    """Store API keys/secrets during setup wizard (accessible without full auth).

    Used by the setup wizard frontend to store provider API keys (OpenAI, Anthropic, etc)
    before the user has completed setup and may not have full authentication yet.
    """
    try:
        body = await request.json()
        name = body.get("name")
        value = body.get("value")
        description = body.get("description", "")

        if not name or not value:
            raise HTTPException(status_code=400, detail="name and value are required")

        user = getattr(request.state, "user", {}) or {}
        uid = user.get("email") or user.get("_id") or "setup-user"

        rec = SecretRecord(owner_id=uid, name=name, description=description)
        rec.set_value(value)

        store = get_secrets_store()
        await store.create(rec)

        audit("setup.secret_created", user, resource="secret", resource_id=rec.secret_id)
        return {"id": rec.secret_id, "name": rec.name}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to store secret during setup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store secret: {str(e)}")

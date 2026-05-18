from __future__ import annotations
"""
Qwen3-Coder Authenticated Proxy
--------------------------------
Sits in front of Ollama, adds Bearer token auth, rate limiting, CORS,
and full streaming support. Exposes both:
  - Ollama native API  (/api/*)
  - OpenAI-compatible API (/v1/*)  ← works with Cursor, Continue, Aider, etc.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import threading
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from langfuse_obs import emit_chat_observation

# Load .env before any config reads (uvicorn does not load .env by default).
load_dotenv()
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, Dict, List, Union,  AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from admin_auth import AdminAuthManager, AdminIdentity
from admin_gui import register_admin_gui
from agent.background import BackgroundAgent, BackgroundTask
from agent.browser import BrowserSession
from agent.commit_tracker import CommitAttribution, CommitTracker
from agent.context import ContextCompressor
from agent.coordinate import router as coordinate_v2_router
from agent.coordinator import (
    AgentCoordinator,
    AgentSpec,
    MultiAgentSwarm,
    TaskSpec,
    WorkerSpec,
)
from agent.github_tools import github_router
from agent.loop import AgentRunner
from agent.memory import SessionMemory
from agent.models import AgentRunRequest, AgentSessionCreateRequest
from agent.permissions import AdaptivePermissions
from agent.playbook import PlaybookLibrary
from agent.quick_note import QuickNoteQueue, start_processor, set_quick_note_queue
from agent.improvement_loop import ImprovementLoop, set_improvement_loop
from agent.self_healing import SelfHealingAgent, set_self_healing_agent
from agent.log_monitor import LogMonitor, set_log_monitor
from agent.error_interceptor import ErrorInterceptorMiddleware
from agent.agency import Agency, set_agency
from agent.trend_watcher import TrendWatcher, set_trend_watcher
from agent.knowledge_sync import KnowledgeSync, set_knowledge_sync
from agent.v4_router import v4_router
from agent.scaffolding import ProjectScaffolder
from agent.scheduler import AgentScheduler
from agent.skills import SkillLibrary
from agent.state import AgentSessionStore
from agent.terminal import TerminalPanel
from agent.token_budget import BudgetExceededError, TokenBudget
from agent.user_memory import UserMemoryStore
from agent.voice import VoiceCommandInterface
from agent.watchdog import ResourceWatchdog
from agents.api import agent_router
from agents.store import get_agent_store, set_agent_store
from chat_handlers import handle_ollama_native_chat, handle_openai_chat_completions
from cost_insights import observability_router
from direct_chat import direct_chat_router, get_agent_job_manager
from handlers.anthropic_compat import handle_anthropic_messages, handle_count_tokens
from handlers.v3_auth import router as v3_auth_router
from handlers.v3_models import router as v3_models_router
from hardware import hardware_router
from key_store import issue_new_api_key, load_key_store
from provider_router import ProviderRouter, get_cooldown_state

# v3: Runtime layer and task system
from runtimes import get_runtime_manager, runtime_router
from routing import routing_router
from schedules import schedules_router
from secrets_store import secrets_router
from service_manager import WindowsServiceManager
from setup import setup_router
from social_auth import auth_router
from social_auth import verify_jwt as verify_social_jwt
from sync import sync_router
from tasks import task_router
from tasks.automation import TaskAutomationService
from tasks.dispatcher import TaskDispatcher
from tasks.store import get_task_store, set_task_store
from webui.config_store import JsonConfigStore
from webui.providers import ProviderManager
from webui.router import register_webui
from features.api import features_router
from webui.workspaces import WorkspaceManager
from features.matrix import get_feature_matrix, FeatureUnavailableError
from agent.workspace import get_workspace_manager
from workflow import WorkflowEngine, workflow_router
from workflow.engine import get_engine
from workflow.ide_bridge import handle_workflow_ide_chat

# ─── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE = (
    os.environ.get("OLLAMA_BASE")
    or os.environ.get("OLLAMA_BASE_URL")
    or "http://localhost:11434"
)
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8000"))
RAW_KEYS = os.environ.get("API_KEYS", "")
VALID_API_KEYS = set(k.strip() for k in RAW_KEYS.split(",") if k.strip())
KEY_STORE = load_key_store()
RATE_LIMIT_RPM = int(
    os.environ.get("RATE_LIMIT_RPM", "60")
)  # requests per minute per key
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def _strip_quoted_env(name: str) -> str:
    raw = os.environ.get(name, "") or ""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1].strip()
    return v


ADMIN_SECRET = _strip_quoted_env("ADMIN_SECRET")
WEAK_ADMIN_SECRETS = frozenset(
    {
        "change-me",
        "admin",
        "password",
        "secret",
        "your-admin-secret",
    }
)
# Comma-separated origins. Safer default is local-only for browser clients.
_default_cors = (
    "http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000"
)
_raw_cors = os.environ.get("CORS_ORIGINS", _default_cors).strip()
CORS_ORIGINS = [
    o.strip() for o in _raw_cors.split(",") if o.strip()
] or _default_cors.split(",")

# Refuse example / default keys from .env templates (must not be used in production)
WEAK_API_KEYS = frozenset(
    {
        "change-me",
        "your-secret-key-here",
        "YOUR_API_KEY",
        "optional-second-key-for-another-device",
    }
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("qwen-proxy")

_ollama_host = urlsplit(OLLAMA_BASE).hostname or ""
if _ollama_host not in ("localhost", "127.0.0.1", "::1") and not _ollama_host.endswith(
    ".local"
):
    log.warning(
        "OLLAMA_BASE=%r is not a local address — LLM calls will route over the network. "
        "If this is your public tunnel URL (ngrok/cloudflare), the proxy will call itself and fail when the tunnel is offline. "
        "For local Ollama, set OLLAMA_BASE=http://localhost:11434 in .env.",
        OLLAMA_BASE,
    )

if not VALID_API_KEYS and len(KEY_STORE) == 0:
    log.warning(
        "⚠  No API keys configured: set API_KEYS and/or create keys with generate_api_key.py (KEYS_FILE). "
        "All authenticated routes will be rejected until at least one key exists.",
    )
elif VALID_API_KEYS:
    bad = VALID_API_KEYS & WEAK_API_KEYS
    if bad:
        log.error(
            "Refusing to start: API_KEYS contains placeholder or default keys: %s. "
            "Replace with secrets from openssl / PowerShell (see .env.example).",
            ", ".join(sorted(bad)),
        )
        sys.exit(1)

if not ADMIN_SECRET or not ADMIN_SECRET.strip():
    log.error("Refusing to start: ADMIN_SECRET must not be empty.")
    sys.exit(1)

if ADMIN_SECRET and ADMIN_SECRET in WEAK_ADMIN_SECRETS:
    log.error(
        "Refusing to start: ADMIN_SECRET is a known weak placeholder. "
        "Generate a strong secret (e.g. Python: secrets.token_urlsafe(32)).",
    )
    sys.exit(1)

if ADMIN_SECRET and not KEY_STORE.is_configured():
    log.warning(
        "ADMIN_SECRET is set but KEYS_FILE is not — POST /admin/keys will return 503 until KEYS_FILE is configured.",
    )
elif ADMIN_SECRET:
    log.info(
        "Admin: POST /admin/keys (API) and browser UI at /admin/ui/login (session after login)",
    )

ADMIN_AUTH = AdminAuthManager(ADMIN_SECRET)
SERVICE_MANAGER = WindowsServiceManager(Path(__file__).resolve().parent)

# ─── Auth context ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AuthContext:
    key: str
    email: str
    department: str
    key_id: Optional[str]
    source: str  # "store" | "legacy"


# ─── Rate limiter (in-memory, per key) ─────────────────────────────────────────

_rate_buckets: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()
_rate_last_sweep = 0.0


def _sweep_rate_buckets(now: float, window: float) -> None:
    """Evict keys that have no entries in the current window. Prevents unbounded dict growth."""
    with _rate_lock:
        buckets_copy = dict(_rate_buckets)

    stale = [k for k, ts in buckets_copy.items() if not ts or now - ts[-1] >= window]

    with _rate_lock:
        for k in stale:
            _rate_buckets.pop(k, None)


def check_rate_limit(api_key: str) -> None:
    global _rate_last_sweep
    now = time.time()
    window = 60.0

    with _rate_lock:
        bucket = _rate_buckets[api_key]
        # Drop entries outside the 1-minute window
        bucket = [t for t in bucket if now - t < window]
        _rate_buckets[api_key] = bucket

        count = len(bucket)
        should_sweep = now - _rate_last_sweep >= window
        if should_sweep:
            _rate_last_sweep = now

    if should_sweep:
        _sweep_rate_buckets(now, window)

    if count >= RATE_LIMIT_RPM:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_RPM} req/min. Slow down.",
        )

    with _rate_lock:
        _rate_buckets[api_key].append(now)


LOCALHOST_BYPASS_PATHS = frozenset(
    {
        "/v1/messages",
        "/v1/chat/completions",
        "/api/chat",
    }
)


def _localhost_auth_bypass_allowed(request: Request) -> bool:
    path = request.url.path
    if path in LOCALHOST_BYPASS_PATHS:
        return True
    if path.startswith("/api/") and path in {"/api/chat"}:
        return True
    return False


# ─── Auth dependency ────────────────────────────────────────────────────────────


def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
) -> AuthContext:
    """Accept API key from: Bearer token, x-api-key header, or ?api_key= query param (for Claude SDK).

    For localhost requests, auth is optional (Claude Code runs locally).
    For remote requests, auth is required.
    """
    key = ""

    # Try from headers first
    if x_api_key:
        key = x_api_key.strip()
    elif authorization:
        if authorization.startswith("Bearer "):
            key = authorization[7:].strip()
        else:
            key = authorization.strip()

    # Claude-code SDK doesn't send headers, check query param as fallback
    if not key:
        api_key_from_query = request.query_params.get("api_key", "").strip()
        if api_key_from_query:
            key = api_key_from_query

    # Allow unauthenticated access from localhost (Claude Code runs locally)
    client_host = request.client.host if request.client else ""
    is_localhost = client_host in ("127.0.0.1", "localhost", "::1", "[::1]")

    # DEBUG: Log what we received
    if LOG_LEVEL == "DEBUG":
        key_preview = (key[:20] + "...") if key else "EMPTY"
        log.debug(
            "Auth check: client=%r, is_localhost=%s, key=%r",
            client_host,
            is_localhost,
            key_preview,
        )

    if not key:
        if is_localhost and _localhost_auth_bypass_allowed(request):
            if LOG_LEVEL == "DEBUG":
                log.debug(
                    "Allowing localhost request without auth on approved local-only path"
                )
            return AuthContext(
                key="localhost-stub",
                email="localhost",
                department="local-dev",
                key_id=None,
                source="localhost",
            )
        if LOG_LEVEL == "DEBUG":
            log.debug("No API key found for remote request from %r", client_host)
        raise HTTPException(
            status_code=401,
            detail="Missing API key.  Set Authorization: Bearer <key> or x-api-key: <key>",
        )

    rec = KEY_STORE.lookup_plain_key(key)
    if rec:
        check_rate_limit(key)
        return AuthContext(
            key=key,
            email=rec.email,
            department=rec.department,
            key_id=rec.key_id,
            source="store",
        )
    if key in VALID_API_KEYS:
        check_rate_limit(key)
        return AuthContext(
            key=key,
            email="unknown",
            department="legacy",
            key_id=None,
            source="legacy",
        )
    log.warning(
        "Rejected request with invalid API key from %r: %r",
        client_host,
        (key[:20] + "...") if key else "EMPTY",
    )
    raise HTTPException(status_code=403, detail="Invalid API key")


class AdminCreateKeyBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    department: str = Field(..., min_length=1, max_length=128)


class AdminLoginBody(BaseModel):
    username: str = Field(default="", max_length=320)
    password: str = Field(..., min_length=1, max_length=512)


class AdminControlBody(BaseModel):
    action: str = Field(..., pattern="^(start|stop|restart)$")
    target: str = Field(..., pattern="^(ollama|proxy|tunnel|stack)$")


class AdminUpdateKeyBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    department: str = Field(..., min_length=1, max_length=128)


def _require_admin(x_admin_secret: Optional[str], authorization: Optional[str]) -> None:
    if not ADMIN_SECRET:
        raise HTTPException(status_code=404, detail="Not Found")
    got = (x_admin_secret or "").strip()
    if not got and authorization and authorization.startswith("Bearer "):
        got = authorization[7:].strip()
    expected = ADMIN_SECRET.encode("utf-8")
    provided = got.encode("utf-8") if got else b""
    if not hmac.compare_digest(provided, expected) or not got:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _get_admin_identity_from_request(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> AdminIdentity:
    token = ""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    # Allow direct ADMIN_SECRET as Bearer token (used by bot/API clients)
    if token and ADMIN_SECRET and token == ADMIN_SECRET:
        return AdminIdentity(username="api", auth_source="token")
    session = ADMIN_AUTH.sessions.get(token) if token else None
    if session:
        return session.identity
    if request.session.get("admin_ok"):
        username = str(request.session.get("admin_user") or "admin")
        source = str(request.session.get("admin_auth_source") or "session")
        return AdminIdentity(username=username, auth_source=source)
    raise HTTPException(status_code=401, detail="Unauthorized")


def _origin_tuple(url: str) -> tuple[str, str, Optional[int]]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port is None:
        if scheme == "http":
            port = 80
        elif scheme == "https":
            port = 443
    return scheme, host, port


def _provider_headers_for_request(
    secret: object, request: Request, auth: AuthContext
) -> Optional[Dict[str, str]]:
    api_key = str(getattr(secret, "api_key", "") or "").strip()
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}

    secret_base_url = str(getattr(secret, "base_url", "") or "").strip()
    if secret_base_url and _origin_tuple(secret_base_url) == _origin_tuple(
        str(request.base_url)
    ):
        return {"Authorization": f"Bearer {auth.key}"}

    return None


def _agent_failure_result(instruction: str) -> dict[str, object]:
    return {
        "goal": instruction,
        "plan": None,
        "steps": [],
        "commits": [],
        "summary": "Agent run failed. Check server logs for details.",
        "status": "failed",
    }


# ─── App ────────────────────────────────────────────────────────────────────────

_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None
_task_dispatcher: Optional[TaskDispatcher] = None
_dispatcher_task: Optional[asyncio.Task] = None


_AUTOSTART_INIT_DELAY_S = int(os.environ.get("AUTOSTART_INIT_DELAY_S", "8"))


async def _autostart_services_bg() -> None:
    """Ensure docker-compose services are running.

    Runs as a background task at proxy startup so it never blocks request
    handling. Safe to call when already inside a compose container — docker
    compose up -d will fail (no socket) and the function returns silently.
    """
    if not shutil.which("docker"):
        log.debug("Docker not in PATH — skipping compose auto-start")
        return

    compose_file = Path(__file__).resolve().parent / "docker-compose.yml"
    if not compose_file.is_file():
        log.debug("docker-compose.yml not found — skipping compose auto-start")
        return

    log.info("Auto-starting docker-compose services (this may take up to 3 min on first run)…")
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose",
            "--file", str(compose_file),
            "up", "-d", "--no-recreate",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        if proc.returncode == 0:
            log.info("docker-compose services started/verified")
        else:
            log.debug(
                "docker-compose up returned %d: %s",
                proc.returncode,
                stderr.decode(errors="replace").strip()[:300],
            )
    except asyncio.TimeoutError:
        log.warning("docker-compose auto-start timed out after 180 s")
    except Exception as exc:
        log.debug("docker-compose auto-start skipped: %s", exc)

    # Brief pause for containers to initialise, then attempt runtime health refresh.
    # Configurable via AUTOSTART_INIT_DELAY_S env var (default 8 s).
    await asyncio.sleep(_AUTOSTART_INIT_DELAY_S)
    try:
        from runtimes.control import start_all_runtimes
        result = await start_all_runtimes()
        log.info(
            "Runtime auto-start: %d runtimes processed",
            len(result.get("runtimes", {})),
        )
    except Exception as exc:
        log.debug("Runtime auto-start skipped: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mongo_client, _mongo_db, _task_dispatcher, _dispatcher_task, TASK_AUTOMATION

    mongo_url = os.environ.get("MONGO_URL")
    is_prod = os.environ.get("IS_PRODUCTION", "false").lower() in ("true", "1", "yes")

    _mongo_client = None
    if not mongo_url:
        if is_prod:
            log.warning("MONGO_URL not set in production! Mongo-dependent features (persistence, long-running tasks) will be disabled.")
        else:
            mongo_url = "mongodb://localhost:27017"

    if mongo_url:
        try:
            _mongo_client = AsyncIOMotorClient(mongo_url)
            _mongo_db = _mongo_client["local_llm_server"]
            from agents.store import AgentStore
            from tasks.store import TaskStore

            agent_store = AgentStore(db=_mongo_db)
            task_store = TaskStore(db=_mongo_db)
            set_agent_store(agent_store)
            set_task_store(task_store)
            log.info("MongoDB connected for agent store persistence")
        except Exception as e:
            log.warning(
                "MongoDB unavailable for agent store at %s: %s. Using in-memory store.",
                mongo_url, e
            )

    should_register = os.environ.get("REGISTER_RUNTIMES", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    if should_register:
        try:
            from agents.store import AgentDefinition

            runtimes = {
                "hermes": {
                    "name": "Hermes (Executor)",
                    "description": "Fast, lightweight code execution runtime",
                    "task_types": ["code_generation", "refactoring"],
                    "model": "hermes:latest",
                    "base_url": "http://hermes:8080",
                },
                "opencode": {
                    "name": "OpenCode (Generator)",
                    "description": "Code generation and scaffolding runtime",
                    "task_types": ["code_generation", "scaffolding"],
                    "model": "opencode:latest",
                    "base_url": "http://opencode:8080",
                },
                "goose": {
                    "name": "Goose (Multi-Purpose)",
                    "description": "Multi-purpose AI development agent",
                    "task_types": ["code_generation", "testing", "review"],
                    "model": "goose:latest",
                    "base_url": "http://goose:8080",
                },
                "aider": {
                    "name": "Aider (Pair Programmer)",
                    "description": "Pair programming and collaborative development",
                    "task_types": ["code_generation", "refactoring", "debugging"],
                    "model": "aider:latest",
                    "base_url": "http://aider:8080",
                },
                "internal_agent": {
                    "name": "Built-in Local Agent",
                    "description": "Uses the internal AgentRunner and Ollama directly",
                    "task_types": [
                        "code_generation",
                        "refactoring",
                        "debugging",
                        "general",
                    ],
                    "model": os.environ.get(
                        "AGENT_PLANNER_MODEL",
                        "qwen/qwen2.5-coder-32b-instruct" if _nim_key else "nemotron-3-super-120b-a12b",
                    ),
                },
            }
            store = get_agent_store()
            for runtime_id, config in runtimes.items():
                existing = await store.get(runtime_id)
                if existing:
                    log.info("Runtime %s already registered, skipping", runtime_id)
                    continue
                agent = AgentDefinition(
                    agent_id=runtime_id,
                    owner_id="system",
                    name=config["name"],
                    description=config["description"],
                    model=config["model"],
                    runtime_id=runtime_id,
                    task_types=config["task_types"],
                    is_public=True,
                    cost_policy="local_only",
                    tags=["runtime", "system", "docker"],
                )
                await store.create(agent)
                log.info("Registered runtime: %s -> %s", runtime_id, agent.name)
        except Exception as e:
            log.error("Failed to register agent runtimes: %s", e, exc_info=True)

    mgr = get_runtime_manager()
    await mgr.start()
    log.info(
        "RuntimeManager started (%d runtimes registered)", len(mgr._registry.ids())
    )
    # Warm up health state immediately so the first dispatch cycle has real data.
    # The health service also kicks off its own async initial poll in start(),
    # but verify_all() ensures we wait for results before accepting tasks.
    try:
        health_results = await mgr.verify_all()
        healthy = [h["runtime_id"] for h in health_results if h.get("available")]
        unavailable = [h["runtime_id"] for h in health_results if not h.get("available")]
        log.info(
            "Runtime health warm-up: %d healthy=%s, %d unavailable=%s",
            len(healthy), healthy, len(unavailable), unavailable,
        )
    except Exception as _hc_exc:
        log.warning("Runtime health warm-up failed: %s", _hc_exc)

    _task_dispatcher = TaskDispatcher(
        workspace_root=str(Path(__file__).resolve().parent),
        poll_interval_s=10.0,
    )
    # Refresh TASK_AUTOMATION to use the MongoDB-backed store
    TASK_AUTOMATION = TaskAutomationService(store=get_task_store())
    SCHEDULER.set_on_fire(TASK_AUTOMATION.handle_scheduled_job)
    _dispatcher_task = asyncio.create_task(_task_dispatcher.run_forever())
    log.info("Task dispatcher started in background")

    app.state.webui_workspaces = WEBUI_WORKSPACES
    app.state.PROVIDER_ROUTER = PROVIDER_ROUTER

    # Kick off a background auto-start for docker-compose services and runtimes.
    # This ensures the MCP server, agent runtimes, and supporting containers
    # are up when users first connect, without delaying proxy startup.
    def _log_autostart_exc(task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception as exc:
            log.error("Autostart background task failed: %s", exc, exc_info=True)

    _autostart_task = asyncio.create_task(_autostart_services_bg())
    _autostart_task.add_done_callback(_log_autostart_exc)

    try:
        yield
    finally:
        if _task_dispatcher:
            _task_dispatcher.stop()
        if _dispatcher_task:
            _dispatcher_task.cancel()
            try:
                await _dispatcher_task
            except asyncio.CancelledError:
                pass
        log.info("Task dispatcher stopped")

        await mgr.stop()
        log.info("RuntimeManager stopped")

        if _mongo_client:
            _mongo_client.close()
            log.info("MongoDB connection closed")


app = FastAPI(
    title="LLM Relay — Control Plane",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# DEBUG: Log all incoming requests with headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest


class DebugHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        if LOG_LEVEL == "DEBUG":
            path = request.url.path
            method = request.method
            auth_header = request.headers.get("authorization", "")
            x_api_key = request.headers.get("x-api-key", "")
            log.debug(
                f"{method} {path} | Authorization: {auth_header[:30] if auth_header else 'NONE'}... | x-api-key: {x_api_key[:20] if x_api_key else 'NONE'}..."
            )
        response = await call_next(request)
        return response


if LOG_LEVEL == "DEBUG":
    app.add_middleware(DebugHeadersMiddleware)

# Error interceptor: catches unhandled 5xx responses and creates self-healing tasks.
app.add_middleware(ErrorInterceptorMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT authentication middleware for v3 dashboard
from tokens import verify_token


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        request.state.user = None
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header[:7].lower() == "bearer ":
            token = auth_header[7:].strip()
        elif request.headers.get("x-api-key"):
            token = request.headers.get("x-api-key")

        if token:
            log.info("Auth attempt with token: %s...", token[:10])
            # 1. Try JWT
            try:
                payload = verify_token(token, token_type="access")
                if payload:
                    log.info("JWT Auth success for %s", payload.get("email"))
                    request.state.user = {
                        "email": payload.get("email"),
                        "_id": payload.get("sub"),
                        "name": payload.get("name"),
                        "role": payload.get("role", "user"),
                    }
                    return await call_next(request)
            except Exception as e:
                log.debug("JWT Auth failed: %s", e)

            # 2. Try Legacy API Keys
            if token in VALID_API_KEYS:
                log.info("Legacy API Key Auth success")
                request.state.user = {
                    "email": "legacy@local",
                    "_id": "legacy_user",
                    "name": "Legacy API User",
                    "role": "admin",
                }
            else:
                log.warning(
                    "Token not in VALID_API_KEYS. VALID_API_KEYS has %d keys",
                    len(VALID_API_KEYS),
                )

        response = await call_next(request)
        return response


app.add_middleware(JWTAuthMiddleware)

if ADMIN_AUTH.enabled:
    _session_seed = (
        ADMIN_SECRET or os.environ.get("COMPUTERNAME") or str(Path(__file__).resolve())
    )
    _session_secret = hashlib.sha256(
        f"qwen-admin-session:{_session_seed}".encode()
    ).hexdigest()
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_secret,
        session_cookie="qwen_admin_session",
        max_age=60 * 60 * 24 * 7,
        same_site="lax",
    )

register_admin_gui(app, KEY_STORE, ADMIN_AUTH, SERVICE_MANAGER)
AGENT_SESSIONS = AgentSessionStore()
USER_MEMORY = UserMemoryStore()

# Build AGENT_RUNNER with NIM headers when the API key is configured so that
# session-based runs (/agent/run, /agent/sessions/{id}/run) also benefit from
# the free NVIDIA NIM models instead of always hitting local Ollama.
_nim_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey") or ""
_nim_base = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
_runner_headers = {"Authorization": f"Bearer {_nim_key}"} if _nim_key else None
_runner_base = _nim_base if _nim_key else OLLAMA_BASE
AGENT_RUNNER = AgentRunner(
    ollama_base=_runner_base,
    workspace_root=Path(__file__).resolve().parent,
    provider_headers=_runner_headers,
    session_store=AGENT_SESSIONS,
)

# ─── Feature singletons ────────────────────────────────────────────────────────
SESSION_MEMORY = SessionMemory()
CTX_COMPRESSOR = ContextCompressor()
PERMISSIONS = AdaptivePermissions()
TOKEN_BUDGET = TokenBudget()
PLAYBOOKS = PlaybookLibrary()
SCAFFOLDER = ProjectScaffolder()
SKILL_LIBRARY = SkillLibrary()
TERMINAL_PANEL = TerminalPanel()
COMMIT_TRACKER = CommitTracker(repo_root=Path(__file__).resolve().parent)
VOICE_INTERFACE = VoiceCommandInterface()
WATCHDOG = ResourceWatchdog()
SCHEDULER = AgentScheduler()
from agent.scheduler import set_scheduler as _set_scheduler
_set_scheduler(SCHEDULER)
BACKGROUND_AGENT = BackgroundAgent()
COORDINATOR = AgentCoordinator(
    ollama_base=OLLAMA_BASE, workspace_root=str(Path(__file__).resolve().parent)
)

# ─── Provider Router singleton (local-first, free-first fallback chain) ────────
# Module-level so cooldown state persists across requests in the same process.
# Priority order: local Ollama → Windows Ollama → HuggingFace → DeepSeek → Anthropic
PROVIDER_ROUTER = ProviderRouter.from_env()
BROWSER_SESSION = BrowserSession()
QUICK_NOTE_QUEUE = QuickNoteQueue()
set_quick_note_queue(QUICK_NOTE_QUEUE)
TASK_AUTOMATION: TaskAutomationService = TaskAutomationService(store=get_task_store())
start_processor(QUICK_NOTE_QUEUE, repo_root=Path(__file__).resolve().parent)

# ─── Continuous Improvement & Self-Healing ─────────────────────────────────────
SELF_HEALING_AGENT = SelfHealingAgent()
set_self_healing_agent(SELF_HEALING_AGENT)

IMPROVEMENT_LOOP = ImprovementLoop(
    repo_root=Path(__file__).resolve().parent,
    on_task=SCHEDULER.create,
)
set_improvement_loop(IMPROVEMENT_LOOP)
IMPROVEMENT_LOOP.start()

# Log monitor: captures backend ERROR/CRITICAL log records and creates fix tasks.
LOG_MONITOR = LogMonitor()
set_log_monitor(LOG_MONITOR)
LOG_MONITOR.attach()

# Agency: CEO (LLM-powered) + specialist agents (Dev, Security, Reviewer, Release, Scout, Optimizer).
AGENCY = Agency()
set_agency(AGENCY)
AGENCY.start()

# Trend Watcher: internet-connected AI trend intelligence.
TREND_WATCHER = TrendWatcher()
set_trend_watcher(TREND_WATCHER)

# Knowledge Sync: bridges trend intelligence into Wiki + Sources RAG.
KNOWLEDGE_SYNC = KnowledgeSync()
set_knowledge_sync(KNOWLEDGE_SYNC)

WEBUI_STORE = JsonConfigStore()
WEBUI_PROVIDERS = ProviderManager(WEBUI_STORE)
WEBUI_WORKSPACES = WorkspaceManager(
    WEBUI_STORE, default_local_root=Path(__file__).resolve().parent
)
WEBUI_PROVIDERS.ensure_defaults(local_base_url=OLLAMA_BASE)
WEBUI_WORKSPACES.ensure_defaults()
register_webui(
    app,
    providers=WEBUI_PROVIDERS,
    workspaces=WEBUI_WORKSPACES,
    admin_enabled=ADMIN_AUTH.enabled,
    verify_user=verify_api_key,
    get_admin_identity=_get_admin_identity_from_request,
)

# ─── Workflow Engine ──────────────────────────────────────────────────────────
# Initialise the shared WorkflowEngine singleton so it is available before any
# request hits the /workflow/* or /v1/workflow/chat endpoints.
WORKFLOW_ENGINE = get_engine()
app.include_router(
    workflow_router,
)
log.info("CRISPY WorkflowEngine mounted at /workflow/*")

# ─── v3: Runtime layer ────────────────────────────────────────────────────────
app.include_router(runtime_router)
log.info("Runtime layer mounted at /runtimes/*")

# ─── v3: Task system ──────────────────────────────────────────────────────────
app.include_router(task_router)
log.info("Task system mounted at /api/tasks/*")

# ─── v3.1: Agent profiles ─────────────────────────────────────────────────────
app.include_router(agent_router)
log.info("Agent profiles mounted at /api/agents/*")

# ─── v3.1: Hardware detection ─────────────────────────────────────────────────
app.include_router(
    hardware_router,
)
log.info("Hardware detection mounted at /api/hardware/*")

# ─── v3.1: User-scoped secrets ────────────────────────────────────────────────
app.include_router(
    secrets_router,
)
log.info("Secrets store mounted at /api/secrets/*")

# ─── v3: JWT Authentication (no API key required — for v3 dashboard) ─────────
app.include_router(v3_auth_router)
log.info("V3 JWT auth mounted at /api/auth/*")

# ─── v3: Models & Providers (requires V3 JWT token) ────────────────────────────
app.include_router(v3_models_router)
log.info(
    "V3 Models & Providers mounted at /api/models/*, /api/providers/*, /api/stats, /api/activity"
)

# ─── v3.1: Social auth (no API key required — OAuth public endpoints) ─────────
app.include_router(auth_router)
log.info("Social auth (OAuth) mounted at /api/social/*")

# ─── v3.1: Setup wizard ───────────────────────────────────────────────────────
app.include_router(setup_router)
log.info("Setup wizard mounted at /api/setup/* (public — no API key required)")

# ─── v3.1: Direct Chat (requires JWT token) ────────────────────────────────────
app.include_router(direct_chat_router)
log.info("Direct Chat mounted at /api/chat/* (requires JWT token)")

# ─── v4: Continuous Improvement Dashboard ──────────────────────────────────────
app.include_router(v4_router)
log.info("v4 Improvement Dashboard mounted at /v4/*")

# Register standing improvement schedules (run after app boots).
# Uses cron expressions: daily test scan at 03:00 UTC, weekly dep audit on Monday.
_default_schedules = [
    {
        "name": "daily-test-scan",
        "cron": "0 3 * * *",
        "instruction": (
            "Run the full pytest suite (`pytest -x`). "
            "If any tests fail, diagnose the root cause and apply the minimum fix. "
            "Update docs/changelog.md and commit the fix to master."
        ),
        "tags": ["auto-improvement", "tests", "daily"],
    },
    {
        "name": "weekly-dep-audit",
        "cron": "0 4 * * 1",
        "instruction": (
            "Run the dependency-audit skill: check requirements.txt for outdated or "
            "vulnerable packages using `pip list --outdated`. Pin safe upgrades, "
            "update changelog, and commit."
        ),
        "tags": ["auto-improvement", "dependencies", "weekly"],
    },
    {
        "name": "daily-changelog-check",
        "cron": "0 5 * * *",
        "instruction": (
            "Review docs/changelog.md. Ensure [Unreleased] contains entries for all "
            "recent commits that changed behaviour. Add any missing entries. "
            "Commit changelog updates with prefix `docs:`."
        ),
        "tags": ["auto-improvement", "docs", "daily"],
    },
    {
        "name": "weekly-todo-cleanup",
        "cron": "0 6 * * 3",
        "instruction": (
            "Search the codebase for FIXME and TODO:FIX markers. "
            "For each one, either resolve it (make the smallest correct fix) or "
            "convert it to a GitHub issue comment if it requires larger work. "
            "Commit resolved markers."
        ),
        "tags": ["auto-improvement", "cleanup", "weekly"],
    },
    # ── New autonomous agency schedules ────────────────────────────────────────
    {
        "name": "bi-daily-security-scan",
        "cron": "0 2 */2 * *",
        "instruction": (
            "Run the security scanner: bandit SAST on all Python files, safety CVE check "
            "on requirements.txt, and secret grep on the codebase. "
            "For each high-severity finding, apply the minimum safe fix or open a GitHub "
            "issue tagged 'security'. Update docs/changelog.md under `### Security`."
        ),
        "tags": ["auto-improvement", "security", "bi-daily"],
    },
    {
        "name": "weekly-trend-fetch",
        "cron": "0 7 * * 1",
        "instruction": (
            "Fetch the latest AI trends: new Ollama model releases, trending GGUF models "
            "on HuggingFace, relevant arXiv papers, and trending LLM-serving GitHub repos. "
            "Review high-relevance results. If a new Ollama model warrants adding to our "
            "router registry, update router/registry.py. Create feature-request GitHub "
            "issues for applicable techniques. Update changelog."
        ),
        "tags": ["auto-improvement", "trends", "weekly"],
    },
    {
        "name": "weekly-performance-profiling",
        "cron": "0 10 * * 2",
        "instruction": (
            "Profile key proxy paths: model routing latency, chat streaming throughput, "
            "health check cache hit rate. Identify bottlenecks (blocking I/O, redundant "
            "DB calls, uncached computations). Apply targeted micro-optimizations and "
            "update docs/changelog.md under `### Changed`."
        ),
        "tags": ["auto-improvement", "performance", "weekly"],
    },
    {
        "name": "daily-missing-test-scan",
        "cron": "0 4 * * *",
        "instruction": (
            "Find Python modules in agent/, router/, handlers/ that have no corresponding "
            "test file in tests/. For each untested module, write a test file covering "
            "the public API (happy path + one edge case per method). "
            "Run pytest to confirm new tests pass. Commit with prefix `test:`."
        ),
        "tags": ["auto-improvement", "tests", "daily"],
    },
    {
        "name": "weekly-docs-sync",
        "cron": "0 9 * * 4",
        "instruction": (
            "Run the docs-sync skill: compare module interfaces against docs/architecture/ "
            "and docs/adrs/. Update any stale architecture docs or ADRs. "
            "Ensure CLAUDE.md files in agent/ and router/ reflect current reality. "
            "Commit docs updates with prefix `docs:`."
        ),
        "tags": ["auto-improvement", "docs", "weekly"],
    },
    {
        "name": "weekly-council-review",
        "cron": "0 11 * * 5",
        "instruction": (
            "Run the council-review skill on all commits since last Friday. "
            "Simulate security, correctness, performance, and maintainability reviewers. "
            "Open a GitHub issue for each significant finding with label 'council-review'. "
            "If any finding is critical (security or data loss), also open a P1 issue."
        ),
        "tags": ["auto-improvement", "review", "weekly"],
    },
    {
        "name": "monthly-release-check",
        "cron": "0 8 1 * *",
        "instruction": (
            "Run the release-readiness skill on the first of each month. "
            "If all checks pass (tests green, changelog updated, no open P1 issues), "
            "bump the version in docs/changelog.md, tag the release, and push. "
            "If checks fail, create a GitHub issue listing blockers."
        ),
        "tags": ["auto-improvement", "release", "monthly"],
    },
    {
        "name": "weekly-hermes-deep-refactor",
        "cron": "0 14 * * 6",
        "instruction": (
            "Deep refactoring pass via Hermes agent: identify the most complex module "
            "(by cyclomatic complexity or LOC) in agent/ or router/. Propose and apply "
            "a modular decomposition that reduces complexity without changing behaviour. "
            "Ensure all existing tests still pass after refactoring. "
            "Update docs/changelog.md under `### Changed`."
        ),
        "tags": ["auto-improvement", "refactoring", "hermes", "weekly"],
    },
    {
        "name": "daily-goose-lint",
        "cron": "0 6 * * *",
        "instruction": (
            "Run code quality checks via Goose: flake8 (PEP8), mypy (type coverage), "
            "and radon (complexity). For each violation, apply the minimum correct fix. "
            "Commit fixes with prefix `style:` (exempt from changelog requirement). "
            "Report summary of remaining issues as a GitHub comment on the latest PR."
        ),
        "tags": ["auto-improvement", "lint", "goose", "daily"],
    },
    {
        "name": "weekly-aider-coverage-boost",
        "cron": "0 16 * * 0",
        "instruction": (
            "Use aider to improve test coverage: run pytest --cov and find the 5 modules "
            "with lowest coverage. For each, add targeted tests using aider's context-aware "
            "editing. Aim to reach ≥80% coverage per module. "
            "Commit with prefix `test:` and update changelog."
        ),
        "tags": ["auto-improvement", "coverage", "aider", "weekly"],
    },
    {
        "name": "weekly-knowledge-sync",
        "cron": "0 8 * * 1",
        "instruction": (
            "Run the KnowledgeSync pipeline: fetch fresh AI trends, ingest all "
            "high-relevance URLs into the Sources RAG database, and create a weekly "
            "Wiki digest page summarising what was found. "
            "Report count of ingested sources in the changelog under `### Added`."
        ),
        "tags": ["auto-improvement", "knowledge", "wiki", "sources", "weekly"],
    },
]
for _sched in _default_schedules:
    try:
        if not any(j.name == _sched["name"] for j in SCHEDULER.list()):
            SCHEDULER.create(**_sched)
            log.info("Registered improvement schedule: %s", _sched["name"])
    except Exception as _sched_exc:
        log.warning("Could not register schedule %s: %s", _sched["name"], _sched_exc)


@app.get("/api/agent/stream", response_model=None)
async def stream_agent_activity(
    request: Request,
    session_id: str | None = None,
    access_token: str | None = None,
) -> StreamingResponse | JSONResponse:
    """Server-Sent Events stream of agent job progress events.

    EventSource cannot send custom headers, so the JWT access token is accepted
    as the `access_token` query parameter in addition to the standard Bearer
    header (which JWTAuthMiddleware already processes into request.state.user).
    """
    user = getattr(request.state, "user", None)
    if user is None and access_token:
        try:
            payload = verify_token(access_token, token_type="access")
            if payload:
                user = {
                    "email": payload.get("email"),
                    "_id": payload.get("sub"),
                    "role": payload.get("role", "user"),
                }
        except Exception:
            pass

    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    owner_email: str | None = user.get("email") if isinstance(user, dict) else getattr(user, "email", None)
    _jobs = get_agent_job_manager()

    async def _event_stream():
        seen: dict[str, int] = {}
        while True:
            jobs = _jobs.list_jobs(session_id=session_id)
            if owner_email:
                jobs = [j for j in jobs if getattr(j, "owner_id", None) == owner_email]
            emitted = False
            for job in jobs:
                events = job.progress_events
                cursor = seen.get(job.job_id, 0)
                new_events = events[cursor:]
                for i, evt in enumerate(new_events, start=cursor):
                    # Normalize to ActivityEvent shape expected by AgentActivityFeed.tsx:
                    # {id, timestamp, agent, type, content, metadata}
                    evt_type = evt.get("type", "status")
                    agent = evt.get("phase") or job.phase or "system"
                    content = evt.get("message") or evt.get("tool_name") or ""
                    activity_event = {
                        "id": f"{job.job_id}-{i}",
                        "timestamp": evt.get("timestamp", ""),
                        "agent": agent,
                        "type": evt_type,
                        "content": content,
                        "metadata": {
                            k: v for k, v in evt.items()
                            if k not in {"timestamp", "type", "phase", "message"}
                        },
                        # extra job context for consumers that want it
                        "job_id": job.job_id,
                        "job_status": job.status,
                    }
                    yield f"data: {json.dumps(activity_event)}\n\n"
                    emitted = True
                seen[job.job_id] = len(events)
            if not emitted:
                yield ": keepalive\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class AuditLogResponse(BaseModel):
    entries: list[dict]
    total: int


@app.get("/api/audit-log")
async def get_audit_log_endpoint(
    request: Request,
    limit: int = 100,
    user_id: str | None = None,
    resource: str | None = None,
    outcome: str | None = None,
) -> AuditLogResponse:
    """Return RBAC audit log entries (newest first). Requires admin role."""
    user = getattr(request.state, "user", None)
    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})
    from rbac import is_admin as _is_admin
    if not _is_admin(user):
        return JSONResponse(status_code=403, content={"detail": "Admin access required"})
    from rbac import get_audit_log as _get_audit_log
    entries = _get_audit_log(limit=min(limit, 500), user_id=user_id, resource=resource, outcome=outcome)
from typing import Any

# --- Audit session models ---
class AuditSessionCreateRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

class AuditSessionResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]
    metadata: Dict[str, Any]

class AuditMessageCreateRequest(BaseModel):
    role: str
    content: str

class AuditMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: float

class AuditRollbackRequest(BaseModel):
    index: int

# --- Audit session endpoints ---
@app.post("/v1/audit/sessions")
async def create_audit_session(
    request: Request,
    body: AuditSessionCreateRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    from audit import create_session
    import uuid
    session_id = str(uuid.uuid4())
    session = create_session(session_id, body.metadata)
    return AuditSessionResponse(
        session_id=session_id,
        messages=session.get_conversation(),
        metadata=session.metadata,
    )

@app.get("/v1/audit/sessions/{session_id}")
async def get_audit_session(
    session_id: str,
    auth: AuthContext = Depends(verify_api_key),
):
    from audit import get_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    return AuditSessionResponse(
        session_id=session.session_id,
        messages=session.get_conversation(),
        metadata=session.metadata,
    )

@app.post("/v1/audit/sessions/{session_id}/messages")
async def add_audit_message(
    session_id: str,
    body: AuditMessageCreateRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    from audit import get_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    session.add_message(body.role, body.content)
    # Return the added message
    msg = session.messages[-1]
    return AuditMessageResponse(
        role=msg.role,
        content=msg.content,
        timestamp=msg.timestamp,
    )

@app.post("/v1/audit/sessions/{session_id}/rollback")
async def rollback_audit_session(
    session_id: str,
    body: AuditRollbackRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    from audit import get_session
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Audit session not found")
    try:
        session.rollback(body.index)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AuditSessionResponse(
        session_id=session_id,
        messages=session.get_conversation(),
        metadata=session.metadata,
    )

@app.delete("/v1/audit/sessions/{session_id}")
async def delete_audit_session(
    session_id: str,
    auth: AuthContext = Depends(verify_api_key),
):
    from audit import delete_session
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Audit session not found")
    return {"status": "deleted"}
    return AuditLogResponse(entries=entries, total=len(entries))

# ─── v3.1: Cost insights / observability ──────────────────────────────────────
app.include_router(
    observability_router,
)
log.info("Cost insights mounted at /api/observability/*")

# ─── v3.1: GitHub workspace integration ──────────────────────────────────────
app.include_router(
    github_router,
)
log.info("GitHub integration mounted at /api/github/*")

# ─── v3.1: Workspace sync ─────────────────────────────────────────────────────
app.include_router(
    sync_router,
)
log.info("Workspace sync mounted at /api/sync/*")

# ─── Admin: Feature support matrix ────────────────────────────────────────────
app.include_router(features_router)
log.info("Feature support matrix mounted at /admin/features/*")

# ─── v2: Multi-agent coordinate ───────────────────────────────────────────────
app.include_router(coordinate_v2_router)
log.info("Multi-agent coordinate v2 mounted at /v2/agent/coordinate")

# ─── Control Plane: Schedules ─────────────────────────────────────────────────
app.include_router(schedules_router)
log.info("Schedules API mounted at /api/schedules/*")

# ─── Control Plane: Routing policy ───────────────────────────────────────────
app.include_router(routing_router)
log.info("Routing policy API mounted at /api/routing/*")

# ── MCP Server (sub-app) ───────────────────────────────────────────────────────
# Mounted at /mcp-internal so the agent loop can reach workspace/git tools
# without a separate container.  On Render, MCP_SERVER_BASE_URL points at
# this service's own external URL + "/mcp-internal".
try:
    from mcp_server.server import app as _mcp_app
    app.mount("/mcp-internal", _mcp_app)
    log.info("MCP server mounted at /mcp-internal")
except Exception as _mcp_err:
    log.warning("MCP server not mounted: %s", _mcp_err)


# ─── Health (no auth) ──────────────────────────────────────────────────────────


@app.post("/admin/keys")
async def admin_create_key(
    body: AdminCreateKeyBody,
    x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret"),
    authorization: Optional[str] = Header(default=None),
):
    """Issue a new user API key (requires ADMIN_SECRET). Plain key returned once in JSON."""
    _require_admin(x_admin_secret, authorization)
    if not KEY_STORE.is_configured():
        raise HTTPException(
            status_code=503, detail="KEYS_FILE is not set on the server"
        )
    plain, rec = issue_new_api_key(
        KEY_STORE, body.email.strip(), body.department.strip()
    )
    log.info(
        "Admin issued key_id=%s email=%s department=%s",
        rec.key_id,
        rec.email,
        rec.department,
    )
    return {
        "api_key": plain,
        "key_id": rec.key_id,
        "email": rec.email,
        "department": rec.department,
        "created": rec.created,
    }


@app.post("/admin/api/login")
async def admin_login(body: AdminLoginBody):
    if not ADMIN_AUTH.enabled:
        # Bug 3: help the user recover from this — admin portal uses ADMIN_SECRET
        # as the password, not ADMIN_PASSWORD (which is the dashboard user login).
        raise HTTPException(
            status_code=404,
            detail=(
                "Admin login is not enabled. Set ADMIN_SECRET in your .env file "
                'to any strong random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`), restart the proxy, then log in at '
                "/admin/ui/login with any username and that secret as the password."
            ),
        )
    identity = ADMIN_AUTH.authenticate(body.username, body.password)
    if not identity:
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid admin credentials. The Admin Portal uses ADMIN_SECRET as the "
                "password (NOT ADMIN_PASSWORD — that one is for the dashboard user login). "
                "Check the ADMIN_SECRET value in your .env file."
            ),
        )
    session = ADMIN_AUTH.sessions.create(identity)
    return {
        "token": session.token,
        "username": identity.username,
        "auth_source": identity.auth_source,
        "expires_in": ADMIN_AUTH.sessions.ttl_seconds,
        "supports_windows_auth": ADMIN_AUTH.supports_windows_auth,
    }


@app.post("/admin/api/logout")
async def admin_logout(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    if authorization and authorization.startswith("Bearer "):
        ADMIN_AUTH.sessions.revoke(authorization[7:].strip())
    request.session.clear()
    return {"ok": True, "username": admin.username}


@app.get("/admin/api/status")
async def admin_status(
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    status = SERVICE_MANAGER.get_status()
    status["admin"] = {"username": admin.username, "auth_source": admin.auth_source}
    return status


@app.post("/admin/api/control")
async def admin_control(
    body: AdminControlBody,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    try:
        result = SERVICE_MANAGER.control(
            body.action, body.target, current_proxy_pid=os.getpid()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result["admin"] = {"username": admin.username}
    return result


@app.get("/admin/api/users")
async def admin_list_users(
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    if not KEY_STORE.is_configured():
        raise HTTPException(
            status_code=503, detail="KEYS_FILE is not set on the server"
        )
    records = [
        {
            "key_id": rec.key_id,
            "email": rec.email,
            "department": rec.department,
            "created": rec.created,
        }
        for rec in KEY_STORE.list_records()
    ]
    return {
        "records": records,
        "count": len(records),
        "admin": {"username": admin.username},
    }


@app.post("/admin/api/users")
async def admin_create_user(
    body: AdminCreateKeyBody,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    if not KEY_STORE.is_configured():
        raise HTTPException(
            status_code=503, detail="KEYS_FILE is not set on the server"
        )
    plain, rec = issue_new_api_key(
        KEY_STORE, body.email.strip(), body.department.strip()
    )
    return {
        "api_key": plain,
        "record": {
            "key_id": rec.key_id,
            "email": rec.email,
            "department": rec.department,
            "created": rec.created,
        },
        "admin": {"username": admin.username},
    }


@app.patch("/admin/api/users/{key_id}")
async def admin_update_user(
    key_id: str,
    body: AdminUpdateKeyBody,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    rec = KEY_STORE.update_metadata(key_id, body.email, body.department)
    if not rec:
        raise HTTPException(status_code=404, detail="Unknown key_id")
    return {
        "record": {
            "key_id": rec.key_id,
            "email": rec.email,
            "department": rec.department,
            "created": rec.created,
        },
        "admin": {"username": admin.username},
    }


@app.delete("/admin/api/users/{key_id}")
async def admin_delete_user(
    key_id: str,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    if not KEY_STORE.delete_by_key_id(key_id):
        raise HTTPException(status_code=404, detail="Unknown key_id")
    return {"ok": True, "key_id": key_id, "admin": {"username": admin.username}}


@app.post("/admin/api/users/{key_id}/rotate")
async def admin_rotate_user(
    key_id: str,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    out = KEY_STORE.rotate_plain(key_id)
    if not out:
        raise HTTPException(status_code=404, detail="Unknown key_id")
    plain, rec = out
    return {
        "api_key": plain,
        "record": {
            "key_id": rec.key_id,
            "email": rec.email,
            "department": rec.department,
            "created": rec.created,
        },
        "admin": {"username": admin.username},
    }


@app.get("/admin/api/features")
async def admin_list_features(
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    """Return the full feature support matrix.

    Shows maturity tier, enabled state, dependencies, and config flags for
    every feature.  Operators can see what is stable, beta, experimental, or
    disabled at a glance.
    """
    return get_feature_matrix().as_dict(admin_only=True)


@app.get("/admin/api/workspaces/metrics")
async def admin_workspace_metrics(
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    """Return workspace lifecycle metrics (counts by status).

    Scans the workspace base directory and aggregates by status without loading
    every manifest's full content.  Useful for detecting orphaned or stale jobs.
    """
    mgr = get_workspace_manager()
    # direct_chat.py creates legacy workspaces (no manifests) under a separate root.
    # Report both so the admin view is complete regardless of env var alignment.
    legacy_root = Path(
        os.environ.get("DIRECT_CHAT_AGENT_WORKSPACE_ROOT", ".data/direct-chat-agent-workspaces")
    )

    def _count_legacy() -> int:
        if not legacy_root.exists():
            return 0
        return sum(1 for d in legacy_root.glob("*/*") if d.is_dir())

    workspace_metrics, legacy_count = await asyncio.gather(
        asyncio.to_thread(mgr.metrics),
        asyncio.to_thread(_count_legacy),
    )
    return {
        "workspace_base": str(mgr._base),
        "metrics": workspace_metrics,
        "legacy_workspace_root": str(legacy_root),
        "legacy_workspace_count": legacy_count,
    }


@app.get("/health")
async def health():
    """Multi-provider health snapshot — shows state of all configured LLM providers."""
    provider_states = []
    healthy_count = 0
    cooldowns = get_cooldown_state()

    for provider in sorted(PROVIDER_ROUTER.providers, key=lambda p: p.priority):
        try:
            is_healthy = await PROVIDER_ROUTER.health_check(provider)
        except Exception:
            is_healthy = False
        on_cooldown = provider.provider_id in cooldowns
        if is_healthy:
            healthy_count += 1
        provider_states.append(
            {
                "provider_id": provider.provider_id,
                "type": provider.type,
                "base_url": provider.normalized_base_url,
                "priority": provider.priority,
                "healthy": is_healthy,
                "on_cooldown": on_cooldown,
                "cooldown_expires_in_s": (
                    round(
                        cooldowns[provider.provider_id] - __import__("time").time(), 1
                    )
                    if on_cooldown
                    else None
                ),
            }
        )

    # Also check raw Ollama reachability for backward compatibility
    ollama_models: list[str] = []
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            ollama_models = [m["name"] for m in r.json().get("models", [])]
            ollama_ok = True
    except Exception:
        pass

    overall = "healthy" if healthy_count > 0 else "degraded"
    status_code = 200 if overall == "healthy" else 503

    return JSONResponse(
        {
            "status": overall,
            "ollama": OLLAMA_BASE,
            "ollama_reachable": ollama_ok,
            "models": ollama_models,
            "healthy_provider_count": healthy_count,
            "providers": provider_states,
        },
        status_code=status_code,
    )


@app.get("/live")
async def live():
    """Container liveness check: confirms the proxy process is serving HTTP."""
    return {"status": "ok", "service": "proxy"}


@app.options("/api/health")
async def api_health_options():
    return JSONResponse({})


@app.get("/api/health")
async def api_health():
    """Public health check endpoint for setup wizard and frontend."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        return JSONResponse({"status": "ollama_down", "error": str(e)}, status_code=503)
    return JSONResponse({"status": "ok", "ollama": OLLAMA_BASE, "models": models})


@app.get("/api/probe-providers")
async def probe_providers(request: Request):
    """Live-probe every configured LLM provider with a minimal real API call.

    Pass your ADMIN_SECRET or any valid API key:
      ?key=YOUR_KEY   or   Authorization: Bearer YOUR_KEY
    """
    # Accept key via ?key= query param or Authorization Bearer header
    key = request.query_params.get("key", "").strip()
    if not key:
        auth_header = request.headers.get("authorization", "")
        if auth_header[:7].lower() == "bearer ":
            key = auth_header[7:].strip()
    if not key:
        raise HTTPException(status_code=401, detail="Pass ?key=YOUR_ADMIN_SECRET")
    # Validate against ADMIN_SECRET or any configured proxy API key
    valid = (ADMIN_SECRET and key == ADMIN_SECRET) or (key in VALID_API_KEYS)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid key")

    from provider_router import ProviderRouter

    router = ProviderRouter.from_env()
    if not router.providers:
        return JSONResponse({"error": "No providers discovered — check env vars", "results": []})

    probe_payload = {
        "model": "",
        "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
        "max_tokens": 10,
        "temperature": 0,
    }

    results = []
    for provider in router.providers:
        payload = {**probe_payload, "model": provider.default_model or ""}
        t0 = time.time()
        ok = False
        detail = ""
        reply = ""
        try:
            result = await asyncio.wait_for(
                router._try_one_provider(
                    provider, payload,
                    original_model=payload["model"],
                    model_fallbacks=[],
                    is_primary=True,
                    max_retries=0,
                    attempts=[],
                    provider_timeout_sec=12.0,
                ),
                timeout=14.0,
            )
            elapsed_ms = int((time.time() - t0) * 1000)
            if result is not None:
                ok = True
                try:
                    body = result.response.json()
                    reply = (
                        (body.get("choices") or [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        or ""
                    ).strip()[:80]
                except Exception:
                    reply = "(non-JSON response)"
                detail = f"{elapsed_ms}ms"
            else:
                detail = "no result returned"
        except asyncio.TimeoutError:
            detail = "timed out after 12s"
        except Exception as exc:
            detail = str(exc)[:150]

        results.append({
            "provider_id": provider.provider_id,
            "model": provider.default_model or "",
            "ok": ok,
            "detail": detail,
            "reply": reply,
        })

    passed = sum(1 for r in results if r["ok"])
    return JSONResponse({
        "summary": f"{passed}/{len(results)} providers healthy",
        "results": results,
    })


# ─── Agent Chat (provider-failover-aware) ────────────────────────────────────


class AgentChatRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    model: Optional[str] = Field(default=None, max_length=200)
    max_steps: int = Field(default=10, ge=1, le=50)
    timeout: float = Field(default=300.0, ge=10.0, le=600.0)


@app.post("/agent/chat")
async def agent_chat(
    body: AgentChatRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    """
    Agent chat endpoint with automatic provider failover.

    Routes through the priority chain:
      1. Local Ollama
      2. Windows server Ollama
      3. HuggingFace Free
      4. DeepSeek
      5. Anthropic Claude

    Failed providers are placed on cooldown and automatically skipped until recovery.
    """
    import uuid as _uuid

    session_id = body.session_id or str(_uuid.uuid4())

    # Load or create a persistent session so history survives across calls.
    existing = AGENT_SESSIONS.get(session_id)
    if existing is None:
        AGENT_SESSIONS.create_with_id(
            session_id=session_id,
            title=f"Chat for {auth.email}",
            owner_id=auth.email,
        )
    elif existing.owner_id and existing.owner_id != auth.email:
        # Refuse access to another user's session rather than silently leaking history.
        raise HTTPException(status_code=403, detail="Session belongs to a different user")
    # Snapshot history BEFORE appending the new user turn so the planner
    # receives prior context only — the current instruction is already passed
    # as the `instruction` argument to runner.run(), so including it in
    # history would cause the model to see it twice.
    prior_session = AGENT_SESSIONS.get(session_id)
    history = [item.model_dump() for item in (prior_session.history if prior_session else [])]
    AGENT_SESSIONS.append_message(session_id, "user", body.instruction)

    if not PROVIDER_ROUTER.providers:
        raise HTTPException(status_code=503, detail="No LLM providers configured")

    providers = sorted(PROVIDER_ROUTER.providers, key=lambda p: p.priority)
    last_error: Optional[Exception] = None

    for provider in providers:
        # Skip providers on cooldown
        from provider_router import is_provider_on_cooldown, mark_provider_failed

        if is_provider_on_cooldown(provider.provider_id):
            log.info(
                "agent/chat: skipping provider %s (on cooldown)",
                provider.provider_id,
            )
            continue

        try:
            runner = AgentRunner(
                ollama_base=provider.normalized_base_url,
                workspace_root=str(Path(__file__).resolve().parent),
                provider_headers=provider.auth_headers() if provider.api_key else None,
                provider_chain=[],  # outer loop handles fallback; don't let from_env() inject extras
                session_store=AGENT_SESSIONS,
                email=auth.email,
                department=auth.department,
                key_id=auth.key_id,
            )
            log.info(
                "agent/chat: routing to provider=%s session=%s",
                provider.provider_id,
                session_id,
            )
            result = await asyncio.wait_for(
                runner.run(
                    instruction=body.instruction,
                    history=history,
                    requested_model=body.model or provider.default_model,
                    auto_commit=False,
                    max_steps=body.max_steps,
                    user_id=auth.email,
                    department=auth.department,
                    key_id=auth.key_id,
                    memory_store=USER_MEMORY,
                    session_id=session_id,
                ),
                timeout=body.timeout,
            )
            AGENT_SESSIONS.append_message(
                session_id, "assistant", result.get("summary", "")
            )
            return {
                "session_id": session_id,
                "status": "success",
                "provider_used": provider.provider_id,
                "result": result,
            }
        except asyncio.TimeoutError:
            mark_provider_failed(provider.provider_id)
            log.warning(
                "agent/chat: provider %s timed out after %.0fs",
                provider.provider_id,
                body.timeout,
            )
            last_error = asyncio.TimeoutError(
                f"Provider {provider.provider_id} timed out"
            )
        except Exception as exc:
            mark_provider_failed(provider.provider_id)
            log.warning(
                "agent/chat: provider %s failed: %s",
                provider.provider_id,
                exc,
            )
            last_error = exc

    raise HTTPException(
        status_code=503,
        detail=f"All LLM providers failed or are on cooldown. Last error: {last_error}",
    )


@app.get("/runtimes-ui")
async def runtimes_ui():
    """Serve the runtimes control panel (start/stop agents)."""
    try:
        with open(Path(__file__).parent / "webui" / "runtimes_page.html") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Runtimes control panel not found</h1>", status_code=404
        )


@app.post("/agent/sessions")
async def create_agent_session(
    body: AgentSessionCreateRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    title = body.title or f"Session for {auth.email}"
    return AGENT_SESSIONS.create(
        title=title, provider_id=body.provider_id, workspace_id=body.workspace_id
    )


@app.get("/agent/sessions/{session_id}")
async def get_agent_session(
    session_id: str, auth: AuthContext = Depends(verify_api_key)
):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    return session


@app.post("/agent/sessions/{session_id}/run")
async def run_agent_task(
    session_id: str,
    body: AgentRunRequest,
    request: Request,
    auth: AuthContext = Depends(verify_api_key),
):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    AGENT_SESSIONS.append_message(session_id, "user", body.instruction)
    history = [
        item.model_dump()
        for item in (AGENT_SESSIONS.get(session_id) or session).history
    ]
    try:
        provider_id = body.provider_id or session.provider_id
        workspace_id = body.workspace_id or session.workspace_id
        runner = AGENT_RUNNER
        requested_model = body.model
        if provider_id or workspace_id:
            provider_id = provider_id or "prov_local"
            workspace_id = workspace_id or "ws_current"
            secret = WEBUI_PROVIDERS.get_secret(provider_id)
            ws = WEBUI_WORKSPACES.get(workspace_id)
            if not secret:
                raise HTTPException(
                    status_code=404, detail=f"Unknown provider: {provider_id}"
                )
            if not ws:
                raise HTTPException(
                    status_code=404, detail=f"Unknown workspace: {workspace_id}"
                )
            if (
                requested_model is None
                and provider_id != "prov_local"
                and secret.default_model
            ):
                requested_model = secret.default_model
            runner = AgentRunner(
                ollama_base=secret.base_url,
                workspace_root=ws.path,
                provider_headers=_provider_headers_for_request(secret, request, auth),
                provider_temperature=secret.default_temperature,
                email=auth.email,
                department=auth.department,
                key_id=auth.key_id,
            )
        result = await runner.run(
            instruction=body.instruction,
            history=history,
            requested_model=requested_model,
            auto_commit=body.auto_commit,
            max_steps=body.max_steps,
            user_id=auth.email,
            department=auth.department,
            key_id=auth.key_id,
            memory_store=USER_MEMORY,
        )
    except Exception as exc:
        log.exception("Agent run failed")
        result = _agent_failure_result(body.instruction)
    AGENT_SESSIONS.append_message(session_id, "assistant", result["summary"])
    updated = AGENT_SESSIONS.update_result(
        session_id,
        plan=result["plan"] or {"goal": body.instruction, "steps": []},
        result=result,
    )
    return {"session": updated, "result": result}


@app.post("/agent/run")
async def run_agent_once(
    body: AgentRunRequest,
    request: Request,
    auth: AuthContext = Depends(verify_api_key),
):
    temp = AGENT_SESSIONS.create(
        title=f"One-off run for {auth.email}",
        provider_id=body.provider_id,
        workspace_id=body.workspace_id,
    )
    AGENT_SESSIONS.append_message(temp.session_id, "user", body.instruction)
    history = [
        item.model_dump()
        for item in (AGENT_SESSIONS.get(temp.session_id) or temp).history
    ]
    try:
        provider_id = body.provider_id
        workspace_id = body.workspace_id
        runner = AGENT_RUNNER
        requested_model = body.model
        if provider_id or workspace_id:
            provider_id = provider_id or "prov_local"
            workspace_id = workspace_id or "ws_current"
            secret = WEBUI_PROVIDERS.get_secret(provider_id)
            ws = WEBUI_WORKSPACES.get(workspace_id)
            if not secret:
                raise HTTPException(
                    status_code=404, detail=f"Unknown provider: {provider_id}"
                )
            if not ws:
                raise HTTPException(
                    status_code=404, detail=f"Unknown workspace: {workspace_id}"
                )
            if (
                requested_model is None
                and provider_id != "prov_local"
                and secret.default_model
            ):
                requested_model = secret.default_model
            runner = AgentRunner(
                ollama_base=secret.base_url,
                workspace_root=ws.path,
                provider_headers=_provider_headers_for_request(secret, request, auth),
                provider_temperature=secret.default_temperature,
                email=auth.email,
                department=auth.department,
                key_id=auth.key_id,
            )
        result = await runner.run(
            instruction=body.instruction,
            history=history,
            requested_model=requested_model,
            auto_commit=body.auto_commit,
            max_steps=body.max_steps,
            user_id=auth.email,
            department=auth.department,
            key_id=auth.key_id,
            memory_store=USER_MEMORY,
        )
    except Exception as exc:
        log.exception("Agent one-off run failed")
        result = _agent_failure_result(body.instruction)
    AGENT_SESSIONS.append_message(temp.session_id, "assistant", result["summary"])
    updated = AGENT_SESSIONS.update_result(
        temp.session_id,
        plan=result["plan"] or {"goal": body.instruction, "steps": []},
        result=result,
    )
    return {"session": updated, "result": result}


@app.post("/agent/sessions/{session_id}/rollback-last-commit")
async def rollback_agent_commit(
    session_id: str, auth: AuthContext = Depends(verify_api_key)
):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    last_result = session.last_result or {}
    commits = last_result.get("commits") or []
    if not commits:
        raise HTTPException(
            status_code=400, detail="No agent commit available to roll back"
        )
    target = commits[-1]
    cwd = Path(__file__).resolve().parent
    if session.workspace_id:
        ws = WEBUI_WORKSPACES.get(session.workspace_id)
        if ws:
            cwd = Path(ws.path)
    try:
        proc = subprocess.run(
            ["git", "revert", "--no-edit", target],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail=(exc.stderr or exc.stdout or "git revert failed").strip(),
        ) from exc
    AGENT_SESSIONS.append_message(session_id, "system", f"Rolled back commit {target}")
    return {
        "status": "ok",
        "reverted_commit": target,
        "git_output": proc.stdout.strip(),
    }


# ─── Session Memory ───────────────────────────────────────────────────────────


@app.post("/agent/memory/{session_id}/snapshot")
async def memory_snapshot(session_id: str, auth: AuthContext = Depends(verify_api_key)):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    state = session.model_dump()
    path = SESSION_MEMORY.snapshot(session_id, state)
    return {"session_id": session_id, "path": str(path)}


@app.get("/agent/memory/{session_id}")
async def memory_restore(session_id: str, auth: AuthContext = Depends(verify_api_key)):
    state = SESSION_MEMORY.restore(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="No snapshot for this session")
    return state


@app.get("/agent/memory")
async def memory_list(auth: AuthContext = Depends(verify_api_key)):
    return {"snapshots": SESSION_MEMORY.list_snapshots()}


@app.delete("/agent/memory/{session_id}")
async def memory_delete(session_id: str, auth: AuthContext = Depends(verify_api_key)):
    deleted = SESSION_MEMORY.delete(session_id)
    return {"deleted": deleted}


# ─── Context Compression ──────────────────────────────────────────────────────


class ContextCompressRequest(BaseModel):
    messages: list[dict] = Field(..., min_length=1)
    strategy: str = Field(default="reactive", pattern="^(reactive|micro|inspect)$")


@app.post("/agent/context/compress")
async def context_compress(
    body: ContextCompressRequest, auth: AuthContext = Depends(verify_api_key)
):
    compressed = CTX_COMPRESSOR.compress(body.messages, strategy=body.strategy)  # type: ignore[arg-type]
    stats = CTX_COMPRESSOR.inspect(compressed)
    return {"messages": compressed, "stats": stats.as_dict()}


@app.post("/agent/context/inspect")
async def context_inspect(
    body: ContextCompressRequest, auth: AuthContext = Depends(verify_api_key)
):
    stats = CTX_COMPRESSOR.inspect(body.messages)
    needs = CTX_COMPRESSOR.needs_compression(body.messages)
    return {"stats": stats.as_dict(), "needs_compression": needs}


# ─── Conversation Surgery ─────────────────────────────────────────────────────


class HistorySnipRequest(BaseModel):
    indices: list[int] = Field(..., min_length=1)


@app.post("/agent/sessions/{session_id}/snip")
async def history_snip(
    session_id: str,
    body: HistorySnipRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    """Remove specific messages from session history by index."""
    indices_set = set(body.indices)
    with AGENT_SESSIONS._lock:
        s = AGENT_SESSIONS._sessions.get(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Unknown session")
        kept = [msg for i, msg in enumerate(s.history) if i not in indices_set]
        removed = len(s.history) - len(kept)
        s.history = kept
        remaining = len(kept)
    return {"removed": removed, "remaining": remaining}


# ─── Adaptive Permissions ─────────────────────────────────────────────────────


@app.get("/agent/sessions/{session_id}/permissions")
async def session_permissions(
    session_id: str, auth: AuthContext = Depends(verify_api_key)
):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    msgs = [m.model_dump() for m in session.history]
    assessment = PERMISSIONS.assess(msgs)
    return assessment.as_dict()


# ─── Token Budget ─────────────────────────────────────────────────────────────


class BudgetSetRequest(BaseModel):
    cap: int = Field(..., ge=1)


@app.put("/agent/budget/{session_id}")
async def budget_set(
    session_id: str, body: BudgetSetRequest, auth: AuthContext = Depends(verify_api_key)
):
    usage = TOKEN_BUDGET.set_cap(session_id, body.cap)
    return usage.as_dict()


@app.get("/agent/budget/{session_id}")
async def budget_get(session_id: str, auth: AuthContext = Depends(verify_api_key)):
    usage = TOKEN_BUDGET.get(session_id)
    if usage is None:
        raise HTTPException(status_code=404, detail="No budget set for this session")
    return usage.as_dict()


@app.get("/agent/budget")
async def budget_list(auth: AuthContext = Depends(verify_api_key)):
    return {"budgets": [u.as_dict() for u in TOKEN_BUDGET.list_all()]}


# ─── Multi-Agent Coordinator ──────────────────────────────────────────────────


class CoordinateRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    workers: list[dict] = Field(default_factory=list, max_length=10)
    agents: list[dict] = Field(default_factory=list, max_length=20)
    tasks: list[dict] = Field(default_factory=list, max_length=50)
    max_concurrent: int = Field(default=3, ge=1, le=10)


@app.post("/agent/coordinate")
async def coordinate(
    body: CoordinateRequest, auth: AuthContext = Depends(verify_api_key)
):
    if body.tasks:
        agents = [
            AgentSpec(
                agent_id=a.get("agent_id", a.get("id", f"agent-{i}")),
                role=a.get("role", "worker"),
                capabilities=list(a.get("capabilities") or ["general"]),
                model=a.get("model"),
                max_parallel_tasks=int(a.get("max_parallel_tasks", 1)),
            )
            for i, a in enumerate(
                body.agents
                or [
                    {
                        "agent_id": "default-worker",
                        "capabilities": ["general", "code", "research", "writing"],
                    }
                ]
            )
        ]
        tasks = [
            TaskSpec(
                task_id=t.get("task_id", t.get("id", f"task-{i}")),
                instruction=t["instruction"],
                task_type=t.get("task_type", t.get("type", "general")),
                dependencies=list(t.get("dependencies") or []),
                priority=int(t.get("priority", 0)),
                model=t.get("model"),
                max_steps=int(t.get("max_steps", 3)),
                retry_limit=int(t.get("retry_limit", 1)),
            )
            for i, t in enumerate(body.tasks)
        ]
        swarm = MultiAgentSwarm(
            ollama_base=OLLAMA_BASE, workspace_root=str(Path(__file__).resolve().parent)
        )
        result = await swarm.run(
            goal=body.goal,
            agents=agents,
            tasks=tasks,
            max_concurrent=body.max_concurrent,
            email=auth.email,
            department=auth.department,
            key_id=auth.key_id,
        )
        return result.as_dict()

    if not body.workers:
        raise HTTPException(
            status_code=400, detail="Provide either workers or dependency-aware tasks"
        )
    specs = [
        WorkerSpec(
            worker_id=w.get("worker_id", f"w{i}"),
            instruction=w["instruction"],
            model=w.get("model"),
            max_steps=int(w.get("max_steps", 3)),
        )
        for i, w in enumerate(body.workers)
    ]
    result = await COORDINATOR.run(
        body.goal,
        specs,
        max_concurrent=body.max_concurrent,
        email=auth.email,
        department=auth.department,
        key_id=auth.key_id,
    )
    return result.as_dict()


# ─── Background Agent ─────────────────────────────────────────────────────────


class BackgroundTaskRequest(BaseModel):
    kind: str = Field(default="manual", max_length=64)
    payload: dict = Field(default_factory=dict)


@app.post("/agent/background/tasks")
async def background_submit(
    body: BackgroundTaskRequest, auth: AuthContext = Depends(verify_api_key)
):
    task = BACKGROUND_AGENT.create_and_submit(kind=body.kind, payload=body.payload)
    return task.as_dict()


@app.get("/agent/background/tasks")
async def background_list(
    status: Optional[str] = None,
    auth: AuthContext = Depends(verify_api_key),
):
    tasks = BACKGROUND_AGENT.list_tasks(status=status)
    return {"tasks": [t.as_dict() for t in tasks]}


@app.get("/agent/background/tasks/{task_id}")
async def background_get(task_id: str, auth: AuthContext = Depends(verify_api_key)):
    task = BACKGROUND_AGENT.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.as_dict()


# ─── Scheduled Jobs ───────────────────────────────────────────────────────────


class ScheduleJobRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    cron: str = Field(..., min_length=9, max_length=100)
    instruction: str = Field(..., min_length=1, max_length=4000)
    agent_id: Optional[str] = Field(default=None, max_length=64)
    runtime_id: Optional[str] = Field(default=None, max_length=64)
    model: Optional[str] = Field(default=None, max_length=200)
    task_type: str = Field(default="scheduled", max_length=64)
    requires_approval: bool = False
    tags: list[str] = Field(default_factory=list)


@app.post("/agent/scheduler/jobs")
async def scheduler_create(
    body: ScheduleJobRequest, auth: AuthContext = Depends(verify_api_key)
):
    job = SCHEDULER.create(
        name=body.name,
        cron=body.cron,
        instruction=body.instruction,
        agent_id=body.agent_id,
        runtime_id=body.runtime_id,
        model=body.model,
        task_type=body.task_type,
        requires_approval=body.requires_approval,
        tags=body.tags,
    )
    return job.as_dict()


@app.get("/agent/scheduler/jobs")
async def scheduler_list(auth: AuthContext = Depends(verify_api_key)):
    return {"jobs": [j.as_dict() for j in SCHEDULER.list()]}


@app.get("/agent/scheduler/jobs/{job_id}")
async def scheduler_get(job_id: str, auth: AuthContext = Depends(verify_api_key)):
    job = SCHEDULER.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.as_dict()


@app.post("/agent/scheduler/jobs/{job_id}/trigger")
async def scheduler_trigger(job_id: str, auth: AuthContext = Depends(verify_api_key)):
    try:
        job = SCHEDULER.trigger(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.as_dict()


@app.delete("/agent/scheduler/jobs/{job_id}")
async def scheduler_delete(job_id: str, auth: AuthContext = Depends(verify_api_key)):
    deleted = SCHEDULER.delete(job_id)
    return {"deleted": deleted}


class SchedulerToggleRequest(BaseModel):
    status: str = Field(..., pattern="^(active|paused)$")


@app.patch("/agent/scheduler/jobs/{job_id}")
async def scheduler_toggle(
    job_id: str, body: SchedulerToggleRequest, auth: AuthContext = Depends(verify_api_key)
):
    try:
        job = SCHEDULER.toggle(job_id, enabled=(body.status == "active"))
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.as_dict()


# ─── Automation Playbooks ─────────────────────────────────────────────────────


class PlaybookRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    steps: list[dict] = Field(..., min_length=1, max_length=20)
    tags: list[str] = Field(default_factory=list)


@app.post("/agent/playbooks")
async def playbook_register(
    body: PlaybookRegisterRequest, auth: AuthContext = Depends(verify_api_key)
):
    pb = PLAYBOOKS.register(
        name=body.name,
        description=body.description,
        steps=body.steps,
        tags=body.tags,
    )
    return pb.as_dict()


@app.get("/agent/playbooks")
async def playbook_list(
    tag: Optional[str] = None, auth: AuthContext = Depends(verify_api_key)
):
    return {"playbooks": [p.as_dict() for p in PLAYBOOKS.list(tag=tag)]}


@app.get("/agent/playbooks/{playbook_id}")
async def playbook_get(playbook_id: str, auth: AuthContext = Depends(verify_api_key)):
    pb = PLAYBOOKS.get(playbook_id)
    if pb is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return pb.as_dict()


@app.delete("/agent/playbooks/{playbook_id}")
async def playbook_delete(
    playbook_id: str, auth: AuthContext = Depends(verify_api_key)
):
    deleted = PLAYBOOKS.delete(playbook_id)
    return {"deleted": deleted}


@app.post("/agent/playbooks/{playbook_id}/run")
async def playbook_run(playbook_id: str, auth: AuthContext = Depends(verify_api_key)):
    try:
        run = PLAYBOOKS.start_run(playbook_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Playbook not found")
    playbook = PLAYBOOKS.get(playbook_id)
    created_task_ids: list[str] = []
    if playbook:
        for step in playbook.steps:
            task = await TASK_AUTOMATION.create_playbook_task(
                owner_id=auth.email,
                playbook_id=playbook.playbook_id,
                run_id=run.run_id,
                playbook_name=playbook.name,
                step_id=step.step_id,
                instruction=step.instruction,
                model=step.model,
                tags=list(playbook.tags),
            )
            created_task_ids.append(task.task_id)
        PLAYBOOKS.finish_run(
            run.run_id,
            step_results=[
                {"step_id": step.step_id, "task_id": task_id}
                for step, task_id in zip(playbook.steps, created_task_ids)
            ],
            created_task_ids=created_task_ids,
            status="running",
        )
        run = PLAYBOOKS.get_run(run.run_id) or run
    return run.as_dict()


@app.get("/agent/playbooks/{playbook_id}/runs")
async def playbook_runs(playbook_id: str, auth: AuthContext = Depends(verify_api_key)):
    return {"runs": [r.as_dict() for r in PLAYBOOKS.list_runs(playbook_id=playbook_id)]}


# ─── Resource Watchdog ────────────────────────────────────────────────────────


class WatchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kind: str = Field(..., pattern="^(url|file)$")
    target: str = Field(..., min_length=1, max_length=2000)
    action: str = Field(default="", max_length=500)


@app.post("/agent/watchdog/resources")
async def watchdog_add(body: WatchRequest, auth: AuthContext = Depends(verify_api_key)):
    resource = WATCHDOG.watch(
        name=body.name, kind=body.kind, target=body.target, action=body.action
    )
    return resource.as_dict()


@app.get("/agent/watchdog/resources")
async def watchdog_list(auth: AuthContext = Depends(verify_api_key)):
    return {"resources": [r.as_dict() for r in WATCHDOG.list()]}


@app.delete("/agent/watchdog/resources/{resource_id}")
async def watchdog_remove(
    resource_id: str, auth: AuthContext = Depends(verify_api_key)
):
    removed = WATCHDOG.unwatch(resource_id)
    return {"removed": removed}


@app.post("/agent/watchdog/resources/{resource_id}/check")
async def watchdog_check(resource_id: str, auth: AuthContext = Depends(verify_api_key)):
    event = WATCHDOG.check_once(resource_id)
    return {"changed": event is not None, "event": event.as_dict() if event else None}


# ─── Project Scaffolding ──────────────────────────────────────────────────────


class ScaffoldRequest(BaseModel):
    template: str = Field(..., min_length=1, max_length=200)
    target_dir: str = Field(..., min_length=1, max_length=500)
    overwrite: bool = False


@app.get("/agent/scaffolding/templates")
async def scaffolding_list(auth: AuthContext = Depends(verify_api_key)):
    return {"templates": [t.as_dict() for t in SCAFFOLDER.list()]}


@app.post("/agent/scaffolding/apply")
async def scaffolding_apply(
    body: ScaffoldRequest, auth: AuthContext = Depends(verify_api_key)
):
    result = SCAFFOLDER.apply(body.template, body.target_dir, overwrite=body.overwrite)
    return result.as_dict()


# ─── Skill Library ────────────────────────────────────────────────────────────


class MpcSkillRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    content: str = Field(default="", max_length=50000)
    tags: list[str] = Field(default_factory=list)


@app.get("/agent/skills")
async def skills_list(
    source: Optional[str] = None, auth: AuthContext = Depends(verify_api_key)
):
    return {"skills": [s.as_dict() for s in SKILL_LIBRARY.list(source=source)]}


@app.get("/agent/skills/search")
async def skills_search(q: str, auth: AuthContext = Depends(verify_api_key)):
    return {"skills": [s.as_dict() for s in SKILL_LIBRARY.search(q)]}


@app.post("/agent/skills/mcp")
async def skills_register_mcp(
    body: MpcSkillRequest, auth: AuthContext = Depends(verify_api_key)
):
    skill = SKILL_LIBRARY.register_mcp(
        name=body.name,
        description=body.description,
        content=body.content,
        tags=body.tags,
    )
    return skill.as_dict()


# ─── AI Commit Tracking ───────────────────────────────────────────────────────


@app.get("/agent/commits")
async def commit_log(limit: int = 10, auth: AuthContext = Depends(verify_api_key)):
    entries = COMMIT_TRACKER.log(limit=min(limit, 100))
    return {"commits": entries}


# ─── Terminal Panel ───────────────────────────────────────────────────────────


@app.get("/agent/terminal/snapshot")
async def terminal_snapshot(auth: AuthContext = Depends(verify_api_key)):
    snap = TERMINAL_PANEL.snapshot()
    return snap.as_dict()


class TerminalRunRequest(BaseModel):
    command: list[str] = Field(..., min_length=1, max_length=20)
    timeout: int = Field(default=30, ge=1, le=120)


@app.post("/agent/terminal/run")
async def terminal_run(
    body: TerminalRunRequest, auth: AuthContext = Depends(verify_api_key)
):
    return TERMINAL_PANEL.run_and_capture(body.command, timeout=body.timeout)


# ─── Browser Automation ───────────────────────────────────────────────────────


class BrowserActionRequest(BaseModel):
    action: str = Field(
        ..., pattern="^(navigate|click|fill|screenshot|evaluate|get_state)$"
    )
    url: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    path: Optional[str] = None
    expression: Optional[str] = None


@app.post("/agent/browser/action")
async def browser_action(
    body: BrowserActionRequest, auth: AuthContext = Depends(verify_api_key)
):
    if not BROWSER_SESSION.available:
        return {
            "available": False,
            "hint": "pip install playwright && playwright install chromium",
        }
    if body.action == "navigate" and body.url:
        result = await BROWSER_SESSION.navigate(body.url)
    elif body.action == "click" and body.selector:
        result = await BROWSER_SESSION.click(body.selector)
    elif body.action == "fill" and body.selector and body.value is not None:
        result = await BROWSER_SESSION.fill(body.selector, body.value)
    elif body.action == "screenshot" and body.path:
        result = await BROWSER_SESSION.screenshot(body.path)
    elif body.action == "evaluate" and body.expression:
        result = await BROWSER_SESSION.evaluate(body.expression)
    elif body.action == "get_state":
        state = await BROWSER_SESSION.get_state()
        return (
            state.as_dict()
            if state
            else {"url": None, "title": None, "content_preview": ""}
        )
    else:
        raise HTTPException(
            status_code=400, detail="Invalid action or missing required parameters"
        )
    return result.as_dict()


@app.post("/agent/browser/start")
async def browser_start(auth: AuthContext = Depends(verify_api_key)):
    await BROWSER_SESSION.start()
    return {"started": True, "available": BROWSER_SESSION.available}


@app.post("/agent/browser/stop")
async def browser_stop(auth: AuthContext = Depends(verify_api_key)):
    await BROWSER_SESSION.stop()
    return {"stopped": True}


# ─── Voice Commands ───────────────────────────────────────────────────────────


class VoiceTranscribeRequest(BaseModel):
    audio_b64: str = Field(..., description="Base64-encoded raw PCM audio bytes")
    duration_hint_s: float = Field(default=5.0, ge=0.1, le=60.0)


@app.get("/agent/voice/status")
async def voice_status(auth: AuthContext = Depends(verify_api_key)):
    return {
        "mic_available": VOICE_INTERFACE.mic_available,
        "whisper_url": bool(VOICE_INTERFACE._whisper_url),
    }


@app.post("/agent/voice/transcribe")
async def voice_transcribe(
    body: VoiceTranscribeRequest, auth: AuthContext = Depends(verify_api_key)
):
    import base64

    try:
        audio_bytes = base64.b64decode(body.audio_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")
    result = VOICE_INTERFACE.transcribe(audio_bytes)
    return result.as_dict()


# ─── Streaming proxy helper ─────────────────────────────────────────────────────


async def stream_response(
    url: str, method: str, headers: dict, body: bytes
) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream(method, url, content=body, headers=headers) as resp:
            if resp.status_code >= 400:
                content = await resp.aread()
                yield content
                return
            async for chunk in resp.aiter_bytes(chunk_size=512):
                yield chunk


async def proxy_request(
    request: Request, target_path: str, auth: Optional[AuthContext] = None
):
    body = await request.body()
    content_type = request.headers.get("content-type", "application/json")

    # Determine if client wants streaming
    is_stream = False
    if body:
        try:
            payload = json.loads(body)
            is_stream = bool(payload.get("stream", False))
        except (json.JSONDecodeError, AttributeError):
            pass

    target_url = f"{OLLAMA_BASE}/{target_path}"
    forward_headers = {"Content-Type": content_type}

    log.info("→ %s %s (stream=%s)", request.method, target_path, is_stream)
    start_time = time.perf_counter()

    if is_stream:
        return StreamingResponse(
            stream_response(target_url, request.method, forward_headers, body),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
    else:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0)
        ) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=forward_headers,
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        response_content_type = resp.headers.get("content-type", "")
        is_json_response = response_content_type.startswith("application/json")
        data = resp.json() if is_json_response else resp.content

        # Track legacy generation/completion usage
        if (
            auth
            and target_path in ("api/generate", "v1/completions")
            and request.method == "POST"
        ):
            try:
                payload = json.loads(body)
                model = payload.get("model", "unknown")
                prompt = payload.get("prompt", "")

                out_text = ""
                pt = 0
                ct = 0

                if target_path == "api/generate" and isinstance(data, dict):
                    out_text = data.get("response", "")
                    pt = int(data.get("prompt_eval_count") or 0)
                    ct = int(data.get("eval_count") or 0)
                elif target_path == "v1/completions" and isinstance(data, dict):
                    choices = data.get("choices", [])
                    if choices and isinstance(choices[0], dict):
                        out_text = choices[0].get("text", "")
                    usage = data.get("usage", {})
                    pt = int(usage.get("prompt_tokens") or 0)
                    ct = int(usage.get("completion_tokens") or 0)

                if out_text:
                    await asyncio.to_thread(
                        emit_chat_observation,
                        email=auth.email,
                        department=auth.department,
                        key_id=auth.key_id,
                        model=model,
                        messages=[{"role": "user", "content": prompt}]
                        if isinstance(prompt, str)
                        else prompt,
                        output_text=out_text,
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        latency_ms=duration_ms,
                        task_name="generation",
                    )
            except Exception as exc:
                log.debug("Trackable proxy observation failed: %s", exc)

        if is_json_response:
            return JSONResponse(
                content=data,
                status_code=resp.status_code,
            )

        passthrough_headers = {}
        if response_content_type:
            passthrough_headers["Content-Type"] = response_content_type

        return Response(
            content=data,
            status_code=resp.status_code,
            headers=passthrough_headers,
        )


# ─── Anthropic Messages API (/v1/messages) ─────────────────────────────────────
# Enables Claude Code CLI (set ANTHROPIC_BASE_URL=https://your-tunnel-url)


@app.post("/v1/messages")
async def anthropic_messages(
    request: Request, auth: AuthContext = Depends(verify_api_key)
):
    """Anthropic Messages API — translates to Ollama OpenAI-compat internally."""
    return await handle_anthropic_messages(
        request=request,
        ollama_base=OLLAMA_BASE,
        email=auth.email,
        department=auth.department,
        key_id=auth.key_id,
    )


@app.post("/v1/messages/count_tokens")
async def anthropic_count_tokens(
    request: Request, auth: AuthContext = Depends(verify_api_key)
):
    """Anthropic token counting endpoint.

    Estimates how many input tokens the given messages would consume.
    Used by Claude Code CLI for preflight context-size checks.
    Returns: {"input_tokens": N}
    """
    return await handle_count_tokens(request=request)


@app.get("/v1/models")
async def list_models_openai(auth: AuthContext = Depends(verify_api_key)):
    """List available models — union of live Ollama models and the router registry."""
    from router.registry import get_registry

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
        ollama_models = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        ollama_models = []

    registry = get_registry()
    ollama_set = set(ollama_models)

    # Models known to Ollama
    local_entries = [
        {"id": name, "object": "model", "owned_by": "ollama"} for name in ollama_models
    ]
    # Registry models not already reported by Ollama (e.g. not yet pulled)
    registry_only = []
    alias_entries = []
    for name, cap in registry.items():
        if name in ollama_set:
            continue
        if "alias" in (cap.tags or []):
            alias_entries.append({
                "id": name,
                "object": "model",
                "owned_by": "llm-relay-alias",
                "description": "Alias → routed to best available local model",
            })
        else:
            registry_only.append({"id": name, "object": "model", "owned_by": "router-registry"})
    return {"object": "list", "data": local_entries + registry_only + alias_entries}


# ─── Ollama native routes (/api/*) ─────────────────────────────────────────────


class PingResponse(BaseModel):
    status: str
    timestamp: str


@app.get("/api/ping", response_model=PingResponse)
async def api_ping():
    from datetime import datetime, timezone
    return PingResponse(status="ok", timestamp=datetime.now(timezone.utc).isoformat())


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ollama_api(
    path: str, request: Request, auth: AuthContext = Depends(verify_api_key)
):
    if path == "chat" and request.method == "POST":
        return await handle_ollama_native_chat(
            request=request,
            ollama_base=OLLAMA_BASE,
            email=auth.email,
            department=auth.department,
            key_id=auth.key_id,
        )
    return await proxy_request(request, f"api/{path}", auth=auth)


# ─── OpenAI-compatible routes (/v1/*) ──────────────────────────────────────────
# Ollama natively serves OpenAI-compatible endpoints at /v1/*


@app.post("/v1/workflow/chat")
async def workflow_ide_chat(
    request: Request,
    auth: AuthContext = Depends(verify_api_key),
):
    """OpenAI-compatible chat endpoint that detects CRISPY workflow triggers.

    IDEs (Continue, Cursor, Cline, etc.) can call this endpoint with model
    ``crispy-workflow`` to trigger a full CRISPY build workflow and receive
    SSE-streamed status updates as if the assistant is typing a reply.

    Trigger syntax (first user message):
      @build <task description>
      @workflow <task description>
      /crispy <task description>

    Any other request is forwarded transparently to the normal chat handler.
    """
    return await handle_workflow_ide_chat(
        request=request,
        engine=WORKFLOW_ENGINE,
        ollama_base=OLLAMA_BASE,
        email=auth.email,
        department=auth.department,
        key_id=auth.key_id,
    )


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def openai_compat(
    path: str, request: Request, auth: AuthContext = Depends(verify_api_key)
):
    # /v1/models: inject crispy-workflow into the model list so IDEs can see it.
    if path == "models" and request.method == "GET":
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{OLLAMA_BASE}/v1/models")
                data = r.json()
        except Exception:
            data = {"object": "list", "data": []}
        # Inject the crispy-workflow pseudo-model
        existing_ids = {m.get("id", "") for m in data.get("data", [])}
        if "crispy-workflow" not in existing_ids:
            data.setdefault("data", []).insert(
                0,
                {
                    "id": "crispy-workflow",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "crispy-engine",
                    "description": (
                        "CRISPY deterministic workflow engine. "
                        "Use @build, @workflow, or /crispy prefix to trigger a build workflow."
                    ),
                },
            )
        return JSONResponse(content=data)
    if path == "chat/completions" and request.method == "POST":
        body_bytes = await request.body()
        try:
            payload_peek = json.loads(body_bytes) if body_bytes else {}
        except Exception:
            payload_peek = {}

        if payload_peek.get("model") == "crispy-workflow":
            return await handle_workflow_ide_chat(
                request=request,
                engine=WORKFLOW_ENGINE,
                ollama_base=OLLAMA_BASE,
                email=auth.email,
                department=auth.department,
                key_id=auth.key_id,
                body_override=body_bytes,
            )

        return await handle_openai_chat_completions(
            request=request,
            ollama_base=OLLAMA_BASE,
            email=auth.email,
            department=auth.department,
            key_id=auth.key_id,
            body_override=body_bytes,
        )
    return await proxy_request(request, f"v1/{path}", auth=auth)


# ─── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    log.info("Starting LLM Relay v4.0 Control Plane on port %d", PROXY_PORT)
    log.info(
        "Loaded %d env API key(s), %d key-store key(s)",
        len(VALID_API_KEYS),
        len(KEY_STORE),
    )
    uvicorn.run(
        "proxy:app", host="0.0.0.0", port=PROXY_PORT, log_level=LOG_LEVEL.lower()  # nosec: B104 - Binding to all interfaces is required for external access
    )

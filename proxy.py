"""
Qwen3-Coder Authenticated Proxy
--------------------------------
Sits in front of Ollama, adds Bearer token auth, rate limiting, CORS,
and full streaming support. Exposes both:
  - Ollama native API  (/api/*)
  - OpenAI-compatible API (/v1/*)  ← works with Cursor, Continue, Aider, etc.
"""

import os
import sys
import json
import time
import logging
import hashlib
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any config reads (uvicorn does not load .env by default).
load_dotenv()
from collections import defaultdict
from dataclasses import dataclass
from typing import AsyncIterator

import httpx
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from starlette.middleware.sessions import SessionMiddleware

from admin_auth import AdminAuthManager, AdminIdentity
from admin_gui import register_admin_gui
from agent.loop import AgentRunner
from agent.models import AgentRunRequest, AgentSessionCreateRequest
from agent.state import AgentSessionStore
from chat_handlers import handle_ollama_native_chat, handle_openai_chat_completions
from handlers.anthropic_compat import handle_anthropic_messages
from key_store import issue_new_api_key, load_key_store
from service_manager import WindowsServiceManager

# ─── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE    = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
PROXY_PORT     = int(os.environ.get("PROXY_PORT", "8000"))
RAW_KEYS       = os.environ.get("API_KEYS", "")
VALID_API_KEYS = set(k.strip() for k in RAW_KEYS.split(",") if k.strip())
KEY_STORE      = load_key_store()
RATE_LIMIT_RPM = int(os.environ.get("RATE_LIMIT_RPM", "60"))   # requests per minute per key
LOG_LEVEL      = os.environ.get("LOG_LEVEL", "INFO")


def _strip_quoted_env(name: str) -> str:
    raw = os.environ.get(name, "") or ""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1].strip()
    return v


ADMIN_SECRET = _strip_quoted_env("ADMIN_SECRET")
WEAK_ADMIN_SECRETS = frozenset({
    "change-me",
    "admin",
    "password",
    "secret",
    "your-admin-secret",
})
# Comma-separated origins, or * (default). Example: https://app.example.com,https://other.com
_raw_cors = os.environ.get("CORS_ORIGINS", "*").strip()
CORS_ORIGINS = [o.strip() for o in _raw_cors.split(",") if o.strip()] or ["*"]

# Refuse example / default keys from .env templates (must not be used in production)
WEAK_API_KEYS = frozenset({
    "change-me",
    "your-secret-key-here",
    "YOUR_API_KEY",
    "optional-second-key-for-another-device",
})

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("qwen-proxy")

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
    key_id: str | None
    source: str  # "store" | "legacy"

# ─── Rate limiter (in-memory, per key) ─────────────────────────────────────────

_rate_buckets: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(api_key: str) -> None:
    now = time.time()
    window = 60.0
    bucket = _rate_buckets[api_key]
    # Drop entries outside the 1-minute window
    _rate_buckets[api_key] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[api_key]) >= RATE_LIMIT_RPM:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_RPM} req/min. Slow down."
        )
    _rate_buckets[api_key].append(now)

# ─── Auth dependency ────────────────────────────────────────────────────────────

def verify_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> AuthContext:
    """Accept both Authorization: Bearer <key> (standard) and x-api-key: <key> (Claude Code)."""
    key = ""
    if x_api_key:
        key = x_api_key.strip()
    elif authorization:
        if authorization.startswith("Bearer "):
            key = authorization[7:].strip()
        else:
            key = authorization.strip()

    if not key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Set Authorization: Bearer <key> or x-api-key: <key>",
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
    log.warning("Rejected request with invalid API key")
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


def _require_admin(x_admin_secret: str | None, authorization: str | None) -> None:
    if not ADMIN_SECRET:
        raise HTTPException(status_code=404, detail="Not Found")
    got = (x_admin_secret or "").strip()
    if not got and authorization and authorization.startswith("Bearer "):
        got = authorization[7:].strip()
    if got != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _get_admin_identity_from_request(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AdminIdentity:
    token = ""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    session = ADMIN_AUTH.sessions.get(token) if token else None
    if session:
        return session.identity
    if request.session.get("admin_ok"):
        username = str(request.session.get("admin_user") or "admin")
        source = str(request.session.get("admin_auth_source") or "session")
        return AdminIdentity(username=username, auth_source=source)
    raise HTTPException(status_code=401, detail="Unauthorized")

# ─── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Qwen3-Coder Proxy", version="1.0.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

if ADMIN_AUTH.enabled:
    _session_seed = ADMIN_SECRET or os.environ.get("COMPUTERNAME") or str(Path(__file__).resolve())
    _session_secret = hashlib.sha256(f"qwen-admin-session:{_session_seed}".encode()).hexdigest()
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_secret,
        session_cookie="qwen_admin_session",
        max_age=60 * 60 * 24 * 7,
        same_site="lax",
    )

register_admin_gui(app, KEY_STORE, ADMIN_AUTH, SERVICE_MANAGER)
AGENT_RUNNER = AgentRunner(ollama_base=OLLAMA_BASE, workspace_root=Path(__file__).resolve().parent)
AGENT_SESSIONS = AgentSessionStore()

# ─── Health (no auth) ──────────────────────────────────────────────────────────

@app.post("/admin/keys")
async def admin_create_key(
    body: AdminCreateKeyBody,
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
    authorization: str | None = Header(default=None),
):
    """Issue a new user API key (requires ADMIN_SECRET). Plain key returned once in JSON."""
    _require_admin(x_admin_secret, authorization)
    if not KEY_STORE.is_configured():
        raise HTTPException(status_code=503, detail="KEYS_FILE is not set on the server")
    plain, rec = issue_new_api_key(KEY_STORE, body.email.strip(), body.department.strip())
    log.info("Admin issued key_id=%s email=%s department=%s", rec.key_id, rec.email, rec.department)
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
        raise HTTPException(status_code=404, detail="Admin login is not enabled")
    identity = ADMIN_AUTH.authenticate(body.username, body.password)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
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
    authorization: str | None = Header(default=None),
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    if authorization and authorization.startswith("Bearer "):
        ADMIN_AUTH.sessions.revoke(authorization[7:].strip())
    request.session.clear()
    return {"ok": True, "username": admin.username}


@app.get("/admin/api/status")
async def admin_status(admin: AdminIdentity = Depends(_get_admin_identity_from_request)):
    status = SERVICE_MANAGER.get_status()
    status["admin"] = {"username": admin.username, "auth_source": admin.auth_source}
    return status


@app.post("/admin/api/control")
async def admin_control(
    body: AdminControlBody,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    try:
        result = SERVICE_MANAGER.control(body.action, body.target, current_proxy_pid=os.getpid())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result["admin"] = {"username": admin.username}
    return result


@app.get("/admin/api/users")
async def admin_list_users(admin: AdminIdentity = Depends(_get_admin_identity_from_request)):
    if not KEY_STORE.is_configured():
        raise HTTPException(status_code=503, detail="KEYS_FILE is not set on the server")
    records = [
        {
            "key_id": rec.key_id,
            "email": rec.email,
            "department": rec.department,
            "created": rec.created,
        }
        for rec in KEY_STORE.list_records()
    ]
    return {"records": records, "count": len(records), "admin": {"username": admin.username}}


@app.post("/admin/api/users")
async def admin_create_user(
    body: AdminCreateKeyBody,
    admin: AdminIdentity = Depends(_get_admin_identity_from_request),
):
    if not KEY_STORE.is_configured():
        raise HTTPException(status_code=503, detail="KEYS_FILE is not set on the server")
    plain, rec = issue_new_api_key(KEY_STORE, body.email.strip(), body.department.strip())
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


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        return JSONResponse({"status": "ollama_down", "error": str(e)}, status_code=503)
    return {"status": "ok", "ollama": OLLAMA_BASE, "models": models}


@app.post("/agent/sessions")
async def create_agent_session(
    body: AgentSessionCreateRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    title = body.title or f"Session for {auth.email}"
    return AGENT_SESSIONS.create(title=title)


@app.get("/agent/sessions/{session_id}")
async def get_agent_session(session_id: str, auth: AuthContext = Depends(verify_api_key)):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    return session


@app.post("/agent/sessions/{session_id}/run")
async def run_agent_task(
    session_id: str,
    body: AgentRunRequest,
    auth: AuthContext = Depends(verify_api_key),
):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")

    AGENT_SESSIONS.append_message(session_id, "user", body.instruction)
    history = [item.model_dump() for item in (AGENT_SESSIONS.get(session_id) or session).history]
    try:
        result = await AGENT_RUNNER.run(
            instruction=body.instruction,
            history=history,
            requested_model=body.model,
            auto_commit=body.auto_commit,
            max_steps=body.max_steps,
        )
    except Exception as exc:
        log.exception("Agent run failed")
        result = {
            "goal": body.instruction,
            "plan": None,
            "steps": [],
            "commits": [],
            "summary": f"Agent run failed: {exc}",
            "status": "failed",
        }
    AGENT_SESSIONS.append_message(session_id, "assistant", result["summary"])
    updated = AGENT_SESSIONS.update_result(
        session_id,
        plan=result["plan"] or {"goal": body.instruction, "steps": []},
        result=result,
    )
    return {"session": updated, "result": result}


@app.post("/agent/run")
async def run_agent_once(body: AgentRunRequest, auth: AuthContext = Depends(verify_api_key)):
    temp = AGENT_SESSIONS.create(title=f"One-off run for {auth.email}")
    AGENT_SESSIONS.append_message(temp.session_id, "user", body.instruction)
    history = [item.model_dump() for item in (AGENT_SESSIONS.get(temp.session_id) or temp).history]
    try:
        result = await AGENT_RUNNER.run(
            instruction=body.instruction,
            history=history,
            requested_model=body.model,
            auto_commit=body.auto_commit,
            max_steps=body.max_steps,
        )
    except Exception as exc:
        log.exception("Agent one-off run failed")
        result = {
            "goal": body.instruction,
            "plan": None,
            "steps": [],
            "commits": [],
            "summary": f"Agent run failed: {exc}",
            "status": "failed",
        }
    AGENT_SESSIONS.append_message(temp.session_id, "assistant", result["summary"])
    updated = AGENT_SESSIONS.update_result(
        temp.session_id,
        plan=result["plan"] or {"goal": body.instruction, "steps": []},
        result=result,
    )
    return {"session": updated, "result": result}


@app.post("/agent/sessions/{session_id}/rollback-last-commit")
async def rollback_agent_commit(session_id: str, auth: AuthContext = Depends(verify_api_key)):
    session = AGENT_SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    last_result = session.last_result or {}
    commits = last_result.get("commits") or []
    if not commits:
        raise HTTPException(status_code=400, detail="No agent commit available to roll back")
    target = commits[-1]
    try:
        proc = subprocess.run(
            ["git", "revert", "--no-edit", target],
            cwd=Path(__file__).resolve().parent,
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
    return {"status": "ok", "reverted_commit": target, "git_output": proc.stdout.strip()}

# ─── Streaming proxy helper ─────────────────────────────────────────────────────

async def stream_response(url: str, method: str, headers: dict, body: bytes) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream(method, url, content=body, headers=headers) as resp:
            if resp.status_code >= 400:
                content = await resp.aread()
                yield content
                return
            async for chunk in resp.aiter_bytes(chunk_size=512):
                yield chunk

async def proxy_request(request: Request, target_path: str):
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

    if is_stream:
        return StreamingResponse(
            stream_response(target_url, request.method, forward_headers, body),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
    else:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=forward_headers,
            )
        return JSONResponse(
            content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            status_code=resp.status_code,
        )

# ─── Anthropic Messages API (/v1/messages) ─────────────────────────────────────
# Enables Claude Code CLI (set ANTHROPIC_BASE_URL=https://your-tunnel-url)

@app.post("/v1/messages")
async def anthropic_messages(request: Request, auth: AuthContext = Depends(verify_api_key)):
    """Anthropic Messages API — translates to Ollama OpenAI-compat internally."""
    return await handle_anthropic_messages(
        request=request,
        ollama_base=OLLAMA_BASE,
        email=auth.email,
        department=auth.department,
        key_id=auth.key_id,
    )


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
        {"id": name, "object": "model", "owned_by": "ollama"}
        for name in ollama_models
    ]
    # Registry models not already reported by Ollama (e.g. not yet pulled)
    registry_only = [
        {"id": name, "object": "model", "owned_by": "router-registry"}
        for name in registry
        if name not in ollama_set
    ]
    return {"object": "list", "data": local_entries + registry_only}


# ─── Ollama native routes (/api/*) ─────────────────────────────────────────────

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ollama_api(path: str, request: Request, auth: AuthContext = Depends(verify_api_key)):
    if path == "chat" and request.method == "POST":
        return await handle_ollama_native_chat(
            request=request,
            ollama_base=OLLAMA_BASE,
            email=auth.email,
            department=auth.department,
            key_id=auth.key_id,
        )
    return await proxy_request(request, f"api/{path}")

# ─── OpenAI-compatible routes (/v1/*) ──────────────────────────────────────────
# Ollama natively serves OpenAI-compatible endpoints at /v1/*

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def openai_compat(path: str, request: Request, auth: AuthContext = Depends(verify_api_key)):
    if path == "chat/completions" and request.method == "POST":
        return await handle_openai_chat_completions(
            request=request,
            ollama_base=OLLAMA_BASE,
            email=auth.email,
            department=auth.department,
            key_id=auth.key_id,
        )
    return await proxy_request(request, f"v1/{path}")

# ─── Root info ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "Qwen3-Coder Authenticated Proxy",
        "endpoints": {
            "health":         "GET  /health          (no auth)",
            "ollama_api":     "ANY  /api/*            (Bearer auth)",
            "openai_compat":  "ANY  /v1/*             (Bearer auth)",
            "agent_sessions": "POST /agent/sessions   (Bearer auth)",
            "agent_run":      "POST /agent/run        (Bearer auth)",
        },
        "docs": "Set Authorization: Bearer <your-key> on all /api/* and /v1/* requests",
        "admin_ui": "GET /admin/ui/login (Windows credentials if enabled, otherwise admin secret)",
        "admin_api": "POST /admin/api/login then call /admin/api/status, /admin/api/control, /admin/api/users",
    }

# ─── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    log.info("Starting Qwen3-Coder Proxy on port %d", PROXY_PORT)
    log.info("Loaded %d env API key(s), %d key-store key(s)", len(VALID_API_KEYS), len(KEY_STORE))
    uvicorn.run("proxy:app", host="0.0.0.0", port=PROXY_PORT, log_level=LOG_LEVEL.lower())

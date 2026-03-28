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
from collections import defaultdict
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# ─── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE    = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
PROXY_PORT     = int(os.environ.get("PROXY_PORT", "8000"))
RAW_KEYS       = os.environ.get("API_KEYS", "")
VALID_API_KEYS = set(k.strip() for k in RAW_KEYS.split(",") if k.strip())
RATE_LIMIT_RPM = int(os.environ.get("RATE_LIMIT_RPM", "60"))   # requests per minute per key
LOG_LEVEL      = os.environ.get("LOG_LEVEL", "INFO")
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

if not VALID_API_KEYS:
    log.warning("⚠  No API_KEYS set — all requests will be REJECTED. Set API_KEYS env var.")
else:
    bad = VALID_API_KEYS & WEAK_API_KEYS
    if bad:
        log.error(
            "Refusing to start: API_KEYS contains placeholder or default keys: %s. "
            "Replace with secrets from openssl / PowerShell (see .env.example).",
            ", ".join(sorted(bad)),
        )
        sys.exit(1)

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

def verify_api_key(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <key>'")
    key = authorization[7:].strip()
    if key not in VALID_API_KEYS:
        log.warning("Rejected request with invalid API key")
        raise HTTPException(status_code=403, detail="Invalid API key")
    check_rate_limit(key)
    return key

# ─── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Qwen3-Coder Proxy", version="1.0.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health (no auth) ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        return JSONResponse({"status": "ollama_down", "error": str(e)}, status_code=503)
    return {"status": "ok", "ollama": OLLAMA_BASE, "models": models}

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

# ─── Ollama native routes (/api/*) ─────────────────────────────────────────────

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ollama_api(path: str, request: Request, _key: str = Depends(verify_api_key)):
    return await proxy_request(request, f"api/{path}")

# ─── OpenAI-compatible routes (/v1/*) ──────────────────────────────────────────
# Ollama natively serves OpenAI-compatible endpoints at /v1/*

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def openai_compat(path: str, request: Request, _key: str = Depends(verify_api_key)):
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
        },
        "docs": "Set Authorization: Bearer <your-key> on all /api/* and /v1/* requests",
    }

# ─── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    log.info("Starting Qwen3-Coder Proxy on port %d", PROXY_PORT)
    log.info("Loaded %d API key(s)", len(VALID_API_KEYS))
    uvicorn.run("proxy:app", host="0.0.0.0", port=PROXY_PORT, log_level=LOG_LEVEL.lower())

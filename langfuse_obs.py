"""Optional Langfuse traces for chat requests (commercial-equivalent metadata)."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from commercial_equivalent import estimate_commercial_equivalent_usd

log = logging.getLogger("qwen-proxy")

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env_val(name: str) -> str:
    """Read env; strip whitespace and a single pair of surrounding quotes (common copy-paste)."""
    raw = os.environ.get(name, "") or ""
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1].strip()
    return v


def _langfuse_enabled() -> bool:
    return bool(_env_val("LANGFUSE_PUBLIC_KEY") and _env_val("LANGFUSE_SECRET_KEY"))


def _base_url() -> str:
    host = _env_val("LANGFUSE_BASE_URL") or _env_val("LANGFUSE_HOST")
    if not host:
        host = "https://cloud.langfuse.com"
    return host.rstrip("/")


def _truncate_for_langfuse(obj: Any, max_chars: int = 48_000) -> Any:
    """Avoid oversized payloads that make Langfuse reject the event."""
    if obj is None:
        return None
    if isinstance(obj, str):
        if len(obj) <= max_chars:
            return obj
        return obj[: max_chars - 20] + "\n…[truncated]"
    try:
        s = json.dumps(obj, default=str)
    except TypeError:
        s = str(obj)
    if len(s) <= max_chars:
        return json.loads(s) if s.startswith(("{", "[")) else s
    return s[: max_chars - 20] + "\n…[truncated]"


def get_langfuse_client():  # type: ignore[no-untyped-def]
    if not _langfuse_enabled():
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        log.warning("Langfuse env vars set but langfuse package not installed")
        return None
    host = _base_url()
    pk, sk = _env_val("LANGFUSE_PUBLIC_KEY"), _env_val("LANGFUSE_SECRET_KEY")
    try:
        fa = int(_env_val("LANGFUSE_FLUSH_AT") or "0")
        if fa > 0:
            return Langfuse(public_key=pk, secret_key=sk, host=host, flush_at=fa)
    except (TypeError, ValueError):
        pass
    return Langfuse(public_key=pk, secret_key=sk, host=host)


def test_langfuse_connection() -> tuple[bool, str]:
    """Ping Langfuse API with project keys (Basic auth: public_key, secret_key)."""
    if not _langfuse_enabled():
        return False, "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set"
    base = _base_url()
    pk, sk = _env_val("LANGFUSE_PUBLIC_KEY"), _env_val("LANGFUSE_SECRET_KEY")
    health_paths = ("/api/public/health", "/api/public/projects")
    last_err = ""
    for path in health_paths:
        try:
            r = httpx.get(
                f"{base}{path}",
                auth=(pk, sk),
                timeout=15.0,
            )
            if r.status_code == 200:
                return True, f"OK {path} ({base})"
            last_err = f"{path}: HTTP {r.status_code} {r.text[:200]}"
        except Exception as e:
            last_err = f"{path}: {e}"
    return False, last_err or "request failed"


def _department_trace_tags(department: str) -> list[str]:
    d = (department or "").strip().replace(" ", "-")
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in d)[:64]
    if not slug:
        slug = "unknown"
    return [f"dept:{slug}"]


def _emit_langfuse_http(
    *,
    email: str,
    department: str,
    key_id: str | None,
    model: str,
    messages: Any,
    output_text: str,
    prompt_tokens: int,
    completion_tokens: int,
    meta: dict[str, Any],
) -> None:
    base = _base_url()
    pk, sk = _env_val("LANGFUSE_PUBLIC_KEY"), _env_val("LANGFUSE_SECRET_KEY")
    trace_id = str(uuid.uuid4())
    gen_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    trace_body: dict[str, Any] = {
        "id": trace_id,
        "timestamp": now,
        "name": "chat-completion",
        "userId": email,
        "metadata": {"department": department},
        "tags": _department_trace_tags(department),
    }
    gen_body: dict[str, Any] = {
        "id": gen_id,
        "traceId": trace_id,
        "name": "chat completion",
        "startTime": now,
        "endTime": now,
        "model": model or "unknown",
        "input": _truncate_for_langfuse(messages),
        "output": _truncate_for_langfuse(output_text),
        "metadata": meta,
        "usage": {
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": prompt_tokens + completion_tokens,
            "unit": "TOKENS",
        },
    }

    with httpx.Client(timeout=30.0) as client:
        t = client.post(f"{base}/api/public/traces", json=trace_body, auth=(pk, sk))
        if t.status_code >= 400:
            raise RuntimeError(f"trace HTTP {t.status_code}: {t.text[:500]}")
        g = client.post(f"{base}/api/public/generations", json=gen_body, auth=(pk, sk))
        if g.status_code >= 400:
            raise RuntimeError(f"generation HTTP {g.status_code}: {g.text[:500]}")


def _emit_sdk(
    lf: Any,
    *,
    email: str,
    department: str,
    model: str,
    messages: Any,
    output_text: str,
    prompt_tokens: int,
    completion_tokens: int,
    meta: dict[str, Any],
) -> None:
    msg_in = _truncate_for_langfuse(messages)
    out = _truncate_for_langfuse(output_text)
    try:
        trace = lf.trace(
            name="chat-completion",
            user_id=email,
            metadata={"department": department},
            tags=_department_trace_tags(department),
        )
    except TypeError:
        trace = lf.trace(
            name="chat-completion",
            user_id=email,
            metadata={"department": department},
        )
    trace.generation(
        name="chat completion",
        model=model or "unknown",
        input=msg_in,
        output=out,
        usage={
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        },
        metadata=meta,
    )
    lf.flush()


def emit_chat_observation(
    *,
    email: str,
    department: str,
    key_id: str | None,
    model: str,
    messages: Any,
    output_text: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int = 0,
    ttft_ms: int = 0,
) -> None:
    """Record one generation in Langfuse (SDK first, then REST fallback).

    Args:
        latency_ms:  Total wall-clock time from request receipt to last byte (ms).
        ttft_ms:     Time to first token (ms). 0 if not measured.
    """
    if not _langfuse_enabled():
        return
    cost_usd, eq = estimate_commercial_equivalent_usd(model, prompt_tokens, completion_tokens)

    # Real infrastructure cost (electricity + amortised hardware)
    infra_meta: dict[str, Any] = {}
    if latency_ms > 0:
        try:
            from infra_cost import compute_request_cost
            infra = compute_request_cost(latency_ms)
            infra_meta = infra.as_dict()
        except Exception:
            pass

    tokens_per_sec = 0.0
    if latency_ms > 0 and completion_tokens > 0:
        tokens_per_sec = round(completion_tokens / (latency_ms / 1000.0), 2)

    meta: dict[str, Any] = {
        "department": department,
        "local_model": model,
        "estimated_commercial_equivalent_usd": round(cost_usd, 6),
        "estimated_savings_vs_commercial_usd": round(cost_usd, 6),
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "tokens_per_sec": tokens_per_sec,
        **infra_meta,
    }
    if key_id:
        meta["key_id"] = key_id
    if eq:
        meta["commercial_reference_model"] = eq.commercial_name

    use_http = _env_val("LANGFUSE_USE_HTTP_ONLY").lower() in ("1", "true", "yes")
    if use_http:
        try:
            _emit_langfuse_http(
                email=email,
                department=department,
                key_id=key_id,
                model=model,
                messages=messages,
                output_text=output_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                meta=meta,
            )
        except Exception as e:
            log.warning("Langfuse HTTP-only emit failed: %s", e)
        return

    lf = get_langfuse_client()
    if lf is None:
        return
    try:
        _emit_sdk(
            lf,
            email=email,
            department=department,
            model=model,
            messages=messages,
            output_text=output_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            meta=meta,
        )
    except Exception as e:
        log.info("Langfuse SDK emit failed, trying HTTP API: %s", e)
        try:
            _emit_langfuse_http(
                email=email,
                department=department,
                key_id=key_id,
                model=model,
                messages=messages,
                output_text=output_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                meta=meta,
            )
        except Exception as e2:
            log.warning("Langfuse HTTP fallback failed: %s", e2)

#!/usr/bin/env python3
"""Lightweight OpenAI-compatible agent runtime wrapper.

Each runtime (hermes, opencode, goose, aider) is a FastAPI service that:
1. Exposes /v1/chat/completions (OpenAI format)
2. Routes to a configured backend model
3. Reports health on /health
"""

from __future__ import annotations

import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Agent Runtime")

# Get config from environment
RUNTIME_NAME = os.environ.get("RUNTIME_NAME", "unknown")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
OLLAMA_FALLBACK_BASE = os.environ.get(
    "OLLAMA_FALLBACK_BASE", "http://host.docker.internal:11434"
)
# Nvidia NIM free cloud — priority 1 when API key is present
_NVIDIA_KEY = (os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey") or "").strip()
_NVIDIA_BASE = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
_NVIDIA_DEFAULT_MODEL = os.environ.get("NVIDIA_DEFAULT_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")

# Resolve the effective default model: prefer Nvidia NIM when key is present
DEFAULT_MODEL = os.environ.get(
    "DEFAULT_MODEL",
    _NVIDIA_DEFAULT_MODEL if _NVIDIA_KEY else "qwen3-coder:30b",
)
TASK_RESULTS: dict[str, dict] = {}


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 2048


class Choice(BaseModel):
    message: Message
    finish_reason: str = "stop"
    index: int = 0


class ChatResponse(BaseModel):
    id: str = "chatcmpl-local"
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: dict


class RuntimeTaskRequest(BaseModel):
    task_id: str
    instruction: str
    task_type: str = "general"
    workspace_path: str | None = None
    model: str = DEFAULT_MODEL
    timeout_sec: int = 300
    context: dict | None = None
    tool_allowlist: list[str] | None = None


class RuntimeRunRequest(BaseModel):
    instruction: str
    model: str = DEFAULT_MODEL
    workspace: str | None = None
    task_id: str | None = None


@app.get("/health")
async def health():
    """Health check — reports Nvidia NIM when key present, otherwise Ollama status."""
    if _NVIDIA_KEY:
        return {"status": "ok", "runtime": RUNTIME_NAME, "provider": "nvidia-nim", "model": DEFAULT_MODEL}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            return {
                "status": "ok",
                "runtime": RUNTIME_NAME,
                "provider": "ollama",
                "models": len(resp.json().get("models", [])),
            }
    except Exception as e:
        return {
            "status": "degraded",
            "runtime": RUNTIME_NAME,
            "provider": "ollama",
            "backend": str(e),
        }


@app.get("/v1/models")
async def list_models():
    """List available models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return {
                "object": "list",
                "data": [
                    {
                        "id": m["name"],
                        "object": "model",
                        "owned_by": "ollama",
                        "permission": [],
                    }
                    for m in models
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")


def _candidate_ollama_bases() -> list[str]:
    bases = [OLLAMA_BASE]
    if OLLAMA_FALLBACK_BASE and OLLAMA_FALLBACK_BASE not in bases:
        bases.append(OLLAMA_FALLBACK_BASE)
    return bases


async def _pick_fallback_target(
    client: httpx.AsyncClient, requested_model: str
) -> tuple[str, str]:
    first_available: tuple[str, str] | None = None
    for base in _candidate_ollama_bases():
        try:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
        except Exception:
            continue
        models = resp.json().get("models", [])
        if not models:
            continue
        for model in models:
            name = model.get("name")
            if name == requested_model:
                return base, requested_model
        if first_available is None:
            first_available = (base, models[0]["name"])
    if first_available is not None:
        return first_available
    raise HTTPException(status_code=503, detail="No Ollama models are installed")


async def _chat_with_nvidia(
    *,
    messages: list[dict],
    model: str,
    temperature: float = 0.7,
    timeout_sec: float = 60.0,
) -> tuple[str, str]:
    """Call Nvidia NIM via OpenAI-compatible /v1/chat/completions. Returns (content, model)."""
    headers = {"Authorization": f"Bearer {_NVIDIA_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "stream": False}
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        resp = await client.post(f"{_NVIDIA_BASE}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content, data.get("model", model)


async def _chat_with_ollama(
    *,
    instruction: str,
    model: str,
    temperature: float = 0.7,
    timeout_sec: float = 60.0,
) -> tuple[dict, str]:
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": instruction}],
            "temperature": temperature,
            "stream": False,
        }
        resp = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        if resp.status_code == 404 and "not found" in resp.text.lower():
            fallback_base, fallback_model = await _pick_fallback_target(client, model)
            payload["model"] = fallback_model
            resp = await client.post(f"{fallback_base}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json(), fallback_model
        resp.raise_for_status()
        return resp.json(), model


async def _chat(
    *,
    instruction: str,
    model: str,
    temperature: float = 0.7,
    timeout_sec: float = 60.0,
) -> tuple[str, str]:
    """Route to Nvidia NIM (priority 1) when key present, otherwise Ollama."""
    if _NVIDIA_KEY:
        try:
            messages = [{"role": "user", "content": instruction}]
            content, resolved = await _chat_with_nvidia(
                messages=messages, model=model, temperature=temperature, timeout_sec=timeout_sec
            )
            return content, resolved
        except Exception:
            pass  # fall through to Ollama
    data, resolved_model = await _chat_with_ollama(
        instruction=instruction, model=model, temperature=temperature, timeout_sec=timeout_sec
    )
    return data.get("message", {}).get("content", ""), resolved_model


def _completed_task_payload(*, task_id: str, model: str, output: str) -> dict:
    return {
        "task_id": task_id,
        "status": "done",
        "success": True,
        "output": output,
        "result": output,
        "artifacts": [],
        "tool_calls": [],
        "model_used": model,
        "provider_used": "local",
        "tokens_used": 0,
        "cost_usd": 0.0,
        "metadata": {},
    }


@app.post("/tasks")
async def run_task(req: RuntimeTaskRequest):
    """Hermes-compatible task execution endpoint."""
    try:
        output, resolved_model = await _chat(
            instruction=req.instruction,
            model=req.model,
            timeout_sec=float(req.timeout_sec),
        )
        result = _completed_task_payload(
            task_id=req.task_id,
            model=resolved_model,
            output=output,
        )
        TASK_RESULTS[req.task_id] = result
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Backend error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Hermes-compatible task status lookup."""
    result = TASK_RESULTS.get(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@app.post("/run")
async def run_instruction(req: RuntimeRunRequest):
    """OpenCode-compatible single instruction endpoint."""
    try:
        output, resolved_model = await _chat(
            instruction=req.instruction,
            model=req.model,
        )
        task_id = req.task_id or f"run-{int(time.time() * 1000)}"
        result = {
            "task_id": task_id,
            "success": True,
            "output": output,
            "artifacts": [],
            "model_used": resolved_model,
            "provider_used": "local",
        }
        TASK_RESULTS[task_id] = {
            **_completed_task_payload(task_id=task_id, model=resolved_model, output=output),
            "success": True,
        }
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Backend error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat completion endpoint."""
    try:
        instruction = "\n\n".join(f"{m.role}: {m.content}" for m in req.messages)
        content, resolved_model = await _chat(
            instruction=instruction,
            model=req.model,
            temperature=req.temperature,
        )

        return {
            "id": "chatcmpl-local",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": resolved_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Backend error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec: B104 - Binding to all interfaces is required for external access

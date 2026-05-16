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
# Free cloud providers — tried in priority order before local Ollama
_NVIDIA_KEY = (os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey") or "").strip()
_NVIDIA_BASE = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
_NVIDIA_DEFAULT_MODEL = os.environ.get("NVIDIA_DEFAULT_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")

_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
_DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
_DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

_GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
_GROQ_BASE = "https://api.groq.com/openai/v1"
_GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

_QWEN_KEY = (os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY") or "").strip()
_QWEN_BASE = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
_QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")

_HF_KEY = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN") or "").strip()
_HF_BASE = os.environ.get("HF_BASE_URL", "https://api-inference.huggingface.co/v1").rstrip("/")
_HF_MODEL = os.environ.get("HF_MODEL_ID", "Qwen/Qwen2.5-Coder-7B-Instruct")

_ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "").strip()
_ZHIPU_BASE = "https://open.bigmodel.cn/api/paas/v4"
_ZHIPU_MODEL = os.environ.get("ZHIPU_MODEL", "glm-4-flash")

_MINIMAX_KEY = os.environ.get("MINIMAX_API_KEY", "").strip()
_MINIMAX_BASE = "https://api.minimax.chat/v1"
_MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-Text-01")

# Resolve the effective default model: prefer first available cloud key
def _default_model() -> str:
    for key, model in [
        (_NVIDIA_KEY, _NVIDIA_DEFAULT_MODEL),
        (_DEEPSEEK_KEY, _DEEPSEEK_MODEL),
        (_GROQ_KEY, _GROQ_MODEL),
        (_QWEN_KEY, _QWEN_MODEL),
        (_HF_KEY, _HF_MODEL),
        (_ZHIPU_KEY, _ZHIPU_MODEL),
        (_MINIMAX_KEY, _MINIMAX_MODEL),
    ]:
        if key:
            return model
    return "qwen3-coder:30b"

DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL") or _default_model()
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


def _active_cloud_provider() -> str | None:
    if _NVIDIA_KEY:
        return "nvidia-nim"
    if _DEEPSEEK_KEY:
        return "deepseek"
    if _GROQ_KEY:
        return "groq"
    if _QWEN_KEY:
        return "qwen-dashscope"
    if _HF_KEY:
        return "huggingface"
    if _ZHIPU_KEY:
        return "zhipu"
    if _MINIMAX_KEY:
        return "minimax"
    return None


@app.get("/health")
async def health():
    """Health check — reports active cloud provider when any key present, otherwise Ollama."""
    provider = _active_cloud_provider()
    if provider:
        return {"status": "ok", "runtime": RUNTIME_NAME, "provider": provider, "model": DEFAULT_MODEL}
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


async def _chat_with_openai_compat(
    *,
    base_url: str,
    api_key: str,
    messages: list[dict],
    model: str,
    temperature: float = 0.7,
    timeout_sec: float = 60.0,
) -> tuple[str, str]:
    """Generic OpenAI-compatible /v1/chat/completions call."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "stream": False}
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content, data.get("model", model)


async def _chat(
    *,
    instruction: str,
    model: str,
    temperature: float = 0.7,
    timeout_sec: float = 60.0,
) -> tuple[str, str]:
    """Try free cloud providers in priority order, fall back to local Ollama."""
    messages = [{"role": "user", "content": instruction}]

    cloud_providers = [
        (_NVIDIA_KEY,   _NVIDIA_BASE,   _NVIDIA_DEFAULT_MODEL),
        (_DEEPSEEK_KEY, _DEEPSEEK_BASE, _DEEPSEEK_MODEL),
        (_GROQ_KEY,     _GROQ_BASE,     _GROQ_MODEL),
        (_QWEN_KEY,     _QWEN_BASE,     _QWEN_MODEL),
        (_HF_KEY,       _HF_BASE,       _HF_MODEL),
        (_ZHIPU_KEY,    _ZHIPU_BASE,    _ZHIPU_MODEL),
        (_MINIMAX_KEY,  _MINIMAX_BASE,  _MINIMAX_MODEL),
    ]
    for key, base, default_mdl in cloud_providers:
        if not key:
            continue
        try:
            resolved_model = model if model != DEFAULT_MODEL else default_mdl
            content, used = await _chat_with_openai_compat(
                base_url=base, api_key=key, messages=messages,
                model=resolved_model, temperature=temperature, timeout_sec=timeout_sec,
            )
            return content, used
        except Exception:
            continue  # try next provider

    # Last resort: local Ollama
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

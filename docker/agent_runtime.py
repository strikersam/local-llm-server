#!/usr/bin/env python3
"""Lightweight OpenAI-compatible agent runtime wrapper.

Each runtime (hermes, opencode, goose, aider) is a FastAPI service that:
1. Exposes /v1/chat/completions (OpenAI format)
2. Routes to a configured backend model
3. Reports health on /health
"""

from __future__ import annotations

import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Agent Runtime")

# Get config from environment
RUNTIME_NAME = os.environ.get("RUNTIME_NAME", "unknown")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen3-coder:30b")


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


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            return {
                "status": "ok",
                "runtime": RUNTIME_NAME,
                "models": len(resp.json().get("models", [])),
            }
    except Exception as e:
        return {"status": "error", "runtime": RUNTIME_NAME, "error": str(e)}, 503


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


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat completion endpoint."""
    try:
        # Convert our format to Ollama format
        messages = [{"role": m.role, "content": m.content} for m in req.messages]

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/api/chat",
                json={
                    "model": req.model,
                    "messages": messages,
                    "temperature": req.temperature,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "id": "chatcmpl-local",
                "object": "chat.completion",
                "created": int(__import__("time").time()),
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": data.get("message", {}).get("content", ""),
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
    uvicorn.run(app, host="0.0.0.0", port=port)

"""V3 API endpoints for models and providers (/api/models/*, /api/providers/*)."""
from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from handlers.v3_auth import _get_current_user, UserResponse


router = APIRouter(prefix="/api", tags=["models", "providers"])


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    owner: str  # "ollama", "huggingface", etc.
    size_gb: float | None = None
    status: str  # "available", "loading", "error"


class ModelsListResponse(BaseModel):
    """List of models."""
    object: str = "list"
    data: list[ModelInfo]


class ProviderInfo(BaseModel):
    """Provider information."""
    id: str
    name: str
    type: str  # "local", "cloud", etc.
    enabled: bool
    models_count: int


class ProvidersListResponse(BaseModel):
    """List of providers."""
    object: str = "list"
    data: list[ProviderInfo]


async def _get_ollama_models(ollama_base: str) -> list[str]:
    """Fetch list of models from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{ollama_base}/api/tags")
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


async def _get_ollama_model_info(ollama_base: str, model_name: str) -> dict | None:
    """Get detailed info about a model from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{ollama_base}/api/show", params={"name": model_name})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


@router.get("/models", response_model=ModelsListResponse)
async def list_models(
    user: Annotated[UserResponse, Depends(_get_current_user)],
) -> ModelsListResponse:
    """List all available models from Ollama and registry."""
    from router.registry import get_registry
    import os

    ollama_base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")

    # Get Ollama models
    ollama_models = await _get_ollama_models(ollama_base)
    ollama_set = set(ollama_models)

    # Get registry models
    registry = get_registry()

    models: list[ModelInfo] = []

    # Add Ollama models
    for name in ollama_models:
        models.append(
            ModelInfo(
                id=name,
                name=name,
                owner="ollama",
                status="available",
            )
        )

    # Add registry-only models
    for name in registry:
        if name not in ollama_set:
            models.append(
                ModelInfo(
                    id=name,
                    name=name,
                    owner="registry",
                    status="available",
                )
            )

    return ModelsListResponse(data=models)


@router.get("/models/{model_name}")
async def get_model(
    model_name: str,
    user: Annotated[UserResponse, Depends(_get_current_user)],
) -> ModelInfo:
    """Get details about a specific model."""
    import os

    ollama_base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")

    info = await _get_ollama_model_info(ollama_base, model_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    return ModelInfo(
        id=model_name,
        name=model_name,
        owner="ollama",
        status="available",
    )


@router.post("/models/pull")
async def pull_model(
    req: dict,
    user: Annotated[UserResponse, Depends(_get_current_user)],
) -> dict:
    """Pull a model from Ollama."""
    import os

    model_name = req.get("name") or req.get("model")
    if not model_name:
        raise HTTPException(status_code=400, detail="'name' or 'model' field required")

    ollama_base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                f"{ollama_base}/api/pull",
                json={"name": model_name},
            )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Failed to pull model: {r.text}",
            )
        return {"status": "pulling", "model": model_name}
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")


@router.delete("/models/{model_name}")
async def delete_model(
    model_name: str,
    user: Annotated[UserResponse, Depends(_get_current_user)],
) -> dict:
    """Delete a model from Ollama."""
    import os

    ollama_base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(
                f"{ollama_base}/api/delete",
                json={"name": model_name},
            )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Failed to delete model: {r.text}",
            )
        return {"status": "deleted", "model": model_name}
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")


@router.get("/providers", response_model=ProvidersListResponse)
async def list_providers(
    user: Annotated[UserResponse, Depends(_get_current_user)],
) -> ProvidersListResponse:
    """List available LLM providers."""
    import os

    ollama_base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")

    # Get Ollama models count
    ollama_models = await _get_ollama_models(ollama_base)

    providers = [
        ProviderInfo(
            id="ollama",
            name="Ollama (Local)",
            type="local",
            enabled=len(ollama_models) > 0,
            models_count=len(ollama_models),
        ),
    ]

    return ProvidersListResponse(data=providers)


@router.get("/stats")
async def get_stats(
    user: Annotated[UserResponse, Depends(_get_current_user)],
) -> dict:
    """Get system statistics."""
    import os
    import psutil

    ollama_base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
    ollama_models = await _get_ollama_models(ollama_base)

    # System stats
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "models": {
            "total": len(ollama_models),
            "available": len(ollama_models),
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
        },
        "uptime_seconds": int(sum(psutil.Process(os.getpid()).cpu_times())),
    }


@router.get("/activity")
async def get_activity(
    user: Annotated[UserResponse, Depends(_get_current_user)],
    limit: int = 50,
) -> dict:
    """Get recent activity log (stub for now)."""
    return {
        "object": "list",
        "data": [
            {
                "timestamp": "2026-04-24T14:40:00Z",
                "action": "model_loaded",
                "model": "gemma4:latest",
                "user": "admin",
            },
        ],
        "total": 1,
        "limit": limit,
    }

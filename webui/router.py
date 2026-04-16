from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from webui.providers import ProviderCreate, ProviderManager, ProviderUpdate
from webui.workspaces import WorkspaceCreate, WorkspaceManager, WorkspaceUpdate
from webui.commands import run_command

log = logging.getLogger("qwen-proxy")

def _admin_out(admin: Any) -> dict[str, Any]:
    return {
        "username": getattr(admin, "username", "admin"),
        "auth_source": getattr(admin, "auth_source", "unknown"),
    }


class UiChatRequest(BaseModel):
    provider_id: str = Field(default="prov_local", max_length=64)
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    messages: list[dict[str, Any]] = Field(default_factory=list)


class UiSearchBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=400)
    limit: int = Field(default=20, ge=1, le=200)


class UiRoutePreviewBody(BaseModel):
    """Body for POST /ui/api/route — preview which model auto-routing would pick."""
    text: str = Field(..., min_length=1, max_length=8000)


class AdminCommandBody(BaseModel):
    workspace_id: str = Field(default="ws_current", max_length=64)
    command: list[str] = Field(..., min_length=1, max_length=32)
    timeout_sec: int = Field(default=60, ge=1, le=600)


def register_webui(
    app: FastAPI,
    *,
    providers: ProviderManager,
    workspaces: WorkspaceManager,
    admin_enabled: bool,
    verify_user: Any,
    get_admin_identity: Any,
) -> None:
    app.state.webui_providers = providers
    app.state.webui_workspaces = workspaces
    app.state.webui_admin_enabled = admin_enabled

    dist = Path(__file__).resolve().parent / "frontend" / "dist"
    index_html = dist / "index.html"

    # Static assets (built by Vite).
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    router = APIRouter(prefix="/ui/api", tags=["webui"])
    admin_router = APIRouter(prefix="/admin/api", tags=["admin-webui"])

    @router.get("/bootstrap")
    async def bootstrap():
        return {
            "ok": True,
            "admin_enabled": admin_enabled,
            "has_ui_build": index_html.is_file(),
        }

    @router.get("/providers")
    async def list_providers(request: Request, _: Any = Depends(verify_user)):
        mgr: ProviderManager = request.app.state.webui_providers
        return {"providers": [p.model_dump() for p in mgr.list_public()]}

    @router.get("/providers/{provider_id}/models")
    async def provider_models(request: Request, provider_id: str, _: Any = Depends(verify_user)):
        mgr: ProviderManager = request.app.state.webui_providers
        secret = mgr.get_secret(provider_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Unknown provider")
        headers: dict[str, str] = {}
        if secret.api_key:
            headers["Authorization"] = f"Bearer {secret.api_key}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(f"{secret.base_url}/v1/models", headers=headers)
                if resp.status_code == 404:
                    # Ollama exposes model listing via /api/tags (older or non-OpenAI endpoints).
                    resp = await client.get(f"{secret.base_url}/api/tags", headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"Provider unreachable: {exc}") from exc
        data = resp.json()

        # OpenAI: {"data": [{"id": "..."}]}
        if isinstance(data, dict) and "data" in data:
            models = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
            return {"provider_id": provider_id, "models": [m for m in models if isinstance(m, str)]}

        # Ollama: {"models": [{"name": "..."}]}
        models = [m.get("name") for m in (data.get("models") or []) if isinstance(m, dict)]
        return {"provider_id": provider_id, "models": [m for m in models if isinstance(m, str)]}

    @router.post("/chat")
    async def ui_chat(request: Request, body: UiChatRequest, _: Any = Depends(verify_user)):
        mgr: ProviderManager = request.app.state.webui_providers
        secret = mgr.get_secret(body.provider_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Unknown provider")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if secret.api_key:
            headers["Authorization"] = f"Bearer {secret.api_key}"
        model = body.model or secret.default_model
        if not model:
            raise HTTPException(status_code=400, detail="Missing model (set provider default or pass model)")
        payload = {
            "model": model,
            "messages": body.messages,
            "temperature": body.temperature if body.temperature is not None else secret.default_temperature,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            resp = await client.post(f"{secret.base_url}/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"model": model, "content": content}

    @router.post("/route")
    async def preview_route(request: Request, body: UiRoutePreviewBody, _: Any = Depends(verify_user)):
        """Return which model the auto-router would pick for *text* (dry-run, no LLM call)."""
        try:
            from router.model_router import get_router
            messages = [{"role": "user", "content": body.text}]
            decision = get_router().route(messages=messages, stream=False)
            return {
                "resolved_model":   decision.resolved_model,
                "task_category":    decision.task_category,
                "selection_source": decision.selection_source,
                "routing_reason":   decision.routing_reason,
            }
        except Exception as exc:
            log.warning("route preview failed: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.get("/workspaces")
    async def list_workspaces(request: Request, _: Any = Depends(verify_user)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        return {"workspaces": [w.model_dump() for w in mgr.list()]}

    @router.get("/workspaces/{workspace_id}/files")
    async def list_files(
        request: Request,
        workspace_id: str,
        path: str = ".",
        limit: int = 200,
        _: Any = Depends(verify_user),
    ):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        tools = mgr.tools_for(workspace_id)
        return {"workspace_id": workspace_id, "files": tools.list_files(path, limit=limit)}

    @router.get("/workspaces/{workspace_id}/file")
    async def read_file(request: Request, workspace_id: str, path: str, _: Any = Depends(verify_user)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        tools = mgr.tools_for(workspace_id)
        return {"workspace_id": workspace_id, "path": path, "content": tools.read_file(path, max_chars=200000)}

    @router.post("/workspaces/{workspace_id}/search")
    async def search(request: Request, workspace_id: str, body: UiSearchBody, _: Any = Depends(verify_user)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        tools = mgr.tools_for(workspace_id)
        return {
            "workspace_id": workspace_id,
            "query": body.query,
            "matches": tools.search_code(body.query, limit=body.limit),
        }

    # --- Admin: providers/workspaces CRUD ---

    @admin_router.get("/providers")
    async def admin_list_providers(request: Request, admin: Any = Depends(get_admin_identity)):
        mgr: ProviderManager = request.app.state.webui_providers
        return {"providers": [p.model_dump() for p in mgr.list_admin()], "admin": _admin_out(admin)}

    @admin_router.post("/providers")
    async def admin_create_provider(request: Request, body: ProviderCreate, admin: Any = Depends(get_admin_identity)):
        mgr: ProviderManager = request.app.state.webui_providers
        rec = mgr.create(body)
        return {"provider": rec.model_dump(), "admin": _admin_out(admin)}

    @admin_router.patch("/providers/{provider_id}")
    async def admin_update_provider(
        request: Request,
        provider_id: str,
        body: ProviderUpdate,
        admin: Any = Depends(get_admin_identity),
    ):
        mgr: ProviderManager = request.app.state.webui_providers
        rec = mgr.update(provider_id, body)
        if not rec:
            raise HTTPException(status_code=404, detail="Unknown provider")
        return {"provider": rec.model_dump(), "admin": _admin_out(admin)}

    @admin_router.delete("/providers/{provider_id}")
    async def admin_delete_provider(request: Request, provider_id: str, admin: Any = Depends(get_admin_identity)):
        mgr: ProviderManager = request.app.state.webui_providers
        ok = mgr.delete(provider_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Unknown provider")
        return {"ok": True, "provider_id": provider_id, "admin": _admin_out(admin)}

    @admin_router.get("/workspaces")
    async def admin_list_workspaces(request: Request, admin: Any = Depends(get_admin_identity)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        return {"workspaces": [w.model_dump() for w in mgr.list()], "admin": _admin_out(admin)}

    @admin_router.post("/workspaces")
    async def admin_create_workspace(request: Request, body: WorkspaceCreate, admin: Any = Depends(get_admin_identity)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        try:
            ws = mgr.create(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"workspace": ws.model_dump(), "admin": _admin_out(admin)}

    @admin_router.patch("/workspaces/{workspace_id}")
    async def admin_update_workspace(
        request: Request,
        workspace_id: str,
        body: WorkspaceUpdate,
        admin: Any = Depends(get_admin_identity),
    ):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        ws = mgr.update(workspace_id, body)
        if not ws:
            raise HTTPException(status_code=404, detail="Unknown workspace")
        return {"workspace": ws.model_dump(), "admin": _admin_out(admin)}

    @admin_router.delete("/workspaces/{workspace_id}")
    async def admin_delete_workspace(
        request: Request,
        workspace_id: str,
        admin: Any = Depends(get_admin_identity),
    ):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        ok = mgr.delete(workspace_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Unknown workspace")
        return {"ok": True, "workspace_id": workspace_id, "admin": _admin_out(admin)}

    @admin_router.post("/workspaces/{workspace_id}/sync")
    async def admin_sync_workspace(request: Request, workspace_id: str, admin: Any = Depends(get_admin_identity)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        try:
            result = mgr.sync_git(workspace_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"result": result, "admin": _admin_out(admin)}

    @admin_router.post("/commands/run")
    async def admin_run_command(request: Request, body: AdminCommandBody, admin: Any = Depends(get_admin_identity)):
        mgr: WorkspaceManager = request.app.state.webui_workspaces
        ws = mgr.get(body.workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Unknown workspace")
        try:
            result = run_command(
                command=body.command,
                cwd=Path(ws.path),
                timeout_sec=body.timeout_sec,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except subprocess.TimeoutExpired:  # type: ignore[name-defined]
            raise HTTPException(status_code=408, detail="Command timed out")
        return {"result": result, "admin": _admin_out(admin)}

    app.include_router(router)
    app.include_router(admin_router)

    if not index_html.is_file():
        log.warning(
            "Web UI build not found at %s (run `npm ci && npm run build` in webui/frontend/)", dist
        )

    def _serve_index() -> FileResponse:
        if not index_html.is_file():
            raise HTTPException(status_code=503, detail="Web UI not built on server")
        return FileResponse(str(index_html))

    @app.get("/app")
    async def _app_index():
        return _serve_index()

    @app.get("/app/{path:path}")
    async def _app_spa(path: str):
        return _serve_index()

    @app.get("/admin/app")
    async def _admin_app_index():
        return _serve_index()

    @app.get("/admin/app/{path:path}")
    async def _admin_app_spa(path: str):
        return _serve_index()

    @app.get("/")
    async def _root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return _serve_index()
        return JSONResponse(
            {
                "service": "Qwen3-Coder Authenticated Proxy",
                "ui": "GET / (HTML), /app (HTML), /admin/app (HTML)",
                "endpoints": {
                    "health": "GET  /health          (no auth)",
                    "ollama_api": "ANY  /api/*            (Bearer auth)",
                    "openai_compat": "ANY  /v1/*             (Bearer auth)",
                    "agent_sessions": "POST /agent/sessions   (Bearer auth)",
                    "agent_run": "POST /agent/run        (Bearer auth)",
                    "webui_api": "GET/POST /ui/api/*     (Bearer auth for most routes)",
                },
            }
        )

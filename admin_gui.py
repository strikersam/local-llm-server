"""Browser admin UI for login, service control, key management, and diagnostics."""

from __future__ import annotations

import logging
import os
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from key_store import issue_new_api_key
from langfuse_obs import test_langfuse_connection

_ENV_PATH = Path(__file__).resolve().parent / ".env"


def _save_env_var(key: str, value: str) -> None:
    """Update or append a KEY=value line in the .env file."""
    line = f"{key}={value}\n"
    if _ENV_PATH.is_file():
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, l in enumerate(lines):
            if l.startswith(f"{key}=") or l.startswith(f"{key} ="):
                lines[i] = line
                _ENV_PATH.write_text("".join(lines), encoding="utf-8")
                return
        lines.append(line)
        _ENV_PATH.write_text("".join(lines), encoding="utf-8")
    else:
        _ENV_PATH.write_text(line, encoding="utf-8")

if TYPE_CHECKING:
    from fastapi import FastAPI

    from admin_auth import AdminAuthManager
    from key_store import KeyStore
    from service_manager import WindowsServiceManager

log = logging.getLogger("qwen-proxy")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def register_admin_gui(
    app: "FastAPI",
    key_store: "KeyStore",
    admin_auth: "AdminAuthManager",
    service_manager: "WindowsServiceManager",
) -> None:
    if not admin_auth.enabled:
        return

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])

    def _guest_redirect(request: Request) -> RedirectResponse | None:
        if not request.session.get("admin_ok"):
            return RedirectResponse(url="/admin/ui/login", status_code=302)
        return None

    def _redirect(request: Request, path: str = "/admin/ui/") -> RedirectResponse:
        return RedirectResponse(url=path, status_code=302)

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if request.session.get("admin_ok"):
            return _redirect(request)
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {
                "request": request,
                "error": None,
                "supports_windows_auth": admin_auth.supports_windows_auth,
            },
        )

    @router.post("/login", response_class=HTMLResponse)
    async def login_submit(
        request: Request,
        username: str = Form(default=""),
        password: str = Form(...),
    ):
        identity = admin_auth.authenticate(username, password)
        if not identity:
            return templates.TemplateResponse(
                request,
                "admin/login.html",
                {
                    "request": request,
                    "error": "Invalid admin credentials",
                    "supports_windows_auth": admin_auth.supports_windows_auth,
                },
                status_code=401,
            )
        request.session["admin_ok"] = True
        request.session["admin_user"] = identity.username
        request.session["admin_auth_source"] = identity.auth_source
        request.session["flash"] = f"Signed in as {identity.username}"
        return _redirect(request)

    @router.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/admin/ui/login", status_code=302)

    @router.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        gr = _guest_redirect(request)
        if gr:
            return gr
        records = key_store.list_records() if key_store.is_configured() else []
        dept_counts = dict(Counter(r.department for r in records))
        langfuse_diag = request.session.pop("langfuse_diag", None)
        services = service_manager.get_status()
        return templates.TemplateResponse(
            request,
            "admin/dashboard.html",
            {
                "request": request,
                "admin_user": request.session.get("admin_user", "admin"),
                "keys_file_ok": key_store.is_configured(),
                "records": records,
                "dept_counts": dept_counts,
                "flash": request.session.pop("flash", None),
                "flash_key": request.session.pop("flash_key", None),
                "langfuse_diag": langfuse_diag,
                "services": services,
                "supports_windows_auth": admin_auth.supports_windows_auth,
            },
        )

    @router.post("/control")
    async def service_control(
        request: Request,
        action: str = Form(...),
        target: str = Form(...),
    ):
        gr = _guest_redirect(request)
        if gr:
            return gr
        result = service_manager.control(action, target, current_proxy_pid=os.getpid())
        request.session["flash"] = result.get("message", f"{action} requested for {target}")
        return _redirect(request)

    @router.post("/users/create")
    async def user_create(
        request: Request,
        email: str = Form(...),
        department: str = Form(...),
    ):
        gr = _guest_redirect(request)
        if gr:
            return gr
        if not key_store.is_configured():
            raise HTTPException(status_code=503, detail="KEYS_FILE not set")
        plain, rec = issue_new_api_key(key_store, email.strip(), department.strip())
        log.info("GUI issued key_id=%s email=%s department=%s", rec.key_id, rec.email, rec.department)
        request.session["flash"] = f"Created key for {rec.email} ({rec.department}). Copy the token below because it will not be shown again."
        request.session["flash_key"] = plain
        return _redirect(request)

    @router.post("/users/update")
    async def user_update(
        request: Request,
        key_id: str = Form(...),
        email: str = Form(...),
        department: str = Form(...),
    ):
        gr = _guest_redirect(request)
        if gr:
            return gr
        rec = key_store.update_metadata(key_id, email, department)
        if not rec:
            request.session["flash"] = f"Update failed: unknown key_id {key_id}"
        else:
            request.session["flash"] = f"Updated {rec.key_id} ({rec.email} / {rec.department})"
        return _redirect(request)

    @router.post("/users/delete")
    async def user_delete(request: Request, key_id: str = Form(...)):
        gr = _guest_redirect(request)
        if gr:
            return gr
        if key_store.delete_by_key_id(key_id):
            request.session["flash"] = f"Revoked and deleted {key_id}"
        else:
            request.session["flash"] = f"Delete failed: unknown key_id {key_id}"
        return _redirect(request)

    @router.post("/users/rotate")
    async def user_rotate(request: Request, key_id: str = Form(...)):
        gr = _guest_redirect(request)
        if gr:
            return gr
        out = key_store.rotate_plain(key_id)
        if not out:
            request.session["flash"] = f"Rotate failed: unknown key_id {key_id}"
        else:
            plain, rec = out
            request.session["flash"] = f"Rotated secret for {rec.key_id}. Old Bearer token no longer works."
            request.session["flash_key"] = plain
        return _redirect(request)

    @router.post("/diag/langfuse")
    async def diag_langfuse(request: Request):
        gr = _guest_redirect(request)
        if gr:
            return gr
        ok, msg = test_langfuse_connection()
        request.session["langfuse_diag"] = {"ok": ok, "message": msg}
        return _redirect(request)

    @router.post("/public-url")
    async def save_public_url(request: Request, public_url: str = Form(default="")):
        gr = _guest_redirect(request)
        if gr:
            return gr
        url = public_url.strip().rstrip("/")
        _save_env_var("PUBLIC_URL", url)
        os.environ["PUBLIC_URL"] = url
        if url:
            request.session["flash"] = f"Public URL saved: {url}"
        else:
            request.session["flash"] = "Public URL cleared — will auto-detect from tunnel log."
        return _redirect(request)

    app.include_router(router)

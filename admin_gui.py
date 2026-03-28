"""Browser admin UI: CRUD user API keys (KEYS_FILE) and Langfuse diagnostics."""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from key_store import issue_new_api_key
from langfuse_obs import test_langfuse_connection

if TYPE_CHECKING:
    from fastapi import FastAPI

    from key_store import KeyStore

log = logging.getLogger("qwen-proxy")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def register_admin_gui(app: "FastAPI", key_store: "KeyStore", admin_secret: str) -> None:
    if not admin_secret:
        return

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])

    def _guest_redirect(request: Request) -> RedirectResponse | None:
        if not request.session.get("admin_ok"):
            return RedirectResponse(url="/admin/ui/login", status_code=302)
        return None

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if request.session.get("admin_ok"):
            return RedirectResponse(url="/admin/ui/", status_code=302)
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"request": request, "error": None},
        )

    @router.post("/login", response_class=HTMLResponse)
    async def login_submit(request: Request, admin_password: str = Form(...)):
        if admin_password.strip() != admin_secret:
            return templates.TemplateResponse(
                request,
                "admin/login.html",
                {"request": request, "error": "Invalid admin secret"},
                status_code=401,
            )
        request.session["admin_ok"] = True
        return RedirectResponse(url="/admin/ui/", status_code=302)

    @router.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/admin/ui/login", status_code=302)

    @router.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        gr = _guest_redirect(request)
        if gr:
            return gr
        if not key_store.is_configured():
            return templates.TemplateResponse(
                request,
                "admin/dashboard.html",
                {
                    "request": request,
                    "keys_file_ok": False,
                    "records": [],
                    "dept_counts": {},
                    "flash": request.session.pop("flash", None),
                    "flash_key": request.session.pop("flash_key", None),
                    "langfuse_diag": None,
                },
            )
        records = key_store.list_records()
        dept_counts = dict(Counter(r.department for r in records))
        langfuse_diag = request.session.pop("langfuse_diag", None)
        return templates.TemplateResponse(
            request,
            "admin/dashboard.html",
            {
                "request": request,
                "keys_file_ok": True,
                "records": records,
                "dept_counts": dept_counts,
                "flash": request.session.pop("flash", None),
                "flash_key": request.session.pop("flash_key", None),
                "langfuse_diag": langfuse_diag,
            },
        )

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
        request.session["flash"] = f"Created key for {rec.email} ({rec.department}). Copy the token below — it will not be shown again."
        request.session["flash_key"] = plain
        return RedirectResponse(url="/admin/ui/", status_code=302)

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
        return RedirectResponse(url="/admin/ui/", status_code=302)

    @router.post("/users/delete")
    async def user_delete(request: Request, key_id: str = Form(...)):
        gr = _guest_redirect(request)
        if gr:
            return gr
        if key_store.delete_by_key_id(key_id):
            request.session["flash"] = f"Revoked and deleted {key_id}"
        else:
            request.session["flash"] = f"Delete failed: unknown key_id {key_id}"
        return RedirectResponse(url="/admin/ui/", status_code=302)

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
            request.session["flash"] = f"Rotated secret for {rec.key_id}. Old Bearer token no longer works. New token below."
            request.session["flash_key"] = plain
        return RedirectResponse(url="/admin/ui/", status_code=302)

    @router.post("/diag/langfuse")
    async def diag_langfuse(request: Request):
        gr = _guest_redirect(request)
        if gr:
            return gr
        ok, msg = test_langfuse_connection()
        request.session["langfuse_diag"] = {"ok": ok, "message": msg}
        return RedirectResponse(url="/admin/ui/", status_code=302)

    app.include_router(router)

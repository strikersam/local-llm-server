"""Generate Web UI screenshots for README/docs.

Requires:
  pip install playwright
  python -m playwright install chromium

Usage:
  source .venv/bin/activate
  python scripts/gen_webui_screenshots.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


def _out_dir() -> Path:
    out = Path("docs/screenshots").resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


async def main() -> None:
    from playwright.async_api import async_playwright

    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    base_url = str(args.base_url).rstrip("/")
    out = _out_dir()

    admin_secret = (os.environ.get("ADMIN_SECRET") or "").strip()
    if not admin_secret:
        raise SystemExit("ADMIN_SECRET is required in env/.env to capture admin screenshots safely.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})

        # App (empty state).
        page = await ctx.new_page()
        await page.goto(f"{base_url}/app", wait_until="networkidle")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(out / "webui-app.png"), full_page=True)

        # Admin app (login screen).
        admin_page = await ctx.new_page()
        await admin_page.goto(f"{base_url}/admin/app", wait_until="networkidle")
        await admin_page.evaluate("() => window.localStorage.removeItem('lls_admin_token')")
        await admin_page.reload(wait_until="networkidle")
        await admin_page.wait_for_timeout(200)
        await admin_page.screenshot(path=str(out / "webui-admin-login.png"), full_page=True)

        # Fetch an admin session token, then screenshot the authenticated admin app.
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{base_url}/admin/api/login",
                json={"username": "screenshot", "password": admin_secret},
            )
        resp.raise_for_status()
        token = resp.json().get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Admin login did not return a token")

        await admin_page.add_init_script(f"window.localStorage.setItem('lls_admin_token', {token!r});")
        await admin_page.goto(f"{base_url}/admin/app", wait_until="networkidle")
        await admin_page.wait_for_timeout(400)
        await admin_page.screenshot(path=str(out / "webui-admin.png"), full_page=True)

        await browser.close()

    print(f"Saved: {out / 'webui-app.png'}")
    print(f"Saved: {out / 'webui-admin-login.png'}")
    print(f"Saved: {out / 'webui-admin.png'}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())


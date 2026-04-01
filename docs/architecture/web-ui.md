# Web UI + Admin (Claude Code–style)

## Goal

Add a browser-based chat + coding UI (Claw Code / Claude Code–style) to `local-llm-server`, with a protected admin area for configuration and management, and a deployment path that does not rely on Vercel.

## Approach

Ship a single deployable FastAPI service that serves a static SPA and exposes JSON APIs. Reuse existing auth primitives:
- **User access** uses existing **API keys** (`Authorization: Bearer <key>` / `x-api-key`).
- **Admin access** uses existing **admin sessions** (`POST /admin/api/login` → `Bearer sess_...`), plus the existing server-rendered dashboard at `/admin/ui/*`.

Add:
- A **workspace registry** (selectable repo/workspace roots; optionally clone extra repos).
- A **provider registry** (OpenAI-compatible endpoints + server-side secret storage) so the agent and UI can target local Ollama or remote hosted LLMs.

## Files to change

- `proxy.py` — mount the SPA, add workspace/provider APIs, run agent with selected workspace/provider.
- `agent/loop.py` — support OpenAI-compatible providers (base URL + Authorization header), include tool/observation trace in results for the UI.
- `agent/models.py` — extend request schema to include `provider_id` + `workspace_id` (backwards-compatible defaults).
- `docs/admin-dashboard.md` — remove Vercel section; point to built-in web UI admin route.
- `docs/changelog.md` — add an Unreleased entry for the web UI + deployment change.

New backend modules:
- `webui/config_store.py` — small JSON-backed store for providers/workspaces (server-side only).
- `webui/providers.py` — provider types and safe redaction.
- `webui/workspaces.py` — workspace registry + optional git clone/update.
- `webui/router.py` — FastAPI router for UI pages + JSON APIs.

New frontend:
- `webui/frontend/*` — Vite + React SPA (`/` for app, `/admin` for admin).

Deployment:
- `Dockerfile` — multi-stage build (frontend → backend).
- `docs/deploy/cloud-run.md` — recommended “as-free-as-possible” hosting.

## Files to read first

- `proxy.py`, `agent/loop.py`, `agent/tools.py`, `docs/admin-dashboard.md` (completed during implementation).

## Risks

- **Public deployment + secrets:** provider API keys must never be returned to the client; redact in all responses and logs.
- **Command execution:** running arbitrary shell commands is dangerous on a public endpoint; expose only an allow-listed runner and require admin auth.
- **Workspace path traversal:** all file operations must stay within the selected workspace root.

## Acceptance checks

- [ ] `pytest -x` passes
- [ ] SPA build completes (`npm ci && npm run build` in `webui/frontend/`)
- [ ] UI works end-to-end: create agent session → run → see plan/steps/tool trace
- [ ] Admin login works and can manage providers/workspaces
- [ ] No secrets are returned to the client
- [ ] `docs/changelog.md` updated under `## [Unreleased]`


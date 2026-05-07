# Documentation map

Canonical project docs now live under `docs/`.

## Start here

- [README.md](../README.md) — product overview, quick start, UI tour.
- [features.md](features.md) — end-to-end feature inventory.
- [configuration-reference.md](configuration-reference.md) — environment variables and config knobs.
- [troubleshooting.md](troubleshooting.md) — operational fixes and common failure modes.

## Architecture and operations

- [architecture/overview.md](architecture/overview.md)
- [model-routing.md](model-routing.md)
- [runbooks/](runbooks/)
- [deploy/](deploy/)
- [admin-dashboard.md](admin-dashboard.md)
- [telegram-bot.md](telegram-bot.md)

## Screenshots and README sync

- Screenshots are grouped by area under `docs/screenshots/`:
  - `readme/` — screenshots rendered in the README gallery
  - `webui/` — built-in `/app` and `/admin/app` captures
  - `admin/`, `langfuse/`, `telegram/` — docs-only assets
- Run `make ui-docs` after built-in web UI changes to:
  1. capture fresh built-in web UI screenshots
  2. refresh the generated README gallery block
  3. rewrite `docs/screenshots/manifest.json`

## Repo hygiene

- One-off setup transcripts, stale backups, logs, and generated reports were removed from the repo root.
- `scratch/verification/` now holds the lightweight verification prompt/report pair used by `check_auto.py`.

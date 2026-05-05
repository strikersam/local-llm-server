# PRD — README Marketing Refresh

## Original Problem Statement
> There are a lot of new features and pages added to the repo. I don't see the readme doing justice. If you are an analyst and if you know how to market the repo well, take right screenshots and elevate the readme file.

## User Decisions
- Style: hybrid (marketing + technical)
- Screenshots: auto-detect, focus on **LLM Relay v3.1** features
- Branding: pulled from existing repo (no new logo)
- Audience: everyone (devs, recruiters, evaluators, end users)
- Surprise me on extras (badges, comparisons, repo map, CTA)

## What Was Done — 2026-04-27
1. Explored full repo to inventory v3.1 features (control plane, kanban, agents, runtimes, routing policy, providers, models, knowledge wiki, logs, RBAC admin, schedules, settings, setup wizard, login).
2. Seeded the running backend with 4 demo agents, 8 demo tasks across all kanban lanes, and 4 wiki pages so screenshots tell a real story.
3. Captured 14 fresh, high-quality screenshots of the live v3.1 UI (1920x1200, dark theme):
   - `v3-login.png`, `v3-setup-wizard.png`, `v3-control-plane.png`,
     `v3-tasks-kanban.png`, `v3-agents.png`, `v3-runtimes.png`,
     `v3-routing.png`, `v3-providers.png`, `v3-models.png`,
     `v3-knowledge.png`, `v3-chat.png`, `v3-logs.png`, `v3-admin.png`,
     `v3-schedules.png`, `v3-settings.png`.
4. Rewrote `/app/README.md` end-to-end:
   - Hero + 60-second pitch with hard cost numbers
   - "What's new in v3.1" feature matrix (13 pillars)
   - Visual product tour (1 hero shot + 13 contextual screenshots)
   - Comparison table vs Ollama / Paid API
   - Tightened Quick Start, Connect Your Tools (collapsible per IDE)
   - Cleaned API reference (collapsible by surface)
   - Added repo map and refreshed troubleshooting
   - Polished badges (for-the-badge style), styled CTA footer
5. Helper script lives at `/app/scratch/seed_demo_data.py` for re-seeding screenshot data.

## Files Touched
- `/app/README.md` (full rewrite, ~540 lines)
- `/app/docs/screenshots/readme/v3-*.png` (14 new screenshots)
- `/app/scratch/seed_demo_data.py` (new — for repeatable demo data)

## Backlog / Nice-to-Have
- Capture an animated GIF of the kanban → approval → run flow
- Add a "Cost Saved" sparkline chart screenshot once that page renders data
- Replace static placeholder Langfuse screenshots with live ones if the org enables Langfuse

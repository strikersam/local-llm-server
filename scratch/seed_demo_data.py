#!/usr/bin/env python3
"""Seed demo agents, tasks, and wiki pages so the dashboard screenshots tell a story."""
import asyncio
import json
import sys
import urllib.request

BASE = "http://localhost:8001"


def req(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            txt = resp.read().decode()
            return resp.status, json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def login():
    s, body = req("POST", "/api/auth/login", {"email": "admin@llmrelay.local", "password": "WikiAdmin2026!"})
    assert s == 200, body
    return body["access_token"]


AGENTS = [
    {"name": "Code Architect", "description": "Plans large refactors and writes long-form code via DeepSeek-R1 671B.", "model": "deepseek-r1:671b", "task_types": ["coding", "refactor"], "tags": ["coding", "reasoning"], "cost_policy": "local_only", "is_public": True},
    {"name": "Doc Curator",   "description": "Maintains the markdown wiki, fixes orphan pages, summarises long PRs.", "model": "qwen3-coder:30b", "task_types": ["documentation"], "tags": ["wiki", "docs"], "cost_policy": "local_only", "is_public": True},
    {"name": "Triage Bot",    "description": "Auto-labels GitHub issues, drafts replies, escalates to humans only when necessary.", "model": "qwen3-coder:30b", "task_types": ["triage"], "tags": ["github", "ops"], "cost_policy": "local_first_paid_fallback", "is_public": True},
    {"name": "Research Scout", "description": "Reads arxiv + HN, writes daily digests into the knowledge base.", "model": "deepseek-r1:32b", "task_types": ["research"], "tags": ["research"], "cost_policy": "local_only", "is_public": True},
]

TASKS = [
    {"title": "Refactor provider_router fallback chain",     "description": "Apply tier classifier and add unit tests for commercial-escalation gate.", "priority": "high",   "task_type": "refactor", "tags": ["routing", "v3"],    "status": "in_progress"},
    {"title": "Wire approval modal into Tasks Kanban",      "description": "Confirm modal fires on commercial fallback before any paid call lands.",   "priority": "medium", "task_type": "feature",  "tags": ["frontend", "ux"],   "status": "in_progress"},
    {"title": "Index new SKILL.md pack from .claude/skills","description": "Run /agent/skills/search regression after re-index.",                       "priority": "medium", "task_type": "ingest",   "tags": ["skills"],           "status": "todo"},
    {"title": "Daily wiki lint",                            "description": "Cron job at 03:00 to surface orphans and stale references.",                "priority": "low",    "task_type": "automation", "tags": ["wiki"],            "status": "todo"},
    {"title": "Dashboard cost-savings chart",               "description": "Add 30-day rolling chart of $ saved vs the cloud equivalent.",              "priority": "medium", "task_type": "feature",   "tags": ["dashboard"],       "status": "todo"},
    {"title": "Cloudflare tunnel auto-restart",             "description": "Watchdog: if tunnel down >60s, restart with backoff.",                      "priority": "high",   "task_type": "ops",       "tags": ["tunnel", "infra"], "status": "in_review", "requires_approval": True},
    {"title": "RBAC v3 migration script",                   "description": "Backfill permission flags for legacy users; idempotent re-runs.",          "priority": "high",   "task_type": "migration", "tags": ["rbac"],            "status": "blocked"},
    {"title": "DeepSeek-R1 671B benchmark",                 "description": "Sanity check 64k context window with the full reasoning trace.",           "priority": "low",    "task_type": "research",  "tags": ["models"],          "status": "done"},
    {"title": "Telegram bot /restart confirmation",         "description": "Two-step ack before any restart action fires from the bot.",               "priority": "medium", "task_type": "feature",   "tags": ["telegram"],        "status": "done"},
]

WIKI_PAGES = [
    {"slug": "deepseek-r1-671b-on-laptop", "title": "DeepSeek-R1 671B on a single laptop",     "content": "## Overview\n\nWe ran the DeepSeek-R1 671B reasoning model end-to-end on a 128GB workstation using Ollama and the LLM Relay routing layer.\n\n- Throughput: ~14 tok/s with `q4_K_M` quant\n- Cost per 1M tokens: $0.04 in electricity vs $12.84 via the cloud equivalent\n- Memory: 119GB peak, 5–8s TTFB on cold load\n\n## Routing\n\nLLM Relay's tier classifier auto-selects this model for `task_type=reasoning|architecture` and falls back to `deepseek-r1:32b` if VRAM pressure exceeds the threshold.\n", "tags": ["models", "benchmarks", "reasoning"]},
    {"slug": "control-plane-architecture",  "title": "v3.1 Control Plane architecture",        "content": "The Control Plane is split into five panes: WORKSPACE / AGENTS / KNOWLEDGE / INFRASTRUCTURE / SYSTEM.\n\nEach pane is backed by a dedicated FastAPI router and a Mongo collection. The frontend is a single React 18 SPA served either standalone (port 3000) or as static assets via the proxy at `/admin/app`.\n", "tags": ["architecture", "v3"]},
    {"slug": "rbac-v3-permission-matrix",   "title": "RBAC v3 permission matrix",              "content": "Three roles, 27 permission flags, full audit trail. Admins can grant `manage_workspace_agents`, `manage_secrets`, `restart_runtime`, etc. Power Users get a curated subset.\n", "tags": ["rbac", "security"]},
    {"slug": "syncthing-style-peer-sync",   "title": "Syncthing-style peer sync",              "content": "Workspaces sync between machines via HMAC-authenticated WebSocket channels. Conflicts surface as merge requests in the Tasks board rather than silent overwrites.\n", "tags": ["sync", "p2p"]},
]


def main():
    token = login()
    print(f"Logged in. Token len={len(token)}")

    # Seed agents
    for a in AGENTS:
        s, b = req("POST", "/api/agents/", a, token)
        print(f"agent {a['name']} -> {s}")

    # Fetch agents to get IDs
    s, b = req("GET", "/api/agents/", token=token)
    agent_ids = []
    if isinstance(b, dict):
        agent_ids = [x.get("agent_id") for x in (b.get("agents") or b.get("items") or [])]
    elif isinstance(b, list):
        agent_ids = [x.get("agent_id") for x in b]
    print(f"agents available: {len(agent_ids)}")

    # Seed tasks
    for i, t in enumerate(TASKS):
        if agent_ids:
            t = {**t, "agent_id": agent_ids[i % len(agent_ids)]}
        s, b = req("POST", "/api/tasks/", t, token)
        print(f"task {t['title'][:40]} -> {s}")

    # Seed wiki pages
    for p in WIKI_PAGES:
        s, b = req("POST", "/api/wiki/pages", p, token)
        print(f"wiki {p['slug']} -> {s}")


if __name__ == "__main__":
    main()

# Verification Report

| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | DeepSeek API provider | ✅ |  |
| 2 | Zhipu AI (GLM) provider | ✅ |  |
| 3 | AliCloud DashScope (Qwen) provider | ✅ |  |
| 4 | MiniMax provider | ✅ |  |
| 5 | Google Gemini provider | ✅ |  |
| 6 | Moonshot AI (Kimi) provider | ✅ |  |
| 7 | DeepSeek as default LLM provider | ✅ |  |
| 8 | Commercial equivalent pricing for new models | ✅ |  |
| 9 | emit_chat_observation supports task_name | ✅ |  |
| 10 | Auth propagation to agent calls | ✅ |  |
| 11 | Legacy endpoint tracking | ✅ |  |
| 12 | AgentRunner/Coordinator instrumented | ✅ |  |
| 13 | E701 lint fix in update_wiki_page | ✅ |  |
| 14 | Agent chat infinite loading fix | ✅ |  |
| 15 | Orphaned Google OAuth fragment removed | ✅ |  |
| 16 | GitHub OAuth mobile redirect fallback | ✅ |  |
| 17 | Settings page GitHub buttons fixed | ✅ |  |
| 18 | @app.on_event("startup") replaced | ✅ |  |
| 19 | Anthropic/OpenAI 503 on Ollama unreachable | ✅ |  |
| 20 | bash_20250124/text_editor_20250124 stripped | ✅ |  |
| 21 | /agent/terminal/run field command (not cmd) | ✅ |  |
| 22 | /agent/commits NUL-byte separator | ✅ |  |
| 23 | /admin/api/status Linux fix | ✅ |  |
| 24 | /ui/api/providers/{id}/models 503 handling | ✅ |  |
| 25 | GitHub repo listing endpoint | ✅ |  |
| 26 | GitHub repo authorization endpoint | ✅ |  |
| 27 | File-tree explorer | ✅ |  |
| 28 | Inline file editor with commits | ✅ |  |
| 29 | Pull-request panel | ✅ |  |
| 30 | Unified AgentRunner architecture | ✅ |  |
| 31 | github_repo_token injection | ✅ |  |
| 32 | GitHub social login | ✅ |  |
| 33 | Google social login | ✅ |  |
| 34 | CSRF state parameter | ✅ |  |
| 35 | OpenRouter provider | ✅ |  |
| 36 | Together AI provider | ✅ |  |
| 37 | Predefined model catalog | ✅ |  |
| 38 | Live + predefined model merge | ✅ |  |
| 39 | Auto-classification (simple/complex) | ✅ |  |
| 40 | Three-role orchestration (plan/execute/verify) | ✅ |  |
| 41 | AGENT_ROLE_MODELS mapping | ✅ |  |
| 42 | Agent mode toggle in chat UI | ✅ |  |
| 43 | Observation masking (≤300 chars) | ✅ |  |
| 44 | Context compaction (>16 messages) | ✅ |  |
| 45 | HuggingFace serverless in dashboard | ✅ |  |
| 46 | Ollama fallback (OpenAI-compat → native /api/chat) | ✅ |  |
| 47 | ContextManager class | ✅ |  |
| 48 | head_file tool | ✅ |  |
| 49 | file_index tool | ✅ |  |
| 50 | Append-only event log | ✅ |  |
| 51 | AgentEvent model | ✅ |  |
| 52 | AgentSession.event_count | ✅ |  |
| 53 | Sub-agent condensed summaries | ✅ |  |
| 54 | Resilient tool dispatch | ✅ |  |
| 55 | Advisor tool types stripped | ✅ |  |
| 56 | Advisor result blocks converted | ✅ |  |
| 57 | docs/architecture/advisor-strategy.md | ✅ |  |
| 58 | HF_TOKEN env-var sync on startup | ✅ |  |
| 59 | ChatMessage.session_id nullable | ✅ |  |
| 60 | [object Object] error in dashboard chat | ✅ |  |
| 61 | [object Object] error in webui | ✅ |  |
| 62 | Docker dashboard profile | ✅ |  |
| 63 | Browser automation disabled by default | ✅ |  |
| 64 | render.yaml correct config | ✅ |  |
| 65 | docker-compose.yml correct services | ✅ |  |
| 66 | deploy-frontend.yml correct paths | ✅ |  |
| 67 | Dockerfile.frontend correct project | ✅ |  |
| 68 | /v1/models includes Claude aliases | ❌ | Missing files: Code in models endpoint. Found in git history: d9dc551 feat: multi-agent orchestration, cloud providers, and model catalog |
| 69 | .env.example cleaned | ✅ |  |
| 70 | MODEL_MAP parser fix | ✅ |  |
| 71 | KeyStore corruption handling | ✅ |  |
| 72 | Dockerfile HEALTHCHECK | ✅ |  |
| 73 | Vercel disabled | ✅ |  |
| 74 | pytest.ini test discovery | ✅ |  |
| 75 | VITE_API_BASE support | ✅ |  |
| 76 | Cloudflare Tunnel profile | ✅ |  |
| 77 | Persistent agent memory (SQLite) | ✅ |  |
| 78 | Durable session history (SQLite) | ✅ |  |
| 79 | Memory-aware planning | ✅ |  |
| 80 | CLAUDE.md root guide | ✅ |  |
| 81 | AGENTS.md + TOOLS.md | ✅ |  |
| 82 | .claude/skills/ (11 skills) | ✅ |  |
| 83 | .claude/hooks/ (3 hooks) | ✅ |  |
| 84 | .claude/agents/ (4 personas) | ✅ |  |
| 85 | .claude/agents/scout.md | ✅ |  |
| 86 | .claude/commands/ | ✅ |  |
| 87 | .claude/state/ | ✅ |  |
| 88 | scripts/ai_runner.py | ✅ |  |
| 89 | Makefile | ✅ |  |
| 90 | .github/workflows/ci.yml | ✅ |  |
| 91 | .github/workflows/changelog-check.yml | ✅ |  |
| 92 | .github/PULL_REQUEST_TEMPLATE.md | ✅ |  |
| 93 | .github/CODEOWNERS | ✅ |  |
| 94 | agent/memory.py (SessionMemory) | ✅ |  |
| 95 | agent/context.py (ContextCompressor) | ✅ |  |
| 96 | agent/permissions.py (AdaptivePermissions) | ✅ |  |
| 97 | agent/token_budget.py (TokenBudget) | ✅ |  |
| 98 | agent/coordinator.py (AgentCoordinator) | ✅ |  |
| 99 | agent/background.py (BackgroundAgent) | ✅ |  |
| 100 | agent/scheduler.py (AgentScheduler) | ✅ |  |
| 101 | agent/playbook.py (PlaybookLibrary) | ✅ |  |
| 102 | agent/watchdog.py (ResourceWatchdog) | ✅ |  |
| 103 | agent/commit_tracker.py (CommitTracker) | ✅ |  |
| 104 | agent/scaffolding.py (ProjectScaffolder) | ✅ |  |
| 105 | agent/skills.py (SkillLibrary) | ✅ |  |
| 106 | agent/terminal.py (TerminalPanel) | ✅ |  |
| 107 | agent/browser.py (BrowserSession) | ✅ |  |
| 108 | agent/voice.py (VoiceCommandInterface) | ✅ |  |
| 109 | /agent/memory/* | ❌ | Missing files: snapshot, restore, list, delete. Not found in git history. |
| 110 | /agent/context/* | ❌ | Missing files: compress, inspect. Not found in git history. |
| 111 | /agent/sessions/{id}/snip | ❌ | Missing files: Message removal by index. Found in git history: 8282b2e docs: fill README gaps — managed-agents, user memory, SQLite, ngrok, admin API |
| 112 | /agent/sessions/{id}/permissions | ❌ | Missing files: Adaptive permission check. Found in git history: 8282b2e docs: fill README gaps — managed-agents, user memory, SQLite, ngrok, admin API |
| 113 | /agent/budget/* | ❌ | Missing files: set, get, list. Not found in git history. |
| 114 | /agent/coordinate | ❌ | Missing files: Multi-agent dispatch. Not found in git history. |
| 115 | /agent/background/* | ❌ | Missing files: Task queue CRUD. Not found in git history. |
| 116 | /agent/scheduler/* | ❌ | Missing files: Cron CRUD + trigger. Not found in git history. |
| 117 | /agent/playbooks/* | ❌ | Missing files: CRUD + run lifecycle. Not found in git history. |
| 118 | /agent/watchdog/* | ❌ | Missing files: Watch CRUD + manual check. Not found in git history. |
| 119 | /agent/scaffolding/* | ❌ | Missing files: Template list + apply. Not found in git history. |
| 120 | /agent/skills/* | ❌ | Missing files: List, search, MCP registration. Not found in git history. |
| 121 | /agent/commits | ❌ | Missing files: AI-attributed commit log. Found in git history: c1f95c3 merge: claude/test-fix-model-ui-M3EYG — model UI testing and bug fixes |
| 122 | /agent/terminal/* | ❌ | Missing files: Snapshot + command capture. Found in git history: c1f95c3 merge: claude/test-fix-model-ui-M3EYG — model UI testing and bug fixes |
| 123 | /agent/browser/* | ❌ | Missing files: Start/stop/action. Not found in git history. |
| 124 | /agent/voice/* | ❌ | Missing files: Status + transcription. Not found in git history. |
| 125 | Context manager tests (14) | ✅ |  |
| 126 | Event log tests (8) | ✅ |  |
| 127 | Agent tools extended (6 new) | ✅ |  |
| 128 | Model router tests (40) | ✅ |  |
| 129 | Total suite ≥210 tests | ❌ | Missing files: Run pytest --co -q and count. Not found in git history. |
| 130 | No hardcoded tunnel domain in README | ✅ |  |
| 131 | Provider API keys not returned | ✅ |  |
| 132 | Admin-only command runner | ✅ |  |
| 133 | router/ package | ✅ |  |
| 134 | ModelRouter | ✅ |  |
| 135 | RoutingDecision dataclass | ✅ |  |
| 136 | Task classifier | ✅ |  |
| 137 | fast_response category | ✅ |  |
| 138 | Model capability registry | ✅ |  |
| 139 | ROUTER_EXTRA_MODELS env var | ✅ |  |
| 140 | X-Model-Override header | ✅ |  |
| 141 | Ollama health check | ✅ |  |
| 142 | Fallback execution on 5xx | ✅ |  |
| 143 | Routing metadata in Langfuse | ✅ |  |
| 144 | docs/model-routing.md | ✅ |  |
| 145 | docs/screenshots/ (12 screenshots) | ✅ |  |
| 146 | scripts/gen_screenshots.py | ✅ |  |
| 147 | docs/claude-code-setup.md | ❌ | Missing files: File exists. Found in git history: ffdf556 docs(v2.2): complete documentation overhaul + new model support |
| 148 | docs/telegram-bot.md | ❌ | Missing files: File exists. Found in git history: 0f46e21 security: remove exposed secrets from documentation |
| 149 | docs/admin-dashboard.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 150 | docs/features.md | ❌ | Missing files: File exists. Found in git history: 01d83fa feat: ngrok permanent static URL + configurable Public URL in Admin UI |
| 151 | docs/langfuse-observability.md | ❌ | Missing files: File exists. Found in git history: d35d223 docs(v2.2.1): add 12 screenshots + wire into documentation |
| 152 | docs/configuration-reference.md | ❌ | Missing files: File exists. Found in git history: 01d83fa feat: ngrok permanent static URL + configurable Public URL in Admin UI |
| 153 | docs/troubleshooting.md | ❌ | Missing files: File exists. Found in git history: ffdf556 docs(v2.2): complete documentation overhaul + new model support |
| 154 | commercial_equivalent.py updated pricing | ✅ |  |
| 155 | download_models.ps1 | ❌ | Missing files: File exists with -Lightweight, -IncludeFlagship, -Extended, -CloudProxy flags. Found in git history: ffdf556 docs(v2.2): complete documentation overhaul + new model support |
| 156 | Claude 4.6 model IDs in _BUILTIN_MODEL_MAP | ✅ |  |
| 157 | .env.example updated with Claude 4.6 | ✅ |  |
| 158 | PROXY_DEFAULT_MAX_TOKENS = 8192 | ✅ |  |
| 159 | Agent model env vars documented | ✅ |  |
| 160 | INFRA_* defaults for Intel AI PC | ✅ |  |
| 161 | generate_api_key.py shim | ❌ | Missing files: generate_api_key.py (root). Found in git history: c45682e fix(v2.0.1): env config, gitignore, test imports, generate_api_key shim |
| 162 | POST /v1/messages Anthropic compat | ✅ |  |
| 163 | x-api-key header support | ❌ | Missing files: Auth middleware. Found in git history: 4f6fc00 feat(v2.0): Claude Code compat, agent package, infra cost, Telegram bot |
| 164 | MODEL_MAP env var | ❌ | Missing files: handlers/anthropic_compat.py or router/. Found in git history: 9b5ee29 fix: 4 additional bugs from QA audit |
| 165 | GET /v1/models with aliases | ❌ | Missing files: Models endpoint. Found in git history: c4c5e5c fix: replace missing _build_model_map with get_registry() in /v1/models |
| 166 | infra_cost.py | ✅ |  |
| 167 | Langfuse infra cost annotations | ✅ |  |
| 168 | latency_ms, ttft_ms, tokens_per_sec | ✅ |  |
| 169 | telegram_bot.py | ✅ |  |
| 170 | agent/ package structure | ✅ |  |
| 171 | scripts/generate_api_key.py | ✅ |  |
| 172 | handlers/ package | ✅ |  |
| 173 | Agent endpoints (session-based) | ✅ |  |
| 174 | Admin UI | ❌ | Missing files: templates/admin/ or webui/. Found in git history: 01d83fa feat: ngrok permanent static URL + configurable Public URL in Admin UI |
| 175 | Langfuse integration | ✅ |  |
| 176 | Rate limiting | ❌ | Missing files: Auth/middleware code. Not found in git history. |
| 177 | CORS configuration | ❌ | Missing files: proxy.py or backend/server.py. Not found in git history. |
| 178 | Think-tag stripping | ❌ | Missing files: Relevant handler. Not found in git history. |
| 179 | Exact-output short-circuit | ❌ | Missing files: Relevant handler. Not found in git history. |
| 180 | docs/architecture/overview.md | ❌ | Missing files: File exists. Found in git history: 0ba0568 feat: add advisor strategy support to Anthropic compat layer |
| 181 | docs/architecture/agent-orchestration.md | ❌ | Missing files: File exists. Found in git history: 0ba0568 feat: add advisor strategy support to Anthropic compat layer |
| 182 | docs/runbooks/auto-resume.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 183 | docs/runbooks/release.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 184 | docs/runbooks/openclaw-setup.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 185 | docs/adrs/001-local-llm-proxy.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 186 | docs/adrs/002-model-routing.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 187 | docs/adrs/003-multi-agent-orchestration.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 188 | docs/admin/github-branch-protection.md | ❌ | Missing files: File exists. Found in git history: 0dc71d7 feat: retrofit repo-native AI engineering system |
| 189 | docs/deploy/cloud-run.md | ❌ | Missing files: File exists. Not found in git history. |
| 190 | docs/deploy/docker.md | ❌ | Missing files: File exists. Not found in git history. |
| 191 | webui/frontend/ SPA | ✅ |  |
| 192 | webui/router.py | ✅ |  |
| 193 | webui/providers.py | ✅ |  |
| 194 | webui/workspaces.py | ✅ |  |
| 195 | Dockerfile bundles SPA | ✅ |  |
| 196 | .dockerignore | ✅ |  |

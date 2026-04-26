# PRD — LLM Relay Critical Issues Fixes

## Original Problem Statement
My repo has the attached issues as mentioned in the pdf and I would like you to fix all of them. You can do one by one in the order of severity and priority that you determine and keep pushing changes to master one by one. Do not stop until all the issues and fixed and tested.

User follow-up: fix by criticality/priority, proceed autonomously, make/test changes in the workspace; user will use Save to Github when ready.

## Architecture Decisions
- Added a centralized `ProviderRouter` that supports priority-ordered provider fallback, retry with exponential backoff, health checking, OpenAI-compatible providers, Ollama native fallback, and Anthropic message conversion.
- Wired provider fallback into proxy chat completions, backend chat calls, and `AgentRunner` so agent chat no longer depends on a single Ollama-only path.
- Reworked multi-agent coordination around `MultiAgentSwarm`, task dependencies, capability-based agent assignment, bounded concurrency, blocked task reporting, and retry handling while preserving the legacy workers API.
- Hardened Docker Compose startup by replacing strict Ollama health waits for dependent services with `service_started`, adding a process-level `/live` proxy liveness endpoint, and using `ollama list` for Ollama health.

## Implemented
- Automatic provider fallback chain for `/v1/chat/completions`, backend LLM calls, and agent runtime LLM calls.
- Dependency-aware `/agent/coordinate` flow with `agents` + `tasks`, plus backward-compatible `workers` support.
- Structured provider attempt metadata and clear `503` failure when all configured providers fail.
- Docker Compose health/dependency improvements and `/live` liveness endpoint.
- Regression tests for provider fallback, model fallback, agent runner fallback, multi-agent dependencies, legacy coordinate compatibility, and compose validation.

## Validation
- Main-agent full test suite: `624 passed, 1 warning`.
- Independent testing-agent backend validation: `22/22 targeted tests passed`; report at `/app/test_reports/iteration_5.json`.
- Docker Compose syntax/health/dependency rules validated via YAML parsing because Docker CLI is unavailable in this environment.

## Backlog
### P0
- None remaining from the PDF issues.

### P1
- Enforce fail-fast production configuration for sensitive secrets and admin credentials in oversized legacy modules.
- Add live integration tests for configured cloud providers when real API credentials are available.

### P2
- Split `proxy.py` and `backend/server.py` into smaller modules for easier review and safer future changes.
- Add dashboard visibility for provider fallback attempts and multi-agent task timelines.

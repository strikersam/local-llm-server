# CLAUDE.md — router/

> Model routing is a core correctness concern. Changes here affect every request
> in the system. Read this before modifying any file in this package.

---

## What This Package Does

`router/` provides the central model-selection layer for all API surfaces.

```
model_router.py   ModelRouter.route() → RoutingDecision
classifier.py     classify_task() → task category string
registry.py       Model capability registry + best_model_for()
health.py         Ollama /api/tags health check + TTL cache
```

Selection priority (highest first):
1. Manual override (`X-Model-Override` header or `override_model` kwarg)
2. `MODEL_MAP` env var (or built-in Anthropic alias table)
3. Heuristic: task classification → capability registry lookup
4. Default: `AGENT_EXECUTOR_MODEL`

---

## Invariants — Do Not Break

1. **`route()` always returns a `RoutingDecision`.** It must never raise; use defaults on failure.
2. **`resolved_model` is always a non-empty string.**
3. **`fallback_chain` is always a list** (may be empty).
4. **Health check is cached.** TTL is `ROUTER_HEALTH_CACHE_TTL` (default 60 s). The cache is intentionally invalidated before fallback retries.
5. **`is_model_available()` returns `True` when health checks are disabled.** This is the safe-degrade path — never invert it.
6. **Passthrough models** (local Ollama model names) bypass the alias table and go directly to `RoutingDecision(selection_source="passthrough")`.

---

## Adding a New Model

1. Add an entry to `MODEL_REGISTRY` in `registry.py`.
2. Set `strengths` accurately — this drives heuristic selection.
3. Set `cost_tier` (1=cheapest, higher=more expensive) — used for fast-response routing.
4. Add a test in `tests/test_model_router.py` for the new model's routing behaviour.
5. Update `docs/architecture/overview.md` if the model changes the capability profile.

---

## Adding a New Task Category

1. Add the category string to the classifier in `classifier.py`.
2. Add matching logic (keyword, heuristic, or metadata-based).
3. Update `MODEL_REGISTRY` entries to list the new category in `strengths` where appropriate.
4. Add tests in `tests/test_model_router.py` under the "Task classification" section.

---

## Environment Variables

```
MODEL_MAP                   Colon-separated alias overrides. E.g. "claude-sonnet-4-6:deepseek-r1:32b"
ROUTER_EXTRA_MODELS         Add models at runtime: "name:type:strength1+strength2"
ROUTER_HEALTH_CHECK_ENABLED Set "false" to disable health filtering (useful in tests)
ROUTER_HEALTH_CACHE_TTL     Cache TTL in seconds (default: 60)
ROUTER_FAST_RESPONSE_CHARS  Char threshold for fast_response classification (default: 200)
AGENT_EXECUTOR_MODEL        Default fallback model when nothing else resolves
```

---

## Testing

All router tests live in `tests/test_model_router.py`.
Run with: `pytest -x tests/test_model_router.py`

Key test areas to always cover after changes:
- Manual override still takes priority
- Built-in alias table maps correctly
- Heuristic fallback works when alias not found
- Health check bypass works (`ROUTER_HEALTH_CHECK_ENABLED=false`)
- Singleton `reset_router()` works between tests

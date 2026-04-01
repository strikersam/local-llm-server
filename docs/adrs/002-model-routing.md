# ADR 002: Dynamic Model Routing with Task Classification

**Status:** Accepted
**Date:** 2026-03-31

## Context

Different task types benefit from different models. Code generation benefits from
Qwen3-Coder's large code training set. Planning and reasoning tasks benefit from
DeepSeek-R1's chain-of-thought capability. We need to route automatically without
requiring clients to know local model names.

## Decision

Implement a centralized `ModelRouter` in `router/` with:
1. **Priority-based selection:** override → MODEL_MAP → heuristic → default
2. **Task classification:** lightweight regex-based, no LLM call required
3. **Model capability registry:** declarative model capability profiles
4. **Health check integration:** skip unavailable models, walk fallback chain
5. **Anthropic alias translation:** `claude-opus-4-6` → `deepseek-r1:32b` etc.

## Consequences

### Positive
- Clients using any Claude alias get the best available local model
- Task classification adds ~0.1ms overhead (regex only)
- Health check prevents failed requests to unavailable models
- `ROUTER_EXTRA_MODELS` env var allows extending the registry without code changes

### Negative
- Heuristic classification is not perfect (keyword-based)
- Fast-response optimization relies on accurate model `cost_tier` in the registry
- Health check adds 2s latency on cache miss (mitigated by 60s TTL)

### Neutral
- Routing metadata in Langfuse enables future analysis of model performance by task type

# ADR 001: Self-Hosted OpenAI-Compatible Proxy

**Status:** Accepted
**Date:** 2026-03-31

## Context

AI coding tools (Claude Code, Cursor, Aider, Continue) expect an OpenAI-compatible
`/v1/chat/completions` endpoint. We want to run local LLMs (Ollama) without requiring
developers to reconfigure their tools or pay per-token to cloud APIs during development.

## Decision

Build a FastAPI proxy that:
1. Exposes OpenAI and Anthropic-compatible API surfaces
2. Authenticates with Bearer token auth (so tools work without modification)
3. Forwards to locally-running Ollama
4. Applies intelligent model routing to map cloud model names to local equivalents
5. Emits Langfuse traces for cost/performance observability

## Consequences

### Positive
- AI coding tools work unchanged — just point at `http://localhost:8000`
- No per-token cloud costs during development for code completion
- Full observability via Langfuse
- Model routing allows testing multiple local models transparently

### Negative
- Requires Ollama running locally (GPU or CPU)
- Large model downloads required (Qwen3-Coder: 17-19 GB, DeepSeek-R1: 20 GB)
- Latency higher than cloud APIs for first token

### Neutral
- The proxy adds ~1-5ms overhead, negligible for LLM workloads

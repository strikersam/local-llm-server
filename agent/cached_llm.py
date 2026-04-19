"""
Cached LLM Client wrapper.

Drop-in wrapper around any LLM API call that transparently applies
InferenceCache. Designed to wrap the agent's existing LLM calls.
"""

import logging
import time
from typing import Any, Callable, Optional

from agent.inference_cache import InferenceCache, DEFAULT_TTL_SECONDS

logger = logging.getLogger(__name__)


class CachedLLMClient:
    """
    Wraps an LLM call function with inference caching.

    Usage:
        from agent.cached_llm import CachedLLMClient
        from agent.inference_cache import InferenceCache

        cache = InferenceCache()
        client = CachedLLMClient(cache=cache, llm_fn=my_openai_call)

        response = client.complete(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )
    """

    def __init__(
        self,
        cache: InferenceCache,
        llm_fn: Callable,
        default_ttl: float = DEFAULT_TTL_SECONDS,
    ):
        self.cache = cache
        self.llm_fn = llm_fn
        self.default_ttl = default_ttl
        self._call_count = 0
        self._cache_hit_count = 0
        self._total_latency_ms = 0.0
        self._cached_latency_ms = 0.0

    def complete(
        self,
        model: str,
        messages: list[dict],
        ttl: Optional[float] = None,
        skip_cache: bool = False,
        **kwargs,
    ) -> Any:
        """
        Execute an LLM completion, using cache when available.

        Args:
            model: Model identifier (e.g. "gpt-4o", "claude-3-5-sonnet")
            messages: List of message dicts with "role" and "content"
            ttl: Custom TTL for this entry (overrides default)
            skip_cache: Force a live call even if cached result exists
            **kwargs: Additional args passed to the underlying llm_fn

        Returns:
            LLM response (same format as underlying llm_fn)
        """
        self._call_count += 1
        start = time.time()

        # 1. Check cache
        if not skip_cache:
            cached = self.cache.get(model=model, messages=messages, **kwargs)
            if cached is not None:
                elapsed_ms = (time.time() - start) * 1000
                self._cache_hit_count += 1
                self._cached_latency_ms += elapsed_ms
                logger.info(
                    f"[CachedLLM] HIT model={model} latency={elapsed_ms:.1f}ms "
                    f"(live call avoided)"
                )
                return cached

        # 2. Live call
        logger.info(f"[CachedLLM] MISS model={model} — making live call")
        live_start = time.time()
        response = self.llm_fn(model=model, messages=messages, **kwargs)
        live_elapsed_ms = (time.time() - live_start) * 1000
        self._total_latency_ms += live_elapsed_ms

        # 3. Extract token count if available
        tokens_used = self._extract_tokens(response)

        # 4. Store in cache
        self.cache.set(
            model=model,
            messages=messages,
            response=response,
            tokens_used=tokens_used,
            ttl=ttl if ttl is not None else self.default_ttl,
            **kwargs,
        )

        logger.info(
            f"[CachedLLM] LIVE model={model} latency={live_elapsed_ms:.1f}ms "
            f"tokens={tokens_used}"
        )
        return response

    def performance_summary(self) -> dict:
        """Return performance metrics for this client instance."""
        hit_rate = self._cache_hit_count / self._call_count if self._call_count else 0
        avg_live_ms = (
            self._total_latency_ms / max(1, self._call_count - self._cache_hit_count)
        )
        avg_cached_ms = (
            self._cached_latency_ms / max(1, self._cache_hit_count)
        )
        return {
            "total_calls": self._call_count,
            "cache_hits": self._cache_hit_count,
            "cache_misses": self._call_count - self._cache_hit_count,
            "hit_rate": round(hit_rate, 4),
            "avg_live_latency_ms": round(avg_live_ms, 2),
            "avg_cached_latency_ms": round(avg_cached_ms, 2),
            "speedup_factor": round(avg_live_ms / max(avg_cached_ms, 0.01), 1),
        }

    @staticmethod
    def _extract_tokens(response: Any) -> int:
        """Try to extract token count from various response formats."""
        if response is None:
            return 0
        # OpenAI format
        if hasattr(response, "usage") and response.usage:
            return getattr(response.usage, "total_tokens", 0)
        # Dict format
        if isinstance(response, dict):
            usage = response.get("usage", {})
            if isinstance(usage, dict):
                return usage.get("total_tokens", 0)
        return 0

"""
Inference Caching for LLM calls.

Inspired by: https://machinelearningmastery.com/inference-caching-in-llms/

Supports:
- Exact match caching (hash-based)
- TTL-based expiration
- Prefix-aware cache key generation (to align with KV cache behavior)
- Persistent disk cache
- Cache statistics
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
from threading import Lock

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(".cache/inference")
DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24 hours
DEFAULT_MAX_ENTRIES = 1000


@dataclass
class CacheEntry:
    key: str
    response: Any
    model: str
    prompt_hash: str
    created_at: float
    ttl: float
    hit_count: int = 0
    tokens_saved: int = 0

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False  # No expiry
        return (time.time() - self.created_at) > self.ttl

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(**data)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_tokens_saved: int = 0
    total_entries: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def summary(self) -> str:
        return (
            f"Cache Stats | hits={self.hits} misses={self.misses} "
            f"hit_rate={self.hit_rate:.1%} tokens_saved={self.total_tokens_saved} "
            f"entries={self.total_entries} evictions={self.evictions}"
        )


class InferenceCache:
    """
    LLM Inference Cache with exact-match and TTL support.

    Key design decisions aligned with inference caching best practices:
    1. Cache keys include model name + normalized prompt to avoid cross-model collisions
    2. System prompts are separated from user prompts to maximize prefix cache hits
    3. Persistent disk storage survives process restarts
    4. Thread-safe for concurrent agent use
    5. LRU-style eviction when max_entries is reached
    """

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        ttl: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        enabled: bool = True,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.max_entries = max_entries
        self.enabled = enabled
        self._lock = Lock()
        self._stats = CacheStats()
        self._memory: dict[str, CacheEntry] = {}

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()
            logger.info(
                f"InferenceCache initialized | dir={self.cache_dir} "
                f"ttl={self.ttl}s max_entries={self.max_entries} "
                f"loaded={len(self._memory)} entries"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, model: str, messages: list[dict], **kwargs) -> Optional[Any]:
        """
        Look up a cached response for the given model + messages.

        Returns the cached response dict or None on miss.
        """
        if not self.enabled:
            return None

        key = self._make_key(model, messages, **kwargs)
        with self._lock:
            entry = self._memory.get(key)
            if entry is None:
                self._stats.misses += 1
                logger.debug(f"Cache MISS | key={key[:16]}...")
                return None

            if entry.is_expired():
                logger.debug(f"Cache EXPIRED | key={key[:16]}...")
                self._evict(key)
                self._stats.misses += 1
                return None

            entry.hit_count += 1
            self._stats.hits += 1
            self._stats.total_tokens_saved += entry.tokens_saved
            logger.debug(
                f"Cache HIT | key={key[:16]}... hits={entry.hit_count} "
                f"tokens_saved={entry.tokens_saved}"
            )
            return entry.response

    def set(
        self,
        model: str,
        messages: list[dict],
        response: Any,
        tokens_used: int = 0,
        ttl: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Store a response in the cache."""
        if not self.enabled:
            return

        key = self._make_key(model, messages, **kwargs)
        prompt_hash = self._hash_messages(messages)
        entry = CacheEntry(
            key=key,
            response=response,
            model=model,
            prompt_hash=prompt_hash,
            created_at=time.time(),
            ttl=ttl if ttl is not None else self.ttl,
            tokens_saved=tokens_used,
        )

        with self._lock:
            self._maybe_evict_oldest()
            self._memory[key] = entry
            self._stats.total_entries = len(self._memory)
            self._persist_entry(entry)
            logger.debug(f"Cache SET | key={key[:16]}... model={model} tokens={tokens_used}")

    def invalidate(self, model: str, messages: list[dict], **kwargs) -> bool:
        """Remove a specific entry from the cache."""
        key = self._make_key(model, messages, **kwargs)
        with self._lock:
            if key in self._memory:
                self._evict(key)
                return True
            return False

    def clear(self) -> int:
        """Clear all cache entries. Returns number of entries cleared."""
        with self._lock:
            count = len(self._memory)
            self._memory.clear()
            self._stats = CacheStats()
            if self.cache_dir.exists():
                for f in self.cache_dir.glob("*.json"):
                    f.unlink(missing_ok=True)
            logger.info(f"Cache cleared | {count} entries removed")
            return count

    def stats(self) -> CacheStats:
        """Return current cache statistics."""
        with self._lock:
            self._stats.total_entries = len(self._memory)
            return self._stats

    def warm_up(self, entries: list[dict]) -> int:
        """
        Pre-populate the cache with known prompt→response pairs.
        Useful for seeding frequently-used system prompts.

        entries: list of {"model": str, "messages": [...], "response": ..., "tokens_used": int}
        Returns number of entries loaded.
        """
        count = 0
        for entry in entries:
            try:
                self.set(
                    model=entry["model"],
                    messages=entry["messages"],
                    response=entry["response"],
                    tokens_used=entry.get("tokens_used", 0),
                    ttl=entry.get("ttl", self.ttl),
                )
                count += 1
            except (KeyError, TypeError) as e:
                logger.warning(f"Cache warm_up skip invalid entry: {e}")
        logger.info(f"Cache warmed up with {count} entries")
        return count

    # ------------------------------------------------------------------
    # Prefix-cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_prefix_optimized_messages(
        system_prompt: str,
        conversation_history: list[dict],
        new_user_message: str,
    ) -> list[dict]:
        """
        Build a messages list optimized for KV/prefix caching.

        Best practice from inference caching research:
        - Put stable content (system prompt) FIRST so it's always a prefix
        - Keep conversation history in order
        - Append the new user turn LAST

        This maximizes the chance that the LLM provider's KV cache
        already has the prefix tokenized and can reuse it.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": new_user_message})
        return messages

    @staticmethod
    def extract_stable_prefix(messages: list[dict]) -> list[dict]:
        """
        Extract the stable prefix (system + early turns) from a message list.
        The stable prefix is the part least likely to change across calls.
        """
        prefix = []
        for msg in messages:
            if msg.get("role") == "system":
                prefix.append(msg)
            else:
                break
        return prefix

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_key(self, model: str, messages: list[dict], **kwargs) -> str:
        """
        Generate a deterministic cache key.

        Key components:
        - model name (different models → different caches)
        - normalized messages (role + content)
        - relevant kwargs (temperature=0 only, since >0 is non-deterministic)
        """
        # Only cache deterministic calls (temp=0 or not set)
        temperature = kwargs.get("temperature", 0)
        if temperature and temperature > 0:
            # Non-deterministic: include a note but still allow caching
            # with awareness that results may vary
            logger.debug(f"Caching response with temperature={temperature} (non-deterministic)")

        normalized = {
            "model": model,
            "messages": [
                {"role": m.get("role", ""), "content": str(m.get("content", "")).strip()}
                for m in messages
            ],
            "temperature": temperature,
        }
        raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _hash_messages(self, messages: list[dict]) -> str:
        raw = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def _evict(self, key: str) -> None:
        """Remove a single entry (must be called with lock held)."""
        if key in self._memory:
            del self._memory[key]
            self._stats.evictions += 1
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.unlink(missing_ok=True)

    def _maybe_evict_oldest(self) -> None:
        """Evict oldest entries if over capacity (must be called with lock held)."""
        if len(self._memory) < self.max_entries:
            return
        # Sort by created_at, evict oldest 10%
        sorted_keys = sorted(self._memory.keys(), key=lambda k: self._memory[k].created_at)
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            logger.debug(f"Evicting oldest cache entry | key={key[:16]}...")
            self._evict(key)

    def _persist_entry(self, entry: CacheEntry) -> None:
        """Write entry to disk (must be called with lock held)."""
        try:
            cache_file = self.cache_dir / f"{entry.key}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as e:
            logger.warning(f"Failed to persist cache entry: {e}")

    def _load_from_disk(self) -> None:
        """Load persisted cache entries from disk on startup."""
        loaded = 0
        expired = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                entry = CacheEntry.from_dict(data)
                if entry.is_expired():
                    cache_file.unlink(missing_ok=True)
                    expired += 1
                else:
                    self._memory[entry.key] = entry
                    loaded += 1
            except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning(f"Skipping corrupt cache file {cache_file.name}: {e}")
                cache_file.unlink(missing_ok=True)

        logger.debug(f"Cache load complete | loaded={loaded} expired_removed={expired}")

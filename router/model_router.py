"""Dynamic model router.

Central routing logic for all chat and agent requests.  Every request
passes through ``ModelRouter.route()`` which returns a ``RoutingDecision``
describing exactly which local Ollama model to call and *why*.

Selection priority (highest to lowest):
    1. Manual override via ``X-Model-Override`` header or ``override_model`` kwarg
    2. Explicit MODEL_MAP match (backwards-compatible Anthropic name translation)
    3. Heuristic task classification → best-fit model from capability registry
    4. Default model (AGENT_EXECUTOR_MODEL env var)

Usage::

    from router.model_router import get_router, RoutingDecision

    decision = get_router().route(
        requested_model="claude-opus-4-6",
        messages=openai_messages,
        system=system_text,
        has_tools=bool(tools),
        stream=stream,
    )
    local_model = decision.resolved_model
    # Pass decision.to_meta() to emit_chat_observation() for tracking
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from router.classifier import classify_task
from router.health import is_model_available
from router.registry import best_model_for, get_registry

log = logging.getLogger("qwen-proxy")


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Full record of a routing decision — both what was chosen and why.

    Fields:
        resolved_model:   Ollama model name that will be called.
        requested_model:  Raw model name the client sent (may be a Claude alias).
        mode:             ``"auto"`` (heuristic) or ``"manual"`` (explicit override).
        routing_reason:   Human-readable explanation of the choice.
        task_category:    Classified task type (e.g. ``"code_generation"``).
        selection_source: How the model was chosen:
                          ``"override"``      — X-Model-Override header / kwarg
                          ``"model_map"``     — MODEL_MAP / built-in alias table
                          ``"heuristic"``     — task-classification registry lookup
                          ``"passthrough"``   — client sent a valid local model name
                          ``"default"``       — fell back to AGENT_EXECUTOR_MODEL
        fallback_chain:   Other models we could try on failure (ordered).
        provider:         Backend provider (always ``"ollama"`` today).
    """

    resolved_model: str
    requested_model: str | None
    mode: str                       # "auto" | "manual"
    routing_reason: str
    task_category: str
    selection_source: str
    fallback_chain: list[str] = field(default_factory=list)
    provider: str = "ollama"

    def to_meta(self) -> dict[str, Any]:
        """Flat dict suitable for Langfuse observation metadata."""
        return {
            "routing_mode": self.mode,
            "routing_requested_model": self.requested_model or "",
            "routing_resolved_model": self.resolved_model,
            "routing_reason": self.routing_reason,
            "routing_task_category": self.task_category,
            "routing_selection_source": self.selection_source,
            "routing_fallback_chain": ",".join(self.fallback_chain),
            "routing_provider": self.provider,
        }


# ── Model map (Anthropic alias → local) ──────────────────────────────────────

_BUILTIN_MODEL_MAP: dict[str, str] = {
    # Claude 4.6 family
    "claude-opus-4-6":            "deepseek-r1:32b",
    "claude-sonnet-4-6":          "qwen3-coder:30b",
    "claude-haiku-4-5-20251001":  "qwen3-coder:30b",
    # Claude 4.5 family
    "claude-opus-4-5":            "deepseek-r1:32b",
    "claude-opus-4":              "deepseek-r1:32b",
    "claude-sonnet-4-5":          "qwen3-coder:30b",
    "claude-sonnet-4":            "qwen3-coder:30b",
    # Claude 3.5 family
    "claude-3-5-sonnet-20241022": "qwen3-coder:30b",
    "claude-3-5-haiku-20241022":  "qwen3-coder:30b",
    # Claude 3 family
    "claude-3-opus-20240229":     "deepseek-r1:32b",
    "claude-3-sonnet-20240229":   "qwen3-coder:30b",
    "claude-3-haiku-20240307":    "qwen3-coder:30b",
}

_resolved_model_map: dict[str, str] | None = None


def _get_model_map() -> dict[str, str]:
    """Merge built-in defaults with MODEL_MAP env overrides (lazy, cached)."""
    global _resolved_model_map
    if _resolved_model_map is not None:
        return _resolved_model_map

    merged = dict(_BUILTIN_MODEL_MAP)
    raw = os.environ.get("MODEL_MAP", "").strip()
    if raw:
        for pair in raw.split(","):
            pair = pair.strip()
            if not pair:
                continue
            if ":" not in pair:
                continue
            # split on first ":" only — dst may itself contain colons (e.g. "qwen3-coder:30b")
            src, dst = pair.split(":", 1)
            src, dst = src.strip(), dst.strip()
            if src and dst:
                merged[src] = dst

    _resolved_model_map = merged
    return merged


def _default_model() -> str:
    return os.environ.get("AGENT_EXECUTOR_MODEL", "qwen3-coder:30b")


def _default_reasoning_model() -> str:
    return os.environ.get("AGENT_PLANNER_MODEL", "deepseek-r1:32b")


# ── Router ────────────────────────────────────────────────────────────────────

class ModelRouter:
    """Central model router.  Create one instance (use ``get_router()``).

    ``route()`` is the single entry point for all model selection decisions.
    Callers should treat the returned ``RoutingDecision`` as immutable.
    """

    def route(
        self,
        *,
        requested_model: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        system: str | None = None,
        has_tools: bool = False,
        stream: bool = False,
        override_model: str | None = None,
        endpoint_type: str = "chat",
        context_tokens: int | None = None,
    ) -> RoutingDecision:
        """Decide which Ollama model to use for this request.

        Args:
            requested_model:  Model field from the client request (may be a
                              Claude alias like ``"claude-opus-4-6"`` or a local
                              Ollama name like ``"qwen3-coder:30b"``).
            messages:         OpenAI-format messages (used for task classification).
            system:           System prompt text (if separated from messages).
            has_tools:        True when tool/function definitions are present.
            stream:           Whether the client requested streaming (used for fast_response detection).
            override_model:   Explicit local model name from ``X-Model-Override``
                              header or API parameter. Bypasses all other logic.
            endpoint_type:    One of ``"chat"``, ``"agent_plan"``,
                              ``"agent_execute"``, ``"agent_verify"``.
            context_tokens:   Estimated prompt token count (enables long-context
                              routing when > 16 000).

        Returns:
            A ``RoutingDecision`` with ``resolved_model`` set to the Ollama model
            name to call.
        """
        # ── 1. Manual override — highest priority ─────────────────────────────
        if override_model and override_model.strip():
            return RoutingDecision(
                resolved_model=override_model.strip(),
                requested_model=requested_model,
                mode="manual",
                routing_reason=f"Explicit override via X-Model-Override → {override_model.strip()}",
                task_category="unknown",
                selection_source="override",
                fallback_chain=[_default_model()],
            )

        # ── 2. Classify the task ──────────────────────────────────────────────
        category = classify_task(
            messages=messages,
            system=system,
            endpoint_type=endpoint_type,
            has_tools=has_tools,
            context_tokens=context_tokens,
            stream=stream,
        )

        # ── 3. MODEL_MAP lookup (Anthropic alias translation) ─────────────────
        model_map = _get_model_map()
        if requested_model and requested_model in model_map:
            resolved = model_map[requested_model]
            resolved = self._ensure_available(resolved, category, requested_model)
            return RoutingDecision(
                resolved_model=resolved,
                requested_model=requested_model,
                mode="auto",
                routing_reason=(
                    f"MODEL_MAP: {requested_model} → {resolved} "
                    f"(task: {category})"
                ),
                task_category=category,
                selection_source="model_map",
                fallback_chain=self._fallback_chain(resolved, category),
            )

        # Catch-all MODEL_MAP wildcard
        if "*" in model_map:
            resolved = model_map["*"]
            resolved = self._ensure_available(resolved, category, requested_model)
            return RoutingDecision(
                resolved_model=resolved,
                requested_model=requested_model,
                mode="auto",
                routing_reason=f"MODEL_MAP wildcard (*) → {resolved} (task: {category})",
                task_category=category,
                selection_source="model_map",
                fallback_chain=self._fallback_chain(resolved, category),
            )

        # ── 4. Check if requested model is already a known local model ────────
        registry = get_registry()
        if requested_model and requested_model in registry:
            return RoutingDecision(
                resolved_model=requested_model,
                requested_model=requested_model,
                mode="auto",
                routing_reason=f"Client passed local model name directly: {requested_model}",
                task_category=category,
                selection_source="passthrough",
                fallback_chain=self._fallback_chain(requested_model, category),
            )

        # ── 5. Heuristic: pick best model for the classified task ─────────────
        best = best_model_for(category, registry)
        if best:
            best = self._ensure_available(best, category, requested_model)
            return RoutingDecision(
                resolved_model=best,
                requested_model=requested_model,
                mode="auto",
                routing_reason=(
                    f"Heuristic: task={category} → {best}"
                    + (f" (client requested {requested_model!r})" if requested_model else "")
                ),
                task_category=category,
                selection_source="heuristic",
                fallback_chain=self._fallback_chain(best, category),
            )

        # ── 6. Ultimate fallback ──────────────────────────────────────────────
        default = _default_model()
        log.warning(
            "ModelRouter: no match for requested=%r category=%s — falling back to %s",
            requested_model,
            category,
            default,
        )
        return RoutingDecision(
            resolved_model=default,
            requested_model=requested_model,
            mode="auto",
            routing_reason=f"Default fallback (AGENT_EXECUTOR_MODEL={default})",
            task_category=category,
            selection_source="default",
            fallback_chain=[],
        )

    def _ensure_available(
        self,
        model: str,
        category: str,
        requested_model: str | None,
    ) -> str:
        """Return *model* if it is available in Ollama, else the first available
        fallback.  If no fallback is available either, return *model* unchanged
        (let the call fail naturally with a clear error from Ollama).
        """
        if is_model_available(model):
            return model

        log.warning(
            "ModelRouter: preferred model %r not available in Ollama "
            "(task=%s, requested=%r) — trying fallback chain",
            model, category, requested_model,
        )
        for fb in self._fallback_chain(model, category):
            if is_model_available(fb):
                log.info("ModelRouter: using fallback model %r", fb)
                return fb

        # Nothing in the fallback chain is available either — return original
        # so Ollama returns a clear 404/error rather than silently wrong output.
        log.warning("ModelRouter: no available fallback found — using %r anyway", model)
        return model

    def _fallback_chain(self, primary: str, category: str) -> list[str]:
        """Build an ordered list of alternative models to try if *primary* fails."""
        registry = get_registry()
        alternatives: list[str] = []

        for cap in registry.values():
            if cap.name == primary:
                continue
            if category in cap.strengths:
                alternatives.append(cap.name)

        # Always include the default executor as a last resort
        default = _default_model()
        if default not in alternatives and default != primary:
            alternatives.append(default)

        return alternatives[:3]  # Keep the chain short


# ── Module-level singleton ─────────────────────────────────────────────────────

_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    """Return the shared ``ModelRouter`` singleton."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def reset_router() -> None:
    """Reset the singleton and clear the cached model map (test helper)."""
    global _router, _resolved_model_map
    _router = None
    _resolved_model_map = None

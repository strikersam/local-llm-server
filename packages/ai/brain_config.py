"""services/brain_config_store.py — DB-persisted, UI-switchable "brain" config.

Implements the architectural change specified in
``docs/plans/db-brain-switcher.md`` (PR #824):

* One Pydantic ``BrainConfig`` model holds the active provider + the
  per-role (planner / executor / verifier / judge) model ids.
* Persistence is a single document in the ``app_settings`` Mongo
  collection keyed ``_id="brain_config"``, **mirrored to a sqlite row**
  so the no-Mongo CI/dev path still works. This mirrors the dual-storage
  pattern used by ``key_store.py`` and the company-graph store.
* An in-process cache with a short TTL (5s) + explicit ``invalidate()``
  on write so a UI change is picked up by the next agent run without a
  restart — the core call-time resolution requirement of the plan.
* ``get_brain_config()`` never raises: on any store error it returns the
  safe default so a DB outage can never brick the agent loop.

The store deliberately keeps **only model ids and provider names** —
never API keys. Keys stay in env (``NVIDIA_API_KEY`` / ``CEREBRAS_API_KEY``
/ ``GROQ_API_KEY`` / ``OLLAMA_BASE``) so a leaked DB document does not
leak credentials.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

log = logging.getLogger("brain_config_store")


# ── Model catalog loader (config/models.yaml) ──────────────────────────────
#
# The YAML file at ``config/models.yaml`` is the canonical source of truth
# for per-provider metadata, role presets, and the failover candidate list.
# It is loaded once at module import time. If the file is missing or
# corrupt, the in-module hardcoded defaults below are used — a bad YAML
# edit can never brick the agent loop.
#
# The hardcoded dicts are kept in sync with the YAML so a no-YAML install
# behaves identically to a YAML-present install. Tests in
# ``tests/test_model_catalog.py`` enforce parity.

_MODELS_YAML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "models.yaml",
)


def _load_models_yaml() -> dict[str, Any] | None:
    """Load ``config/models.yaml`` and return the parsed dict.

    Returns ``None`` on any error (missing file, YAML parse error, schema
    mismatch). Callers fall back to the in-module hardcoded defaults.
    """
    try:
        if not os.path.isfile(_MODELS_YAML_PATH):
            return None
        import yaml  # PyYAML — implicit dep already used by agent/loop_registry.py
        with open(_MODELS_YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return None
        if not isinstance(data.get("providers"), dict):
            return None
        return data
    except Exception as exc:  # noqa: BLE001 — never break module import
        log.warning("brain_config_store: models.yaml load failed (%s) — using hardcoded defaults", exc)
        return None


def _provider_ids_from_literal() -> tuple[str, ...]:
    """Return the provider ids allowed by the ``BrainProvider`` Literal.

    Reads the Literal's args via ``typing.get_args`` so adding a provider
    to the Literal (and to ``config/models.yaml``) is the only change
    needed — no parallel list to keep in sync.
    """
    import typing
    args = typing.get_args(BrainProvider)
    return tuple(str(a) for a in args)  # type: ignore[name-defined]


def _build_presets_from_yaml(yaml_data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Extract the per-provider ``role_presets`` mapping from the YAML."""
    out: dict[str, dict[str, str]] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        presets = pinfo.get("role_presets") or {}
        if not isinstance(presets, dict):
            continue
        clean: dict[str, str] = {}
        for role in ("planner", "executor", "verifier", "judge"):
            v = presets.get(role)
            if isinstance(v, str) and v.strip():
                clean[role] = v.strip()
        if clean:
            out[str(pid)] = clean
    return out


def _build_key_env_from_yaml(yaml_data: dict[str, Any]) -> dict[str, str | None]:
    """Extract the per-provider ``key_env`` mapping from the YAML."""
    out: dict[str, str | None] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        v = pinfo.get("key_env")
        out[str(pid)] = str(v) if isinstance(v, str) and v.strip() else None
    return out


def _build_base_url_env_from_yaml(yaml_data: dict[str, Any]) -> dict[str, str | None]:
    """Extract the per-provider ``base_url_env`` mapping from the YAML."""
    out: dict[str, str | None] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        v = pinfo.get("base_url_env")
        out[str(pid)] = str(v) if isinstance(v, str) and v.strip() else None
    return out


def _build_default_base_url_from_yaml(yaml_data: dict[str, Any]) -> dict[str, str]:
    """Extract the per-provider ``default_base_url`` mapping from the YAML."""
    out: dict[str, str] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        v = pinfo.get("default_base_url")
        if isinstance(v, str) and v.strip():
            out[str(pid)] = v.strip()
    return out


def _build_candidates_from_yaml(yaml_data: dict[str, Any]) -> dict[str, list[str]]:
    """Extract the per-provider ``candidates`` failover list from the YAML."""
    out: dict[str, list[str]] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        cands = pinfo.get("candidates") or []
        if not isinstance(cands, list):
            continue
        clean: list[str] = []
        for c in cands:
            if isinstance(c, str) and c.strip():
                clean.append(c.strip())
        if clean:
            out[str(pid)] = clean
    return out


def _build_display_names_from_yaml(yaml_data: dict[str, Any]) -> dict[str, str]:
    """Extract the per-provider ``display_name`` mapping from the YAML."""
    out: dict[str, str] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        v = pinfo.get("display_name")
        if isinstance(v, str) and v.strip():
            out[str(pid)] = v.strip()
    return out


def _build_tier_from_yaml(yaml_data: dict[str, Any]) -> dict[str, str]:
    """Extract the per-provider ``tier`` mapping from the YAML."""
    out: dict[str, str] = {}
    for pid, pinfo in (yaml_data.get("providers") or {}).items():
        v = pinfo.get("tier")
        if isinstance(v, str) and v.strip():
            out[str(pid)] = v.strip().lower()
    return out

# ── Safe default ────────────────────────────────────────────────────────────
#
# The plan's hard constraint #1: "Never land on a dead model. Always keep a
# known-good fallback." The 49B Nemotron Super is the live-verified (2026-06-20
# probe) model the rest of the codebase already uses as its free-brain default
# (see ``brain_policy.DEFAULT_FREE_NVIDIA_MODEL``). A bad DB write or a corrupt
# config doc must never displace it.
SAFE_DEFAULT_PROVIDER: str = "nvidia"
SAFE_DEFAULT_MODEL: str = "nvidia/nemotron-3-super-120b-a12b"

# Provider ids the Brain card recognises. The Literal keeps the Pydantic model
# strict so a typo in the UI ("cerebrass") fails validation instead of
# silently storing an unusable provider.
BrainProvider = Literal["nvidia", "tokenin", "cerebras", "groq", "ollama", "mistral", "deepseek", "zhipu", "zai", "together", "dashscope", "moonshot", "openrouter", "anthropic", "aerolink", "google"]

# Per-provider sensible presets surfaced by the UI's "presets" dropdown.
# Operators can still type any model id — these are just convenience defaults.
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "cerebras": {
        # Probed 2026-08-29: the account serves gpt-oss-120b and gemma-4-31b.
        # The four ids previously here answered 404. See config/models.yaml.
        # 2026-09-07: catalogue-probe found gpt-oss-120b returns HTTP 402.
        # All roles now use gemma-4-31b.
        "planner":   "gemma-4-31b",
        "executor":  "gemma-4-31b",
        "verifier":  "gemma-4-31b",
        "judge":     "gemma-4-31b",
    },
    "groq": {
        # Probed 2026-09-01 (run 33483861221): HTTP 200 plus a real tool_call.
        "planner":   "openai/gpt-oss-120b",
        "executor":  "openai/gpt-oss-120b",
        "verifier":  "openai/gpt-oss-120b",
        "judge":     "openai/gpt-oss-120b",
    },
    "nvidia": {
        "planner":   "nvidia/nemotron-3-super-120b-a12b",
        "executor":  "nvidia/nemotron-3-super-120b-a12b",
        "verifier":  "nvidia/nemotron-3-super-120b-a12b",
        "judge":     "nvidia/nemotron-3-super-120b-a12b",
    },
    "tokenin": {
        "planner":   "myt/deepseek-v4-pro-free",
        "executor":  "myt/glm-5.3-free",
        "verifier":  "myt/glm-5.3-free",
        "judge":     "myt/deepseek-v4-pro-free",
    },
    "ollama": {
        "planner":   "deepseek-r1:32b",
        "executor":  "north-mini-code-1.0",
        "verifier":  "deepseek-r1:32b",
        "judge":     "deepseek-r1:32b",
    },
    "mistral": {
        "planner":   "mistral-large-latest",
        "executor":  "mistral-small-latest",
        "verifier":  "mistral-small-latest",
        "judge":     "mistral-large-latest",
    },
    "deepseek": {
        "planner":   "deepseek-chat",
        "executor":  "deepseek-coder",
        "verifier":  "deepseek-chat",
        "judge":     "deepseek-chat",
    },
    "zai": {
        "planner":   "glm-5.2",
        "executor":  "glm-5.2",
        "verifier":  "glm-5.2",
        "judge":     "glm-5.2",
    },
    "colibri": {
        "planner":   "glm-5.2",
        "executor":  "glm-5.2",
        "verifier":  "glm-5.2",
        "judge":     "glm-5.2",
    },
    "aerolink": {
        # 2026-09-07: catalogue-probe found claude-sonnet-5 returns HTTP 400.
        # Executor and verifier now use claude-opus-4-8.
        "planner":   "claude-opus-5",
        "executor":  "claude-opus-4-8",
        "verifier":  "claude-opus-4-8",
        "judge":     "claude-opus-5",
    },
    "anthropic": {
        # 2026-09-07: catalogue-probe found claude-sonnet-5 returns HTTP 400.
        # Executor and verifier now use claude-opus-4-8.
        "planner":   "claude-opus-5",
        "executor":  "claude-opus-4-8",
        "verifier":  "claude-opus-4-8",
        "judge":     "claude-opus-5",
    },
    "google": {
        "planner":   "gemini-2.5-pro",
        "executor":  "gemini-2.5-flash",
        "verifier":  "gemini-2.5-flash",
        "judge":     "gemini-2.5-pro",
    },
}

# Env-var names each provider reads its API key from. Used by the GET endpoint
# to surface "key present" flags to the UI without exposing the key itself.
PROVIDER_KEY_ENV: dict[str, str | None] = {
    "nvidia":  "NVIDIA_API_KEY",
    "tokenin": "TOKENIN_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "groq":    "GROQ_API_KEY",
    "ollama":  None,  # local — no key
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "zhipu":   "ZHIPU_API_KEY",
    "zai":     "ZAI_API_KEY",
    "together": "TOGETHER_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "aerolink": "AEROLINK_API_KEY",
    "google": "GOOGLE_API_KEY",
    # local — no key (colibri serves GLM-5.2 744B MoE on `coli serve`, OpenAI-compat).
    # uses port 8081; COLIBRI_URL / COLIBRI_MODEL / COLIBRI_ENABLED env are read by
    # providers/colibri.py at provider registration time.
    "colibri": None,
}

# Env-var name each provider reads its base URL from (optional override).
PROVIDER_BASE_URL_ENV: dict[str, str | None] = {
    "nvidia":   "NVIDIA_BASE_URL",
    "tokenin":  "TOKENIN_BASE_URL",
    "cerebras": "CEREBRAS_BASE_URL",
    "groq":     "GROQ_BASE_URL",
    "ollama":   "OLLAMA_BASE",
    "mistral":  "MISTRAL_BASE_URL",
    "deepseek": "DEEPSEEK_BASE_URL",
    "zhipu":    "ZHIPU_BASE_URL",
    "zai":      "ZAI_BASE_URL",
    "together": "TOGETHER_BASE_URL",
    "dashscope": "DASHSCOPE_BASE_URL",
    "moonshot": "MOONSHOT_BASE_URL",
    "openrouter": "OPENROUTER_BASE_URL",
    "anthropic": "ANTHROPIC_BASE_URL",
    "aerolink": "AEROLINK_BASE_URL",
    "google": "GOOGLE_BASE_URL",
    "colibri": "COLIBRI_URL",
}

# Default public base URL for each provider (used when no env override).
PROVIDER_DEFAULT_BASE_URL: dict[str, str] = {
    "nvidia":   "https://integrate.api.nvidia.com",
    "tokenin":  "https://tokenin.my.id/v1",
    "cerebras": "https://api.cerebras.ai",
    "groq":     "https://api.groq.com/openai/v1",
    "ollama":   "http://localhost:11434",
    "mistral":  "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "zhipu":    "https://open.bigmodel.cn/api/paas/v4",
    "zai":      "https://api.z.ai/api/paas/v4",
    "together": "https://api.together.xyz/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com",
    "aerolink": "https://capi.aerolink.lat/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    # Local — port 8081 serves `coli serve` for the JustVugg/colibri GLM-5.2 runtime.
    # Override via the COLIBRI_URL env var when the operator tunnels the port.
    "colibri":  "http://localhost:8081/v1",
}

# Per-provider failover candidate list. The first model is the preset;
# subsequent models are tried in order by the watchdog / brain_failover
# chain on 404 / 410 / timeout. Mirrored from config/models.yaml.
# NOTE: append-only — adding a provider adds an entry above and inserts into
# the YAML catalog; never reorder existing keys (sort-stable external contract).
PROVIDER_CANDIDATES: dict[str, list[str]] = {
    "nvidia": [
        # Probed live 2026-08-28 — every id here returned HTTP 200 to a real
        # completion. The previous list was made entirely of ids that were
        # listed in the catalogue and returned 410 or 404 when called.
        "nvidia/nemotron-3-super-120b-a12b",
        # Intermittent, not dead — 404 at 17:02/17:05 on 2026-08-28, then HTTP
        # 200 with a real tool_call at 23:25 and again on 2026-08-29 07:37.
        # Kept behind the default, which has answered on every probe.
        "nvidia/nemotron-3-ultra-550b-a55b",
        "mistralai/mistral-nemotron",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ],
    # tokenin.my.id — free frontier gateway. Ordered highest-RPM first so the
    # rotation prefers the models that 429 least; opus is last so it stays a
    # reachable fallback without soaking up the scarce 2 req/min budget.
    "tokenin": [
        "myt/glm-5.3-free",
        "myt/deepseek-v4-pro-free",
        "myt/MiniMax-M3-free",
        "myt/mimo-v2.5-free",
        "myt/qwen3.8-max-free",
        "myt/kimi-k3-free",
        "myt/gemini-3.5-flash-free",
        "myt/grok-4.6-free",
        "myt/gpt-5.6-sol-free",
        "myt/claude-opus-4-8-free",
    ],
    "cerebras": [
        # Read off the account's own /v1/models on 2026-08-29, not from docs.
        # Everything else this file used to list answers 404.
        # 2026-09-07: catalogue-probe found gpt-oss-120b returns HTTP 402.
        # Removed from candidates; only gemma-4-31b remains.
        "gemma-4-31b",
    ],
    "groq": [
        # Probed against the live account 2026-09-01 (run 33483861221): each
        # returned HTTP 200 to a real completion and emitted a genuine
        # tool_call. The five ids previously here are none of them in this
        # account's 14-model catalogue; the three that were tried answered
        # 404/400 (run 33483766556) and the other two were never checked.
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
    ],
    "mistral": [
        "mistral-small-latest",
        "mistral-large-latest",
        "codestral-latest",
        "mistral-nemo",
    ],
    "deepseek": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
    "zhipu": ["glm-5.2", "glm-5.1", "glm-4", "glm-4-flash", "glm-4-air"],
    "zai": ["glm-5.2", "glm-5.1", "glm-4-flash", "glm-4", "glm-4-air"],
    "together": [
        "Llama-3.3-70B-Instruct-Turbo-Free",
        "Mixtral-8x7B-Instruct-v0.1-Free",
    ],
    "dashscope": ["qwen-plus", "qwen-max", "qwen-turbo", "qwen-coder-plus"],
    "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    "openrouter": [
        "cohere/north-mini-code:free",
        "meta-llama/llama-3.3-70b-instruct",
        "anthropic/claude-3.5-sonnet",
    ],
    "anthropic": [
        # 2026-09-07: catalogue-probe found claude-sonnet-5 returns HTTP 400.
        # Removed from candidates.
        "claude-opus-5",
        "claude-fable-5",
        "claude-opus-4-8",
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-6",
    ],
    "aerolink": [
        # 2026-09-07: catalogue-probe found claude-sonnet-5 returns HTTP 400.
        # Removed from candidates.
        "claude-opus-5",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-fable-5",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "ollama": ["north-mini-code-1.0", "deepseek-r1:32b", "qwen3-coder:30b", "qwen3-coder:7b", "llama3.3:70b"],
    # Colibri serves a single loaded model — the watchdog's failover chain stays
    # on the same id. If coli ever exposes an int8 or fp8 fallback model, append
    # it here.
    "colibri": ["glm-5.2"],
}

# Per-provider human-readable label surfaced by the BrainCard dropdown.
# When the UI's PROVIDER_LABELS map doesn't have an entry, it falls back
# to this dict (UNIT 5 makes the UI server-driven).
PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "nvidia":    "NVIDIA NIM (free, broad catalogue)",
    "tokenin":   "TokenIn (free frontier gateway)",
    "cerebras":  "Cerebras (fast, free tier)",
    "groq":      "Groq (fast, free tier)",
    "ollama":    "Local Ollama (no key, private)",
    "mistral":   "Mistral (free tier)",
    "deepseek":  "DeepSeek (free tier)",
    "zhipu":     "ZhipuAI / GLM (China)",
    "zai":       "Z.ai (GLM international)",
    "together":  "Together AI (free tier)",
    "dashscope": "Qwen DashScope (Alibaba)",
    "moonshot":  "Moonshot / Kimi (China)",
    "openrouter": "OpenRouter (paid aggregator)",
    "anthropic": "Anthropic (Claude, paid)",
    "aerolink":  "Aerolink (Claude gateway)",
    "colibri":   "Local Colibri / GLM-5.2 (no key, private, ~370 GB on disk)",
}

# Per-provider tier: free | paid | local. Used by brain_failover to order
# the failover chain (free first, paid last when ALLOW_PAID_BRAIN=true,
# local always available if configured).
PROVIDER_TIERS: dict[str, str] = {
    "nvidia":    "free",
    "tokenin":   "free",
    "cerebras":  "free",
    "groq":      "free",
    "mistral":   "free",
    "deepseek":  "free",
    "zhipu":     "free",
    "zai":       "free",
    "together":  "free",
    "dashscope": "free",
    "moonshot":  "free",
    "openrouter": "paid",
    "anthropic": "paid",
    "aerolink":  "paid",
    "ollama":    "local",
    "colibri":   "local",
}


def get_provider_candidates(provider: str) -> list[str]:
    """Return the ordered failover candidate list for *provider*.

    The first element is the role preset; subsequent elements are tried in
    order by the watchdog / brain_failover chain on 404 / 410 / timeout.
    Returns an empty list if the provider is unknown (callers fall back to
    the safe default model).
    """
    return list(PROVIDER_CANDIDATES.get(provider, []))


def get_provider_display_name(provider: str) -> str:
    """Return the human-readable label for *provider* (fallback: the id)."""
    return PROVIDER_DISPLAY_NAMES.get(provider, provider)


def get_provider_tier(provider: str) -> str:
    """Return the tier (``free`` / ``paid`` / ``local``) for *provider*.

    Returns ``"unknown"`` if the provider isn't in the catalog.
    """
    return PROVIDER_TIERS.get(provider, "unknown")


def all_provider_ids() -> tuple[str, ...]:
    """Return every provider id recognised by the brain config system.

    Iterates the ``BrainProvider`` Literal via ``typing.get_args`` so
    adding a provider to the Literal (and to ``config/models.yaml``) is
    the only change needed — no parallel list to keep in sync.
    """
    return _provider_ids_from_literal()


# ── Apply YAML overrides (catalog is the source of truth) ───────────────────
#
# Load ``config/models.yaml`` once at module import. If present + valid,
# the YAML overrides the hardcoded defaults above. The hardcoded defaults
# stay as the fallback so a missing/corrupt YAML never breaks the agent
# loop. Tests in ``tests/test_model_catalog.py`` verify both paths.

_YAML_DATA: dict[str, Any] | None = _load_models_yaml()
if _YAML_DATA is not None:
    # Override the in-module dicts with the YAML data. Use ``update`` so a
    # partial YAML (only some providers) doesn't lose entries from the
    # hardcoded fallback for the providers it doesn't mention.
    PROVIDER_PRESETS.update(_build_presets_from_yaml(_YAML_DATA))
    PROVIDER_KEY_ENV.update(_build_key_env_from_yaml(_YAML_DATA))
    PROVIDER_BASE_URL_ENV.update(_build_base_url_env_from_yaml(_YAML_DATA))
    PROVIDER_DEFAULT_BASE_URL.update(_build_default_base_url_from_yaml(_YAML_DATA))
    PROVIDER_CANDIDATES.update(_build_candidates_from_yaml(_YAML_DATA))
    PROVIDER_DISPLAY_NAMES.update(_build_display_names_from_yaml(_YAML_DATA))
    PROVIDER_TIERS.update(_build_tier_from_yaml(_YAML_DATA))

    # Override the safe-default provider/model if the YAML specifies one.
    _yaml_safe = _YAML_DATA.get("safe_default") or {}
    if isinstance(_yaml_safe, dict):
        _sp = _yaml_safe.get("provider")
        _sm = _yaml_safe.get("model")
        if isinstance(_sp, str) and _sp.strip():
            SAFE_DEFAULT_PROVIDER = _sp.strip()  # noqa: PLW0603
        if isinstance(_sm, str) and _sm.strip():
            SAFE_DEFAULT_MODEL = _sm.strip()  # noqa: PLW0603

    # Override the recommended priority if the YAML specifies one.
    _yaml_prio = _YAML_DATA.get("recommended_priority")
    if isinstance(_yaml_prio, list) and _yaml_prio:
        _clean_prio = tuple(str(p).strip() for p in _yaml_prio if isinstance(p, str) and p.strip())
        if _clean_prio:
            RECOMMENDED_PROVIDER_PRIORITY = _clean_prio  # noqa: PLW0603


def resolve_hermes_base_url() -> str:
    """Resolve the base URL of the agency's own Hermes server.

    Precedence: ``HERMES_BASE_URL`` env → ``http://localhost:8100`` default.
    In docker-compose the backend gets ``HERMES_BASE_URL=http://hermes:8100``
    so the Hermes runtime (``services/hermes_server.py``) is reachable with no
    extra config. Sync + never raises; safe for the adapter's hot path.
    """
    return (os.environ.get("HERMES_BASE_URL") or "http://localhost:8100").strip().rstrip("/")


def resolve_ollama_base_url() -> str:
    """Resolve the Ollama base URL the UI controls — DB value wins over env.

    Precedence:
      1. The ``ollama_base_url`` saved from the Brain card (read synchronously
         from the sqlite mirror, which is written on every Apply even when Mongo
         is primary). This is how the operator points the brain at a local /
         tunnelled Ollama **from the UI, with no env/redeploy**.
      2. ``OLLAMA_BASE`` / ``OLLAMA_BASE_URL`` env (legacy / dev).
      3. ``http://localhost:11434`` default.

    Sync + never raises so it is safe to call from hot resolution paths
    (``provider_base_url``, ``brain_policy``, the internal-agent adapter).
    """
    try:
        cfg = BrainConfigStore()._load_sqlite_mirror()
        if cfg is not None:
            ui_url = (getattr(cfg, "ollama_base_url", "") or "").strip()
            if ui_url:
                return ui_url.rstrip("/")
    except Exception:  # pragma: no cover - defensive; never break resolution
        pass
    env_url = (os.environ.get("OLLAMA_BASE") or os.environ.get("OLLAMA_BASE_URL") or "").strip()
    return (env_url or "http://localhost:11434").rstrip("/")


def provider_base_url(provider: str) -> str:
    """Return the OpenAI-compatible base URL for *provider* (env- and UI-aware)."""
    # Ollama's base URL is UI-configurable (DB-persisted) so a local/tunnelled
    # Ollama can be the brain without touching Render env. DB value wins.
    if provider == "ollama":
        return resolve_ollama_base_url()
    env_key = PROVIDER_BASE_URL_ENV.get(provider)
    if env_key:
        v = (os.environ.get(env_key) or "").strip()
        if v:
            return v.rstrip("/")
    return PROVIDER_DEFAULT_BASE_URL.get(provider, "")


def provider_api_key(provider: str) -> str | None:
    """Return the live API key for *provider* (env-only — never persisted)."""
    env_key = PROVIDER_KEY_ENV.get(provider)
    if not env_key:
        return None
    return (os.environ.get(env_key) or "").strip() or None


def _provider_env_value(provider: str, suffix: str) -> str | None:
    """Read a per-provider env var, tolerating dashes in the provider id.

    Provider ids from the router are slugs like ``nvidia-nim``; naively
    upper-casing them yields ``NVIDIA-NIM_MAX_RPM``, which most shells and
    dashboards refuse to set. We look up the literal upper-cased name first
    (so any var an operator already set keeps working) and then the
    dash-to-underscore variant, which is the one that is actually settable.
    """
    literal = f"{provider.upper()}{suffix}"
    raw = os.environ.get(literal)
    if raw:
        return raw
    normalized = f"{provider.upper().replace('-', '_')}{suffix}"
    if normalized != literal:
        return os.environ.get(normalized)
    return None


def _provider_positive_float(provider: str, suffix: str) -> float | None:
    """Shared parse/validate for the numeric per-provider traffic budgets.

    Returns None when the var is unset, unparseable, non-finite, or <= 0 —
    every one of which must mean "no limit configured" rather than a limit of
    zero, which would wedge the provider out of rotation permanently.
    """
    raw = _provider_env_value(provider, suffix)
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def provider_max_rpm(provider: str) -> float | None:
    """Return the operator-configured requests/min cap for *provider*, or
    None if unset/invalid. Reads ``<PROVIDER>_MAX_RPM`` (dynamic per-provider
    key, so any provider id works without a YAML entry — unlike
    ``PROVIDER_KEY_ENV``, this isn't a fixed table). Used by
    ``packages/ai/rate_limiter.py`` to pace requests and by
    ``packages/ai/traffic_director.py`` to route around a provider that has
    already spent its minute; centralized here rather than read directly so
    the value is validated once, in the config module, not in business logic.
    """
    return _provider_positive_float(provider, "_MAX_RPM")


def provider_max_tpm(provider: str) -> float | None:
    """Return the operator-configured tokens/min cap for *provider*.

    Reads ``<PROVIDER>_MAX_TPM``. Free tiers usually publish both a request
    and a token ceiling, and the token one is what large-context agent calls
    actually hit first. Unset means "unknown" — the traffic director then
    distributes on request count alone.
    """
    return _provider_positive_float(provider, "_MAX_TPM")


def provider_weight(provider: str) -> float | None:
    """Return the operator-configured share weight for *provider*.

    Reads ``<PROVIDER>_WEIGHT``. Used only by the ``weighted-shuffle``
    routing strategy: a provider with weight 3 is picked roughly three times
    as often as one with weight 1. Unset means the director falls back to
    remaining RPM headroom, then to an equal share.
    """
    return _provider_positive_float(provider, "_WEIGHT")


def provider_max_parallel(provider: str) -> int | None:
    """Return the operator-configured in-flight request cap for *provider*.

    Reads ``<PROVIDER>_MAX_PARALLEL``. This is the concurrency ceiling that
    NVIDIA NIM enforces with 419 responses; setting it lets the router spread
    load to a sibling provider instead of collecting the 419 first.

    A fractional value is rounded rather than truncated, and anything that
    rounds below 1 is treated as unset. ``int(0.5)`` would otherwise be ``0``,
    and a concurrency cap of zero makes the ``in_flight >= cap`` check true at
    zero in-flight requests — excluding the provider permanently. That is
    exactly the "limit of zero" outcome a malformed value must never produce.
    """
    value = _provider_positive_float(provider, "_MAX_PARALLEL")
    if value is None:
        return None
    rounded = round(value)
    return rounded if rounded >= 1 else None


def routing_strategy() -> str:
    """Return the configured traffic-distribution strategy (lower-cased).

    Reads ``LLM_ROUTING_STRATEGY`` and defaults to ``priority``, which is the
    router's historical strict priority order. Validation of the name against
    the supported set lives in ``packages/ai/traffic_director.py`` so this
    module stays free of routing logic.
    """
    return (os.environ.get("LLM_ROUTING_STRATEGY") or "priority").strip().lower()


# Numbered suffixes past the base key variable are probed up to this many times.
# The scan stops at the first gap regardless, so this only bounds a pathological
# scan; it is not a supported number of accounts.
_MAX_EXTRA_KEYS: int = 10


def provider_key_rotation_enabled(provider: str) -> bool:
    """True when the operator has explicitly opted *this provider* into using
    more than one API key.

    Deliberately opt-in per provider rather than automatic. Several providers'
    acceptable-use policies prohibit registering additional accounts to exceed
    published rate limits — Groq's, for one, states this explicitly — so
    discovering ``<KEY>_2`` and silently using it would let the platform commit
    a terms violation on the operator's behalf, from nothing more than an env
    var being present. Requiring ``<PROVIDER>_KEY_ROTATION=true`` makes that a
    decision someone took, for a provider they checked.
    """
    raw = _provider_env_value(provider, "_KEY_ROTATION") or ""
    return raw.strip().lower() in ("1", "true", "yes", "on")


def provider_api_keys(provider: str, base_env: str) -> list[str]:
    """Every API key configured for *provider*, primary first.

    Reads ``base_env`` then ``base_env_2``, ``_3`` … but **only** when
    :func:`provider_key_rotation_enabled` is true for the provider; otherwise
    just the primary key is returned and any siblings are ignored.

    The scan stops at the first gap so a typo'd ``_4`` cannot silently promote
    itself into the ``_2`` slot, leaving an operator believing three keys are
    live when two are. Duplicates are dropped: the same key twice is one
    budget, and counting it twice would advertise capacity that does not exist
    while halving the real cooldown.

    Lives here rather than in the pool because this module is the only place
    permitted to read the environment (CLAUDE.md §3), and because a
    secret-discovery path in particular should sit where the project's config
    review looks for it.
    """
    primary = (os.environ.get(base_env) or "").strip()
    if not primary:
        # No primary means no keys, even when a sibling variable survives. The
        # first-gap rule has to start at the first slot or it is not a gap rule:
        # otherwise clearing `<BASE>` to switch a provider off would silently
        # promote a leftover `<BASE>_2` and keep dispatching on it.
        return []
    keys: list[str] = [primary]
    if not provider_key_rotation_enabled(provider):
        return keys
    for index in range(2, _MAX_EXTRA_KEYS + 2):
        value = (os.environ.get(f"{base_env}_{index}") or "").strip()
        if not value:
            break
        if value not in keys:
            keys.append(value)
    return keys


def provider_key_present(provider: str) -> bool:
    """True when the env var for *provider*'s key is set (or it's Ollama)."""
    if provider == "ollama":
        return True
    return bool(provider_api_key(provider))


# ── Pydantic model ──────────────────────────────────────────────────────────


class BrainConfig(BaseModel):
    """The agency's active brain — provider + per-role models.

    Stored as a single document. All fields are model ids / provider names —
    no API keys. ``max_tokens`` is the planner/executor budget; the verifier
    and judge get smaller budgets hardcoded in ``agent/loop.py``.
    """

    primary_provider: BrainProvider = Field(
        default=SAFE_DEFAULT_PROVIDER,
        description="Which provider's endpoint the brain routes to",
    )
    planner_model: str = Field(default=SAFE_DEFAULT_MODEL, min_length=1, max_length=200)
    executor_model: str = Field(default=SAFE_DEFAULT_MODEL, min_length=1, max_length=200)
    verifier_model: str = Field(default=SAFE_DEFAULT_MODEL, min_length=1, max_length=200)
    judge_model: str = Field(default=SAFE_DEFAULT_MODEL, min_length=1, max_length=200)
    max_tokens: int = Field(default=4096, ge=256, le=32768)
    # Per-request LLM timeout for agent-loop calls (planner/executor/verifier),
    # in seconds. UI-configurable so an operator who picks a slower/larger model
    # can give it room, or tighten it to fail over to a faster provider sooner.
    # The agent loop reads this via ``resolve_agent_generation_sync`` and passes
    # it to ``failover_chat_completion`` — a planner call that previously hung the
    # full 16384-token budget on a slow reasoning model is bounded here.
    request_timeout_sec: int = Field(default=120, ge=15, le=600)
    # UI-configurable Ollama base URL (a tunnel URL when the brain runs on a
    # local/remote Ollama). Empty → fall back to OLLAMA_BASE env / localhost.
    # Lets the operator point the brain at their own GPU from the Brain card
    # with no Render env edit. Never holds a secret.
    ollama_base_url: str = Field(default="", max_length=300)
    updated_at: str = Field(default="")
    updated_by: str = Field(default="")


def default_brain_config() -> BrainConfig:
    """Return the safe-default brain (used on first boot + store errors)."""
    return BrainConfig()


# Priority order for auto-selecting the default brain when no config has been
# saved yet, and for the brain watchdog's failover chain. The first provider
# whose API key is present in env wins for auto-config (Ollama is skipped in
# that path because it has no API key — it must be explicitly chosen via the UI
# or BRAIN_PREFERENCE=ollama env).
#
# For failover: the watchdog walks this list when the current provider fails
# consecutively. Ollama leads so the operator's explicit local-brain choice is
# preserved across failovers (falls to Cerebras -> Groq -> NIM when local is
# down).
#
# Cerebras leads the cloud chain because it serves even the 480B Qwen3-Coder
# at wafer-scale speed on a generous, non-expiring free tier; Groq is the fast
# second; NIM is the always-on safe floor.
RECOMMENDED_PROVIDER_PRIORITY: tuple[str, ...] = ("nvidia", "tokenin", "cerebras", "groq", "ollama")


def recommended_brain_config() -> BrainConfig:
    """Return the recommended default brain based on which provider keys are present.

    Walks :data:`RECOMMENDED_PROVIDER_PRIORITY` and selects the first provider
    whose API key is configured in env, seeding the per-role models from
    :data:`PROVIDER_PRESETS`. Falls back to the safe NIM default when no cloud
    key is present. Never raises.

    This makes the agency self-configuring: drop a ``CEREBRAS_API_KEY`` into the
    Render env and the next agent run uses the recommended Cerebras chain with no
    UI click and no redeploy — while a saved UI config always takes precedence
    (this function is only consulted when no config has been persisted yet).
    """
    for provider in RECOMMENDED_PROVIDER_PRIORITY:
        if provider_api_key(provider):
            preset = PROVIDER_PRESETS.get(provider)
            if preset:
                return BrainConfig(
                    primary_provider=provider,  # type: ignore[arg-type]
                    planner_model=preset["planner"],
                    executor_model=preset["executor"],
                    verifier_model=preset["verifier"],
                    judge_model=preset["judge"],
                )
    return default_brain_config()


# ── Patch model ─────────────────────────────────────────────────────────────


class BrainConfigPatch(BaseModel):
    """Editable subset of ``BrainConfig`` sent by PATCH /admin/api/policy/brain.

    All fields are optional — only the supplied ones are merged. The store
    fills ``updated_at`` / ``updated_by`` automatically.
    """

    primary_provider: BrainProvider | None = None
    planner_model: str | None = Field(default=None, min_length=1, max_length=200)
    executor_model: str | None = Field(default=None, min_length=1, max_length=200)
    verifier_model: str | None = Field(default=None, min_length=1, max_length=200)
    judge_model: str | None = Field(default=None, min_length=1, max_length=200)
    max_tokens: int | None = Field(default=None, ge=256, le=32768)
    request_timeout_sec: int | None = Field(default=None, ge=15, le=600)
    # Empty string is allowed (clears the override → fall back to env/localhost);
    # min_length is therefore 0, unlike the model fields.
    ollama_base_url: str | None = Field(default=None, max_length=300)


# ── Store ───────────────────────────────────────────────────────────────────

# Mongo collection + document key. The ``app_settings`` collection is the
# established home for single-doc settings (provider_policy lives in the
# ``providers`` collection for legacy reasons; app_settings is the cleaner
# new home, mirroring how scheduler_store / decisions_store keep their
# one-per-instance state).
_BRAIN_DOC_ID = "brain_config"
_BRAIN_COLLECTION = "app_settings"

# Cache TTL — short so a UI Apply is picked up within seconds, but non-zero so
# the hot agent loop doesn't hit the DB on every planner/executor call.
_CACHE_TTL_SECONDS = 5.0


class BrainConfigStore:
    """Dual-storage brain config store (Mongo primary, sqlite mirror).

    The store is a singleton accessed via ``get_brain_config_store()`` so the
    cache is shared process-wide. All public methods are async and never
    raise — on any storage error they fall back to the safe default.
    """

    def __init__(self) -> None:
        self._cache: BrainConfig | None = None
        self._cache_at: float = 0.0
        self._lock = asyncio.Lock()

    # ── Public API ──────────────────────────────────────────────────────

    async def get_brain_config(self) -> BrainConfig:
        """Return the active brain config.

        Resolution order:
          1. In-process cache (if fresh)
          2. Mongo ``app_settings`` doc
          3. Sqlite mirror (no-Mongo path)
          4. Safe default

        Never raises — a DB error returns the safe default so the agent loop
        can keep running. This is the plan's "Brain resolution is hot-path →
        never throw" mitigation.
        """
        # Fast path: cache hit.
        if self._cache is not None and (time.monotonic() - self._cache_at) < _CACHE_TTL_SECONDS:
            return self._cache

        async with self._lock:
            # Re-check after acquiring the lock (another coroutine may have
            # just refreshed).
            if self._cache is not None and (time.monotonic() - self._cache_at) < _CACHE_TTL_SECONDS:
                return self._cache

            cfg = await self._load_unlocked()
            self._cache = cfg
            self._cache_at = time.monotonic()
            return cfg

    async def set_brain_config(
        self,
        patch: BrainConfigPatch,
        *,
        actor: str,
    ) -> BrainConfig:
        """Merge *patch* into the current config and persist.

        Returns the applied config. Persists to Mongo (primary) and sqlite
        (mirror) so either backend can serve the next read. Invalidates the
        in-process cache so the next ``get_brain_config()`` reflects the
        write immediately (no restart needed).
        """
        async with self._lock:
            current = await self._load_unlocked()
            merged = current.model_copy(
                update={
                    k: v
                    for k, v in patch.model_dump(exclude_none=True).items()
                    if v is not None
                }
            )
            # Stamp audit fields.
            merged.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            merged.updated_by = (actor or "unknown")[:200]

            await self._persist_unlocked(merged)
            # Refresh cache so the next get() returns the new value immediately.
            self._cache = merged
            self._cache_at = time.monotonic()
            return merged

    def invalidate(self) -> None:
        """Clear the in-process cache.

        Called by the admin API after a successful PATCH (defensive — the
        write path already refreshes the cache) and by tests that patch the
        store directly.
        """
        self._cache = None
        self._cache_at = 0.0

    # ── Storage backends ────────────────────────────────────────────────

    async def _load_unlocked(self) -> BrainConfig:
        """Read the persisted config from Mongo (primary) or sqlite (mirror).

        Falls back to the safe default on any error.
        """
        # 1. Try Mongo.
        try:
            from backend.server import get_db  # local import — avoids cycle
            db = get_db()
            collection = getattr(db, _BRAIN_COLLECTION, None)
            if collection is None:
                # STORAGE_BACKEND=sqlite exposes a synthetic collection.
                raise RuntimeError(f"collection {_BRAIN_COLLECTION!r} not present")
            doc = await collection.find_one({"_id": _BRAIN_DOC_ID})
            if doc:
                return self._from_doc(doc)
        except Exception as exc:
            log.debug("brain_config_store: Mongo read failed (%s) — trying sqlite mirror", exc)

        # 2. Sqlite mirror (no-Mongo path / CI).
        try:
            cfg = self._load_sqlite_mirror()
            if cfg is not None:
                return cfg
        except Exception as exc:
            log.debug("brain_config_store: sqlite mirror read failed (%s) — using safe default", exc)

        # 3. No persisted config yet.
        #
        # Render free-tier cold-start gap: when Render restarts after
        # inactivity, Mongo is slow to connect AND the sqlite mirror is
        # wiped (ephemeral storage). Without the check below, the brain
        # silently reverts to the cloud recommended chain (Cerebras →
        # Groq → NIM) even when the operator explicitly chose Ollama,
        # because provider_api_key("ollama") is None (no API key) and
        # recommended_brain_config() skips it.
        #
        # Resolve: honour BRAIN_PREFERENCE=ollama so a Render cold start
        # preserves the operator's explicit Ollama choice. The Ollama base
        # URL is read from the sqlite mirror (if still present) or the
        # OLLAMA_BASE / OLLAMA_BASE_URL env var (which survives restarts;
        # set it to the ngrok tunnel URL when running local-only).
        if os.environ.get("BRAIN_PREFERENCE", "").strip().lower() == "ollama":
            ollama_url = resolve_ollama_base_url()
            preset = PROVIDER_PRESETS.get("ollama", {})
            # Stamp updated_at so resolve_active_brain() step 2 honours this
            # config (transient — cache TTL is 5s; once Mongo recovers the
            # real persisted config displaces this cold-start fallback).
            return BrainConfig(
                primary_provider="ollama",
                planner_model=preset.get("planner", "deepseek-r1:32b"),
                executor_model=preset.get("executor", "qwen3-coder:30b"),
                verifier_model=preset.get("verifier", "deepseek-r1:32b"),
                judge_model=preset.get("judge", "deepseek-r1:32b"),
                ollama_base_url=ollama_url if ollama_url != "http://localhost:11434" else "",
                updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                updated_by="cold_start:brain_preference",
            )

        # 4. Recommended free-cloud chain (Cerebras → Groq → NIM) based on
        # which provider keys are present, falling back to the safe NIM
        # default. A saved UI config (steps 1-2) always wins.
        return recommended_brain_config()

    async def _persist_unlocked(self, cfg: BrainConfig) -> None:
        """Persist *cfg* to Mongo (primary) and sqlite (mirror).

        Either backend failing is non-fatal — the other still serves reads.
        """
        # 1. Mongo (upsert).
        try:
            from backend.server import get_db
            db = get_db()
            collection = getattr(db, _BRAIN_COLLECTION, None)
            if collection is not None:
                doc = cfg.model_dump(mode="json")
                doc["_id"] = _BRAIN_DOC_ID
                await collection.update_one(
                    {"_id": _BRAIN_DOC_ID},
                    {"$set": doc},
                    upsert=True,
                )
        except Exception as exc:
            log.warning("brain_config_store: Mongo persist failed (%s) — sqlite mirror only", exc)

        # 2. Sqlite mirror (always — even when Mongo succeeds, so a later
        # Mongo outage can still serve reads from the mirror).
        try:
            self._save_sqlite_mirror(cfg)
        except Exception as exc:
            log.warning("brain_config_store: sqlite mirror persist failed (%s)", exc)

    # ── Sqlite mirror ───────────────────────────────────────────────────
    #
    # The mirror is a tiny JSON blob in a single-row sqlite table. We use the
    # aiosqlite connection that db/sqlite_store.py already manages when
    # STORAGE_BACKEND=sqlite, and a standalone fallback file otherwise so the
    # store still works in tests that don't boot the full DB stack.

    # The table name + row id are static class constants — never user input.
    # We inline them as string literals (rather than f-strings) so Bandit's
    # B608 hardcoded-SQL check doesn't flag a non-existent injection vector.
    # Mirror what db/sqlite_store.py does for its own internal tables.
    _MIRROR_TABLE = "brain_config_mirror"
    _MIRROR_ROW_ID = "brain_config"
    _MIRROR_DDL = (
        "CREATE TABLE IF NOT EXISTS brain_config_mirror "
        "(id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )

    def _load_sqlite_mirror(self) -> BrainConfig | None:
        import sqlite3
        path = self._mirror_db_path()
        if not path or not os.path.isfile(path):
            return None
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            cur.execute(self._MIRROR_DDL)
            cur.execute(
                "SELECT data FROM brain_config_mirror WHERE id = ?",
                (self._MIRROR_ROW_ID,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return BrainConfig.model_validate_json(row[0])
        finally:
            conn.close()

    def _save_sqlite_mirror(self, cfg: BrainConfig) -> None:
        import sqlite3
        path = self._mirror_db_path()
        if not path:
            return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            cur.execute(self._MIRROR_DDL)
            cur.execute(
                "INSERT OR REPLACE INTO brain_config_mirror (id, data, updated_at) VALUES (?, ?, ?)",
                (
                    self._MIRROR_ROW_ID,
                    cfg.model_dump_json(),
                    cfg.updated_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _mirror_db_path(self) -> str:
        # The mirror lives in its own file (``brain_config.db`` next to the
        # main agency DB) so a stale mirror can never collide with the
        # sqlite_store's tables, and tests that wipe /tmp dirs don't lose
        # the production brain config (and vice-versa).
        #
        # ``SQLITE_DB_PATH`` is honoured when set so test fixtures can point
        # the mirror at an isolated tmp dir.
        base = os.environ.get("SQLITE_DB_PATH", ".data/agency.db")
        # If the caller set a path that ends in .db, derive the brain mirror
        # name from it so tests get isolation for free.
        if base.endswith(".db"):
            return base[:-3] + "_brain.db"
        return base + "_brain.db"

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _from_doc(doc: dict[str, Any]) -> BrainConfig:
        """Build a ``BrainConfig`` from a Mongo doc, dropping Mongo's ``_id``."""
        data = {k: v for k, v in doc.items() if k != "_id"}
        return BrainConfig.model_validate(data)


# ── Singleton accessor ──────────────────────────────────────────────────────

_store: BrainConfigStore | None = None
_store_lock = asyncio.Lock()


async def get_brain_config_store() -> BrainConfigStore:
    """Return the process-wide ``BrainConfigStore`` singleton."""
    global _store
    if _store is None:
        async with _store_lock:
            if _store is None:
                _store = BrainConfigStore()
    return _store


async def get_brain_config() -> BrainConfig:
    """Convenience wrapper used by the agent loop + brain resolver."""
    store = await get_brain_config_store()
    return await store.get_brain_config()


async def set_brain_config(patch: BrainConfigPatch, *, actor: str) -> BrainConfig:
    """Convenience wrapper used by the admin API endpoints."""
    store = await get_brain_config_store()
    cfg = await store.set_brain_config(patch, actor=actor)
    # Also invalidate the brain_policy resolver cache so the next agent run
    # picks up the new provider/model immediately.
    try:
        from packages.ai.brain import invalidate_brain_cache
        invalidate_brain_cache()
    except Exception:  # noqa: BLE001 — best-effort
        pass
    return cfg


def invalidate_brain_config_cache() -> None:
    """Clear the singleton's cache (used by tests + brain_policy invalidation)."""
    global _store
    if _store is not None:
        _store.invalidate()


# ── Role resolver (used by agent/loop.py at call time) ─────────────────────
#
# The plan's core change: move model resolution from import-time env
# (agent/loop.py:114-127) to a call-time resolver with precedence:
#
#     requested_model  →  BrainConfig (DB)  →  env var  →  safe default
#
# Synchronous variant ``resolve_role_model_sync`` is used by the hot agent
# loop to avoid an await on every planner/executor call. It reads the
# process-wide cache; if the cache is cold or stale it falls back to env /
# safe default rather than blocking on the DB — the async ``get_brain_config``
# refresh happens opportunistically in the background.

_ROLE_TO_DB_FIELD = {
    "planner": "planner_model",
    "executor": "executor_model",
    "verifier": "verifier_model",
    "judge": "judge_model",
}

_ROLE_TO_ENV_VAR = {
    "planner": "AGENT_PLANNER_MODEL",
    "executor": "AGENT_EXECUTOR_MODEL",
    "verifier": "AGENT_VERIFIER_MODEL",
    "judge": "AGENT_JUDGE_MODEL",
}

# The "shared" env override the existing import-time constants consult.
_ROLE_TO_FALLBACK_ENV_VAR = {
    "planner": "NVIDIA_DEFAULT_MODEL",
    "verifier": "NVIDIA_DEFAULT_MODEL",
    # executor + judge have no NVIDIA_DEFAULT_MODEL fallback in the
    # existing code — they go straight to the safe default.
}


def resolve_role_model_sync(role: str, requested: str | None = None) -> str:
    """Synchronous call-time resolver for an agent role model id.

    Precedence (highest to lowest):
      1. ``requested`` — the per-call override (e.g. a sub-agent config)
      2. BrainConfig DB field for this role (if cache is fresh)
      3. Env var (``AGENT_<ROLE>_MODEL``)
      4. Safe default (``meta/llama-3.3-70b-instruct``)

    Never raises — returns the safe default on any error so the agent loop
    can keep running even if the cache is in a weird state.
    """
    # 1. Per-call override wins.
    if requested and requested.strip():
        return requested.strip()

    field = _ROLE_TO_DB_FIELD.get(role)
    if field:
        # 2. BrainConfig cache (if fresh).
        try:
            if _store is not None and _store._cache is not None:
                if (time.monotonic() - _store._cache_at) < _CACHE_TTL_SECONDS:
                    val = getattr(_store._cache, field, None)
                    if val and val.strip():
                        return val.strip()
        except Exception:  # noqa: BLE001 — defensive
            pass

    # 3. Env var (kept working so nothing regresses).
    env_var = _ROLE_TO_ENV_VAR.get(role)
    if env_var:
        v = (os.environ.get(env_var) or "").strip()
        if v:
            return v
    fallback_env = _ROLE_TO_FALLBACK_ENV_VAR.get(role)
    if fallback_env:
        v = (os.environ.get(fallback_env) or "").strip()
        if v:
            return v

    # 4. Safe default.
    return SAFE_DEFAULT_MODEL


_DEFAULT_AGENT_MAX_TOKENS = 4096
_DEFAULT_AGENT_TIMEOUT_SEC = 120


def resolve_agent_generation_sync() -> tuple[int, int]:
    """Return ``(max_output_tokens, request_timeout_sec)`` for an agent LLM call.

    Same cache-first, never-blocking contract as :func:`resolve_role_model_sync`:
    the hot agent loop calls this on every planner/executor/verifier request, so
    it reads the process-wide BrainConfig cache when fresh and otherwise falls
    back to env then a safe default rather than awaiting the DB.

    Precedence per value (highest to lowest):
      1. BrainConfig cache (``max_tokens`` / ``request_timeout_sec``) if fresh
      2. Env (``AGENT_MAX_OUTPUT_TOKENS`` / ``AGENT_REQUEST_TIMEOUT_SEC``)
      3. Safe default (4096 tokens / 120s)

    Both values are the fix for the production ``planning: TimeoutError``: the
    loop previously hardcoded a 16384-token budget, so a slow reasoning model
    could spend minutes generating thinking tokens and blow the failover budget.
    Capping the budget (and making the timeout tunable from the Brain card)
    bounds it. Never raises.
    """
    max_tokens = _DEFAULT_AGENT_MAX_TOKENS
    timeout = _DEFAULT_AGENT_TIMEOUT_SEC

    # 1. BrainConfig cache (if fresh).
    try:
        if _store is not None and _store._cache is not None:
            if (time.monotonic() - _store._cache_at) < _CACHE_TTL_SECONDS:
                mt = getattr(_store._cache, "max_tokens", None)
                if isinstance(mt, int) and mt > 0:
                    max_tokens = mt
                ts = getattr(_store._cache, "request_timeout_sec", None)
                if isinstance(ts, int) and ts > 0:
                    timeout = ts
                return max_tokens, timeout
    except Exception:  # noqa: BLE001 — defensive; never block the loop
        pass

    # 2. Env fallbacks (kept working so nothing regresses on a cold cache).
    try:
        v = (os.environ.get("AGENT_MAX_OUTPUT_TOKENS") or "").strip()
        if v:
            max_tokens = max(256, min(int(v), 32768))
    except (TypeError, ValueError):
        pass
    try:
        v = (os.environ.get("AGENT_REQUEST_TIMEOUT_SEC") or "").strip()
        if v:
            timeout = max(15, min(int(v), 600))
    except (TypeError, ValueError):
        pass

    return max_tokens, timeout


async def resolve_role_model(role: str, requested: str | None = None) -> str:
    """Async variant — refreshes the cache if stale before resolving.

    Used by code paths that already await (the workflow orchestrator). The
    hot ``AgentRunner`` loop uses the sync variant to avoid an await per
    step.
    """
    if requested and requested.strip():
        return requested.strip()
    try:
        await get_brain_config()  # refreshes cache if stale
    except Exception:  # noqa: BLE001 — never block resolution
        pass
    return resolve_role_model_sync(role, requested)


# ── Component-level model resolver (UNIT 6) ────────────────────────────────
#
# The codebase has multiple call sites that need "the model id for this
# role on this provider" — e.g. ``telegram_bot.cmd_setbrain`` PATCHes all
# four role models when switching providers, ``brain_failover`` walks the
# provider chain, ``server._default_agent_role_models`` seeds the wizard.
# Each had its own duplicate preset table (UNIT 6 deletes them).
#
# ``resolve_component_model`` is the single entry point: it consults the
# catalog (``config/models.yaml`` → ``PROVIDER_PRESETS``) and the active
# BrainConfig (DB), with DB winning when the requested provider matches
# the active primary. Never raises — falls back to the safe default.


def resolve_component_model(
    component: str,
    role: str = "executor",
    provider: str | None = None,
    requested: str | None = None,
) -> str:
    """Resolve the model id for a component's role on a provider.

    Parameters
    ----------
    component : str
        The calling component id (e.g. ``"telegram_bot"``,
        ``"brain_failover"``, ``"router"``, ``"server"``). Used only for
        logging — there are no per-component overrides (the catalog is
        the single source of truth).
    role : str
        One of ``"planner"``, ``"executor"``, ``"verifier"``, ``"judge"``,
        or ``"default"``. ``"default"`` is a synonym for ``"executor"``
        (the most-used role).
    provider : str | None
        The provider id whose preset should be used. If ``None``, the
        active brain config's ``primary_provider`` is consulted. If the
        provider matches the active primary AND the cache is fresh, the
        DB-saved model for that role wins (so a UI Apply is honoured).
    requested : str | None
        Per-call override. If non-empty, returned verbatim (highest
        precedence).

    Returns
    -------
    str
        The resolved model id. Never empty. Falls back to
        ``SAFE_DEFAULT_MODEL`` on any error.

    Precedence (highest to lowest):
      1. ``requested`` — per-call override
      2. DB-saved model for this role (when ``provider`` is None or
         matches the active brain's ``primary_provider`` AND the cache
         is fresh)
      3. Catalog preset: ``PROVIDER_PRESETS[provider][role]``
      4. Env var ``AGENT_<ROLE>_MODEL`` (backward compat)
      5. ``SAFE_DEFAULT_MODEL``
    """
    # Normalise role.
    role_norm = (role or "executor").strip().lower()
    if role_norm == "default":
        role_norm = "executor"
    if role_norm not in _ROLE_TO_DB_FIELD:
        # Unknown role — return the safe default rather than raising.
        return SAFE_DEFAULT_MODEL

    # 1. Per-call override wins.
    if requested and requested.strip():
        return requested.strip()

    # 2. DB-saved model (if cache is fresh and provider matches).
    try:
        if _store is not None and _store._cache is not None:
            if (time.monotonic() - _store._cache_at) < _CACHE_TTL_SECONDS:
                cfg = _store._cache
                active_provider = str(getattr(cfg, "primary_provider", "")).strip()
                if provider is None or provider == active_provider:
                    field = _ROLE_TO_DB_FIELD[role_norm]
                    val = getattr(cfg, field, None)
                    if val and val.strip():
                        return val.strip()
    except Exception:  # noqa: BLE001 — defensive
        pass

    # 3. Catalog preset for the resolved provider.
    resolved_provider = provider
    if resolved_provider is None:
        # Use the active brain's primary_provider if available.
        try:
            if _store is not None and _store._cache is not None:
                resolved_provider = str(
                    getattr(_store._cache, "primary_provider", "")
                ).strip() or None
        except Exception:  # noqa: BLE001
            pass
    if resolved_provider:
        presets = PROVIDER_PRESETS.get(resolved_provider) or {}
        v = presets.get(role_norm)
        if v and v.strip():
            return v.strip()

    # 4. Env var (kept working so nothing regresses).
    env_var = _ROLE_TO_ENV_VAR.get(role_norm)
    if env_var:
        v = (os.environ.get(env_var) or "").strip()
        if v:
            return v

    # 5. Safe default.
    return SAFE_DEFAULT_MODEL


def resolve_component_role_models(
    component: str,
    provider: str | None = None,
    requested: dict[str, str] | None = None,
) -> dict[str, str]:
    """Convenience: resolve all four role models for a component.

    Returns a dict with keys ``planner``, ``executor``, ``verifier``,
    ``judge`` — the same shape as ``PROVIDER_PRESETS[provider]`` but
    resolved through the full precedence chain (DB → catalog → env →
    safe default). Used by ``telegram_bot.cmd_setbrain`` to PATCH all
    four role models at once.
    """
    requested = requested or {}
    out: dict[str, str] = {}
    for role in ("planner", "executor", "verifier", "judge"):
        out[role] = resolve_component_model(
            component=component,
            role=role,
            provider=provider,
            requested=requested.get(role),
        )
    return out


async def refresh_brain_config_cache() -> BrainConfig:
    """Force a cache refresh (used by tests + the GET /admin/api/policy/brain endpoint)."""
    store = await get_brain_config_store()
    store.invalidate()
    return await store.get_brain_config()


# ── North Mini Code — the default agentic coding model ─────────────────────
#
# Cohere Labs' first open-weight code model (Apache-2.0): a 30B / 3B-active
# sparse MoE with a 256K context window, native tool-use, and interleaved
# thinking, purpose-trained (two-stage SFT + RLVR) to drive full agentic
# software-engineering trajectories (SWE-bench Verified 67.6, Terminal-Bench
# 2.0 36.0). Because its active footprint is tiny it runs locally under
# Ollama, and it is also served free on OpenRouter — the two providers below.
#
# When ``NORTH_MINI_CODE_DEFAULT`` is on (the default), the agency's code-
# execution loop + Hermes prefer North wherever the active provider can serve
# it. Providers that can't (e.g. NVIDIA NIM in production) get ``None`` back,
# which the callers read as "no override" so the normal per-role brain runs —
# North can never break a deployment that doesn't host it.

NORTH_MINI_CODE_OLLAMA_ID: str = "north-mini-code-1.0"
NORTH_MINI_CODE_OPENROUTER_ID: str = "cohere/north-mini-code:free"

# Providers that can actually serve North Mini Code today → their model id.
_NORTH_MINI_CODE_PROVIDER_IDS: dict[str, str] = {
    "ollama": NORTH_MINI_CODE_OLLAMA_ID,
    "openrouter": NORTH_MINI_CODE_OPENROUTER_ID,
}


def north_mini_code_model_for(provider: str | None) -> str | None:
    """Return the North Mini Code model id served by *provider*, else ``None``.

    ``ollama`` → ``north-mini-code-1.0``; ``openrouter`` →
    ``cohere/north-mini-code:free``. Any other provider (nvidia, cerebras,
    groq, …) returns ``None`` because it cannot serve North.
    """
    if not provider:
        return None
    return _NORTH_MINI_CODE_PROVIDER_IDS.get(provider.strip().lower())


def is_north_mini_code_default() -> bool:
    """True when the ``NORTH_MINI_CODE_DEFAULT`` flag is on (default ON).

    Reads the central settings flag; never raises (defaults to ON if the
    settings module can't be imported, mirroring the flag's default value).
    """
    try:
        from packages.config import settings
        return settings.is_north_mini_code_default
    except Exception:  # noqa: BLE001 — defensive; flag defaults ON
        return True


def _active_primary_provider() -> str | None:
    """Best-effort read of the active brain's primary provider (or ``None``)."""
    try:
        if _store is not None and _store._cache is not None:
            return str(getattr(_store._cache, "primary_provider", "")).strip().lower() or None
    except Exception:  # noqa: BLE001 — defensive; must not break model resolution
        log.debug("resolve_coding_model_preference: active-provider read failed", exc_info=True)
    # Fall back to the explicit BRAIN_PREFERENCE env (set on local Ollama boxes).
    pref = (os.environ.get("BRAIN_PREFERENCE") or "").strip().lower()
    return pref or None


def resolve_coding_model_preference(provider: str | None = None) -> str | None:
    """Resolve the model id to force for a code-execution run, or ``None``.

    Returns the North Mini Code id **only** when the default flag is on AND
    the resolved provider (explicit *provider*, else the active brain's
    primary) can actually serve it. Otherwise returns ``None``, which callers
    treat as "no override" so the normal per-role brain resolution runs —
    this is what keeps NVIDIA-only production untouched.

    Callers pass the returned value as ``requested_model`` / ``model_preference``;
    a non-``None`` value makes the whole plan→execute→verify loop run on North
    (its intended single-model agentic-harness usage), while ``None`` leaves
    each role to resolve its own catalog preset.
    """
    if not is_north_mini_code_default():
        return None
    resolved = (provider or "").strip().lower() or _active_primary_provider()
    return north_mini_code_model_for(resolved)

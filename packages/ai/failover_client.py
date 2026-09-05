"""packages/ai/failover_client.py — one dispatcher for the brain-failover chain.

``services/brain_failover`` decides *which* provider to try next; this module is
the single place that actually performs the HTTP call against it, handling the
per-status failover rules and the Anthropic wire format.

Why it exists
-------------
The dispatch loop used to live inline inside ``AgentRunner._chat_text``, which
meant only the agent loop could reach the env-configured provider chain
(nvidia, groq, cerebras, zai, zhipu, deepseek, together, dashscope, moonshot,
mistral, aerolink, openrouter, minimax, google, anthropic, ollama). Everything
routed through ``backend.server.call_llm`` — the CEO strategic assessment above
all — fell back only across the DB-configured ``providers`` records, so when
those were rate-limited the CEO dropped straight to its rule-based path while
the agent loop still had a dozen untried providers available.

Extracting the loop here gives both callers the same breadth from one
implementation, per the repository rule that no logic may be duplicated.

Policy is unchanged: paid providers are admitted to the chain only by
``services.brain_failover._build_registry``, which gates them behind
``ALLOW_PAID_BRAIN`` or the Providers UI toggle. This module never widens that.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

# Models tried per provider before moving on. A provider that 410s its default
# model may still serve an alternate, but past three the next provider is the
# better bet.
_MAX_MODELS_PER_PROVIDER = 3

_DEFAULT_TIMEOUT_SEC = 120.0
_CONNECT_TIMEOUT_SEC = 10.0


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int((os.environ.get(name) or "").strip() or default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return max(1.0, float((os.environ.get(name) or "").strip() or default))
    except (TypeError, ValueError):
        return default


def _router_enabled() -> bool:
    """Whether to delegate to ``packages.llm.router.LLMRouter`` (ADR-008 §8).

    Read on every call so the operator can flip the flag at runtime. An import
    failure keeps the legacy path — the new layer must never be able to break
    the old one.
    """
    try:
        from packages.llm.config import router_enabled

        return router_enabled()
    except Exception:  # pragma: no cover - defensive
        return False


async def _try_router(
    payload: dict[str, Any], timeout_sec: float
) -> "FailoverResult | None":
    """Serve the call through ``LLMRouter``, or return None for the legacy path.

    When ``LLM_ROUTER_ENABLED=true`` the request is routed by
    :class:`packages.llm.router.LLMRouter` (ADR-008 §8). The signature, return
    type, and raised exception are identical either way, so no caller can tell
    which path ran; the flag is the rollback switch. Kept as its own function
    so the dispatcher stays inside the repo's 50-line cap.
    """
    if not _router_enabled():
        return None
    try:
        from packages.llm.compat import failover_chat_completion_via_router
    except Exception as exc:  # pragma: no cover - defensive
        # A broken routing layer must degrade to the legacy chain, never take
        # the brain down with it. _router_enabled() already guards the config
        # import; this guards the rest of the package.
        log.warning("llm router unavailable (%s) — using the legacy chain", exc)
        return None

    return await failover_chat_completion_via_router(payload, timeout_sec=timeout_sec)


# ── Fan-out budget ───────────────────────────────────────────────────────────
#
# Without a cap the attempt count MULTIPLIES and self-inflicts the very 429s it
# is trying to route around. Measured on the real registry:
#
#   14 providers x 3 models                        =  42 HTTP calls per call
#   x up to 4 _chat_json parse retries             = 168 per planning step
#   x _DISPATCH_RETRY_LIMIT (5) task re-queues     = 840 per task
#
# ...and the agency runs many tasks plus 34 loops concurrently. No free tier
# survives that, so every provider returns 429 and every task ends up BLOCKED —
# which looks like "all providers are broken" when the caller is the cause.
#
# These two budgets bound one logical completion. BRAIN_MAX_PROVIDER_ATTEMPTS is
# the total HTTP attempts across ALL providers and models (not per provider), so
# the worst case is linear instead of the product above. Raise it if you have
# paid capacity and want more breadth; lower it to protect a tight free tier.
_MAX_TOTAL_ATTEMPTS = _env_int("BRAIN_MAX_PROVIDER_ATTEMPTS", 6)
_WALL_CLOCK_BUDGET_SEC = _env_float("BRAIN_FAILOVER_BUDGET_SEC", 180.0)

# ...but a flat cap alone STARVES the paid tier, which is the whole point of
# having one. Providers are ordered free → local → paid, so an operator with ten
# free keys configured spends all six attempts inside the free tier and the chain
# raises BrainFailoverExhausted having never contacted the paid provider they are
# actually paying for. Measured, not inferred: with ten free providers all
# returning 429 the chain stopped at the sixth free provider and never reached
# Aerolink — so paid capacity bought to cover exactly this situation (free tiers
# rate-limited) could not be used at all.
#
# This reserves a slice of the budget that ONLY paid-tier providers may spend.
# The reserve is inert unless a paid provider is both admitted (allow_paid, which
# is still the sole spend gate) and untried, so an operator running free-only
# keeps the entire budget for the free tier and sees no change.
#
# Parsed with its own bounded reader rather than _env_int, which floors at 1 and
# so cannot express "off", and does not cap against the total. Both mattered:
# 0 silently became 1, and a reserve at or above the cap left the free tier a
# single attempt — turning a cost-control knob into an accidental paid-first
# switch. The range is 0 (off) through _MAX_TOTAL_ATTEMPTS - 1 (always leave the
# free tier at least one attempt), clamped rather than rejected so a fat-fingered
# value degrades predictably instead of failing a deploy at import time.
def _paid_reserve() -> int:
    """Read BRAIN_PAID_RESERVE_ATTEMPTS, clamped to a range that cannot starve.

    ``0`` means off. The upper bound is ``_MAX_TOTAL_ATTEMPTS - 1`` so the free
    tier always keeps at least one attempt. Unparseable input falls back to the
    default rather than raising, because a bad env var must not stop a boot.
    """
    raw = (os.environ.get("BRAIN_PAID_RESERVE_ATTEMPTS") or "").strip()
    try:
        value = int(raw) if raw else 2
    except ValueError:
        return 2
    return max(0, min(value, _MAX_TOTAL_ATTEMPTS - 1))


_PAID_RESERVE_ATTEMPTS = _paid_reserve()


class BrainFailoverExhausted(RuntimeError):
    """Every provider in the failover chain failed — the terminal error.

    Carries the reason **every** provider failed, not just the last one. Reporting
    only the last error made a whole-chain outage look like a single-provider
    problem: an operator seeing "401 Unauthorized for open.bigmodel.cn" would fix
    the Zhipu key and still be dead, because four other providers were also
    failing for their own reasons. ``failures`` lists each one so the real
    remediation is visible from the message alone.
    """

    def __init__(
        self,
        last_error: str,
        tried: set[str] | None = None,
        failures: list[str] | None = None,
    ) -> None:
        self.last_error = last_error
        self.tried = set(tried or ())
        self.failures = list(failures or ())
        if self.failures:
            detail = "; ".join(self.failures)
            super().__init__(
                f"All {len(self.failures)} brain provider attempt(s) failed: {detail}"
            )
        elif last_error:
            super().__init__(f"All brain providers exhausted. Last error: {last_error}")
        elif self.tried:
            # Providers WERE attempted but none reported a reason — previously
            # this fell through to "none configured", sending operators to look
            # for missing API keys while the real cause was a chain that ran and
            # failed silently. Name what was tried instead of denying it happened.
            super().__init__(
                f"All brain providers exhausted after attempting "
                f"{len(self.tried)} provider(s) ({', '.join(sorted(self.tried))}) — "
                "no provider reported a reason. Check the model ids configured for "
                "these providers; a decommissioned model returns 410 for every "
                "request without a usable error."
            )
        else:
            super().__init__(
                "All brain providers exhausted — none configured or all in cooldown."
            )


class _Budget:
    """Shared attempt + wall-clock budget for one logical completion.

    Bounds the whole chain rather than each provider, so the cost of a failing
    call is linear in the budget instead of the product of providers x models x
    parse retries x task re-queues.
    """

    def __init__(self, max_attempts: int, deadline_sec: float) -> None:
        self._max = max_attempts
        self._used = 0
        self._started = time.monotonic()
        self._deadline = deadline_sec

    def charge(self) -> None:
        self._used += 1

    def spent(self) -> bool:
        if self._used >= self._max:
            return True
        return (time.monotonic() - self._started) >= self._deadline

    def unpaid_slice_spent(self, reserve: int) -> bool:
        """True when free/local providers have used everything but the reserve.

        Only the attempt count is reserved, never the wall clock: holding back
        seconds would let the deadline expire with the reserve unspent, which is
        the starvation this exists to prevent.
        """
        return reserve > 0 and self._used >= max(self._max - reserve, 1)

    @property
    def used(self) -> int:
        return self._used

    def reason(self) -> str:
        if self._used >= self._max:
            return (
                f"attempt budget exhausted after {self._used} provider attempt(s) "
                f"(BRAIN_MAX_PROVIDER_ATTEMPTS={self._max})"
            )
        return (
            f"time budget exhausted after {self._used} attempt(s) "
            f"(BRAIN_FAILOVER_BUDGET_SEC={self._deadline:.0f}s)"
        )


@dataclass
class FailoverResult:
    """A successful completion plus the accounting its callers need."""

    text: str
    model: str
    provider_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    attempts: list[str] = field(default_factory=list)


def _key_pool() -> Any:
    """The process key pool (lazy import keeps this module's import graph flat)."""
    from packages.ai.key_pool import get_pool
    return get_pool()


def _provider_keys(provider: Any) -> list[str]:
    """Every configured key for *provider*, primary first.

    Returns an empty list when the provider's key variable cannot be resolved,
    which makes every caller fall through to the single key already on the
    provider record — the pre-rotation behaviour.
    """
    base_env = getattr(provider, "key_env", "") or ""
    if not base_env:
        return []
    try:
        from packages.ai.key_pool import api_keys_for
        return api_keys_for(provider.id, base_env)
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("brain_failover: key pool lookup failed for %s: %s", provider.id, exc)
        return []


def _retry_after_seconds(resp: Any) -> float | None:
    """Parse ``Retry-After`` from a response, or None when absent/unparseable."""
    try:
        from packages.ai.router import ProviderRouter
        return ProviderRouter._parse_retry_after(resp)
    except Exception:  # pragma: no cover - a header parse must never raise here
        return None


def _build_request(
    provider: Any, *, api_key: str | None = None
) -> tuple[str, dict[str, str], bool]:
    """Return ``(url, headers, is_anthropic_native)`` for *provider*.

    Anthropic's native API has no ``/chat/completions`` route and rejects
    ``Authorization: Bearer``, so sending it the OpenAI-compatible shape returns
    a deterministic 400 for every model. OpenAI-compatible Claude gateways
    (OpenRouter, Aerolink) are not Anthropic-native and keep the standard path.

    ``api_key`` overrides the key on the provider record so the caller can
    rotate across a pool; omitting it keeps the record's own key.
    """
    from packages.ai.router import (
        ProviderConfig,
        _openai_url,
        is_anthropic_base_url,
    )

    key = api_key or provider.api_key

    if is_anthropic_base_url(provider.base_url):
        cfg = ProviderConfig(
            provider_id=provider.id,
            type="anthropic",
            base_url=provider.base_url,
            api_key=key or None,
        )
        return f"{cfg.normalized_base_url}/v1/messages", cfg.auth_headers(), True

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return _openai_url(provider.base_url, "/chat/completions"), headers, False


def _looks_unknown_model(last_error: str | None) -> bool:
    """True when the provider rejected the model id itself, not the request.

    Some providers explain themselves ("model_not_found", "does not exist");
    others (observed on NVIDIA NIM) return a bare 404 with an empty body on a
    chat-completions endpoint that unambiguously means the model id does not
    exist there — no other 4xx in this chain reaches here with that code (429/
    419/413/401/403/402 all return before this point), so " 404:" only ever
    comes from ``_try_provider``'s generic fallthrough formatting. Without this,
    a provider whose whole static candidate list drifted 404s silently forever:
    ``_looks_unknown_model`` never fires, ``_disable_unless_key_serves_other_models``
    (which checks the account's real model list before touching anything) never
    runs, and every call retries the same three dead model ids.
    """
    text = last_error or ""
    return "model_not_found" in text or "does not exist" in text or " 404:" in text


def _models_to_try(provider: Any, provider_model: str) -> list[str]:
    """Order the models to attempt on *provider*, correcting a stale catalogue.

    Cache-only: discovery never runs here, because a chat request must not wait
    on a second HTTP round trip. When nothing has been discovered yet this
    returns exactly the static ordering it always did.
    """
    from packages.ai.model_discovery import attempted, cached_models, dead_models

    static = [provider_model] + [m for m in provider.models if m != provider_model]
    served = cached_models(provider.id)
    if not served:
        ordered = static
    else:
        known = set(served)
        ordered = [m for m in static if m in known]
        # Anything the key serves but the catalogue never listed is still a valid
        # fallback, and on a drifted catalogue it is the only one left.
        ordered += [m for m in served if m not in ordered]
        if not ordered:
            ordered = static

    # Drop models still inside their dead-cooldown window (a prior 410/404). This
    # is what stops a catalogue-listed-but-dead id — e.g. NVIDIA still lists an
    # end-of-lifed model that 404s on call — from burning one of the capped
    # per-provider slots every round. Never filter to empty: if every model is
    # cooling, keep the order and let one through to re-confirm rather than
    # sidelining the whole provider on stale marks.
    dead = dead_models(provider.id)
    if dead:
        live = [m for m in ordered if m not in dead]
        if live:
            ordered = live

    # Only the first _MAX_MODELS_PER_PROVIDER entries are ever sent, so a key
    # serving more than that would otherwise have its tail retried forever and
    # its head retried every round. Models no round has tried yet go first, which
    # is what lets successive rounds cover the whole list.
    fresh = attempted(provider.id)
    return sorted(ordered, key=lambda m: m in fresh)


async def _disable_unless_key_serves_other_models(
    provider: Any, tried: list[str]
) -> None:
    """Auto-disable *provider*, unless its key demonstrably serves other models.

    "No accessible model" is a claim about the account, and acting on it flips a
    kill switch an operator has to notice and undo by hand. A stale catalogue
    produces the identical symptom, so confirm the claim against the provider's
    own model list before believing it.

    *tried* must be the models this round actually sent, not the full ordered
    list: only ``_MAX_MODELS_PER_PROVIDER`` of them are attempted, so counting
    the rest as tried would let a key serving more models than the cap be
    disabled on evidence that was never gathered.

    Attempts accumulate across rounds, so this terminates: each round covers up
    to ``_MAX_MODELS_PER_PROVIDER`` previously-untried models, and once the
    record covers everything the key serves, the account really is unusable.
    """
    from packages.ai.model_discovery import attempted, discover_models, record_attempted

    record_attempted(provider.id, tried)

    served = await discover_models(provider)
    if served is None:
        # Discovery unavailable: no evidence either way, so keep the established
        # behaviour rather than leaving a provider that really is misconfigured
        # to fail forever.
        _auto_disable(provider.id, "no accessible model (404 model_not_found)")
        return

    seen = attempted(provider.id)
    untried = [m for m in served if m not in seen]
    if untried:
        log.warning(
            "brain_failover: %s rejected %s as unknown, but its key serves %d "
            "models, %d of them never tried (%s...) — the catalogue is stale, "
            "not the account. Leaving the provider enabled; the next call "
            "tries the ones still outstanding.",
            provider.id, ", ".join(tried), len(served), len(untried),
            ", ".join(untried[:3]),
        )
        return

    _auto_disable(provider.id, "no accessible model (404 model_not_found)")


def _is_ollama(provider: Any) -> bool:
    return (
        "ollama" in (getattr(provider, "id", "") or "").lower()
        or ":11434" in (getattr(provider, "base_url", "") or "")
    )


_BILLING_SIGNALS: tuple[str, ...] = (
    "credit balance is too low",
    "insufficient balance",
    "insufficient_quota",
    "quota exceeded",
    "billing",
    "payment required",
    "exceeded your current quota",
)


def _is_billing_refusal(resp: httpx.Response) -> bool:
    """True when a 4xx body says the account is out of credit or quota.

    Providers disagree on the status code for "you have no money": DeepSeek uses
    402, Anthropic uses 400 with an ``invalid_request_error``. Both mean every
    model on that provider will refuse identically, so both must fail over to the
    next provider instead of burning the remaining model attempts.
    """
    if not (400 <= resp.status_code < 500):
        return False
    try:
        body = resp.text[:600].lower()
    except Exception:  # noqa: BLE001 — a body we cannot read is not a billing signal
        return False
    return any(signal in body for signal in _BILLING_SIGNALS)


def _auto_disable(provider_id: str, reason: str) -> None:
    """Take a permanently-broken provider out of rotation until a human returns it.

    Only called for states no retry can fix: an invalid key, an empty balance, or
    an account with no access to any of the provider's models. Transient states
    (429, 5xx, network) are deliberately excluded — they already have circuit
    breakers, and disabling on a 429 would switch off every free provider the
    first time a burst tripped a rate limit.
    """
    try:
        from services.brain_failover import auto_disable_provider
        auto_disable_provider(provider_id, reason)
    except Exception as exc:  # noqa: BLE001 — never fail a call over bookkeeping
        log.debug("brain_failover: auto-disable of %s failed: %s", provider_id, exc)


def _parse_success(resp: httpx.Response) -> tuple[str, int, int]:
    """Extract ``(text, prompt_tokens, completion_tokens)`` from a 2xx body.

    Raises ``ValueError``/``KeyError``/``IndexError``/``TypeError`` on a
    malformed body so the caller can treat it as a failed attempt and fail over
    rather than propagating the parse error out of the dispatcher.
    """
    data = resp.json()
    usage = data.get("usage") if isinstance(data, dict) else {}
    usage = usage if isinstance(usage, dict) else {}
    text = data["choices"][0]["message"]["content"]
    if text is None:
        raise ValueError("provider returned a null message content")
    return (
        text,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
    )


async def _try_provider(
    provider: Any,
    payload: dict[str, Any],
    fm: Any,
    attempts: list[str],
    timeout_sec: float,
    budget: "_Budget",
) -> tuple[FailoverResult | None, str]:
    """Try up to ``_MAX_MODELS_PER_PROVIDER`` models on one provider.

    Returns ``(result, last_error)``. ``result`` is ``None`` when every model on
    this provider failed, in which case the caller moves to the next provider.

    Every failure here is logged at WARNING, never ERROR: while the chain still
    has untried providers a single provider failing is a recoverable step, not an
    outage. Only the caller, once the whole chain is exhausted, logs an error.
    This also keeps ``agent/log_monitor``'s ERROR-triggered issue-filing from
    opening a ticket for a provider the system successfully failed over.
    """
    from packages.ai.router import ProviderRouter, with_ollama_reasoning_effort

    requested_model = str(payload.get("model") or "")
    # Key rotation: pick this attempt's key from the provider's pool. Falls back
    # to the single key already on the provider record when no extra keys are
    # configured, which is the default and changes nothing.
    pool_keys = _provider_keys(provider)
    active_key = (
        _key_pool().next_key(provider.id, pool_keys) if pool_keys else None
    )
    if pool_keys and active_key is None:
        # Every key in a configured pool is resting. Falling through here would
        # hand `_build_request` a None, whose `api_key or provider.api_key`
        # fallback then sends the provider record's *primary* key — the very key
        # that is supposed to be resting. That is reachable with the shipped
        # defaults: a provider whose breaker reopens after 30s while its keys
        # are still resting on the 60s key cooldown would retry the primary key
        # and defeat the per-key backoff entirely.
        return None, (
            f"{provider.id} all {len(pool_keys)} key(s) rate-limited"
        )
    chat_url, headers, is_anthropic = _build_request(provider, api_key=active_key)
    provider_model = fm.resolve_model(provider, requested_model)
    # Bind the capped list once: the disable gate must be told exactly what was
    # sent, and slicing it in two places is how the two drift apart.
    models_to_try = _models_to_try(provider, provider_model)[:_MAX_MODELS_PER_PROVIDER]
    last_error = ""

    for try_model in models_to_try:
        if budget.spent():
            return None, last_error or f"{provider.id} skipped (budget spent)"
        budget.charge()
        call_payload = {**payload, "model": try_model}
        post_payload = with_ollama_reasoning_effort(
            call_payload, is_ollama=_is_ollama(provider)
        )
        if is_anthropic:
            post_payload = ProviderRouter._anthropic_payload(post_payload)

        attempts.append(f"{provider.id}/{try_model}")
        call_start = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_sec, connect=_CONNECT_TIMEOUT_SEC)
            ) as client:
                resp = await client.post(chat_url, json=post_payload, headers=headers)
        except Exception as exc:  # noqa: BLE001 — network errors fail over
            log.warning("brain_failover: %s network error: %s", provider.id, exc)
            fm.record_failure(provider.id, "network_error")
            return None, f"{provider.id} network error: {exc}"

        call_ms = int((time.perf_counter() - call_start) * 1000)

        if resp.status_code < 400:
            fm.record_success(provider.id, latency_ms=call_ms)
            if is_anthropic:
                resp = ProviderRouter._anthropic_to_openai_response(resp, try_model)
            try:
                text, prompt_tokens, completion_tokens = _parse_success(resp)
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                # A 2xx with an unusable body is a failed attempt, not a crash —
                # the dispatcher must never surface a partial result.
                last_error = f"{provider.id} malformed success response: {exc}"
                log.warning(
                    "brain_failover: %s returned an unparsable body: %s",
                    provider.id, exc,
                )
                continue
            return (
                FailoverResult(
                    text=text,
                    model=try_model,
                    provider_id=provider.id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=call_ms,
                    attempts=list(attempts),
                ),
                last_error,
            )

        if resp.status_code == 410:
            # Model permanently gone — another model on this provider may serve.
            # Record it: without this, a provider whose models have ALL been
            # decommissioned returns an empty error, contributes nothing to
            # `failures`, and the terminal message reports "none configured"
            # for a provider that was configured, healthy, and fully attempted.
            # Hold it out of the rotation for a long cooldown (rule 4) so the
            # next rounds do not keep re-spending a slot on a decommissioned id.
            from packages.ai.model_discovery import DEAD_TTL_GONE_SEC, mark_dead

            mark_dead(provider.id, try_model, ttl_sec=DEAD_TTL_GONE_SEC)
            last_error = f"{provider.id} model {try_model} 410 gone"
            log.warning(
                "brain_failover: %s model %s 410 Gone - trying next model",
                provider.id, try_model,
            )
            continue

        # The remaining statuses fail identically for every model on this
        # provider, so trying another model here would repeat the same error.
        if resp.status_code in (429, 419):
            # Free tiers rate-limit per *key*, not per provider. Rest only the
            # key that was refused; the provider itself is cooled once every key
            # in its pool is resting. With a single key configured (the default)
            # `all_cooling` is True immediately, so this is byte-for-byte the
            # old behaviour — rotation only engages from two keys up.
            if pool_keys and active_key:
                _key_pool().mark_rate_limited(
                    provider.id,
                    active_key,
                    retry_after_sec=_retry_after_seconds(resp),
                )
                if not _key_pool().all_cooling(provider.id, pool_keys):
                    log.info(
                        "brain_failover: %s key rate-limited but siblings remain "
                        "— rotating instead of cooling the provider",
                        provider.id,
                    )
                    return None, f"{provider.id} {resp.status_code} key rate-limited"
            fm.record_failure(provider.id, "rate_limited", resp.status_code)
            return None, f"{provider.id} {resp.status_code} rate-limited"
        if resp.status_code == 413:
            fm.record_failure(provider.id, "payload_too_large", resp.status_code)
            return None, f"{provider.id} 413 payload too large"
        if resp.status_code in (401, 403):
            fm.record_failure(provider.id, "auth_failed", resp.status_code)
            _auto_disable(provider.id, f"{resp.status_code} invalid or expired API key")
            return None, f"{provider.id} {resp.status_code} unauthorized/forbidden"
        if resp.status_code == 402:
            fm.record_failure(provider.id, "payment_required", resp.status_code)
            _auto_disable(provider.id, "402 out of credit")
            return None, f"{provider.id} 402 payment required (out of credit)"
        if resp.status_code >= 500:
            fm.record_failure(provider.id, "server_error", resp.status_code)
            return None, f"{provider.id} {resp.status_code} server error"

        # A 4xx that is really a billing/quota refusal, not a bad request.
        # Anthropic returns 400 with "credit balance is too low" — semantically
        # the same class as 402: no model on this provider can succeed, so the
        # next two model attempts are guaranteed to repeat it verbatim.
        if _is_billing_refusal(resp):
            fm.record_failure(provider.id, "payment_required", resp.status_code)
            _auto_disable(provider.id, f"{resp.status_code} out of credit/quota")
            return None, (
                f"{provider.id} {resp.status_code} out of credit/quota: "
                f"{resp.text[:120]}"
            )

        if resp.status_code == 404:
            # A bare 404 on chat-completions means this id does not exist for
            # this key — the catalogue still lists it but the account cannot call
            # it. Hold it out briefly (a 404 can be transient drift, so shorter
            # than a 410) so the next rounds spend their slots on models that
            # might answer. Still falls through to try the next model now, and
            # last_error keeps the " 404:" marker `_looks_unknown_model` reads.
            from packages.ai.model_discovery import DEAD_TTL_UNKNOWN_SEC, mark_dead

            mark_dead(provider.id, try_model, ttl_sec=DEAD_TTL_UNKNOWN_SEC)

        last_error = f"{provider.id} {resp.status_code}: {resp.text[:200]}"
        log.warning(
            "brain_failover: %s model %s returned %d - trying next model",
            provider.id, try_model, resp.status_code,
        )

    fm.record_failure(provider.id, "all_models_failed")
    if _looks_unknown_model(last_error):
        await _disable_unless_key_serves_other_models(provider, models_to_try)
    return None, last_error


def _log_recovery(result: FailoverResult, failures: list[str]) -> None:
    """Report a successful failover at INFO — recovery is not an incident.

    Everything logged before this point was a warning, so a call that recovered
    leaves no ERROR behind, and ``agent/log_monitor`` files no issue for it.
    """
    if failures:
        log.info(
            "brain_failover: recovered via %s/%s after %d failed attempt(s): %s",
            result.provider_id, result.model, len(failures), "; ".join(failures),
        )


def _describe_registry() -> str:
    """Explain a zero-attempt outcome, from the module that owns provider state.

    "no provider attempted" has exactly three causes needing opposite responses —
    nothing configured (set a key), everything switched off by the kill switch
    (fix the named cause and re-enable), everything in cooldown (wait) — and the
    old message distinguished none of them.

    Formats ``brain_failover.brain_availability_summary()`` rather than
    recomputing it: that helper already derives total/usable/disabled+remedy/
    cooling and is the shared answer for the public doctor endpoint, the CEO
    supervisor and the Providers screen. A second implementation here would be
    the one thing worse than no diagnostic — two that can disagree.
    """
    try:
        from services.brain_failover import brain_availability_summary
        summary = brain_availability_summary()
    except Exception as exc:  # noqa: BLE001 — a diagnostic must never raise
        return f"registry unavailable ({str(exc)[:80]})"
    total = summary.get("total", 0)
    if not total:
        return "no providers configured — set at least one provider API key"
    parts = [f"{total} configured", f"{summary.get('usable', 0)} usable"]
    off = summary.get("disabled") or []
    if off:
        named = "; ".join(
            f"{d.get('id')} ({d.get('remedy') or d.get('summary') or 'switched off'})"
            for d in off
        )
        parts.append(f"{len(off)} switched OFF: {named}")
    cooling = summary.get("cooling") or []
    if cooling:
        parts.append(f"{len(cooling)} in cooldown: {', '.join(map(str, cooling))}")
    if not summary.get("state_durable", True):
        parts.append("state not durable (switches reset on deploy)")
    return " | ".join(parts)


def _log_exhaustion(attempted: list[str], failures: list[str]) -> None:
    """The one and only error-level log in the dispatch path.

    Emitted solely when the chain is exhausted and the caller genuinely cannot
    proceed, and it names every provider that failed so the log line alone is
    enough to act on.

    Takes ``attempted`` (an append-only list) rather than the caller's ``tried``
    set: ``tried`` is the exclusion set and ``_recover_all_unhealthy`` clears it
    so providers can be retried after a breaker reset, which made it wrong for
    reporting — production logs showed ``tried=[9 providers]`` beside 14 distinct
    failures, with one provider listed twice. ``failures`` is deduped by the
    caller for the same reason.
    """
    if not attempted:
        # Zero attempts is not "everything failed", it is "nothing was tried".
        # Report the registry state instead of an empty failure list.
        log.error(
            "brain_failover: no provider attempted — %s", _describe_registry(),
        )
        return
    log.error(
        "brain_failover: all %d provider(s) exhausted (%s) — %s",
        len(attempted), ", ".join(attempted) or "none",
        "; ".join(failures) or "no provider attempted",
    )


def _untried_paid(fm: Any, tried: set[str]) -> set[str]:
    """Paid-tier providers admitted to the chain and not yet attempted.

    Empty when the operator has not enabled paid providers — ``_build_registry``
    is the sole spend gate and simply omits them — which is what keeps the paid
    reserve inert for a free-only deployment.
    """
    off = _disabled_ids()
    # Selectable, not merely present. A paid provider that is switched off or
    # cooling down can never be returned by next_provider(), so counting it here
    # made the reserve hold back the free tier's last attempts for a provider
    # that could not be reached — turning a cost-control knob into an outage.
    return {
        p.id for p in fm.get_providers()
        if getattr(p, "tier", "") == "paid"
        and p.id not in tried
        and p.id not in off
        and getattr(p, "is_healthy", True)
    }


def _select_provider(
    fm: Any, budget: "_Budget", tried: set[str], requested_model: str
) -> Any | None:
    """Pick the next provider, honouring the paid reserve.

    Once free/local providers have spent everything but the reserve, they are
    excluded so the remaining attempts can only go to a paid provider. Without
    this the free tier consumes the whole budget and the paid escape hatch — the
    one an operator is paying for precisely because the free tiers are
    rate-limited — is never contacted.
    """
    exclude = tried
    paid = _untried_paid(fm, tried)
    if paid and budget.unpaid_slice_spent(_PAID_RESERVE_ATTEMPTS):
        exclude = tried | {p.id for p in fm.get_providers() if p.id not in paid}
        log.info(
            "brain_failover: free tier used %d of %d attempts — reserving the "
            "remainder for the paid tier (%s)",
            budget.used, _MAX_TOTAL_ATTEMPTS, ", ".join(sorted(paid)),
        )
    provider = fm.next_provider(exclude=exclude, requested_model=requested_model)
    if provider is None and exclude is not tried:
        # No paid provider is selectable (all in cooldown). Fall back to the
        # normal chain rather than giving up with budget still unspent.
        provider = fm.next_provider(exclude=tried, requested_model=requested_model)
    return provider


def _recover_all_unhealthy(
    fm: Any, tried: set[str], requested_model: str
) -> Any | None:
    """Reset every circuit breaker when they have all tripped, and re-select.

    Without this the system deadlocks with no usable brain until the 5-minute
    self-heal tick lands. Returns the next provider to try, or ``None`` when
    some providers are still healthy (so the exhaustion was genuine).
    """
    # Only ENABLED providers count. A provider switched off by the kill switch is
    # not in cooldown, so its breaker is CLOSED and it reads as healthy here —
    # which made a single disabled provider mask the all-unhealthy condition and
    # skip recovery entirely. Combined with every enabled provider being in 429
    # cooldown, the dispatcher then found nothing to try and gave up having made
    # ZERO HTTP attempts, logging "all 0 provider(s) exhausted (none)". Reproduced
    # against the production shape before this fix.
    off = _disabled_ids()
    candidates = [p for p in fm.get_providers() if p.id not in off]
    if not candidates or any(p.is_healthy for p in candidates):
        return None

    # Every enabled provider is cooling. This used to call record_success() on
    # all of them, which is not a breaker reset but a *lie*: record_success sets
    # health=CLOSED and failure_count=0, and is_healthy returns True for CLOSED
    # without ever consulting cooldown_until — so it erased both the cooldown and
    # the exponential-backoff counter that produced it. With every free provider
    # 429ing, that produced a doom loop: all cool → next request resets them all
    # → all four hammered again → 429 again, every few seconds, indefinitely,
    # with the backoff pinned at its base value because the counter never
    # survived a cycle. Production logs showed exactly that for 20+ minutes:
    # "all 4 provider(s) exhausted (nvidia, google, zai, groq)" on repeat.
    #
    # A 429 cooldown is the provider telling us to wait. Waiting is the fix, not
    # something to route around — no ordering of four exhausted providers finds
    # capacity that none of them has.
    # fm is duck-typed (Any). A manager without the newer introspection methods
    # is treated as "nothing is stuck", i.e. wait — never as licence to reset,
    # because reset-and-hammer is the failure mode this whole branch exists to
    # stop, and it must not come back through a missing attribute.
    _stuck_check = getattr(fm, "stuck_beyond_cooldown", None)
    stuck = [p for p in candidates if _stuck_check and _stuck_check(p.id)]
    if not stuck:
        _wait_check = getattr(fm, "seconds_until_recovery", None)
        wait = _wait_check() if _wait_check else None
        log.warning(
            "brain_failover: all %d enabled provider(s) cooling — not resetting "
            "breakers; soonest retry in %s",
            len(candidates),
            f"{wait:.0f}s" if wait is not None else "unknown",
        )
        return None

    # Safety valve only: a provider wedged far beyond its own backoff window is
    # allowed one probe. allow_probe keeps failure_count and cooldown_until, so a
    # failed probe backs off further instead of restarting the ladder at base.
    log.warning(
        "brain_failover: %d provider(s) stuck past their cooldown window — "
        "allowing a probe (tried=%s)",
        len(stuck), tried,
    )
    _probe = getattr(fm, "allow_probe", None) or fm.record_success
    for p in stuck:
        _probe(p.id)
    tried.clear()
    return fm.next_provider(exclude=tried, requested_model=requested_model)


def _disabled_ids() -> dict[str, str]:
    """The operator kill-switch set, or empty when it cannot be read."""
    try:
        from services.brain_failover import disabled_providers
        return dict(disabled_providers())
    except Exception as exc:  # noqa: BLE001 — never let a kv problem break dispatch
        # Fail-open, but never silently: this treats every switched-off provider
        # as enabled for this call, which is the decision the kill switch exists
        # to prevent. disabled_providers() is documented not to raise, so
        # reaching here means something unusual (an import failure) and the
        # operator needs a trace of it.
        log.warning(
            "brain_failover: kill-switch read failed in dispatcher (%s) — "
            "treating all providers as enabled for this call", exc,
        )
        return {}


async def failover_chat_completion(
    payload: dict[str, Any],
    *,
    timeout_sec: float = _DEFAULT_TIMEOUT_SEC,
) -> FailoverResult:
    """Run one chat completion across the brain-failover chain.

    Tries each healthy provider in ``services.brain_failover`` order (free, then
    local, then paid), and up to three models per provider. Raises
    :class:`BrainFailoverExhausted` when nothing succeeds — never returns a
    partial or placeholder result. See :func:`_try_router` (ADR-008 §8).
    """
    if (routed := await _try_router(payload, timeout_sec)) is not None:
        return routed
    from services.brain_failover import get_failover_manager
    requested_model = str(payload.get("model") or "")
    fm = get_failover_manager()
    budget = _Budget(_MAX_TOTAL_ATTEMPTS, _WALL_CLOCK_BUDGET_SEC)
    tried: set[str] = set()          # exclusion set; cleared on breaker reset
    attempted: list[str] = []        # append-only record, for reporting
    attempts: list[str] = []
    failures: list[str] = []
    last_error = ""

    for _attempt in range(fm.max_attempts()):
        if budget.spent():
            failures = list(dict.fromkeys([*failures, budget.reason()]))
            break
        provider = _select_provider(fm, budget, tried, requested_model)
        if provider is None:
            provider = _recover_all_unhealthy(fm, tried, requested_model)
            if provider is None:
                # Falls through to the single terminal error below, not two.
                log.warning("brain_failover: no healthy providers left")
                break

        tried.add(provider.id)
        attempted = list(dict.fromkeys([*attempted, provider.id]))
        result, provider_error = await _try_provider(
            provider, payload, fm, attempts, timeout_sec, budget
        )
        if result is not None:
            _log_recovery(result, failures)
            return result
        if provider_error:
            failures = list(dict.fromkeys([*failures, provider_error]))
            last_error = provider_error

    _log_exhaustion(attempted, failures)
    raise BrainFailoverExhausted(last_error, set(attempted), failures)

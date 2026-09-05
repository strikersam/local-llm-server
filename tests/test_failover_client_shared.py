"""The brain-failover chain must be reachable by the CEO, not just the agent loop.

Before this, the dispatch loop lived inline inside ``AgentRunner._chat_text``, so
only the agent loop could reach the env-configured provider chain. Everything
going through ``backend.server.call_llm`` — the CEO strategic assessment above
all — fell back only across the DB-configured ``providers`` records. When those
were rate-limited the CEO dropped straight to its rule-based path while a dozen
untried providers sat healthy.

These tests pin the extracted dispatcher's behaviour and the fact that both
callers now use it.
"""
from __future__ import annotations

import httpx
import pytest

from packages.ai.failover_client import (
    BrainFailoverExhausted,
    FailoverResult,
    _build_request,
    failover_chat_completion,
)


class _StubProvider:
    def __init__(self, pid, base_url, models, api_key="k", tier="free"):
        self.id = pid
        self.base_url = base_url
        self.models = models
        self.api_key = api_key
        self.tier = tier
        self.is_healthy = True


class _StubManager:
    """Minimal stand-in for BrainFailoverManager."""

    def __init__(self, providers):
        self._providers = list(providers)
        self.successes: list[str] = []
        self.failures: list[tuple[str, str]] = []

    def max_attempts(self):
        return max(len(self._providers), 1)

    def next_provider(self, *, exclude=None, requested_model=None):
        exclude = exclude or set()
        for p in self._providers:
            if p.id not in exclude and p.is_healthy:
                return p
        return None

    def get_providers(self):
        return self._providers

    def resolve_model(self, provider, requested_model):
        return provider.models[0]

    def record_success(self, provider_id, latency_ms=0.0):
        self.successes.append(provider_id)

    def record_failure(self, provider_id, reason, status=None):
        self.failures.append((provider_id, reason))


def _openai_body(text="hello", pt=3, ct=5):
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct},
    }


@pytest.fixture
def patch_chain(monkeypatch):
    """Install a stub manager and a scripted sequence of HTTP responses."""
    # These tests are about the LEGACY failover chain and script its transport
    # directly. LLMRouter owns a different manager and a different client, so
    # an ambient LLM_ROUTER_ENABLED (set in production) would bypass the whole
    # scripted sequence. Pin it off — the router's own chain is covered by
    # tests/test_llm_router_e2e.py.
    monkeypatch.delenv("LLM_ROUTER_ENABLED", raising=False)

    def _apply(providers, responses):
        manager = _StubManager(providers)
        monkeypatch.setattr(
            "services.brain_failover.get_failover_manager", lambda: manager
        )
        calls: list[str] = []
        seq = list(responses)

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, json=None, headers=None):
                calls.append(url)
                nxt = seq.pop(0)
                if isinstance(nxt, Exception):
                    raise nxt
                return nxt

        monkeypatch.setattr(httpx, "AsyncClient", _Client)
        return manager, calls

    return _apply


@pytest.mark.asyncio
async def test_returns_first_success_with_usage(patch_chain) -> None:
    manager, calls = patch_chain(
        [_StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"])],
        [httpx.Response(200, json=_openai_body("ok", pt=11, ct=7))],
    )

    result = await failover_chat_completion(
        {"model": "llama-3.3-70b", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert isinstance(result, FailoverResult)
    assert result.text == "ok"
    assert result.provider_id == "groq"
    assert (result.prompt_tokens, result.completion_tokens) == (11, 7)
    assert manager.successes == ["groq"]


@pytest.mark.asyncio
async def test_rate_limited_provider_fails_over_to_the_next(patch_chain) -> None:
    """A 429 must move to the next provider, not another model on the same one."""
    manager, calls = patch_chain(
        [
            _StubProvider("zai", "https://api.z.ai/api/paas/v4", ["glm-5.2", "glm-5.1"]),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"]),
        ],
        [
            httpx.Response(429, json={"error": "rate limited"}),
            httpx.Response(200, json=_openai_body("recovered")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "glm-5.2", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "recovered"
    assert result.provider_id == "groq"
    # Exactly one call to zai — the second model on it must NOT be tried.
    assert len(calls) == 2
    assert ("zai", "rate_limited") in manager.failures


@pytest.mark.asyncio
async def test_410_tries_the_next_model_on_the_same_provider(patch_chain) -> None:
    """A dead model is per-model, so the sibling model is the right next try."""
    manager, calls = patch_chain(
        [_StubProvider("nvidia", "https://integrate.api.nvidia.com", ["dead", "alive"])],
        [
            httpx.Response(410, json={"error": "gone"}),
            httpx.Response(200, json=_openai_body("second model")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "dead", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "second model"
    assert result.model == "alive"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_network_error_fails_over(patch_chain) -> None:
    manager, calls = patch_chain(
        [
            _StubProvider("ollama", "http://localhost:11434", ["qwen3-coder:30b"]),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"]),
        ],
        [
            httpx.ConnectError("All connection attempts failed"),
            httpx.Response(200, json=_openai_body("cloud")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "qwen3-coder:30b", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "cloud"
    assert ("ollama", "network_error") in manager.failures


@pytest.mark.asyncio
async def test_exhaustion_raises_with_the_last_error(patch_chain) -> None:
    patch_chain(
        [_StubProvider("minimax", "https://api.minimax.chat/v1", ["mimo-v2-flash"])],
        [httpx.Response(401, json={"error": "bad key"})],
    )

    with pytest.raises(BrainFailoverExhausted) as excinfo:
        await failover_chat_completion(
            {"model": "mimo-v2-flash", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert "minimax" in excinfo.value.last_error
    assert "401" in excinfo.value.last_error
    assert "minimax" in excinfo.value.tried


@pytest.mark.asyncio
async def test_anthropic_provider_uses_the_messages_api(patch_chain) -> None:
    """The Anthropic wire format must survive the extraction."""
    manager, calls = patch_chain(
        [
            _StubProvider(
                "anthropic", "https://api.anthropic.com", ["claude-sonnet-5"],
                tier="paid",
            )
        ],
        [
            httpx.Response(
                200,
                json={
                    "id": "msg_1",
                    "content": [{"type": "text", "text": "claude replied"}],
                    "usage": {"input_tokens": 4, "output_tokens": 2},
                },
            )
        ],
    )

    result = await failover_chat_completion(
        {"model": "claude-sonnet-5", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert calls == ["https://api.anthropic.com/v1/messages"]
    assert result.text == "claude replied"
    assert (result.prompt_tokens, result.completion_tokens) == (4, 2)


class TestBuildRequest:
    def test_anthropic_native_gets_messages_route_and_x_api_key(self) -> None:
        url, headers, is_anthropic = _build_request(
            _StubProvider("anthropic", "https://api.anthropic.com", ["m"], api_key="sk")
        )

        assert is_anthropic is True
        assert url == "https://api.anthropic.com/v1/messages"
        assert headers["x-api-key"] == "sk"
        assert "Authorization" not in headers

    def test_openai_compatible_gateway_keeps_chat_completions(self) -> None:
        url, headers, is_anthropic = _build_request(
            _StubProvider("aerolink", "https://capi.aerolink.lat/v1", ["m"], api_key="sk")
        )

        assert is_anthropic is False
        assert url == "https://capi.aerolink.lat/v1/chat/completions"
        assert headers["Authorization"] == "Bearer sk"


def test_agent_loop_delegates_to_the_shared_client() -> None:
    """The loop must not carry its own copy of the dispatch loop."""
    import inspect

    from agent.loop import AgentRunner

    source = inspect.getsource(AgentRunner._chat_text)

    assert "failover_chat_completion" in source, (
        "AgentRunner._chat_text no longer delegates to the shared failover client"
    )
    # The inline loop's tell-tale locals must be gone, or the logic has been
    # duplicated back into the loop.
    assert "fm.next_provider(" not in source, (
        "the dispatch loop has been re-inlined into AgentRunner._chat_text; it "
        "belongs in packages/ai/failover_client.py so call_llm shares it"
    )


def test_call_llm_falls_through_to_the_shared_client() -> None:
    """call_llm must reach the env chain when DB providers are exhausted."""
    import inspect

    import backend.server

    source = inspect.getsource(backend.server.call_llm)

    assert "failover_chat_completion" in source, (
        "call_llm does not fall through to the brain-failover chain, so the CEO "
        "still degrades to rule-based while healthy providers sit untried"
    )
    assert "ProviderFallbackError" in source


@pytest.mark.asyncio
async def test_malformed_2xx_body_fails_over_instead_of_crashing(patch_chain) -> None:
    """A 2xx with an unusable body must be a failed attempt, never a crash.

    The dispatcher promises it either returns a complete result or raises
    BrainFailoverExhausted. Parsing outside the attempt guard broke that: an
    empty `choices` array raised IndexError straight out of the call.
    """
    manager, calls = patch_chain(
        [
            _StubProvider("zai", "https://api.z.ai/api/paas/v4", ["glm-5.2"]),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"]),
        ],
        [
            httpx.Response(200, json={"choices": []}),  # 2xx, unusable
            httpx.Response(200, json=_openai_body("recovered")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "glm-5.2", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "recovered"
    assert result.provider_id == "groq"


@pytest.mark.asyncio
async def test_non_json_2xx_body_fails_over(patch_chain) -> None:
    patch_chain(
        [_StubProvider("zai", "https://api.z.ai/api/paas/v4", ["glm-5.2"])],
        [httpx.Response(200, text="<html>gateway</html>")],
    )

    with pytest.raises(BrainFailoverExhausted) as excinfo:
        await failover_chat_completion(
            {"model": "glm-5.2", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert "malformed" in excinfo.value.last_error


@pytest.mark.asyncio
async def test_null_content_is_treated_as_malformed(patch_chain) -> None:
    patch_chain(
        [_StubProvider("zai", "https://api.z.ai/api/paas/v4", ["glm-5.2"])],
        [httpx.Response(200, json={"choices": [{"message": {"content": None}}]})],
    )

    with pytest.raises(BrainFailoverExhausted):
        await failover_chat_completion(
            {"model": "glm-5.2", "messages": [{"role": "user", "content": "hi"}]}
        )


def test_dispatcher_stays_within_the_function_length_limit() -> None:
    """ENGINEERING_STANDARDS caps functions at 50 lines."""
    import inspect

    source_lines, _ = inspect.getsourcelines(failover_chat_completion)

    assert len(source_lines) <= 50, (
        f"failover_chat_completion is {len(source_lines)} lines; the repo caps "
        f"functions at 50. Extract another helper."
    )


# ── Log severity: fallback working is not an incident ────────────────────────
#
# agent/log_monitor.py attaches an ERROR-level handler that auto-files GitHub
# issues, and its operational-skip list covers 429/502/503/504 but NOT 401. So an
# intermediate provider failure logged at ERROR opened a ticket for a provider
# the system had already successfully failed over.


@pytest.mark.asyncio
async def test_successful_failover_logs_no_error(patch_chain, caplog) -> None:
    """A recovered call must leave zero ERROR records behind."""
    patch_chain(
        [
            _StubProvider("zhipu", "https://open.bigmodel.cn/api/paas/v4", ["glm-4"]),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"]),
        ],
        [
            httpx.Response(401, json={"error": "unauthorized"}),
            httpx.Response(200, json=_openai_body("recovered")),
        ],
    )

    with caplog.at_level("WARNING", logger="qwen-proxy"):
        result = await failover_chat_completion(
            {"model": "glm-4", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert result.text == "recovered"
    errors = [r for r in caplog.records if r.levelname in ("ERROR", "CRITICAL")]
    assert not errors, (
        "fallback recovered but still logged an error, which would trip "
        f"log_monitor's issue-filing: {[r.getMessage() for r in errors]}"
    )


@pytest.mark.asyncio
async def test_exhausted_chain_logs_exactly_one_error(patch_chain, caplog) -> None:
    """The terminal failure is a real error — and only one."""
    patch_chain(
        [
            _StubProvider("zhipu", "https://open.bigmodel.cn/api/paas/v4", ["glm-4"]),
            _StubProvider("minimax", "https://api.minimax.chat/v1", ["mimo-v2-flash"]),
        ],
        [
            httpx.Response(401, json={"error": "unauthorized"}),
            httpx.Response(401, json={"error": "unauthorized"}),
        ],
    )

    with caplog.at_level("WARNING", logger="qwen-proxy"):
        with pytest.raises(BrainFailoverExhausted):
            await failover_chat_completion(
                {"model": "glm-4", "messages": [{"role": "user", "content": "hi"}]}
            )

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1, (
        f"expected exactly one terminal error, got {len(errors)}: "
        f"{[r.getMessage() for r in errors]}"
    )


@pytest.mark.asyncio
async def test_terminal_error_names_every_failed_provider(patch_chain) -> None:
    """Reporting only the last provider hid the other broken keys.

    The production symptom: "401 Unauthorized for open.bigmodel.cn" made a
    whole-chain outage look like one bad Zhipu key.
    """
    patch_chain(
        [
            _StubProvider("zhipu", "https://open.bigmodel.cn/api/paas/v4", ["glm-4"]),
            _StubProvider("minimax", "https://api.minimax.chat/v1", ["mimo-v2-flash"]),
            _StubProvider("ollama", "http://localhost:11434", ["qwen3-coder:30b"]),
        ],
        [
            httpx.Response(401, json={"error": "unauthorized"}),
            httpx.Response(429, json={"error": "rate limited"}),
            httpx.ConnectError("All connection attempts failed"),
        ],
    )

    with pytest.raises(BrainFailoverExhausted) as excinfo:
        await failover_chat_completion(
            {"model": "glm-4", "messages": [{"role": "user", "content": "hi"}]}
        )

    message = str(excinfo.value)
    # Every provider, with its own distinct reason, must be visible.
    assert "zhipu" in message and "401" in message
    assert "minimax" in message and "rate-limited" in message
    assert "ollama" in message and "network error" in message
    assert len(excinfo.value.failures) == 3


# ── Billing refusals and accurate accounting ────────────────────────────────
#
# From a real production chain where all 14 providers failed. Two defects showed
# up in that log: DeepSeek's 402 "Insufficient Balance" and Anthropic's 400
# "credit balance is too low" were not recognised as provider-level, so each
# burned three model attempts repeating an identical refusal; and the reported
# `tried=` list showed 9 providers beside 14 failures with ollama listed twice.


@pytest.mark.asyncio
async def test_402_insufficient_balance_moves_to_next_provider(patch_chain) -> None:
    """DeepSeek's 402 must not burn the other model slots."""
    manager, calls = patch_chain(
        [
            _StubProvider("deepseek", "https://api.deepseek.com/v1", ["a", "b", "c"]),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"]),
        ],
        [
            httpx.Response(402, json={"error": {"message": "Insufficient Balance"}}),
            httpx.Response(200, json=_openai_body("recovered")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "a", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.provider_id == "groq"
    # One call to deepseek only — models "b" and "c" must NOT be tried.
    assert len(calls) == 2
    assert ("deepseek", "payment_required") in manager.failures


@pytest.mark.asyncio
async def test_anthropic_400_credit_balance_is_treated_as_billing(patch_chain) -> None:
    """A 400 whose body is really "you have no money" is provider-level."""
    manager, calls = patch_chain(
        [
            _StubProvider(
                "anthropic", "https://api.anthropic.com", ["m1", "m2", "m3"],
                tier="paid",
            ),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b"]),
        ],
        [
            httpx.Response(
                400,
                json={
                    "type": "error",
                    "error": {
                        "type": "invalid_request_error",
                        "message": (
                            "Your credit balance is too low to access the "
                            "Anthropic API. Please go to Plans & Billing."
                        ),
                    },
                },
            ),
            httpx.Response(200, json=_openai_body("recovered")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.provider_id == "groq"
    assert len(calls) == 2, "the other two Anthropic models must not be retried"
    assert ("anthropic", "payment_required") in manager.failures


@pytest.mark.asyncio
async def test_a_plain_400_still_tries_the_next_model(patch_chain) -> None:
    """Only billing-shaped 400s bail out; a genuine bad request is per-model."""
    manager, calls = patch_chain(
        [_StubProvider("nvidia", "https://integrate.api.nvidia.com", ["bad", "good"])],
        [
            httpx.Response(400, json={"error": "unsupported parameter for model"}),
            httpx.Response(200, json=_openai_body("second model")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "bad", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.model == "good"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_exhaustion_reports_each_provider_once(patch_chain) -> None:
    """The failure list must not double-count a provider, nor undercount."""
    patch_chain(
        [
            _StubProvider("zhipu", "https://open.bigmodel.cn/api/paas/v4", ["glm-4"]),
            _StubProvider("groq", "https://api.groq.com/openai/v1", ["llama"]),
            _StubProvider("ollama", "http://localhost:11434", ["qwen"]),
        ],
        [
            httpx.Response(401, json={"error": "unauthorized"}),
            httpx.Response(429, json={"error": "rate limited"}),
            httpx.ConnectError("All connection attempts failed"),
        ],
    )

    with pytest.raises(BrainFailoverExhausted) as excinfo:
        await failover_chat_completion(
            {"model": "glm-4", "messages": [{"role": "user", "content": "hi"}]}
        )

    failures = excinfo.value.failures
    assert len(failures) == 3, f"expected one entry per provider, got {failures}"
    # The count in the message must match the number of distinct providers.
    assert "All 3 brain provider attempt(s) failed" in str(excinfo.value)
    # And every attempted provider must be reported.
    assert excinfo.value.tried == {"zhipu", "groq", "ollama"}


# ── Fan-out budget ──────────────────────────────────────────────────────────
#
# Without a cap the attempt count multiplies and self-inflicts the 429s the chain
# is trying to route around: 14 providers x 3 models x 4 parse retries x 5 task
# re-queues = up to 840 HTTP calls for ONE task, against free tiers, while the
# agency runs many tasks and 34 loops concurrently.


def _many_providers(n: int) -> list:
    return [
        _StubProvider(f"p{i}", f"https://p{i}.test/v1", ["m1", "m2", "m3"])
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_total_attempts_are_capped_across_the_whole_chain(
    patch_chain, monkeypatch
) -> None:
    """The cap is global, not per provider — worst case linear, not a product."""
    import packages.ai.failover_client as fc

    monkeypatch.setattr(fc, "_MAX_TOTAL_ATTEMPTS", 6)
    # 10 providers x 3 models = 30 attempts if uncapped.
    _, calls = patch_chain(
        _many_providers(10),
        [httpx.Response(500, json={"error": "boom"}) for _ in range(40)],
    )

    with pytest.raises(BrainFailoverExhausted) as excinfo:
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert len(calls) <= 6, (
        f"budget not enforced: {len(calls)} HTTP calls made, cap is 6"
    )
    assert "budget exhausted" in str(excinfo.value)


@pytest.mark.asyncio
async def test_budget_does_not_block_an_early_success(patch_chain, monkeypatch) -> None:
    """A healthy first provider must still answer in one attempt."""
    import packages.ai.failover_client as fc

    monkeypatch.setattr(fc, "_MAX_TOTAL_ATTEMPTS", 6)
    _, calls = patch_chain(
        _many_providers(10), [httpx.Response(200, json=_openai_body("fast"))]
    )

    result = await failover_chat_completion(
        {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "fast"
    assert len(calls) == 1, "a healthy provider must not consume extra budget"


@pytest.mark.asyncio
async def test_budget_still_allows_real_failover(patch_chain, monkeypatch) -> None:
    """Capping must not defeat the point: recovery within budget still works."""
    import packages.ai.failover_client as fc

    monkeypatch.setattr(fc, "_MAX_TOTAL_ATTEMPTS", 6)
    _, calls = patch_chain(
        _many_providers(10),
        [
            httpx.Response(429, json={"error": "rate limited"}),
            httpx.Response(401, json={"error": "unauthorized"}),
            httpx.Response(200, json=_openai_body("third provider")),
        ],
    )

    result = await failover_chat_completion(
        {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "third provider"
    assert len(calls) == 3


def test_budget_is_operator_tunable() -> None:
    """Breadth vs quota is the operator's call, so both budgets are env vars."""
    import inspect

    import packages.ai.failover_client as fc

    src = inspect.getsource(fc)
    assert "BRAIN_MAX_PROVIDER_ATTEMPTS" in src
    assert "BRAIN_FAILOVER_BUDGET_SEC" in src
    assert fc._MAX_TOTAL_ATTEMPTS >= 1


# ── The paid tier must be reachable, not starved by the free tier ────────────
#
# BRAIN_MAX_PROVIDER_ATTEMPTS caps total attempts across the whole chain, and
# providers are ordered free → local → paid. An operator with ten free keys
# therefore spent every attempt inside the free tier and the chain raised
# BrainFailoverExhausted having never contacted the paid provider they pay for —
# precisely when it was needed, since the free tiers were all rate-limited.
#
# _PAID_RESERVE_ATTEMPTS holds back a slice of the budget that only paid-tier
# providers may spend. It stays inert for a free-only deployment, and allow_paid
# (enforced in brain_failover._build_registry, which simply omits paid providers)
# remains the sole spend gate — this changes reachability, never authority.

_FREE_IDS = ["nvidia", "groq", "cerebras", "zhipu", "deepseek", "together",
             "dashscope", "moonshot", "zai", "mistral"]


def _free_tier() -> list[_StubProvider]:
    """The operator's free-tier shape: ten providers, all with keys."""
    return [_StubProvider(p, f"https://{p}.test/v1", ["m1"]) for p in _FREE_IDS]


def _paid(pid: str = "aerolink", healthy: bool = True) -> _StubProvider:
    """A paid-tier provider, optionally in cooldown."""
    p = _StubProvider(pid, f"https://{pid}.test/v1", ["m1"], tier="paid")
    p.is_healthy = healthy
    return p


def _rate_limited(n: int) -> list[httpx.Response]:
    """``n`` scripted 429s — the state every free provider was reported in."""
    return [httpx.Response(429, json={"error": "rate limited"}) for _ in range(n)]


def _hit_ids(calls: list[str]) -> list[str]:
    """Provider ids actually contacted, in order, parsed from the request URLs."""
    return [c.split("//")[1].split(".")[0] for c in calls]


@pytest.mark.asyncio
async def test_paid_provider_is_reached_when_the_free_tier_burns_the_budget(
    patch_chain,
) -> None:
    """The regression this reserve exists for: €50 of paid capacity, never used."""
    import packages.ai.failover_client as fc

    _, calls = patch_chain(_free_tier() + [_paid()], _rate_limited(40))

    with pytest.raises(BrainFailoverExhausted):
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert "aerolink" in _hit_ids(calls), (
        "the paid provider must be contacted before the chain gives up — without "
        "the reserve the free tier consumes all "
        f"{fc._MAX_TOTAL_ATTEMPTS} attempts and paid capacity is unreachable"
    )
    assert len(calls) <= fc._MAX_TOTAL_ATTEMPTS, (
        "the reserve must come OUT of the existing budget, not extend it — "
        "extending it would reintroduce the fan-out that caused the 429s"
    )


@pytest.mark.asyncio
async def test_a_free_only_deployment_keeps_the_whole_budget(patch_chain) -> None:
    """No paid provider admitted → the reserve is inert, nothing changes."""
    import packages.ai.failover_client as fc

    _, calls = patch_chain(_free_tier(), _rate_limited(40))

    with pytest.raises(BrainFailoverExhausted):
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert len(calls) == fc._MAX_TOTAL_ATTEMPTS, (
        "an operator running free-only must not lose attempts to a reserve that "
        "no provider can spend"
    )


@pytest.mark.asyncio
async def test_the_reserve_never_fires_while_the_free_tier_is_working(
    patch_chain,
) -> None:
    """A healthy free provider still answers in one attempt, at no cost."""
    _, calls = patch_chain(
        _free_tier() + [_paid()],
        [httpx.Response(200, json=_openai_body("free tier answered"))],
    )

    result = await failover_chat_completion(
        {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "free tier answered"
    assert _hit_ids(calls) == ["nvidia"]


@pytest.mark.asyncio
async def test_free_tier_uses_the_reserve_when_no_paid_provider_is_selectable(
    patch_chain,
) -> None:
    """A paid provider in cooldown must not strand the reserve unspent."""
    import packages.ai.failover_client as fc

    _, calls = patch_chain(
        _free_tier() + [_paid(healthy=False)], _rate_limited(40)
    )

    with pytest.raises(BrainFailoverExhausted):
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert len(calls) == fc._MAX_TOTAL_ATTEMPTS
    assert "aerolink" not in _hit_ids(calls)


@pytest.mark.asyncio
async def test_the_reserve_can_be_switched_off(patch_chain, monkeypatch) -> None:
    """BRAIN_PAID_RESERVE_ATTEMPTS=0 restores the flat cap for cost-sensitive ops."""
    import packages.ai.failover_client as fc

    monkeypatch.setattr(fc, "_PAID_RESERVE_ATTEMPTS", 0)
    _, calls = patch_chain(_free_tier() + [_paid()], _rate_limited(40))

    with pytest.raises(BrainFailoverExhausted):
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert "aerolink" not in _hit_ids(calls)
    assert len(calls) == fc._MAX_TOTAL_ATTEMPTS


def test_paid_reserve_is_operator_tunable() -> None:
    import inspect

    import packages.ai.failover_client as fc

    assert "BRAIN_PAID_RESERVE_ATTEMPTS" in inspect.getsource(fc)
    assert fc._PAID_RESERVE_ATTEMPTS >= 0
    assert fc._PAID_RESERVE_ATTEMPTS < fc._MAX_TOTAL_ATTEMPTS, (
        "a reserve at or above the total cap would starve the free tier instead"
    )


@pytest.mark.parametrize(
    ("env_value", "expected", "why"),
    [
        (None, 2, "the default"),
        ("0", 0, "0 must mean OFF — the documented escape hatch"),
        ("1", 1, "a valid value passes through"),
        ("5", 5, "the largest value that still leaves the free tier one attempt"),
        ("6", 5, "at the cap: clamped, or the free tier gets nothing"),
        ("20", 5, "far above the cap: clamped, not silently paid-first"),
        ("-3", 0, "negative is nonsense; treat it as off"),
        ("abc", 2, "unparseable falls back to the default"),
    ],
)
def test_the_reserve_is_bounded_when_read_from_the_environment(
    monkeypatch, env_value, expected, why
) -> None:
    """Read through the ENV, not the constant — that is where the bug lived.

    ``_env_int`` floors at 1, so ``BRAIN_PAID_RESERVE_ATTEMPTS=0`` silently
    became 1 and the documented off switch did nothing. A sibling test that
    monkeypatches ``_PAID_RESERVE_ATTEMPTS`` directly cannot catch that, because
    it bypasses the parsing entirely. And an unclamped value at or above the cap
    left the free tier a single attempt, quietly turning a cost-control knob into
    a paid-first switch.
    """
    import packages.ai.failover_client as fc

    if env_value is None:
        monkeypatch.delenv("BRAIN_PAID_RESERVE_ATTEMPTS", raising=False)
    else:
        monkeypatch.setenv("BRAIN_PAID_RESERVE_ATTEMPTS", env_value)

    assert fc._paid_reserve() == expected, why


def test_the_free_tier_always_keeps_at_least_one_attempt() -> None:
    """No reserve value may lock the free tier out from the very first attempt."""
    import packages.ai.failover_client as fc

    for reserve in range(0, fc._MAX_TOTAL_ATTEMPTS + 5):
        budget = fc._Budget(fc._MAX_TOTAL_ATTEMPTS, 180.0)
        assert budget.unpaid_slice_spent(reserve) is False, (
            f"reserve={reserve} excludes free providers before a single attempt "
            f"has been made"
        )


# ── Zero-attempt deadlock: disabled providers masked the recovery path ───────
#
# The most common error in production was "all 0 provider(s) exhausted (none) —
# no provider attempted": the chain gave up having made no HTTP call at all.
#
# Cause: a provider switched off by the kill switch is NOT in cooldown, so its
# breaker is CLOSED and it reads as healthy. `_recover_all_unhealthy` bailed on
# `any(p.is_healthy)` over ALL providers, so one disabled provider was enough to
# mask the all-unhealthy condition and skip the breaker reset. Meanwhile
# `next_provider` correctly excluded the disabled ones and returned None because
# every ENABLED provider was in 429 cooldown. Net effect: total deadlock, zero
# attempts, and a log line that named nothing actionable.

def _mixed_registry(disabled: dict[str, str], cooling: list[str],
                    ready: list[str]) -> tuple:
    """Build the production shape: some switched off, some cooling, some ready."""
    provs = []
    for pid in list(disabled) + cooling + ready:
        p = _StubProvider(pid, f"https://{pid}.test/v1", ["m1"])
        p.is_healthy = pid not in cooling      # disabled ones look healthy
        provs.append(p)
    return provs


@pytest.mark.asyncio
async def test_a_disabled_provider_no_longer_blocks_breaker_recovery(
    patch_chain, monkeypatch
) -> None:
    """The exact production shape: 2 switched off, 2 in 429 cooldown."""
    import services.brain_failover as bf

    disabled = {"zhipu": "auto: 401 invalid or expired API key",
                "deepseek": "auto: 402 out of credit"}
    monkeypatch.setattr(bf, "disabled_providers", lambda force=False: disabled)

    provs = _mixed_registry(disabled, cooling=["groq", "nvidia"], ready=[])
    manager, calls = patch_chain(
        provs, [httpx.Response(200, json=_openai_body("recovered"))]
    )

    def _next(*, exclude=None, requested_model=None):
        off = bf.disabled_providers()
        for p in manager._providers:
            if p.id not in (exclude or set()) and p.id not in off and p.is_healthy:
                return p
        return None

    def _record_success(pid, latency_ms=0.0):
        for p in manager._providers:
            if p.id == pid:
                p.is_healthy = True

    monkeypatch.setattr(manager, "next_provider", _next)
    monkeypatch.setattr(manager, "record_success", _record_success)
    monkeypatch.setattr(manager, "allow_probe", _record_success, raising=False)
    monkeypatch.setattr(
        manager, "seconds_until_recovery", lambda: 30.0, raising=False
    )
    # The two cooling providers are wedged well past their own backoff window,
    # so the anti-deadlock valve applies and a probe is allowed. This is what
    # keeps the original point of this test alive: the two *disabled* providers
    # must not read as healthy and mask the all-unhealthy condition, or the
    # chain gives up having made ZERO attempts.
    monkeypatch.setattr(
        manager, "stuck_beyond_cooldown", lambda pid, **kw: True, raising=False
    )

    result = await failover_chat_completion(
        {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
    )

    assert result.text == "recovered"
    assert len(calls) == 1, (
        "before the fix this made ZERO attempts and raised, because two disabled "
        "providers read as healthy and suppressed the breaker reset"
    )


@pytest.mark.asyncio
async def test_ordinary_rate_limit_cooldown_is_waited_out_not_reset(
    patch_chain, monkeypatch
) -> None:
    """The doom-loop guard, at the level of the whole chain.

    Same shape as the test above but the cooling providers are in an *ordinary*
    429 backoff rather than wedged. Recovery must decline to reset them and the
    call must fail, because four rate-limited providers have no capacity that
    reordering or re-probing can find. Production ran the opposite behaviour for
    20+ minutes: every provider reset and re-hammered every few seconds.
    """
    import services.brain_failover as bf

    disabled = {"zhipu": "auto: 401 invalid or expired API key"}
    monkeypatch.setattr(bf, "disabled_providers", lambda force=False: disabled)

    provs = _mixed_registry(disabled, cooling=["groq", "nvidia"], ready=[])
    manager, calls = patch_chain(
        provs, [httpx.Response(200, json=_openai_body("should-not-happen"))]
    )

    resets: list[str] = []

    def _record_success(pid, latency_ms=0.0):
        resets.append(pid)
        for p in manager._providers:
            if p.id == pid:
                p.is_healthy = True

    monkeypatch.setattr(manager, "next_provider", lambda **kw: None)
    monkeypatch.setattr(manager, "record_success", _record_success)
    monkeypatch.setattr(manager, "allow_probe", _record_success, raising=False)
    monkeypatch.setattr(
        manager, "stuck_beyond_cooldown", lambda pid, **kw: False, raising=False
    )
    monkeypatch.setattr(
        manager, "seconds_until_recovery", lambda: 45.0, raising=False
    )

    with pytest.raises(Exception):
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert calls == [], f"rate-limited providers were re-hammered: {calls}"
    assert resets == [], f"cooldowns were reset instead of waited out: {resets}"


@pytest.mark.asyncio
async def test_recovery_does_not_re_enable_a_switched_off_provider(
    patch_chain, monkeypatch
) -> None:
    """The kill switch must survive a breaker probe, or it means nothing.

    Recovery may re-probe a wedged provider. It must touch only enabled ones —
    probing a disabled provider would quietly undo the operator's decision,
    which is the whole point of a manual-re-enable switch.
    """
    import services.brain_failover as bf

    disabled = {"zhipu": "auto: 401 invalid or expired API key"}
    monkeypatch.setattr(bf, "disabled_providers", lambda force=False: disabled)

    provs = _mixed_registry(disabled, cooling=["groq"], ready=[])
    manager, _ = patch_chain(provs, [httpx.Response(200, json=_openai_body("ok"))])
    revived: list[str] = []
    monkeypatch.setattr(manager, "record_success",
                        lambda pid, latency_ms=0.0: revived.append(pid))
    monkeypatch.setattr(manager, "allow_probe",
                        lambda pid: revived.append(pid), raising=False)
    # Wedged, so the anti-deadlock valve fires and a probe is attempted at all —
    # which is the only way this test can observe who gets revived.
    monkeypatch.setattr(
        manager, "stuck_beyond_cooldown", lambda pid, **kw: True, raising=False
    )
    monkeypatch.setattr(
        manager, "seconds_until_recovery", lambda: None, raising=False
    )
    monkeypatch.setattr(manager, "next_provider",
                        lambda **k: next(
                            (p for p in manager._providers
                             if p.id not in bf.disabled_providers() and p.is_healthy),
                            None))

    with pytest.raises(BrainFailoverExhausted):
        await failover_chat_completion(
            {"model": "m1", "messages": [{"role": "user", "content": "hi"}]}
        )

    assert "zhipu" not in revived, (
        "a switched-off provider must never be revived by breaker recovery"
    )


class TestZeroAttemptDiagnostics:
    """A zero-attempt exhaustion must say WHICH of the three causes it is.

    Nothing configured, everything switched off, and everything in cooldown need
    completely different operator responses, and the old message
    ("no provider attempted") distinguished none of them.

    These assert the FORMATTING only. The underlying counts come from
    ``brain_failover.brain_availability_summary()``, which is the shared source of
    truth for the public doctor endpoint, the CEO supervisor and the Providers
    screen — recomputing them here would create a second implementation that can
    disagree with the one operators actually read.
    """

    def _summary(self, monkeypatch, payload) -> None:
        monkeypatch.setattr(
            "services.brain_failover.brain_availability_summary",
            lambda: payload,
        )

    def test_nothing_configured(self, monkeypatch) -> None:
        import packages.ai.failover_client as fc
        self._summary(monkeypatch, {"total": 0, "usable": 0})
        out = fc._describe_registry()
        assert "no providers configured" in out
        assert "API key" in out, "must say what to do about it"

    def test_switched_off_providers_are_named_with_their_remedy(
        self, monkeypatch
    ) -> None:
        import packages.ai.failover_client as fc
        self._summary(monkeypatch, {
            "total": 4, "usable": 0, "cooling": ["groq", "nvidia"],
            "disabled": [
                {"id": "zhipu", "remedy": "Update the key, then switch it back on."},
                {"id": "deepseek", "remedy": "Top up the account."},
            ],
            "state_durable": True,
        })
        out = fc._describe_registry()

        assert "4 configured" in out
        assert "2 switched OFF" in out
        assert "zhipu (Update the key" in out
        assert "deepseek (Top up the account.)" in out
        assert "2 in cooldown: groq, nvidia" in out

    def test_cooldown_is_distinguished_from_switched_off(self, monkeypatch) -> None:
        import packages.ai.failover_client as fc
        self._summary(monkeypatch, {
            "total": 3, "usable": 1, "cooling": ["groq"],
            "disabled": [{"id": "zhipu", "remedy": "Update the key."}],
            "state_durable": True,
        })
        out = fc._describe_registry()

        assert "1 usable" in out
        assert "1 switched OFF" in out
        assert "1 in cooldown: groq" in out

    def test_non_durable_state_is_called_out(self, monkeypatch) -> None:
        """An operator whose switches reset on deploy needs to know that here."""
        import packages.ai.failover_client as fc
        self._summary(monkeypatch, {
            "total": 2, "usable": 0, "cooling": ["groq"],
            "disabled": [], "state_durable": False,
        })
        assert "state not durable" in fc._describe_registry()

    def test_diagnostics_never_raise(self, monkeypatch) -> None:
        """A broken registry must not turn a failed call into a crash."""
        import packages.ai.failover_client as fc

        def _boom():
            raise RuntimeError("registry exploded")

        monkeypatch.setattr(
            "services.brain_failover.brain_availability_summary", _boom
        )
        assert fc._describe_registry().startswith("registry unavailable")


class TestDeadModelExclusion:
    """A model that answered 410/404 must be held out of the rotation for a
    cooldown, not re-tried on every round.

    #1427's implement runs spent one of the three capped NVIDIA slots on
    ``nvidia/llama-3.1-nemotron-ultra-253b-v1`` every round: NVIDIA's catalogue
    still lists it, but calling it 404s. The failover chain tried it, fell
    through to the next model, and did the same again on the next round. These
    tests lock in that a dead model is remembered and skipped, and that the
    exclusion is learned at run time (no hardcoded list to rot) and self-heals
    when the cooldown lapses.
    """

    @pytest.fixture(autouse=True)
    def _reset_discovery_state(self):
        from packages.ai.model_discovery import reset_cache

        reset_cache()
        yield
        reset_cache()

    @pytest.mark.asyncio
    async def test_410_model_is_skipped_on_the_next_request(self, patch_chain) -> None:
        provider = _StubProvider(
            "nvidia", "https://integrate.api.nvidia.com", ["dead", "alive"]
        )
        # Round 1: dead 410s, sibling serves. Round 2 is scripted with a SINGLE
        # response — proof the dead model is not called again (a re-probe would
        # pop past the end of the sequence and raise).
        manager, calls = patch_chain(
            [provider],
            [
                httpx.Response(410, json={"error": "gone"}),
                httpx.Response(200, json=_openai_body("first")),
                httpx.Response(200, json=_openai_body("second")),
            ],
        )
        payload = {"model": "dead", "messages": [{"role": "user", "content": "hi"}]}

        first = await failover_chat_completion(dict(payload))
        assert first.model == "alive"
        assert len(calls) == 2

        calls.clear()
        second = await failover_chat_completion(dict(payload))
        assert second.model == "alive"
        # Exactly one call — the known-dead model was excluded, not re-probed.
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_404_model_is_skipped_on_the_next_request(self, patch_chain) -> None:
        provider = _StubProvider(
            "nvidia", "https://integrate.api.nvidia.com", ["ghost", "alive"]
        )
        manager, calls = patch_chain(
            [provider],
            [
                httpx.Response(404, text="Not Found"),
                httpx.Response(200, json=_openai_body("first")),
                httpx.Response(200, json=_openai_body("second")),
            ],
        )
        payload = {"model": "ghost", "messages": [{"role": "user", "content": "hi"}]}

        first = await failover_chat_completion(dict(payload))
        assert first.model == "alive"
        assert len(calls) == 2

        calls.clear()
        second = await failover_chat_completion(dict(payload))
        assert second.model == "alive"
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_dead_model_returns_after_its_cooldown_lapses(self, patch_chain) -> None:
        """The mark is a cooldown, not a tombstone: a restored id finds its own
        way back once the TTL expires — no operator action, no list to edit."""
        import packages.ai.model_discovery as md

        provider = _StubProvider(
            "nvidia", "https://integrate.api.nvidia.com", ["dead", "alive"]
        )
        manager, calls = patch_chain(
            [provider],
            [
                httpx.Response(410, json={"error": "gone"}),
                httpx.Response(200, json=_openai_body("first")),
                httpx.Response(410, json={"error": "gone"}),
                httpx.Response(200, json=_openai_body("recovered")),
            ],
        )
        payload = {"model": "dead", "messages": [{"role": "user", "content": "hi"}]}

        await failover_chat_completion(dict(payload))
        assert md.dead_models("nvidia") == {"dead"}

        # Force the cooldown to have already elapsed.
        md._DEAD["nvidia"]["dead"] = 0.0
        assert md.dead_models("nvidia") == set()

        calls.clear()
        result = await failover_chat_completion(dict(payload))
        # Eligible again → the model is re-probed (dead 410s again, alive serves).
        assert len(calls) == 2
        assert result.model == "alive"

    def test_exclusion_never_empties_the_rotation(self) -> None:
        """If every candidate is cooling, keep the order rather than sideline the
        whole provider on stale marks — one gets through to re-confirm."""
        from packages.ai.failover_client import _models_to_try
        from packages.ai.model_discovery import DEAD_TTL_GONE_SEC, mark_dead

        provider = _StubProvider(
            "nvidia", "https://integrate.api.nvidia.com", ["a", "b"]
        )
        mark_dead("nvidia", "a", ttl_sec=DEAD_TTL_GONE_SEC)
        mark_dead("nvidia", "b", ttl_sec=DEAD_TTL_GONE_SEC)

        ordered = _models_to_try(provider, "a")
        assert ordered, "all-dead must not filter to an empty rotation"

    def test_a_live_sibling_is_kept_when_only_one_model_is_dead(self) -> None:
        from packages.ai.failover_client import _models_to_try
        from packages.ai.model_discovery import DEAD_TTL_UNKNOWN_SEC, mark_dead

        provider = _StubProvider(
            "nvidia", "https://integrate.api.nvidia.com", ["dead", "alive"]
        )
        mark_dead("nvidia", "dead", ttl_sec=DEAD_TTL_UNKNOWN_SEC)

        ordered = _models_to_try(provider, "dead")
        assert "dead" not in ordered
        assert "alive" in ordered

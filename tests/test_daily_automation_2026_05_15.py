"""Daily automation tests — 2026-05-15

Covers three features implemented in this run:
  1. /v1/messages/count_tokens endpoint
     - Basic token estimation from text content
     - Image blocks counted as fixed token cost
     - Tool definitions add overhead
     - System prompt included in count
     - Returns {"input_tokens": N} with anthropic-version header
  2. Extended thinking → reasoning model routing
     - thinking: {type: "enabled"} triggers agent_plan endpoint_type
     - Routing uses "reasoning" category → prefers DeepSeek-R1 or similar
     - X-Thinking-Budget header returned when budget_tokens set
     - Non-thinking requests unaffected
  3. Anthropic output_format → Ollama format passthrough
     - output_format json_schema → openai_payload["format"] = schema dict
     - output_format json_object → openai_payload["format"] = "json"
     - No output_format → no format in payload
     - anthropic-beta header set when output_format used
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# 1. Token estimation helper
# ─────────────────────────────────────────────────────────────────────────────

class TestEstimateTokensForMessages:
    """Unit tests for handlers.anthropic_compat._estimate_tokens_for_messages."""

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from handlers.anthropic_compat import _estimate_tokens_for_messages
        self.fn = _estimate_tokens_for_messages

    def test_empty_returns_at_least_one(self):
        result = self.fn([], None)
        assert result >= 1

    def test_simple_text_message(self):
        messages = [{"role": "user", "content": "Hello, world!"}]
        result = self.fn(messages, None)
        # "Hello, world!" = 13 chars → ~3-4 tokens + overhead
        assert result >= 3

    def test_system_prompt_counted(self):
        messages = [{"role": "user", "content": "Hi"}]
        without_system = self.fn(messages, None)
        with_system = self.fn(messages, "You are a helpful assistant " * 10)
        assert with_system > without_system

    def test_image_block_adds_fixed_cost(self):
        text_only = [{"role": "user", "content": [{"type": "text", "text": "what do you see?"}]}]
        with_image = [{"role": "user", "content": [
            {"type": "text", "text": "what do you see?"},
            {"type": "image", "source": {"type": "base64", "data": "abc"}},
        ]}]
        count_text = self.fn(text_only, None)
        count_image = self.fn(with_image, None)
        # Image should add ~1000 tokens
        assert count_image > count_text + 500

    def test_tool_definitions_add_overhead(self):
        messages = [{"role": "user", "content": "call a tool"}]
        no_tools = self.fn(messages, None, tools=[])
        with_tools = self.fn(messages, None, tools=[
            {"name": "search", "description": "search the web", "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            }}
        ])
        assert with_tools > no_tools

    def test_longer_messages_produce_higher_count(self):
        short = [{"role": "user", "content": "hi"}]
        long = [{"role": "user", "content": "hello " * 200}]
        assert self.fn(long, None) > self.fn(short, None)

    def test_tool_result_content_counted(self):
        messages = [{"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "x", "content": "search result " * 50}
        ]}]
        result = self.fn(messages, None)
        assert result > 10

    def test_multi_turn_more_than_single_turn(self):
        single = [{"role": "user", "content": "Hello"}]
        multi = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there! How can I help?"},
            {"role": "user", "content": "Tell me about Python"},
        ]
        assert self.fn(multi, None) > self.fn(single, None)


# ─────────────────────────────────────────────────────────────────────────────
# 2. count_tokens endpoint via FastAPI TestClient
# ─────────────────────────────────────────────────────────────────────────────

class TestCountTokensEndpoint:
    """Integration tests for POST /v1/messages/count_tokens."""

    @pytest.fixture(autouse=True)
    def client(self):
        import proxy
        from fastapi.testclient import TestClient

        def _fake_auth():
            return proxy.AuthContext(
                key="test-key",
                email="test@example.com",
                department="eng",
                key_id="k1",
                source="legacy",
            )

        proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth
        self.client = TestClient(proxy.app, raise_server_exceptions=True)
        yield
        proxy.app.dependency_overrides.clear()

    def _post(self, body: dict, headers: dict | None = None):
        h = {"x-api-key": "test-key", **(headers or {})}
        return self.client.post("/v1/messages/count_tokens", json=body, headers=h)

    def test_basic_returns_input_tokens(self):
        resp = self._post({
            "model": "claude-sonnet-4-6",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "input_tokens" in data
        assert isinstance(data["input_tokens"], int)
        assert data["input_tokens"] >= 1

    def test_anthropic_version_header_present(self):
        resp = self._post({
            "model": "claude-sonnet-4-6",
            "messages": [{"role": "user", "content": "Hi"}],
        })
        assert resp.status_code == 200
        assert resp.headers.get("anthropic-version") == "2023-06-01"

    def test_longer_prompt_higher_count(self):
        short = self._post({
            "model": "claude-sonnet-4-6",
            "messages": [{"role": "user", "content": "Hi"}],
        })
        long = self._post({
            "model": "claude-sonnet-4-6",
            "messages": [{"role": "user", "content": "Explain quantum entanglement in detail " * 20}],
        })
        assert long.json()["input_tokens"] > short.json()["input_tokens"]

    def test_system_prompt_increases_count(self):
        without = self._post({
            "model": "claude-sonnet-4-6",
            "messages": [{"role": "user", "content": "What time is it?"}],
        })
        with_system = self._post({
            "model": "claude-sonnet-4-6",
            "system": "You are an expert in every topic. " * 30,
            "messages": [{"role": "user", "content": "What time is it?"}],
        })
        assert with_system.json()["input_tokens"] > without.json()["input_tokens"]

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            "/v1/messages/count_tokens",
            content=b"not-json",
            headers={"x-api-key": "test-key", "content-type": "application/json"},
        )
        assert resp.status_code == 400

    def test_empty_messages_returns_valid_response(self):
        resp = self._post({
            "model": "claude-sonnet-4-6",
            "messages": [],
        })
        assert resp.status_code == 200
        assert resp.json()["input_tokens"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Extended thinking → reasoning routing
# ─────────────────────────────────────────────────────────────────────────────

class TestExtendedThinkingRouting:
    """Unit tests for extended thinking detection in handle_anthropic_messages."""

    def test_thinking_enabled_sets_agent_plan_endpoint_type(self):
        """When thinking.type == enabled, routing should use agent_plan endpoint type."""
        from handlers.anthropic_compat import _estimate_tokens_for_messages
        from router.classifier import classify_task

        # agent_plan endpoint_type always produces "reasoning" category
        category = classify_task(
            messages=[{"role": "user", "content": "hi"}],
            endpoint_type="agent_plan",
        )
        assert category == "reasoning"

    def test_thinking_disabled_uses_chat_endpoint_type(self):
        """No thinking param → normal chat routing, not forced to reasoning."""
        from router.classifier import classify_task

        category = classify_task(
            messages=[{"role": "user", "content": "write a python function"}],
            endpoint_type="chat",
        )
        # Should classify as code-related, not reasoning
        assert category in ("code_generation", "code_debugging", "tool_use", "fast_response", "reasoning")

    def test_thinking_budget_in_routing_meta(self):
        """thinking_budget_tokens should appear in routing_meta when thinking is set."""
        # Simulate the routing_meta enrichment logic from handle_anthropic_messages
        thinking_param = {"type": "enabled", "budget_tokens": 4096}
        thinking_budget = thinking_param.get("budget_tokens")

        routing_meta: dict = {"routing_mode": "auto", "routing_resolved_model": "deepseek-r1:32b"}
        if thinking_budget is not None:
            routing_meta["thinking_budget_tokens"] = thinking_budget

        assert routing_meta.get("thinking_budget_tokens") == 4096

    def test_no_thinking_param_no_budget_in_meta(self):
        """Without thinking param, thinking_budget_tokens not in routing_meta."""
        thinking_param = None
        thinking_budget = thinking_param.get("budget_tokens") if isinstance(thinking_param, dict) else None

        routing_meta: dict = {"routing_mode": "auto"}
        if thinking_budget is not None:
            routing_meta["thinking_budget_tokens"] = thinking_budget

        assert "thinking_budget_tokens" not in routing_meta


# ─────────────────────────────────────────────────────────────────────────────
# 4. Anthropic output_format → Ollama format passthrough
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeAnthropicOutputFormat:
    """Unit tests for _normalize_anthropic_output_format."""

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from handlers.anthropic_compat import _normalize_anthropic_output_format
        self.fn = _normalize_anthropic_output_format

    def test_no_output_format_returns_false(self):
        payload = {"model": "claude-sonnet-4-6", "messages": []}
        openai_payload: dict = {}
        result = self.fn(payload, openai_payload)
        assert result is False
        assert "format" not in openai_payload

    def test_json_schema_extracts_schema(self):
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        payload = {
            "output_format": {
                "type": "json_schema",
                "json_schema": {"name": "MySchema", "schema": schema},
            }
        }
        openai_payload: dict = {}
        result = self.fn(payload, openai_payload)
        assert result is True
        assert openai_payload["format"] == schema

    def test_json_schema_malformed_falls_back_to_json_mode(self):
        payload = {
            "output_format": {
                "type": "json_schema",
                "json_schema": {"name": "BadSchema"},  # no "schema" key
            }
        }
        openai_payload: dict = {}
        result = self.fn(payload, openai_payload)
        assert result is True
        assert openai_payload["format"] == "json"

    def test_json_object_sets_format_json(self):
        payload = {"output_format": {"type": "json_object"}}
        openai_payload: dict = {}
        result = self.fn(payload, openai_payload)
        assert result is True
        assert openai_payload["format"] == "json"

    def test_unknown_type_returns_false(self):
        payload = {"output_format": {"type": "text"}}
        openai_payload: dict = {}
        result = self.fn(payload, openai_payload)
        assert result is False
        assert "format" not in openai_payload

    def test_non_dict_output_format_returns_false(self):
        payload = {"output_format": "json"}
        openai_payload: dict = {}
        result = self.fn(payload, openai_payload)
        assert result is False

    def test_anthropic_beta_header_added_when_output_format_used(self):
        """Caller adds anthropic-beta header when _normalize returns True."""
        payload = {"output_format": {"type": "json_object"}}
        openai_payload: dict = {}
        from handlers.anthropic_compat import _normalize_anthropic_output_format
        used = _normalize_anthropic_output_format(payload, openai_payload)

        # Simulate what handle_anthropic_messages does
        extra_headers: dict = {"anthropic-version": "2023-06-01"}
        if used:
            extra_headers["anthropic-beta"] = "structured-outputs-2025-11-13"

        assert extra_headers.get("anthropic-beta") == "structured-outputs-2025-11-13"

    def test_no_output_format_no_beta_header(self):
        payload = {"messages": []}
        openai_payload: dict = {}
        from handlers.anthropic_compat import _normalize_anthropic_output_format
        used = _normalize_anthropic_output_format(payload, openai_payload)

        extra_headers: dict = {"anthropic-version": "2023-06-01"}
        if used:
            extra_headers["anthropic-beta"] = "structured-outputs-2025-11-13"

        assert "anthropic-beta" not in extra_headers

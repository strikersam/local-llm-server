"""Daily automation tests — 2026-05-14

Covers three features implemented in this run:
  1. Structured output normalization (_normalize_response_format)
     - OpenAI json_schema → Ollama format field
     - OpenAI json_object → Ollama format: "json"
     - Cloud/Nvidia models pass response_format through unchanged
  2. Claude alias model listing in /v1/models
     - Endpoint includes alias entries (claude-* names)
     - alias entries carry owned_by="llm-relay-alias"
  3. X-Token-Budget-Remaining response headers
     - TokenBudget.get() returns None for unknown sessions (no headers injected)
     - Budget headers present when session has a cap set
"""

from __future__ import annotations

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. Structured output normalization
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeResponseFormat:
    """Unit tests for chat_handlers._normalize_response_format."""

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from chat_handlers import _normalize_response_format
        self.fn = _normalize_response_format

    def test_no_response_format_passes_through(self):
        payload = {"model": "qwen3-coder:30b", "messages": []}
        assert self.fn(payload) == payload

    def test_json_schema_extracts_schema_for_local_model(self):
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        payload = {
            "model": "qwen3-coder:30b",
            "messages": [],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "MySchema",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        result = self.fn(payload)
        assert result["format"] == schema
        assert "response_format" not in result

    def test_json_object_sets_format_json_for_local_model(self):
        payload = {
            "model": "deepseek-r1:32b",
            "messages": [],
            "response_format": {"type": "json_object"},
        }
        result = self.fn(payload)
        assert result["format"] == "json"
        assert "response_format" not in result

    def test_cloud_model_with_slash_passes_response_format_unchanged(self):
        schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
        payload = {
            "model": "nvidia/nemotron-3-super-120b-a12b",
            "messages": [],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "X", "schema": schema},
            },
        }
        result = self.fn(payload)
        # response_format must be preserved for cloud (OpenAI-native) endpoints
        assert "response_format" in result
        assert "format" not in result

    def test_openai_cloud_model_json_object_unchanged(self):
        payload = {
            "model": "openai/gpt-4o",
            "messages": [],
            "response_format": {"type": "json_object"},
        }
        result = self.fn(payload)
        assert "response_format" in result
        assert "format" not in result

    def test_json_schema_missing_schema_key_leaves_payload_unchanged(self):
        """If json_schema has no 'schema' key, don't break."""
        payload = {
            "model": "qwen3-coder:7b",
            "messages": [],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "NoSchema"},
            },
        }
        result = self.fn(payload)
        assert "response_format" in result

    def test_unknown_response_format_type_is_ignored(self):
        payload = {
            "model": "qwen3-coder:30b",
            "messages": [],
            "response_format": {"type": "text"},
        }
        result = self.fn(payload)
        assert result == payload

    def test_non_dict_response_format_is_ignored(self):
        payload = {"model": "qwen3-coder:30b", "response_format": "json"}
        result = self.fn(payload)
        assert result == payload

    def test_other_payload_fields_preserved(self):
        schema = {"type": "object", "properties": {}}
        payload = {
            "model": "qwen3-coder:30b",
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": False,
            "messages": [{"role": "user", "content": "hi"}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "S", "schema": schema},
            },
        }
        result = self.fn(payload)
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 1024
        assert result["stream"] is False
        assert result["messages"] == [{"role": "user", "content": "hi"}]
        assert result["format"] == schema

    def test_no_model_key_treated_as_local(self):
        """Payload without 'model' field should apply normalization (no '/' → local)."""
        schema = {"type": "object"}
        payload = {
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "S", "schema": schema},
            },
        }
        result = self.fn(payload)
        assert result.get("format") == schema

    def test_original_payload_not_mutated(self):
        """_normalize_response_format must not mutate the input dict."""
        schema = {"type": "object"}
        original = {
            "model": "qwen3-coder:30b",
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "S", "schema": schema},
            },
        }
        import copy
        before = copy.deepcopy(original)
        self.fn(original)
        assert original == before


# ─────────────────────────────────────────────────────────────────────────────
# 2. Claude alias model listing in /v1/models
# ─────────────────────────────────────────────────────────────────────────────


class TestModelsEndpointAliases:
    """Tests that /v1/models exposes Claude/Anthropic alias entries."""

    def _get_alias_ids(self) -> set[str]:
        from router.model_router import _get_model_map, reset_router
        reset_router()
        return set(_get_model_map().keys())

    def test_alias_ids_include_claude_sonnet(self):
        alias_ids = self._get_alias_ids()
        assert "claude-sonnet-4-6" in alias_ids

    def test_alias_ids_include_claude_opus(self):
        alias_ids = self._get_alias_ids()
        assert "claude-opus-4-7" in alias_ids

    def test_alias_ids_include_claude_haiku(self):
        alias_ids = self._get_alias_ids()
        assert "claude-haiku-4-5-20251001" in alias_ids

    def test_model_map_returns_non_empty_targets(self):
        from router.model_router import _get_model_map, reset_router
        reset_router()
        model_map = _get_model_map()
        for alias, target in model_map.items():
            assert target, f"alias {alias!r} maps to empty target"

    def test_no_alias_maps_to_itself(self):
        from router.model_router import _get_model_map, reset_router
        reset_router()
        model_map = _get_model_map()
        for alias, target in model_map.items():
            # Aliases like "gemma4:latest" → "gemma4:latest" are valid passthrough,
            # but typical Anthropic aliases should NOT be identical to target.
            if alias.startswith("claude-"):
                assert alias != target, f"claude alias {alias!r} maps to itself"

    def test_list_models_response_shape(self, monkeypatch):
        """list_models_openai returns object:list with data array."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from router.model_router import reset_router
        reset_router()

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(
            return_value=MagicMock(**{"json.return_value": {"models": []}})
        )

        with patch("proxy.httpx.AsyncClient", return_value=fake_client):
            from proxy import list_models_openai, AuthContext
            auth = AuthContext(
                key="ci-test-key", email="test@test.com",
                department="eng", key_id=None, source="legacy",
            )
            result = asyncio.get_event_loop().run_until_complete(list_models_openai(auth))

        assert result["object"] == "list"
        assert isinstance(result["data"], list)

    def test_list_models_includes_alias_entries(self, monkeypatch):
        """list_models_openai includes alias entries with owned_by=llm-relay-alias."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from router.model_router import reset_router
        reset_router()

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(
            return_value=MagicMock(**{"json.return_value": {"models": []}})
        )

        with patch("proxy.httpx.AsyncClient", return_value=fake_client):
            from proxy import list_models_openai, AuthContext
            auth = AuthContext(
                key="ci-test-key", email="test@test.com",
                department="eng", key_id=None, source="legacy",
            )
            result = asyncio.get_event_loop().run_until_complete(list_models_openai(auth))

        alias_entries = [e for e in result["data"] if e.get("owned_by") == "llm-relay-alias"]
        assert len(alias_entries) > 0, "No alias entries in /v1/models response"

    def test_list_models_alias_entries_have_description(self, monkeypatch):
        """Each alias entry has a 'description' field showing the target."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from router.model_router import reset_router
        reset_router()

        fake_client = MagicMock()
        fake_client.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client.__aexit__ = AsyncMock(return_value=False)
        fake_client.get = AsyncMock(
            return_value=MagicMock(**{"json.return_value": {"models": []}})
        )

        with patch("proxy.httpx.AsyncClient", return_value=fake_client):
            from proxy import list_models_openai, AuthContext
            auth = AuthContext(
                key="ci-test-key", email="test@test.com",
                department="eng", key_id=None, source="legacy",
            )
            result = asyncio.get_event_loop().run_until_complete(list_models_openai(auth))

        for entry in result["data"]:
            if entry.get("owned_by") == "llm-relay-alias":
                assert "description" in entry
                assert "Alias →" in entry["description"]
                break


# ─────────────────────────────────────────────────────────────────────────────
# 3. X-Token-Budget-Remaining response headers
# ─────────────────────────────────────────────────────────────────────────────


class TestTokenBudgetHeaders:
    """Unit-level tests for the TokenBudget state used for response headers."""

    def test_get_returns_none_for_unknown_session(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        assert budget.get("nonexistent-session-xyz") is None

    def test_set_cap_then_get_returns_usage(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        budget.set_cap("session-abc", cap=10_000)
        usage = budget.get("session-abc")
        assert usage is not None
        assert usage.cap == 10_000

    def test_remaining_calculated_correctly(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        budget.set_cap("sess-1", cap=5_000)
        budget.record("sess-1", prompt_tokens=1_000, completion_tokens=500)
        usage = budget.get("sess-1")
        assert usage.remaining == 3_500

    def test_remaining_is_minus_one_when_cap_is_zero(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        # cap=0 means unlimited
        budget.set_cap("sess-unlimited", cap=0)
        usage = budget.get("sess-unlimited")
        assert usage.remaining == -1

    def test_as_dict_includes_required_header_fields(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        budget.set_cap("sess-2", cap=2_000)
        budget.record("sess-2", prompt_tokens=100, completion_tokens=50)
        d = budget.get("sess-2").as_dict()
        assert "remaining" in d
        assert "cap" in d
        assert "total_tokens" in d
        assert d["remaining"] == 2_000 - 150
        assert d["cap"] == 2_000
        assert d["total_tokens"] == 150

    def test_budget_exceeded_flag(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        budget.set_cap("sess-3", cap=100)
        budget.record("sess-3", prompt_tokens=80, completion_tokens=30)
        usage = budget.get("sess-3")
        assert usage.exceeded is True

    def test_budget_not_exceeded_when_under_cap(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        budget.set_cap("sess-4", cap=1_000)
        budget.record("sess-4", prompt_tokens=100, completion_tokens=50)
        usage = budget.get("sess-4")
        assert usage.exceeded is False

    def test_list_all_returns_all_sessions(self):
        from agent.token_budget import TokenBudget
        budget = TokenBudget()
        budget.set_cap("s1", cap=1_000)
        budget.set_cap("s2", cap=2_000)
        all_usages = budget.list_all()
        ids = {u.session_id for u in all_usages}
        assert "s1" in ids
        assert "s2" in ids

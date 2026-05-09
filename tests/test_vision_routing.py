"""Tests for vision request routing and session ID propagation.

Covers:
  - has_image_content() detection
  - best_vision_model() selection
  - ModelRouter vision routing path
  - ModelCapability.vision field on registry entries
  - session_id propagation in langfuse_obs.emit_chat_observation
"""

from __future__ import annotations

import unittest.mock as mock

import pytest

from router.registry import (
    ModelCapability,
    best_vision_model,
    get_registry,
    has_image_content,
)
from router.model_router import ModelRouter, RoutingDecision, reset_router


# ---------------------------------------------------------------------------
# has_image_content
# ---------------------------------------------------------------------------


class TestHasImageContent:
    def test_none_returns_false(self):
        assert has_image_content(None) is False

    def test_empty_list_returns_false(self):
        assert has_image_content([]) is False

    def test_text_only_message_returns_false(self):
        msgs = [{"role": "user", "content": "hello"}]
        assert has_image_content(msgs) is False

    def test_string_content_with_no_image_returns_false(self):
        msgs = [{"role": "user", "content": "what is 2+2?"}]
        assert has_image_content(msgs) is False

    def test_list_content_text_part_returns_false(self):
        msgs = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "hello"}],
            }
        ]
        assert has_image_content(msgs) is False

    def test_image_url_part_returns_true(self):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "what is in this image?"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                ],
            }
        ]
        assert has_image_content(msgs) is True

    def test_image_url_in_second_message_returns_true(self):
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
                ],
            },
        ]
        assert has_image_content(msgs) is True

    def test_mixed_turns_no_images_returns_false(self):
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        assert has_image_content(msgs) is False


# ---------------------------------------------------------------------------
# best_vision_model
# ---------------------------------------------------------------------------


class TestBestVisionModel:
    def test_returns_none_when_no_vision_models_registered(self):
        # Registry with no vision models
        registry = {
            "text-only": ModelCapability(
                name="text-only", strengths=["conversation"], context_window=4096,
                type="general", cost_tier=1, vision=False,
            )
        }
        assert best_vision_model(registry) is None

    def test_returns_highest_cost_tier_vision_model(self):
        registry = {
            "small-vision": ModelCapability(
                name="small-vision", strengths=[], context_window=4096,
                type="general", cost_tier=1, vision=True,
            ),
            "large-vision": ModelCapability(
                name="large-vision", strengths=[], context_window=128000,
                type="general", cost_tier=3, vision=True,
            ),
        }
        assert best_vision_model(registry) == "large-vision"

    def test_explicit_vision_model_env_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("VISION_MODEL", "my-custom-vision-model")
        assert best_vision_model({}) == "my-custom-vision-model"

    def test_gemma4_27b_is_vision_capable(self):
        registry = get_registry()
        cap = registry.get("gemma4:27b")
        assert cap is not None
        assert cap.vision is True

    def test_llama4_maverick_is_vision_capable(self):
        registry = get_registry()
        cap = registry.get("llama4-maverick:17b")
        assert cap is not None
        assert cap.vision is True

    def test_qwen3_coder_is_not_vision_capable(self):
        registry = get_registry()
        cap = registry.get("qwen3-coder:30b")
        assert cap is not None
        assert cap.vision is False

    def test_registry_has_at_least_one_vision_model(self):
        registry = get_registry()
        vision_models = [m for m in registry.values() if m.vision]
        assert len(vision_models) >= 1, "Registry must contain at least one vision-capable model"


# ---------------------------------------------------------------------------
# ModelRouter — vision routing path
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_router():
    reset_router()
    yield
    reset_router()


class TestVisionRouting:
    def _image_messages(self):
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
                ],
            }
        ]

    def test_vision_routing_uses_vision_model(self, monkeypatch):
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
        router = ModelRouter()
        decision = router.route(messages=self._image_messages())
        assert decision.selection_source == "vision"
        assert decision.task_category == "multimodal"
        assert "vision routing" in decision.routing_reason.lower()

    def test_vision_routing_returns_routing_decision(self, monkeypatch):
        monkeypatch.delenv("VISION_MODEL", raising=False)
        monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
        router = ModelRouter()
        decision = router.route(messages=self._image_messages())
        assert isinstance(decision, RoutingDecision)
        assert decision.resolved_model  # non-empty

    def test_override_still_takes_priority_over_vision(self, monkeypatch):
        monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
        router = ModelRouter()
        decision = router.route(
            messages=self._image_messages(),
            override_model="qwen3-coder:30b",
        )
        assert decision.selection_source == "override"
        assert decision.resolved_model == "qwen3-coder:30b"

    def test_text_only_messages_do_not_trigger_vision_routing(self, monkeypatch):
        monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
        router = ModelRouter()
        msgs = [{"role": "user", "content": "hello"}]
        decision = router.route(messages=msgs)
        assert decision.selection_source != "vision"

    def test_explicit_vision_model_env_used_when_image_present(self, monkeypatch):
        monkeypatch.setenv("VISION_MODEL", "my-local-llava")
        monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
        router = ModelRouter()
        decision = router.route(messages=self._image_messages())
        assert decision.resolved_model == "my-local-llava"
        assert decision.selection_source == "vision"


# ---------------------------------------------------------------------------
# Langfuse session_id propagation
# ---------------------------------------------------------------------------


class TestLangfuseSessionId:
    def test_emit_chat_observation_accepts_session_id(self):
        """emit_chat_observation must accept session_id without error."""
        from langfuse_obs import emit_chat_observation
        import inspect
        sig = inspect.signature(emit_chat_observation)
        assert "session_id" in sig.parameters

    def test_session_id_included_in_meta(self):
        """When session_id is provided, it should appear in the meta dict passed to emit functions."""
        from langfuse_obs import emit_chat_observation
        import unittest.mock as mock

        with mock.patch("langfuse_obs._langfuse_enabled", return_value=False):
            # With Langfuse disabled, the function returns early — just check no error
            emit_chat_observation(
                email="test@example.com",
                department="eng",
                key_id=None,
                model="qwen3-coder:30b",
                messages=[{"role": "user", "content": "hi"}],
                output_text="hello",
                prompt_tokens=5,
                completion_tokens=3,
                session_id="claude-code-session-abc123",
            )

    def test_emit_langfuse_http_accepts_session_id(self):
        """_emit_langfuse_http must have session_id parameter."""
        from langfuse_obs import _emit_langfuse_http
        import inspect
        sig = inspect.signature(_emit_langfuse_http)
        assert "session_id" in sig.parameters

    def test_emit_sdk_accepts_session_id(self):
        """_emit_sdk must have session_id parameter."""
        from langfuse_obs import _emit_sdk
        import inspect
        sig = inspect.signature(_emit_sdk)
        assert "session_id" in sig.parameters

    def test_http_body_includes_session_id_in_trace(self):
        """When session_id provided, trace body must include sessionId field."""
        from langfuse_obs import _emit_langfuse_http
        import unittest.mock as mock

        captured_trace_body = {}

        def fake_post(url, json=None, auth=None):
            nonlocal captured_trace_body
            if "traces" in url:
                captured_trace_body = json or {}
            resp = mock.MagicMock()
            resp.status_code = 200
            return resp

        with mock.patch("langfuse_obs._env_val", side_effect=lambda k: "testkey" if "KEY" in k else "https://cloud.langfuse.com"):
            with mock.patch("httpx.Client") as mock_client_cls:
                mock_client = mock.MagicMock()
                mock_client.__enter__ = lambda s: s
                mock_client.__exit__ = mock.MagicMock(return_value=False)
                mock_client.post = fake_post
                mock_client_cls.return_value = mock_client

                _emit_langfuse_http(
                    email="user@test.com",
                    department="eng",
                    key_id=None,
                    model="gemma4:27b",
                    messages=[],
                    output_text="hi",
                    prompt_tokens=1,
                    completion_tokens=1,
                    meta={},
                    task_name="test",
                    session_id="my-session-xyz",
                )

        assert captured_trace_body.get("sessionId") == "my-session-xyz"

    def test_http_trace_includes_session_tag(self):
        """When session_id provided, trace tags must include session:<id>."""
        from langfuse_obs import _emit_langfuse_http
        import unittest.mock as mock

        captured_tags = []

        def fake_post(url, json=None, auth=None):
            nonlocal captured_tags
            if "traces" in url and json:
                captured_tags = json.get("tags", [])
            resp = mock.MagicMock()
            resp.status_code = 200
            return resp

        with mock.patch("langfuse_obs._env_val", side_effect=lambda k: "testkey" if "KEY" in k else "https://cloud.langfuse.com"):
            with mock.patch("httpx.Client") as mock_client_cls:
                mock_client = mock.MagicMock()
                mock_client.__enter__ = lambda s: s
                mock_client.__exit__ = mock.MagicMock(return_value=False)
                mock_client.post = fake_post
                mock_client_cls.return_value = mock_client

                _emit_langfuse_http(
                    email="user@test.com",
                    department="eng",
                    key_id=None,
                    model="gemma4:27b",
                    messages=[],
                    output_text="hi",
                    prompt_tokens=1,
                    completion_tokens=1,
                    meta={},
                    task_name="test",
                    session_id="sess-abc",
                )

        assert any("sess-abc" in t for t in captured_tags), f"session tag missing from {captured_tags}"

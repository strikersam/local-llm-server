"""Tests for AWS Bedrock provider support in ProviderRouter."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from provider_router import ProviderConfig, ProviderRouter, _is_bedrock_model_id


@contextmanager
def _mock_boto3(mock_client: MagicMock):
    """Inject a mock boto3 module into sys.modules for the duration of the block."""
    mock_boto3_mod = MagicMock()
    mock_boto3_mod.client.return_value = mock_client
    original = sys.modules.get("boto3")
    sys.modules["boto3"] = mock_boto3_mod  # type: ignore[assignment]
    try:
        yield mock_boto3_mod
    finally:
        if original is not None:
            sys.modules["boto3"] = original
        else:
            sys.modules.pop("boto3", None)


def _bedrock_provider(model: str = "us.anthropic.claude-opus-4-7") -> ProviderConfig:
    return ProviderConfig(
        provider_id="bedrock",
        type="bedrock",
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        api_key="AKIATEST1234567890AB",
        default_model=model,
        priority=15,
        headers={
            "X-Bedrock-Secret": "test_secret_key/test+test",
            "X-Bedrock-Region": "us-east-1",
        },
    )


def _bedrock_api_response(text: str = "Hello there!") -> dict[str, Any]:
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        "stopReason": "end_turn",
    }


# ── _openai_to_bedrock_converse ───────────────────────────────────────────────

class TestOpenAiToBedrockConverse:
    def test_simple_user_message(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Hello!"}],
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert result["messages"] == [{"role": "user", "content": [{"text": "Hello!"}]}]
        assert result["system"] == []

    def test_system_message_extraction(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"},
            ],
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert result["system"] == [{"text": "You are helpful."}]
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"

    def test_multi_turn_conversation(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
                {"role": "user", "content": "How are you?"},
            ],
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert len(result["messages"]) == 3
        assert result["messages"][1]["role"] == "assistant"

    def test_inference_config_max_tokens(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 2048,
            "temperature": 0.5,
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert result["inferenceConfig"]["maxTokens"] == 2048
        assert result["inferenceConfig"]["temperature"] == 0.5

    def test_empty_messages_uses_default(self):
        payload = {"model": "us.anthropic.claude-opus-4-7", "messages": []}
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"

    def test_no_inference_config_when_absent(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Hi"}],
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert result["inferenceConfig"] == {}

    def test_list_content_parts(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Hello from parts"}],
                }
            ],
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert result["messages"][0]["content"][0]["text"] == "Hello from parts"

    def test_skips_messages_with_no_text(self):
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [
                {"role": "user", "content": ""},
                {"role": "user", "content": "Real message"},
            ],
        }
        result = ProviderRouter._openai_to_bedrock_converse(payload)
        assert len(result["messages"]) == 1


# ── _bedrock_response_to_openai ───────────────────────────────────────────────

class TestBedrockResponseToOpenai:
    def test_basic_response(self):
        data = _bedrock_api_response("Hello there!")
        response = ProviderRouter._bedrock_response_to_openai(data, "us.anthropic.claude-opus-4-7")
        assert response.status_code == 200
        body = response.json()
        assert body["choices"][0]["message"]["content"] == "Hello there!"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["model"] == "us.anthropic.claude-opus-4-7"
        assert body["usage"]["prompt_tokens"] == 10
        assert body["usage"]["completion_tokens"] == 5
        assert body["usage"]["total_tokens"] == 15

    def test_multiple_content_blocks(self):
        data = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Part 1"}, {"text": "Part 2"}],
                }
            },
            "usage": {},
        }
        response = ProviderRouter._bedrock_response_to_openai(data, "test-model")
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        assert "Part 1" in content
        assert "Part 2" in content

    def test_empty_output(self):
        data: dict[str, Any] = {"output": {}, "usage": {}}
        response = ProviderRouter._bedrock_response_to_openai(data, "test-model")
        assert response.status_code == 200
        body = response.json()
        assert body["choices"][0]["message"]["content"] == ""
        assert body["usage"]["prompt_tokens"] == 0

    def test_missing_usage(self):
        data = _bedrock_api_response()
        del data["usage"]
        response = ProviderRouter._bedrock_response_to_openai(data, "test-model")
        body = response.json()
        assert body["usage"]["total_tokens"] == 0

    def test_content_type_header(self):
        data = _bedrock_api_response()
        response = ProviderRouter._bedrock_response_to_openai(data, "model")
        assert "application/json" in response.headers.get("content-type", "")


# ── from_env() Bedrock discovery ──────────────────────────────────────────────

class TestFromEnvBedrock:
    def test_bedrock_added_when_both_keys_present(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST1234567890AB")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        bedrock = [p for p in router.providers if p.provider_id == "bedrock"]
        assert len(bedrock) == 1
        assert bedrock[0].type == "bedrock"
        assert bedrock[0].priority == 15

    def test_bedrock_not_added_when_access_key_missing(self, monkeypatch):
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("BEDROCK_ACCESS_KEY", raising=False)
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        assert not any(p.provider_id == "bedrock" for p in router.providers)

    def test_bedrock_not_added_when_secret_missing(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST1234567890AB")
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("BEDROCK_SECRET_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        assert not any(p.provider_id == "bedrock" for p in router.providers)

    def test_bedrock_uses_custom_model(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST1234567890AB")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        bedrock = next(p for p in router.providers if p.provider_id == "bedrock")
        assert bedrock.default_model == "us.anthropic.claude-sonnet-4-6"

    def test_bedrock_alternate_env_vars(self, monkeypatch):
        monkeypatch.setenv("BEDROCK_ACCESS_KEY", "AKIATEST1234567890AB")
        monkeypatch.setenv("BEDROCK_SECRET_KEY", "test_secret")
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        assert any(p.provider_id == "bedrock" for p in router.providers)

    def test_bedrock_custom_region(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST1234567890AB")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        bedrock = next(p for p in router.providers if p.provider_id == "bedrock")
        assert "eu-west-1" in bedrock.base_url
        assert bedrock.headers["X-Bedrock-Region"] == "eu-west-1"

    def test_bedrock_default_model(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST1234567890AB")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
        router = ProviderRouter.from_env()
        bedrock = next(p for p in router.providers if p.provider_id == "bedrock")
        assert bedrock.default_model == "us.anthropic.claude-opus-4-6-v1"


# ── health_check for bedrock ──────────────────────────────────────────────────

class TestBedrockHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_when_both_keys_present(self):
        provider = _bedrock_provider()
        router = ProviderRouter([provider])
        assert await router.health_check(provider) is True

    @pytest.mark.asyncio
    async def test_unhealthy_when_secret_missing(self):
        provider = ProviderConfig(
            provider_id="bedrock",
            type="bedrock",
            base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
            api_key="AKIATEST",
            default_model="us.anthropic.claude-opus-4-7",
            priority=15,
            headers={},  # no X-Bedrock-Secret
        )
        router = ProviderRouter([provider])
        assert await router.health_check(provider) is False


# ── _is_bedrock_model_id ──────────────────────────────────────────────────────

class TestIsBedrockModelId:
    def test_us_inference_profile(self) -> None:
        assert _is_bedrock_model_id("us.anthropic.claude-opus-4-6-v1") is True

    def test_us_opus_4_7(self) -> None:
        assert _is_bedrock_model_id("us.anthropic.claude-opus-4-7") is True

    def test_eu_inference_profile(self) -> None:
        assert _is_bedrock_model_id("eu.anthropic.claude-sonnet-4-6") is True

    def test_global_inference_profile(self) -> None:
        assert _is_bedrock_model_id("global.anthropic.claude-opus-4-7") is True

    def test_arn_format(self) -> None:
        assert _is_bedrock_model_id(
            "arn:aws:bedrock:us-east-1:123456789:inference-profile/us.anthropic.claude-opus-4-7"
        ) is True

    def test_direct_bedrock_model_id(self) -> None:
        assert _is_bedrock_model_id("anthropic.claude-opus-4-7") is True

    def test_nim_model_not_bedrock(self) -> None:
        assert _is_bedrock_model_id("nvidia/nemotron-3-super-120b-a12b") is False

    def test_deepseek_not_bedrock(self) -> None:
        assert _is_bedrock_model_id("deepseek-ai/deepseek-v4-pro") is False

    def test_plain_claude_not_bedrock(self) -> None:
        # Direct Anthropic API model IDs don't have the Bedrock prefix
        assert _is_bedrock_model_id("claude-sonnet-4-6") is False

    def test_empty_string(self) -> None:
        assert _is_bedrock_model_id("") is False


# ── Bedrock routing affinity in chat_completion ───────────────────────────────

@pytest.mark.asyncio
class TestBedrockRoutingAffinity:
    """Verify that Bedrock model IDs bypass non-Bedrock providers."""

    def _nim_provider(self) -> ProviderConfig:
        return ProviderConfig(
            provider_id="nvidia-nim",
            type="nvidia-nim",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="nvapi-test",
            default_model="nvidia/nemotron-3-super-120b-a12b",
            priority=5,
        )

    async def test_bedrock_model_skips_nim(self) -> None:
        """When model is a Bedrock ID, NIM should not be attempted."""
        nim = self._nim_provider()
        bedrock = _bedrock_provider()
        mock_client = MagicMock()
        mock_client.converse.return_value = _bedrock_api_response("hello")

        with _mock_boto3(mock_client):
            router = ProviderRouter([nim, bedrock])
            payload = {
                "model": "us.anthropic.claude-opus-4-6-v1",
                "messages": [{"role": "user", "content": "hi"}],
            }
            result = await router.chat_completion(payload)

        # Only Bedrock should have been attempted — NIM never called
        provider_ids = [a.provider_id for a in result.attempts]
        assert "bedrock" in provider_ids
        assert "nvidia-nim" not in provider_ids

    async def test_bedrock_model_is_primary_for_bedrock_provider(self) -> None:
        """When NIM is skipped, Bedrock becomes the primary provider and uses the original model."""
        nim = self._nim_provider()
        bedrock = _bedrock_provider("us.anthropic.claude-opus-4-6-v1")
        mock_client = MagicMock()
        mock_client.converse.return_value = _bedrock_api_response("ok")

        with _mock_boto3(mock_client):
            router = ProviderRouter([nim, bedrock])
            payload = {
                "model": "us.anthropic.claude-opus-4-6-v1",
                "messages": [{"role": "user", "content": "hi"}],
            }
            result = await router.chat_completion(payload)

        assert result.model == "us.anthropic.claude-opus-4-6-v1"
        # Verify boto3 was called with the correct model ID
        call_kwargs = mock_client.converse.call_args.kwargs
        assert call_kwargs["modelId"] == "us.anthropic.claude-opus-4-6-v1"

    async def test_bedrock_affinity_preserved_in_cooldown_bypass(self) -> None:
        """Bedrock affinity must hold even in the last-resort cooldown-bypass path."""
        from unittest.mock import AsyncMock, patch as mock_patch
        import provider_router as pr_mod

        nim = self._nim_provider()
        bedrock = _bedrock_provider("us.anthropic.claude-opus-4-6-v1")
        mock_client = MagicMock()
        mock_client.converse.return_value = _bedrock_api_response("bypass-ok")

        with _mock_boto3(mock_client):
            router = ProviderRouter([nim, bedrock])
            payload = {
                "model": "us.anthropic.claude-opus-4-6-v1",
                "messages": [{"role": "user", "content": "hi"}],
            }
            # Simulate all providers on cooldown so bypass path is triggered
            with mock_patch.object(pr_mod, "is_provider_on_cooldown", return_value=True):
                with mock_patch.object(pr_mod, "mark_provider_failed"):
                    # Bypass sees skipped_on_cooldown = [nim, bedrock].
                    # NIM must still be skipped because the model is a Bedrock ID.
                    result = await router.chat_completion(payload)

        provider_ids = [a.provider_id for a in result.attempts]
        assert "bedrock" in provider_ids, "Bedrock not attempted in bypass path"
        assert "nvidia-nim" not in provider_ids, "NIM was incorrectly tried in bypass path"

    async def test_non_bedrock_model_still_tries_nim_first(self) -> None:
        """Non-Bedrock model IDs still route to NIM first (existing behaviour)."""
        import httpx

        nim = self._nim_provider()
        bedrock = _bedrock_provider()
        nim_called = []

        original_post_chat = ProviderRouter._post_chat

        async def mock_post_chat(self, provider, payload, timeout_sec=300.0):
            if provider.provider_id == "nvidia-nim":
                nim_called.append(payload.get("model"))
                return httpx.Response(200, json={
                    "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                    "model": payload.get("model"),
                })
            return await original_post_chat(self, provider, payload, timeout_sec)

        with patch.object(ProviderRouter, "_post_chat", mock_post_chat):
            router = ProviderRouter([nim, bedrock])
            payload = {
                "model": "nvidia/nemotron-3-super-120b-a12b",
                "messages": [{"role": "user", "content": "hi"}],
            }
            result = await router.chat_completion(payload)

        assert nim_called, "NIM should be tried first for a NIM model ID"
        assert result.provider.provider_id == "nvidia-nim"


# ── _post_bedrock_converse round-trip ─────────────────────────────────────────

@pytest.mark.asyncio
class TestPostBedrockConverse:
    async def test_successful_call(self):
        provider = _bedrock_provider()
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        mock_client = MagicMock()
        mock_client.converse.return_value = _bedrock_api_response("Hi there!")

        with _mock_boto3(mock_client):
            router = ProviderRouter([provider])
            response = await router._post_bedrock_converse(provider, payload, 30.0)

        assert response.status_code == 200
        body = response.json()
        assert body["choices"][0]["message"]["content"] == "Hi there!"
        assert body["usage"]["prompt_tokens"] == 10

    async def test_passes_correct_credentials(self):
        provider = _bedrock_provider()
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Test"}],
        }
        mock_client = MagicMock()
        mock_client.converse.return_value = _bedrock_api_response()
        captured_kwargs: dict[str, Any] = {}

        mock_boto3_mod = MagicMock()

        def mock_boto3_client(service: str, **kwargs: Any) -> MagicMock:
            captured_kwargs.update(kwargs)
            return mock_client

        mock_boto3_mod.client.side_effect = mock_boto3_client
        original = sys.modules.get("boto3")
        sys.modules["boto3"] = mock_boto3_mod  # type: ignore[assignment]
        try:
            router = ProviderRouter([provider])
            await router._post_bedrock_converse(provider, payload, 30.0)
        finally:
            if original is not None:
                sys.modules["boto3"] = original
            else:
                sys.modules.pop("boto3", None)

        assert captured_kwargs["aws_access_key_id"] == "AKIATEST1234567890AB"
        assert captured_kwargs["aws_secret_access_key"] == "test_secret_key/test+test"
        assert captured_kwargs["region_name"] == "us-east-1"

    async def test_system_prompt_passed_only_when_present(self):
        provider = _bedrock_provider()
        payload_no_system = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        payload_with_system = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [
                {"role": "system", "content": "Be helpful."},
                {"role": "user", "content": "Hello"},
            ],
        }
        mock_client = MagicMock()
        mock_client.converse.return_value = _bedrock_api_response()

        with _mock_boto3(mock_client):
            router = ProviderRouter([provider])

            await router._post_bedrock_converse(provider, payload_no_system, 30.0)
            call_kwargs_no_system = mock_client.converse.call_args.kwargs
            assert "system" not in call_kwargs_no_system

            await router._post_bedrock_converse(provider, payload_with_system, 30.0)
            call_kwargs_with_system = mock_client.converse.call_args.kwargs
            assert "system" in call_kwargs_with_system
            assert call_kwargs_with_system["system"] == [{"text": "Be helpful."}]

    async def test_boto3_import_error_raises_runtime_error(self):
        provider = _bedrock_provider()
        payload = {
            "model": "us.anthropic.claude-opus-4-7",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        real_boto3 = sys.modules.get("boto3")
        sys.modules["boto3"] = None  # type: ignore[assignment]
        try:
            router = ProviderRouter([provider])
            with pytest.raises(RuntimeError, match="boto3 is required"):
                await router._post_bedrock_converse(provider, payload, 30.0)
        finally:
            if real_boto3 is not None:
                sys.modules["boto3"] = real_boto3
            else:
                sys.modules.pop("boto3", None)

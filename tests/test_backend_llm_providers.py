from __future__ import annotations

import json

import httpx
import pytest

from backend.llm_providers import (
    LlmProviderConfig,
    chat_completion_text,
    list_openai_models,
    openai_compat_url,
)


def test_openai_compat_url_adds_v1_when_missing():
    assert openai_compat_url("https://example.com", "/chat/completions") == "https://example.com/v1/chat/completions"


def test_openai_compat_url_does_not_double_v1():
    assert (
        openai_compat_url("https://example.com/v1", "/chat/completions")
        == "https://example.com/v1/chat/completions"
    )


def test_openai_compat_url_google_gemini_does_not_inject_v1():
    # Google's OpenAI-compat surface is at /v1beta/openai — adding /v1 would
    # produce an invalid double-version path and a 400 from the API.
    assert (
        openai_compat_url(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "/chat/completions",
        )
        == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )


@pytest.mark.anyio
async def test_chat_completion_text_sends_auth_header_and_parses_content():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization", "")
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "hf/model"
        body = {"choices": [{"message": {"content": "hello"}}]}
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://router.huggingface.co") as client:
        provider = LlmProviderConfig(
            type="huggingface",
            base_url="https://router.huggingface.co",
            api_key="hf_test",
            default_model="hf/model",
        )
        out = await chat_completion_text(
            provider,
            messages=[{"role": "user", "content": "hi"}],
            model=None,
            temperature=0.3,
            client=client,
        )
    assert out == "hello"
    assert seen["auth"] == "Bearer hf_test"


@pytest.mark.anyio
async def test_list_openai_models_parses_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"data": [{"id": "a"}, {"id": "b"}]}
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.com") as client:
        provider = LlmProviderConfig(type="openai-compatible", base_url="https://example.com/v1", api_key="sk", default_model=None)
        models = await list_openai_models(provider, client=client)
    assert models == ["a", "b"]


@pytest.mark.anyio
async def test_list_openai_models_404_returns_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.com") as client:
        provider = LlmProviderConfig(type="openai-compatible", base_url="https://example.com", api_key=None, default_model=None)
        models = await list_openai_models(provider, client=client)
    assert models == []


@pytest.mark.anyio
async def test_ollama_falls_back_to_native_api_chat_when_openai_surface_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(404, json={"detail": "not found"})
        if request.url.path.endswith("/api/chat"):
            return httpx.Response(200, json={"message": {"role": "assistant", "content": "native-ok"}})
        return httpx.Response(500, json={"detail": "unexpected"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:11434") as client:
        provider = LlmProviderConfig(type="ollama", base_url="http://localhost:11434", api_key=None, default_model="llama3.2")
        out = await chat_completion_text(
            provider,
            messages=[{"role": "user", "content": "hi"}],
            model=None,
            temperature=0.3,
            client=client,
        )
    assert out == "native-ok"

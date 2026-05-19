from __future__ import annotations

"""
Live end-to-end test for AWS Bedrock + Claude Opus 4.6 (highest confirmed-accessible model).

Requires real AWS credentials in the environment:
  AWS_ACCESS_KEY_ID   (or BEDROCK_ACCESS_KEY)
  AWS_SECRET_ACCESS_KEY (or BEDROCK_SECRET_KEY)
  AWS_REGION  [default: us-east-1]

Run locally:
  AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... pytest tests/test_bedrock_live.py -v -s

Skipped automatically when credentials are absent (CI-safe).
"""

import asyncio
import logging
import os
import time

import pytest

log = logging.getLogger("qwen-proxy")

_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("BEDROCK_ACCESS_KEY")
_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get("BEDROCK_SECRET_KEY")
_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID") or "us.anthropic.claude-opus-4-6-v1"

_NEEDS_CREDS = pytest.mark.skipif(
    not (_ACCESS_KEY and _SECRET_KEY),
    reason="AWS credentials not set — skipping live Bedrock tests",
)


# ── Direct boto3 smoke test ───────────────────────────────────────────────────

@_NEEDS_CREDS
def test_bedrock_direct_boto3_ping() -> None:
    """Call Bedrock Converse API directly with boto3 — no proxy layer."""
    import boto3  # type: ignore[import-untyped]

    client = boto3.client(
        "bedrock-runtime",
        region_name=_REGION,
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
    )

    t0 = time.monotonic()
    response = client.converse(
        modelId=_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": "Reply with exactly: BEDROCK_OK"}]}],
        inferenceConfig={"maxTokens": 16, "temperature": 0.0},
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200, "Bedrock HTTP status != 200"

    output_text = ""
    for block in response.get("output", {}).get("message", {}).get("content", []):
        output_text += block.get("text", "")

    usage = response.get("usage", {})
    log.info("model=%s region=%s response=%r input_tok=%s output_tok=%s latency_ms=%s",
             _MODEL_ID, _REGION, output_text,
             usage.get("inputTokens"), usage.get("outputTokens"), latency_ms)

    assert output_text.strip(), "Empty response from Bedrock"
    assert usage.get("outputTokens", 0) > 0, "No output tokens counted"


@_NEEDS_CREDS
def test_bedrock_model_id_is_accessible() -> None:
    """Verify the configured model ID accepts a converse request without auth errors."""
    import boto3  # type: ignore[import-untyped]
    from botocore.exceptions import ClientError  # type: ignore[import-untyped]

    client = boto3.client(
        "bedrock-runtime",
        region_name=_REGION,
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
    )

    try:
        response = client.converse(
            modelId=_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "hi"}]}],
            inferenceConfig={"maxTokens": 8},
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        log.info("%s accessible in %s — PASS", _MODEL_ID, _REGION)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        msg = exc.response["Error"]["Message"]
        pytest.fail(
            f"Bedrock ClientError: {code} — {msg}\n"
            f"  Model : {_MODEL_ID}\n"
            f"  Region: {_REGION}\n"
            "  Check: model enabled in Bedrock console, region correct, IAM permissions."
        )


# ── ProviderRouter integration test ──────────────────────────────────────────

@_NEEDS_CREDS
@pytest.mark.asyncio
async def test_provider_router_bedrock_roundtrip() -> None:
    """ProviderRouter discovers Bedrock from env and completes a real chat call."""
    from provider_router import ProviderRouter

    router = ProviderRouter.from_env()
    bedrock_providers = [p for p in router.providers if p.provider_id == "bedrock"]
    assert bedrock_providers, "Bedrock provider not discovered from env vars"

    provider = bedrock_providers[0]
    assert provider.priority == 15
    assert provider.default_model == _MODEL_ID

    payload = {
        "model": _MODEL_ID,
        "messages": [{"role": "user", "content": "Say exactly: PROXY_OK"}],
        "max_tokens": 16,
        "temperature": 0.0,
    }

    t0 = time.monotonic()
    response = await router._post_bedrock_converse(provider, payload, 30.0)
    latency_ms = int((time.monotonic() - t0) * 1000)

    assert response.status_code == 200, f"Proxy layer returned {response.status_code}"
    body = response.json()

    content = body["choices"][0]["message"]["content"]
    usage = body.get("usage", {})

    log.info("provider=%s(priority=%s) model=%s response=%r "
             "input_tok=%s output_tok=%s latency_ms=%s",
             provider.provider_id, provider.priority, body.get("model"),
             content, usage.get("prompt_tokens"), usage.get("completion_tokens"), latency_ms)

    assert content.strip(), "Empty content in proxy response"
    assert body["choices"][0]["finish_reason"] in ("end_turn", "stop", "max_tokens")
    assert usage.get("completion_tokens", 0) > 0


@_NEEDS_CREDS
def test_bedrock_health_check_with_real_creds() -> None:
    """Health check returns True when real credentials are loaded from env."""
    from provider_router import ProviderRouter

    router = ProviderRouter.from_env()
    bedrock = next((p for p in router.providers if p.provider_id == "bedrock"), None)
    assert bedrock is not None, "No Bedrock provider discovered"

    result = asyncio.run(router.health_check(bedrock))
    assert result is True, "Health check failed with real credentials present"
    log.info("health_check(%s) = %s — PASS", bedrock.provider_id, result)

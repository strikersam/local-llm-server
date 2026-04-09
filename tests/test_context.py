"""Tests for agent/context.py — Smart Context Compression."""
import pytest

from agent.context import ContextCompressor, ContextStats


def _msgs(n: int, content_size: int = 100) -> list[dict]:
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * content_size}
        for i in range(n)
    ]


def test_inspect_returns_stats():
    cc = ContextCompressor()
    msgs = _msgs(4)
    stats = cc.inspect(msgs)
    assert stats.message_count == 4
    assert stats.estimated_tokens > 0
    assert stats.oldest_role in ("user", "assistant")


def test_inspect_empty():
    cc = ContextCompressor()
    stats = cc.inspect([])
    assert stats.message_count == 0
    assert stats.estimated_tokens == 0


def test_needs_compression_true():
    cc = ContextCompressor(token_threshold=10)
    msgs = [{"role": "user", "content": "x" * 100}]  # ~25 tokens
    assert cc.needs_compression(msgs) is True


def test_needs_compression_false():
    cc = ContextCompressor(token_threshold=10_000)
    msgs = _msgs(2)
    assert cc.needs_compression(msgs) is False


def test_reactive_removes_oldest_non_system():
    cc = ContextCompressor(token_threshold=50)
    msgs = [
        {"role": "system", "content": "s" * 10},
        {"role": "user", "content": "u" * 100},
        {"role": "assistant", "content": "a" * 100},
    ]
    result = cc.compress(msgs, strategy="reactive")
    # System message should be preserved
    assert any(m["role"] == "system" for m in result)
    # Result should be shorter
    assert len(result) < len(msgs)


def test_reactive_preserves_single_message():
    cc = ContextCompressor(token_threshold=1)
    msgs = [{"role": "user", "content": "short"}]
    result = cc.compress(msgs, strategy="reactive")
    # Should not crash; at minimum one message remains
    assert len(result) >= 1


def test_micro_removes_duplicates():
    cc = ContextCompressor()
    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "hello"},  # duplicate
        {"role": "assistant", "content": "world"},
    ]
    result = cc.compress(msgs, strategy="micro")
    assert len(result) == 2


def test_micro_removes_near_empty():
    cc = ContextCompressor()
    msgs = [
        {"role": "user", "content": "  "},  # near-empty
        {"role": "user", "content": "real message"},
    ]
    result = cc.compress(msgs, strategy="micro")
    assert len(result) == 1
    assert result[0]["content"] == "real message"


def test_inspect_strategy_does_not_modify():
    cc = ContextCompressor(token_threshold=1)  # would normally compress
    msgs = _msgs(5)
    result = cc.compress(msgs, strategy="inspect")
    assert result == msgs


def test_unknown_strategy_raises():
    cc = ContextCompressor()
    with pytest.raises(ValueError, match="Unknown strategy"):
        cc.compress([], strategy="bogus")  # type: ignore[arg-type]

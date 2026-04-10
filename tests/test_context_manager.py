from __future__ import annotations

"""Tests for agent/context_manager.py.

Covers the three context-engineering strategies implemented in ContextManager:
1. Observation masking
2. Context compaction
3. Just-in-time retrieval hint (prefer_partial_read)
Plus the sub-agent condensed-summary helper.
"""

from agent.context_manager import ContextManager


# ---------------------------------------------------------------------------
# Observation masking
# ---------------------------------------------------------------------------

def _make_obs(n: int) -> list[dict]:
    return [
        {"tool": f"tool_{i}", "args": {"x": i}, "result": f"result body {i} " + "x" * 400}
        for i in range(n)
    ]


def test_mask_observations_short_list_passes_through():
    ctx = ContextManager(mask_after=4)
    obs = _make_obs(3)
    masked = ctx.mask_observations(obs)
    assert len(masked) == 3
    # Nothing should be masked when list is short enough
    assert all("_masked" not in o for o in masked)


def test_mask_observations_truncates_old_entries():
    ctx = ContextManager(mask_after=2, mask_content_limit=50)
    obs = _make_obs(5)
    masked = ctx.mask_observations(obs)

    assert len(masked) == 5
    # First 3 should be masked
    for o in masked[:3]:
        assert o.get("_masked") is True
        # mask_content_limit=50 + " … [masked]" (11 chars) = 61 max
        assert len(o["result"]) <= 65

    # Last 2 should be verbatim
    for o in masked[3:]:
        assert "_masked" not in o
        assert len(o["result"]) > 100


def test_mask_observations_list_result():
    ctx = ContextManager(mask_after=1)
    obs = [
        {"tool": "list_files", "args": {}, "result": ["a.py", "b.py", "c.py"]},
        {"tool": "finish", "args": {}, "result": "done"},
    ]
    masked = ctx.mask_observations(obs)
    assert masked[0].get("_masked") is True
    assert "list" in masked[0]["result"]
    assert "3 items" in masked[0]["result"]


def test_mask_observations_dict_result():
    ctx = ContextManager(mask_after=1)
    obs = [
        {"tool": "search_code", "args": {}, "result": {"path": "a.py", "line": 1}},
        {"tool": "finish", "args": {}, "result": "done"},
    ]
    masked = ctx.mask_observations(obs)
    assert masked[0].get("_masked") is True
    assert "dict" in masked[0]["result"]


# ---------------------------------------------------------------------------
# Context compaction
# ---------------------------------------------------------------------------

def test_needs_compaction_false_for_short_history():
    ctx = ContextManager(compact_after=16)
    history = [{"role": "user", "content": "hi"}] * 10
    assert ctx.needs_compaction(history) is False


def test_needs_compaction_true_for_long_history():
    ctx = ContextManager(compact_after=16)
    history = [{"role": "user", "content": "hi"}] * 20
    assert ctx.needs_compaction(history) is True


def test_compact_history_replaces_old_with_summary():
    ctx = ContextManager(compact_after=4, mask_after=2)
    history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    compacted = ctx.compact_history(history, compaction_summary="The user did X then Y.")

    # First entry should be the compaction note
    assert compacted[0]["role"] == "system"
    assert "compacted" in compacted[0]["content"].lower()
    assert "The user did X then Y." in compacted[0]["content"]

    # Recent messages preserved (mask_after * 2 = 4 most recent)
    tail_contents = [m["content"] for m in compacted[1:]]
    assert "msg 9" in tail_contents
    assert "msg 6" in tail_contents

    # Old messages gone
    assert not any("msg 0" in m.get("content", "") for m in compacted)


def test_compact_history_short_history_unchanged():
    ctx = ContextManager(mask_after=4)
    history = [{"role": "user", "content": "hi"}] * 5
    result = ctx.compact_history(history, compaction_summary="summary")
    # Only 5 messages, keep_tail=8, so nothing to compact
    assert len(result) == len(history)


# ---------------------------------------------------------------------------
# Just-in-time retrieval hint
# ---------------------------------------------------------------------------

def test_prefer_partial_read_large_file():
    ctx = ContextManager(jit_file_limit=80)
    assert ctx.prefer_partial_read(200) is True


def test_prefer_partial_read_small_file():
    ctx = ContextManager(jit_file_limit=80)
    assert ctx.prefer_partial_read(40) is False


def test_prefer_partial_read_unknown_size():
    ctx = ContextManager(jit_file_limit=80)
    assert ctx.prefer_partial_read(None) is False


# ---------------------------------------------------------------------------
# Condensed step result
# ---------------------------------------------------------------------------

def test_condense_step_result_trims_observations():
    result = {
        "status": "applied",
        "changed_files": ["a.py"],
        "observations": [{"tool": f"t{i}", "result": "r"} for i in range(10)],
        "summary": "ok",
    }
    condensed = ContextManager.condense_step_result(result)
    assert len(condensed["observations"]) == 3
    assert condensed["_observations_truncated"] == 7


def test_condense_step_result_trims_long_summary():
    long_summary = "x" * 3000
    result = {"status": "applied", "summary": long_summary, "observations": []}
    condensed = ContextManager.condense_step_result(result, max_chars=500)
    assert len(condensed["summary"]) < 600
    assert "truncated" in condensed["summary"]


def test_condense_step_result_short_result_unchanged():
    result = {"status": "applied", "observations": [{"tool": "t1"}], "summary": "ok"}
    condensed = ContextManager.condense_step_result(result)
    assert "_observations_truncated" not in condensed
    assert condensed["summary"] == "ok"

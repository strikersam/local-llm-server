"""Tests for agent/token_budget.py — Token Spend Caps."""
import pytest

from agent.token_budget import BudgetExceededError, BudgetUsage, TokenBudget


def test_set_cap_and_get():
    tb = TokenBudget()
    usage = tb.set_cap("s1", cap=1000)
    assert usage.cap == 1000
    assert tb.get("s1").cap == 1000


def test_record_accumulates():
    tb = TokenBudget()
    tb.set_cap("s1", cap=5000)
    tb.record("s1", prompt_tokens=100, completion_tokens=50)
    tb.record("s1", prompt_tokens=200, completion_tokens=100)
    usage = tb.get("s1")
    assert usage.prompt_tokens == 300
    assert usage.completion_tokens == 150
    assert usage.total_tokens == 450


def test_check_no_error_under_cap():
    tb = TokenBudget()
    tb.set_cap("s1", cap=1000)
    tb.record("s1", prompt_tokens=100)
    tb.check("s1")  # should not raise


def test_check_raises_over_cap():
    tb = TokenBudget()
    tb.set_cap("s1", cap=50)
    tb.record("s1", prompt_tokens=60)
    with pytest.raises(BudgetExceededError, match="budget exceeded"):
        tb.check("s1")


def test_check_no_error_if_no_cap():
    tb = TokenBudget()
    tb.record("s1", prompt_tokens=999999)
    tb.check("s1")  # no cap set — should not raise


def test_remaining():
    tb = TokenBudget()
    tb.set_cap("s1", cap=1000)
    tb.record("s1", prompt_tokens=400)
    usage = tb.get("s1")
    assert usage.remaining == 600


def test_unlimited_remaining():
    tb = TokenBudget()
    tb.record("s1", prompt_tokens=500)
    usage = tb.get("s1")
    assert usage.remaining == -1  # sentinel for unlimited


def test_reset_clears_usage_keeps_cap():
    tb = TokenBudget()
    tb.set_cap("s1", cap=1000)
    tb.record("s1", prompt_tokens=300)
    tb.reset("s1")
    usage = tb.get("s1")
    assert usage.total_tokens == 0
    assert usage.cap == 1000


def test_record_estimates_from_text():
    tb = TokenBudget()
    # 400 chars ÷ 4 = ~100 tokens
    tb.record("s1", response_text="x" * 400)
    usage = tb.get("s1")
    assert usage.completion_tokens == 100


def test_list_all():
    tb = TokenBudget()
    tb.set_cap("sA", cap=100)
    tb.set_cap("sB", cap=200)
    ids = {u.session_id for u in tb.list_all()}
    assert "sA" in ids
    assert "sB" in ids


def test_as_dict():
    tb = TokenBudget()
    tb.set_cap("s1", cap=500)
    tb.record("s1", prompt_tokens=10)
    d = tb.get("s1").as_dict()
    assert "total_tokens" in d
    assert "exceeded" in d
    assert d["exceeded"] is False

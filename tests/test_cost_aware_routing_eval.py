"""Tests for the cost-aware routing evaluation harness.

These cover the scoring logic — the part that encodes "a cheaper response that
needs rework is not a saving" — and the integrity of the task catalogue.
"""

from __future__ import annotations

import math

import pytest

from evals.cost_aware_routing import (
    TASKS,
    Attempt,
    TaskRun,
    compare,
    load_tasks,
    score_suite,
    token_cost,
)


def test_token_cost_matches_published_rates() -> None:
    # 1M input + 1M output at haiku ($1/$5) = $6.00.
    assert token_cost("haiku", 1_000_000, 1_000_000) == pytest.approx(6.0)
    # opus is 5x/5x haiku on the respective sides.
    assert token_cost("opus", 1_000_000, 0) == pytest.approx(5.0)
    assert token_cost("sonnet", 0, 1_000_000) == pytest.approx(10.0)


def test_unknown_tier_raises() -> None:
    with pytest.raises(KeyError):
        token_cost("gpt", 10, 10)


def test_task_cost_sums_every_attempt() -> None:
    run = TaskRun(
        task_id="t",
        attempts=[
            Attempt("haiku", 100_000, 100_000),  # $0.60
            Attempt("opus", 100_000, 100_000),   # $3.00 redo
        ],
        accepted=True,
    )
    assert run.rework_passes() == 1
    assert run.cost() == pytest.approx(0.6 + 3.0)


def test_cheap_but_reworked_costs_more_than_one_clean_pass() -> None:
    # The core claim: a haiku attempt that fails and is redone on opus should
    # cost more per accepted task than a single clean sonnet pass.
    reworked = TaskRun(
        task_id="x",
        attempts=[Attempt("haiku", 200_000, 200_000), Attempt("opus", 200_000, 200_000)],
        accepted=True,
    )
    clean = TaskRun(
        task_id="x",
        attempts=[Attempt("sonnet", 200_000, 200_000)],
        accepted=True,
    )
    assert score_suite([reworked]).cost_per_accepted_task > score_suite(
        [clean]
    ).cost_per_accepted_task


def test_failed_task_cost_counts_but_acceptance_does_not() -> None:
    # One accepted task and one that burned money but was rejected: the rejected
    # cost lands in the numerator, never in the denominator.
    accepted = TaskRun("a", [Attempt("sonnet", 100_000, 100_000)], accepted=True)  # $1.20
    rejected = TaskRun("b", [Attempt("opus", 100_000, 100_000)], accepted=False)   # $3.00
    result = score_suite([accepted, rejected])
    assert result.accepted_count == 1
    assert result.total_count == 2
    assert result.acceptance_rate == pytest.approx(0.5)
    assert result.total_cost == pytest.approx(1.2 + 3.0)
    assert result.cost_per_accepted_task == pytest.approx(4.2)


def test_zero_accepted_is_infinite_not_zero_division() -> None:
    result = score_suite([TaskRun("a", [Attempt("haiku", 10, 10)], accepted=False)])
    assert math.isinf(result.cost_per_accepted_task)


def test_empty_suite_is_well_defined() -> None:
    result = score_suite([])
    assert result.total_count == 0
    assert result.acceptance_rate == 0.0
    assert math.isinf(result.cost_per_accepted_task)


def test_compare_reports_savings_when_routing_is_cheaper() -> None:
    baseline = [TaskRun("t", [Attempt("opus", 500_000, 500_000)], accepted=True)]  # $15
    routed = [TaskRun("t", [Attempt("haiku", 500_000, 500_000)], accepted=True)]   # $3
    out = compare(baseline, routed)
    assert out["cost_per_accepted_task_delta"] < 0  # routing cheaper
    assert out["savings_pct"] == pytest.approx(80.0)


def test_compare_savings_pct_none_when_baseline_not_finite() -> None:
    baseline = [TaskRun("t", [Attempt("opus", 10, 10)], accepted=False)]
    routed = [TaskRun("t", [Attempt("haiku", 10, 10)], accepted=True)]
    assert compare(baseline, routed)["savings_pct"] is None


def test_catalogue_has_all_four_categories_and_ten_tasks() -> None:
    assert len(TASKS) == 10
    assert {t.category for t in TASKS} == {
        "documentation",
        "exploration",
        "implementation",
        "difficult",
    }
    # Difficult tasks route to opus; documentation/exploration to haiku.
    by_cat = {t.category: t.recommended_tier for t in TASKS}
    assert by_cat["difficult"] == "opus"
    assert by_cat["documentation"] == "haiku"


def test_catalogue_loads_and_validates() -> None:
    tasks = load_tasks()
    assert all(t.success_criteria for t in tasks)
    assert len({t.task_id for t in tasks}) == len(tasks)  # ids unique

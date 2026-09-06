# Cost-aware routing evaluation

Measures the cost-aware subagent routing in [`.claude/agents/`](../../.claude/agents/)
against a baseline workflow, scoring **cost per accepted task** — not raw token
cost. A cheaper response that needs substantial rework is not a saving, and this
harness is built to make that show up in the number.

This directory is the **instrument**, not a set of results. It ships the task
catalogue, the pricing, and the scoring. Producing results means running the ~10
tasks under both workflows and recording what actually happened — that step is
manual, and deliberately so: acceptance is a human/eval judgment, not something
the harness can fabricate.

## What's here

| File | Purpose |
|------|---------|
| `tasks.yaml` | 10 representative tasks across four categories, each with **success criteria fixed before any run** |
| `tasks.py` | Loads and validates the catalogue (`load_tasks()`, `TASKS`) |
| `pricing.py` | Published per-tier rates (haiku `$1/$5`, sonnet `$2/$10`, opus `$5/$25` per 1M tok); `token_cost()` |
| `scoring.py` | `Attempt`, `TaskRun`, `score_suite()`, `compare()` |

Tests: [`tests/test_cost_aware_routing_eval.py`](../../tests/test_cost_aware_routing_eval.py).

## Method

Do not claim the routing saves a fixed percentage. Measure it.

1. **Define success first.** `tasks.yaml` fixes the acceptance criteria per task.
   Judge the baseline and the routed run the *same way*, or the comparison is
   meaningless.
2. **Baseline.** Run each task under the current workflow (one capable model, no
   tiering). For every attempt record `tier`, `input_tokens`, `output_tokens`,
   `wall_seconds`; record whether the final result was `accepted`. Rework and
   retries are separate `Attempt`s on the same `TaskRun`.
3. **Routed.** Run the same tasks under the subagent routing — read-only work to
   haiku, routine implementation to sonnet, difficult/high-risk to opus — keeping
   the acceptance criteria and reviewer identical.
4. **Score.**

```python
from evals.cost_aware_routing import Attempt, TaskRun, compare

baseline = [
    TaskRun("docs-env-parity", [Attempt("opus", 40_000, 6_000)], accepted=True),
    # ... one TaskRun per task, from your recorded runs ...
]
routed = [
    TaskRun("docs-env-parity", [Attempt("haiku", 40_000, 6_000)], accepted=True),
    # ...
]

out = compare(baseline, routed)
print(out["baseline"].cost_per_accepted_task)
print(out["routed"].cost_per_accepted_task)
print(out["savings_pct"])  # None if the baseline metric isn't finite
```

## CLI

Record your runs as JSON (schema in `runsio.py`) and score them without writing
code:

```bash
# your recorded runs
python -m evals.cost_aware_routing runs.json
make eval-routing RUNS=runs.json

# the bundled illustrative sample (numbers are NOT measured)
python -m evals.cost_aware_routing --example
make eval-routing
```

The sample (`runs_example.json`) exists only to show the report shape — its
`note` field says so. Replace it with real run logs before drawing any
conclusion.

## How the metric resists gaming

`cost_per_accepted_task = (total cost of every attempt) / (accepted tasks)`.

- Rework adds attempts → the numerator grows, so a cheap-but-redone task is
  charged for both tries.
- A task that is never accepted still costs money (numerator) but adds nothing to
  the denominator, so failing tasks cheaply makes the number *worse*.
- Zero accepted tasks → `inf`, not a divide-by-zero — infinite spend bought no
  accepted work.

## Caveats

- Prices in `pricing.py` are published list rates as of 2026-09; verify against
  current pricing before quoting dollars, or override with `set_price()`.
- Token counts should come from real run logs. Estimating them defeats the point.
- Wall time is recorded but not part of the headline metric — it is context, not
  the score.

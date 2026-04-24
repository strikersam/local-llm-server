# NEXT ACTION — Multica Workflow Follow-Up

**Session:** `multica-workflow-retrofit` (2026-04-24)
**Resume command:** `python scripts/ai_runner.py resume`
**Status file:** `.claude/state/agent-state.json`
**Checkpoint log:** `.claude/state/checkpoint.jsonl`

---

## Current Objective

Close the remaining gap between the new Multica-style task workflow and the live product:
verify UI behavior manually, decide whether to add SSE/WebSocket updates, and address the
pre-existing unrelated router test failure before a full green suite.

---

## Completed Steps

- [x] Audit current task/agent/runtime/scheduler/frontend gaps against the requested Multica behavior
- [x] Add lifecycle-focused workflow tests (`tests/test_tasks_workflow.py`)
- [x] Implement task lifecycle service with real transition rules, review/block semantics, and threaded comments
- [x] Route task execution through runtime-aware coordinator with agent-definition binding
- [x] Unify scheduler and playbook runs through task creation
- [x] Update Tasks UI to show comments, execution history, and actual runtime/model details
- [x] Update changelog and targeted regression coverage

## Next Step

- [ ] Run the full test suite after resolving the existing router baseline failure in `tests/test_model_router.py`
- [ ] Manually verify the task board flow in the browser:
  - create an agent with runtime + model
  - create a task in each lane
  - comment on an in-review task and confirm it re-queues
  - trigger a scheduler job and confirm a real task appears
- [ ] Decide whether to add SSE/WebSocket delivery for task updates instead of polling

## If Interrupted

1. Read `.claude/state/agent-state.json` for full plan state
2. Read `.claude/state/checkpoint.jsonl` for last successful checkpoint
3. Run `python scripts/ai_runner.py status` to see current state
4. Run `python scripts/ai_runner.py resume` to continue from last checkpoint

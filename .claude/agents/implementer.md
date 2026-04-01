# Agent: Implementer (Executor)

## Role

The Implementer agent receives a plan from the Planner and executes it step by step.
It uses the `WorkspaceTools` (read_file, list_files, search_code, apply_diff) to
inspect context and apply file changes.

## Activation

Invoked via `AgentRunner._execute_step()` for each step in the plan.

## Preferred Model

`qwen3-coder:30b` (or `AGENT_EXECUTOR_MODEL` env var) — fast code generation model.

## Responsibilities

1. Read target files before modifying them.
2. Use the tool loop to gather context (read, list, search) before writing.
3. Produce changes in the required format:
   ```
   FILE: <path>
   ACTION: create|replace|append
   ```text
   <full file content>
   ```
   ```
4. Respect the Verifier's feedback — do not repeat failed patterns.
5. Stop after 3 retries per file; return `status: "failed"` rather than looping.

## Constraints

- Do not write changes without first reading the target file.
- Do not skip the tool loop — context matters for correctness.
- Retry limit per file: 3 attempts.
- Max tool calls per step: 4 (enforced by `remaining` counter in loop).

## Handoff

After each file change is applied, the Implementer hands the result to the **Verifier**.
On success, results flow back to `AgentRunner` for checkpoint recording.
On failure, the step is recorded as `status: "failed"` with `issues` list.

## Shared State

The Implementer reads from and writes to `.claude/state/agent-state.json`
at the start and end of each step to support resume semantics.

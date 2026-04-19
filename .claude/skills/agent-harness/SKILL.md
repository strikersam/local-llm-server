# Skill: agent-harness

## Purpose
Build and run a structured **agent harness** — an outer loop that gives an LLM a defined set of tools (capabilities) and drives it to task completion. Based on the architecture from the OpenAI Agents SDK blog post: an Agent is a for-loop with an LLM running tools until done.

## When to Use
- You need an agent that can take multi-step autonomous action on a complex task.
- You want to define explicit tool capabilities (shell, file I/O, search, etc.) and constrain the agent to them.
- You're building an internal coding agent, research agent, or workflow agent.

## Architecture

```
┌─────────────────────────────────────────────┐
│                  HARNESS                    │
│                                             │
│  ┌──────────┐    ┌────────────────────────┐ │
│  │  Task    │───▶│     Agent Loop         │ │
│  │  Input   │    │  while not done:       │ │
│  └──────────┘    │    action = LLM(state) │ │
│                  │    result = tool(action)│ │
│                  │    state.update(result) │ │
│                  └────────────┬───────────┘ │
│                               │             │
│  ┌────────────────────────────▼───────────┐ │
│  │           CAPABILITIES                 │ │
│  │  shell_exec | file_read | file_write   │ │
│  │  web_search | sandboxed_exec | ...     │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## Key Concepts

| Term | Definition |
|------|-----------|
| **Agent** | LLM + tool loop running until a stop condition |
| **Harness** | The scaffolding around the agent: tools, state, loop control |
| **Capability** | A stateful, bound set of tools for a specific agent instance |
| **Stop condition** | Criteria that ends the loop: task_complete, max_steps, error |
| **Sandbox** | Isolated execution env — use `sandboxed-exec` skill |

## Usage

```
@agent-harness
task: <what the agent should accomplish>
capabilities: [shell, file_read, file_write, search]
max_steps: <N, default 20>
sandbox: <true|false, default true>
stop_on: <task_complete|max_steps|first_success>
```

## Steps (for Claude to follow)

### Step 1 — Define the task clearly
Write a precise task description including:
- Goal (what does "done" look like?)
- Constraints (what must NOT be done?)
- Available context (files, APIs, data)

### Step 2 — Select capabilities
Choose from:
- `shell` — run shell commands (sandboxed if `sandbox: true`)
- `file_read` — read workspace files
- `file_write` — write files (with confirmation if `sandbox: false`)
- `search` — web or codebase search
- `test_runner` — run the test suite and parse results
- `git` — git operations (status, diff, commit)

### Step 3 — Run the agent loop
```
iteration = 0
while iteration < max_steps:
    thought = reason_about_current_state(task, history)
    action  = select_tool(thought, capabilities)
    result  = execute(action, sandbox=sandbox)
    history.append({thought, action, result})
    if stop_condition_met(result, task):
        break
    iteration += 1
```

### Step 4 — Report outcome
Produce a structured report (see Output Format).

## Output Format

```
AGENT HARNESS REPORT
====================
Task        : <task>
Capabilities: <list>
Sandbox     : <true|false>
Steps taken : <N> / <max>
Stop reason : <task_complete | max_steps | error>

EXECUTION TRACE
---------------
[Step 1] Thought: ...
         Action : shell("ls -la")
         Result : ...

[Step 2] Thought: ...
         Action : file_write("solution.py", ...)
         Result : ✅ written

...

FINAL OUTCOME
-------------
<Summary of what was accomplished>
<Files created or modified>
<Remaining work if any>
```

## Safety Rules
1. **Always sandbox** untrusted or generated code before writing to workspace.
2. **Confirm destructive actions** (delete, overwrite) with the user.
3. **Cap iterations** — never run unbounded loops.
4. **Log every step** — maintain the execution trace for auditability.
5. **Fail loudly** — surface errors immediately rather than silently skipping.

## Combining with Other Skills
- `sandboxed-exec` — safe execution environment per step
- `parallel-agents` — fan out to multiple harness instances
- `test-first-executor` — drive the harness with failing tests as the goal
- `debug-tracer` — use when the harness hits an unexpected error
- `scope-guard` — prevent the harness from drifting out of scope

# Refactoring & Improvement Review Framework
**Target System:** Autonomous AI Agency Framework
**Repository:** `strikersam/autonomous-ai-agency` (`local-llm-server`)

---

## 1. PR Analysis Summary & Evaluation Rubric

### Evaluation Rubric

| Dimension | Check | Red Flags Specific to Agent Repos |
|---|---|---|
| **Safety** | Does it widen the agent's blast radius? | New tools without schema validation, timeouts, or permission class; removal of human-approval gates; raised spend thresholds |
| **Necessity** | Solves a real problem vs. gold-plating? | "Refactor" PRs touching the agent loop with no behavioral test coverage |
| **Architecture Fit** | Consistent with (or improving) the core loop? | Bypassing the tool registry with direct API calls; a second, parallel state-management path |
| **Behavioral Tests** | Prompt changes are behavior changes | PRs editing prompt strings with zero eval/behavior tests — the #1 merge hazard in agent repos |
| **Type Safety** | Typed signatures, no `Any` in executor path | `def run(*args, **kwargs)` on tool functions |
| **Secrets** | No credentials in diff | Keys pasted into config files or test fixtures |
| **Concurrency** | Async correctness | `asyncio.create_task` without a stored reference; `gather(return_exceptions=True)` with the result list ignored |

---

### PR Evaluation Summary (Recent & Open PRs #1436 – #1465)

| PR# | Title / Summary | Risk | Conflicts / Surfaces | Missing | Verdict | Required Changes Before Merge |
|---|---|---|---|---|---|---|
| **#1465** | `chore(deps): update pymongo requirement from >=4.17.0 to >=4.18.0` | **Low** | Dependency pins in `requirements.txt` | None (automated semver patch) | **Merge** | Verified green build; safe minor dependency update. |
| **#1462** | `chore(deps): update boto3 requirement from >=1.43.83 to >=1.43.88` | **Low** | `requirements.txt`, AWS SDK | None | **Merge** | None; automated non-breaking version bump. |
| **#1459** | `chore(deps): update anthropic requirement from >=1.2.0 to >=1.3.0` | **Low** | `requirements.txt`, Anthropic SDK | None | **Merge** | Ensure non-temperature / adaptive thinking compatibility remains guarded (`packages/ai/router.py`). |
| **#1458** | `chore(deps): bump all-patches group in /frontend` (5 updates) | **Low** | `frontend/package.json`, `package-lock.json` | None | **Merge** | None; frontend lockfile synchronized. |
| **#1449** | `chore(deps): bump all-patches group in /webui/frontend` | **Low** | `webui/frontend/package.json` | None | **Merge** | None. |
| **#1448** | `fix(agency): stop autonomous-agent workflow crashing on provider error` | **Medium** | `.github/scripts/gh_brain_failover.py`, `autonomous_agent.py` | None (10 regression tests in `test_gh_brain_failover.py`) | **Merge** | Verified multi-provider failover chain works as expected. |
| **#1447** | `fix(agent): stop leaking raw exception text from /v2/agent/coordinate` | **Low** | `agent/coordinate.py` | None (`test_no_exception_detail_leaks.py`) | **Merge** | Replaces 500 `str(exc)` leak with generic error message. |
| **#1446** | `feat(governance): redact SSNs and payment-card numbers in audit scrubber` | **Low** | `packages/governance/audit.py` | None (11 unit tests) | **Merge** | None; fails-closed PII scrubbing pass. |
| **#1443** | `fix(probe): stop reporting disabled local providers as unreachable` | **Low** | `.github/scripts/probe_catalogues.py` | None (3 regression tests) | **Merge** | None. |
| **#1442** | `chore(evals): runnable CLI + docs wiring for cost-aware routing harness` | **Medium** | `evals/cost_aware_routing/` | None (15 tests in `test_cost_aware_routing_eval.py`) | **Merge** | Ensures task evaluation uses real run logs, never synthetic samples. |
| **#1440** | `fix(brain): exclude catalogue-listed-but-dead model from failover for cooldown` | **High** | `packages/ai/model_discovery.py`, `failover_client.py` | None (6 tests) | **Merge** | Dynamic cooldown logic verified; prevents failover loop exhaustion. |
| **#1438** | `chore(agents): cost-aware Claude Code subagents with model-tiered routing` | **Medium** | `.claude/agents/*.md`, `AGENTS.md` | None | **Merge** | Enforces subagent frontmatter discipline and separation of implementation/review. |
| **#1436** | `fix(telegram): stop self_heal from deleting webhook in webhook mode` | **High** | `services/self_heal.py` | None (1 regression test) | **Merge** | Stops 15-minute transport wiping cycle in webhook mode. |

---

## 2. Critical Bugs & Exact Detection Signatures

### 🔴 CRITICAL — Silent Error Propagation in Agent Loop & Tool Dispatch

**Greppable Detection Signatures:**
```bash
grep -rn "except Exception:\s*pass\|except:\s*pass" agent/ packages/
grep -rn "return_exceptions=True" agent/ services/
grep -rn "logging.debug.*error\|logger.debug.*fail" agent/
```

**Location in Codebase:**
- `agent/loop.py`: Tool outputs returning string error messages `[tool error: ...]`.
- `agent/context_manager.py`: Observation truncation masking list/dict outputs (`[dict keys=... - masked]`).

**Drop-in Fix Pattern:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: dict | str | None
    error: str | None
    retryable: bool
    idempotency_key: str | None = None

    def to_model_observation(self) -> str:
        if self.ok:
            return f"SUCCESS:\n{self.output}"
        return f"TOOL_ERROR (retryable={self.retryable}):\n{self.error}"
```

---

### 🔴 CRITICAL — Unsandboxed Tool Execution & SSRF Vulnerabilities

**Greppable Detection Signatures:**
```bash
grep -rn "_safe_path\|unsafe_target_reason" agent/
grep -rn "subprocess.run\|exec(\|eval(" agent/
```

**Location in Codebase:**
- `agent/tools.py`: `_safe_path()` uses `os.path.realpath` prefix checks (`target.startswith(root + os.sep)`).
- `agent/web_reach.py`: `unsafe_target_reason()` validates initial target IP addresses via `ipaddress.ip_address()`.

**Drop-in Fix Pattern (`agent/web_reach.py`):**
```python
def _safe_get_strict(self, url: str, max_redirects: int = 5) -> httpx.Response:
    current = url
    with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            reason = unsafe_target_reason(current)
            if reason:
                raise ValueError(f"SSRF Guard Blocked Hop ({current}): {reason}")
            resp = client.get(current, headers={"User-Agent": _UA})
            if resp.is_redirect:
                current = resp.headers.get("location")
                continue
            resp.raise_for_status()
            return resp
    raise ValueError("Too many redirects")
```

---

### 🔴 CRITICAL — Unhandled Rate Limits & State Checkpointing

**Greppable Detection Signatures:**
```bash
grep -rn "checkpoint_agent_state" agent/
grep -rn "TokenBudget" agent/
```

**Drop-in Fix Pattern (`agent/token_budget.py`):**
```python
from aiolimiter import AsyncLimiter
from tenacity import AsyncRetrying, stop_after_attempt, retry_if_exception_type, wait_exponential

llm_gate = AsyncLimiter(max_rate=40, time_period=60)

async def call_llm_with_rate_limit(client, payload):
    async with llm_gate:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1.5, min=2, max=60),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
            reraise=True,
        ):
            with attempt:
                return await client.post(...)
```

---

## 3. Architectural Refactoring Architecture

```
                     ┌───────────────────────────────────────────────┐
                     │           User / API / Telegram               │
                     └──────────────────────┬────────────────────────┘
                                            │
                                            ▼
                     ┌───────────────────────────────────────────────┐
                     │    services/workflow_orchestrator.py          │
                     │         (Golden Path Execution)               │
                     └──────────────────────┬────────────────────────┘
                                            │
           ┌────────────────────────────────┼────────────────────────────────┐
           ▼                                ▼                                ▼
┌──────────────────────┐        ┌──────────────────────┐         ┌──────────────────────┐
│  agent/user_memory.py│        │agent/procedural_mem. │         │ agent/checkpoint.py  │
│   (Semantic Memory)  │        │ (Skill / Procedural) │         │   (Event Sourcing)   │
└──────────────────────┘        └──────────────────────┘         └──────────────────────┘
```

### Golden Path Orchestration
All agent execution is routed through `services/workflow_orchestrator.py` enforcing the 11-phase Golden Path:
`CLASSIFY` → `PLAN` → `SELECT_SPECIALIST` → `PREFLIGHT` → `BIND_CONTEXT` → `EXECUTE` → `VERIFY` → `JUDGE` → `SUMMARIZE` → `PERSIST` → `MONITOR`.

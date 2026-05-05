from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import time
import asyncio
import httpx

from agent.context_manager import ContextManager
from agent.models import AgentPlan, ToolCall, VerificationResult
from agent.prompts import (
    build_compaction_prompt,
    build_execution_prompt,
    build_planning_prompt,
    build_tool_prompt,
    build_verification_prompt,
)
from agent.state import AgentSessionStore
from agent.tools import WorkspaceTools
from agent.user_memory import UserMemoryStore
from provider_router import CommercialFallbackRequiredError, ProviderConfig, ProviderRouter
from router import get_router

log = logging.getLogger("qwen-agent")

# Security-sensitive files the planner/runner must flag for extra scrutiny.
# Any step that touches these triggers a risky-module warning and extra
# verifier passes.  Kept as a module constant so tests can reference it.
_RISKY_FILES: frozenset[str] = frozenset({
    "admin_auth.py",
    "key_store.py",
    "agent/tools.py",
    "proxy.py",          # auth middleware — changes need risky-module-review
})

# Default to Nvidia NIM free models — no local infra required.
# These are overridden by env vars when local Ollama models are preferred.
DEFAULT_PLANNER_MODEL = os.environ.get(
    "AGENT_PLANNER_MODEL",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1"
    if (os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey"))
    else "deepseek-r1:32b",
)
DEFAULT_EXECUTOR_MODEL = os.environ.get(
    "AGENT_EXECUTOR_MODEL",
    "qwen/qwen2.5-coder-32b-instruct"
    if (os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey"))
    else "qwen3-coder:30b",
)
DEFAULT_VERIFIER_MODEL = os.environ.get(
    "AGENT_VERIFIER_MODEL",
    "deepseek-ai/deepseek-r1"
    if (os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey"))
    else "deepseek-r1:32b",
)


class AgentPhaseError(RuntimeError):
    def __init__(self, phase: str, message: str) -> None:
        self.phase = phase
        super().__init__(f"{phase}: {message}")


class AgentRunner:
    def __init__(
        self,
        *,
        ollama_base: str,
        workspace_root: str | Path | None = None,
        provider_headers: dict[str, str] | None = None,
        provider_chain: list[ProviderConfig] | None = None,
        allow_commercial_fallback: bool = True,
        provider_temperature: float | None = None,
        session_store: AgentSessionStore | None = None,
        github_token: str | None = None,
        email: str | None = None,
        department: str | None = None,
        key_id: str | None = None,
    ) -> None:
        # NOTE: "ollama_base" is kept for backwards compatibility; this runner only needs an
        # OpenAI-compatible base URL with /v1/chat/completions.
        self.ollama_base = ollama_base.rstrip("/")
        self.provider_headers = dict(provider_headers or {})
        self.provider_chain = list(provider_chain or [])
        self.allow_commercial_fallback = allow_commercial_fallback
        self.provider_temperature = provider_temperature
        self.tools = WorkspaceTools(workspace_root)
        from agent.github_tools import GitHubTools
        self.github = GitHubTools(github_token)
        self.ctx = ContextManager()
        # Optional session store for event-log writes (append-only durable log).
        # When provided the harness logs key events so the session is
        # recoverable and queryable outside the LLM context window.
        self._session_store = session_store
        # Legacy auth storage (prefer passing to run())
        self.email = email
        self.department = department
        self.key_id = key_id

    async def run(
        self,
        *,
        instruction: str,
        history: list[dict[str, str]],
        requested_model: str | None,
        auto_commit: bool,
        max_steps: int,
        user_id: str | None = None,
        department: str | None = None,
        key_id: str | None = None,
        memory_store: UserMemoryStore | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        # Context compaction: if history is long, summarise the old portion
        # before planning so the planner doesn't spend tokens on verbatim
        # repetition.  (Anthropic managed-agents: preserve architectural
        # decisions, discard redundant tool outputs.)
        effective_history = history
        if self.ctx.needs_compaction(history):
            effective_history = await self._compact_history(
                history, requested_model, session_id
            )

        self._log_event(session_id, "user_message", {"instruction": instruction})

        plan = await self._generate_plan(
            instruction, effective_history, requested_model, max_steps, user_id, memory_store
        )
        self._log_event(session_id, "step_start", {"goal": plan.goal, "steps": len(plan.steps)})

        # Risky module detection: warn loudly if the plan touches security-sensitive files.
        # Per risky-module-review skill and agent/CLAUDE.md.
        def _step_touches_risky(step_files: list[str]) -> bool:
            return any(
                sf.replace("\\", "/") == rf or sf.replace("\\", "/").endswith(f"/{rf}")
                for sf in step_files
                for rf in _RISKY_FILES
            )

        if plan.requires_risky_review or any(
            _step_touches_risky(step.files) for step in plan.steps
        ):
            log.warning(
                "RISKY MODULE detected in plan for '%s'. "
                "Steps touching: %s. Risks: %s. Proceeding with extra verifier scrutiny.",
                plan.goal,
                [f for step in plan.steps for f in step.files if any(f.replace("\\", "/") == r or f.replace("\\", "/").endswith(f"/{r}") for r in _RISKY_FILES)],
                plan.risks,
            )
            self._log_event(session_id, "step_start", {"risky_review": True, "risks": plan.risks})
        self._write_checkpoint(session_id, plan)

        parallel_result = await self._maybe_run_parallel(
            plan=plan,
            instruction=instruction,
            requested_model=requested_model,
            max_steps=max_steps,
            auto_commit=auto_commit,
            user_id=user_id,
            memory_store=memory_store,
            session_id=session_id,
            department=department,
            key_id=key_id,
        )
        if parallel_result is not None:
            parallel_result["judge"] = await self._run_judge(
                plan=plan,
                step_results=parallel_result.get("steps", []),
                requested_model=requested_model,
                session_id=session_id,
            )
            return parallel_result

        step_results: list[dict[str, Any]] = []
        commits: list[str] = []

        for step in plan.steps[:max_steps]:
            step_data = step.model_dump()
            self._log_event(session_id, "step_start", {"step_id": step_data["id"], "description": step_data["description"]})
            result = await self._execute_step(
                plan.goal,
                step_data,
                requested_model,
                user_id,
                memory_store,
                session_id=session_id,
            )
            # Sub-agent condensed summary: trim step results before storing so
            # the orchestrator's context stays lean.  (1-2k token budget.)
            condensed = ContextManager.condense_step_result(result)
            self._log_event(session_id, "step_complete", condensed)
            step_results.append(result)
            if auto_commit and result["status"] == "applied" and result["changed_files"]:
                commit = self._commit_step(step_data["description"], result["changed_files"])
                if commit:
                    commits.append(commit)

        summary = self._build_summary(plan.goal, step_results, commits)
        report  = self._build_rich_report(plan.goal, step_results, commits)
        self._log_event(session_id, "assistant_message", {"summary": summary})

        # Judge gate: quick holistic review of all applied changes.
        # Mirrors .claude/agents/judge.md — runs after all steps complete.
        judge_verdict = await self._run_judge(
            plan=plan,
            step_results=step_results,
            requested_model=requested_model,
            session_id=session_id,
        )

        # Update auth context if passed in run()
        if user_id:
            self.email = user_id
        if department:
            self.department = department
        if key_id:
            self.key_id = key_id

        return {
            "goal": plan.goal,
            "plan": plan.model_dump(),
            "steps": step_results,
            "commits": commits,
            "summary": summary,
            "report": report,
            "judge": judge_verdict,
        }

    async def _generate_plan(
        self,
        instruction: str,
        history: list[dict[str, str]],
        requested_model: str | None,
        max_steps: int,
        user_id: str | None = None,
        memory_store: UserMemoryStore | None = None,
    ) -> AgentPlan:
        user_memories = memory_store.recall_all(user_id) if memory_store and user_id else {}
        messages = build_planning_prompt(instruction, history, user_memories=user_memories)
        planner_decision = get_router().route(
            requested_model=requested_model,
            messages=messages,
            override_model=requested_model if requested_model else None,
            endpoint_type="agent_plan",
        )
        planner_model = planner_decision.resolved_model if not requested_model else requested_model
        if not planner_model:
            planner_model = DEFAULT_PLANNER_MODEL
        log.debug(
            "agent plan: model=%s [%s/%s]",
            planner_model, planner_decision.mode, planner_decision.selection_source,
        )
        try:
            raw = await self._chat_json(planner_model, messages)
            raw = self._normalize_plan_response(raw, instruction)
            plan = AgentPlan.model_validate(raw)
        except Exception as exc:
            raise AgentPhaseError(
                "planning",
                f"planner output was invalid or incomplete: {exc}",
            ) from exc
        plan.steps = plan.steps[:max_steps]
        return plan

    def _normalize_plan_response(self, raw: dict[str, Any], instruction: str) -> dict[str, Any]:
        """Normalize an LLM planner response to match the AgentPlan schema.

        Some models (especially those trained on workflow/slice terminology) return
        'slices' instead of 'steps', omit 'goal', or omit 'type' on individual steps.
        This method repairs those deviations so Pydantic validation never fails due to
        schema mismatch alone.
        """
        normalized = dict(raw)

        # 'slices' is CRISPY-workflow terminology; map it to 'steps'
        if "steps" not in normalized and "slices" in normalized:
            normalized["steps"] = normalized.pop("slices")

        # Derive goal from instruction when the model omits it
        if not normalized.get("goal"):
            normalized["goal"] = instruction[:200].strip() or "Complete the requested task"

        # Ensure risks is a list
        if "risks" not in normalized or not isinstance(normalized["risks"], list):
            normalized["risks"] = []

        # Ensure each step has a valid 'type' field (Literal on AgentStep requires it).
        # Infer from context when absent: steps with files get "edit", others "analyze".
        valid_types = {"edit", "create", "analyze", "github"}
        for step in normalized.get("steps", []):
            if isinstance(step, dict) and step.get("type") not in valid_types:
                step["type"] = "edit" if step.get("files") else "analyze"

            # Ensure step description is non-empty
            if not isinstance(step.get("description"), str) or not step["description"].strip():
                step["description"] = "Perform step"

            # Ensure acceptance is a string
            if "acceptance" not in step or not isinstance(step["acceptance"], str):
                step["acceptance"] = ""

        return normalized

    async def _execute_step(
        self,
        goal: str,
        step: dict[str, Any],
        requested_model: str | None,
        user_id: str | None = None,
        memory_store: UserMemoryStore | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        observations: list[dict[str, Any]] = []
        context_items: list[dict[str, Any]] = []
        changed_files: list[str] = []
        retries = 0
        target_files = list(step.get("files") or [])

        if not target_files and step.get("type") == "create":
            target_files = [f"generated/step_{step['id']}.txt"]
        elif not target_files and step.get("type") == "github":
            target_files = ["github_operation"]

        executor_decision = get_router().route(
            requested_model=requested_model,
            override_model=requested_model if requested_model else None,
            endpoint_type="agent_execute",
        )
        executor_model = executor_decision.resolved_model if not requested_model else requested_model
        if not executor_model:
            executor_model = DEFAULT_EXECUTOR_MODEL

        verifier_decision = get_router().route(
            requested_model=requested_model,
            endpoint_type="agent_verify",
        )
        verifier_model = verifier_decision.resolved_model if not requested_model else requested_model
        if not verifier_model:
            verifier_model = DEFAULT_VERIFIER_MODEL

        log.debug(
            "agent execute: executor=%s verifier=%s",
            executor_model, verifier_model,
        )

        for remaining in range(15, 0, -1):
            try:
                # Observation masking: pass truncated older observations to
                # keep the tool-selection prompt lean.  Recent observations are
                # passed verbatim; older ones are summarised.
                masked_obs = self.ctx.mask_observations(observations)
                tool_call = await self._chat_json(
                    executor_model,
                    build_tool_prompt(goal=goal, step=step, observations=masked_obs, remaining_calls=remaining),
                )
                call = ToolCall.model_validate(tool_call)
            except CommercialFallbackRequiredError:
                raise
            except Exception as exc:
                observations.append({"tool": "error", "result": f"tool selection failed: {exc}"})
                continue
            if call.tool == "finish":
                observations.append({"tool": "finish", "result": call.args.get("reason", "done inspecting")})
                break
            call_id = f"step-{step['id']}-tool-{16 - remaining}"
            self._log_event(
                session_id,
                "tool_call",
                {
                    "call_id": call_id,
                    "tool_name": call.tool,
                    "args": call.args,
                    "step_id": step["id"],
                    "status": "running",
                },
            )
            result = await self._run_tool(call.tool, call.args, user_id=user_id, memory_store=memory_store)
            tool_failed = isinstance(result, str) and result.startswith("[tool error:")
            self._log_event(
                session_id,
                "tool_result",
                {
                    "call_id": call_id,
                    "tool_name": call.tool,
                    "args": call.args,
                    "step_id": step["id"],
                    "status": "error" if tool_failed else "success",
                    "output": str(result)[:4000],
                },
            )
            observations.append({"tool": call.tool, "args": call.args, "result": result})
            context_items.append({"tool": call.tool, "result": result})

        if not target_files and step.get("type") not in ("github", "analyze"):
            search_hits = self.tools.search_code(step["description"], limit=3)
            target_files = [hit["path"] for hit in search_hits if isinstance(hit.get("path"), str)]

        if not target_files and step.get("type") not in ("github", "analyze"):
            return {
                "step_id": step["id"],
                "description": step["description"],
                "status": "skipped",
                "reason": "No target files identified",
                "changed_files": [],
                "observations": observations,
                "models": {"executor": executor_model, "verifier": verifier_model},
            }

        if step.get("type") in ("github", "analyze"):
            # For analysis/Q&A steps, synthesize a readable answer from observations.
            answer = await self._synthesize_answer(
                goal, step, observations, executor_model
            )
            return {
                "step_id": step["id"],
                "description": step["description"],
                "status": "applied",
                "changed_files": [],
                "observations": observations,
                "answer": answer,
                "models": {"executor": executor_model, "verifier": verifier_model},
            }

        for target_file in target_files:
            original_content = self._safe_read(target_file)
            retries = 0
            feedback_issues: list[str] = []
            file_applied = False
            while retries <= 4:
                response = await self._chat_text(
                    executor_model,
                    build_execution_prompt(
                        goal=goal,
                        step=step,
                        target_file=target_file,
                        context_items=context_items,
                        feedback_issues=feedback_issues,
                    ),
                )
                parsed = self._parse_execution_response(response, target_file)
                if not parsed:
                    repaired = await self._chat_text(
                        executor_model,
                        [
                            {
                                "role": "system",
                                "content": (
                                    "Convert the input into the required format only.\n"
                                    "Return ONLY:\n"
                                    "FILE: <path>\n"
                                    "ACTION: <create|replace|append>\n"
                                    "```text\n"
                                    "<FULL FILE CONTENT>\n"
                                    "```"
                                ),
                            },
                            {"role": "user", "content": response},
                        ],
                    )
                    parsed = self._parse_execution_response(repaired, target_file)
                if not parsed:
                    retries += 1
                    feedback_issues = ["You violated format. Fix only format."]
                    if retries > 2:
                        return {
                            "step_id": step["id"],
                            "description": step["description"],
                            "status": "failed",
                            "issues": feedback_issues,
                            "changed_files": changed_files,
                            "observations": observations,
                            "models": {"executor": executor_model, "verifier": verifier_model},
                        }
                    continue

                out_path, new_content = parsed
                new_content = self._clean_generated_file_content(new_content)
                syntax_issues = self._local_syntax_check(out_path, new_content)
                syntax_issues.extend(self._local_safety_check(out_path, new_content))
                try:
                    verification = await self._chat_json(
                        verifier_model,
                        build_verification_prompt(
                            goal=goal,
                            step=step,
                            target_file=out_path,
                            original_content=original_content,
                            new_content=new_content,
                            syntax_issues=syntax_issues,
                        ),
                    )
                    verdict = VerificationResult.model_validate(verification)
                except Exception as exc:
                    return {
                        "step_id": step["id"],
                        "description": step["description"],
                        "status": "failed",
                        "failure_phase": "verification",
                        "issues": [f"verifier_output_invalid: {exc}"],
                        "changed_files": changed_files,
                        "observations": observations,
                        "models": {"executor": executor_model, "verifier": verifier_model},
                    }
                if verdict.status == "pass" and not syntax_issues:
                    diff_result = self.tools.apply_diff(out_path, new_content)
                    changed_files.append(out_path)
                    context_items.append({"tool": "apply_diff", "result": diff_result})
                    file_applied = True
                    break

                retries += 1
                feedback_issues = syntax_issues + verdict.issues
                if retries > 2:
                    return {
                        "step_id": step["id"],
                        "description": step["description"],
                        "status": "failed",
                        "issues": feedback_issues,
                        "changed_files": changed_files,
                        "observations": observations,
                        "models": {"executor": executor_model, "verifier": verifier_model},
                    }
            if not file_applied:
                return {
                    "step_id": step["id"],
                    "description": step["description"],
                    "status": "failed",
                    "issues": ["Executor did not produce an applicable file update."],
                    "changed_files": changed_files,
                    "observations": observations,
                    "models": {"executor": executor_model, "verifier": verifier_model},
                }

        step_review_issues = self._review_step_result(step=step, changed_files=changed_files)
        if step_review_issues:
            return {
                "step_id": step["id"],
                "description": step["description"],
                "status": "failed",
                "issues": step_review_issues,
                "changed_files": changed_files,
                "observations": observations,
                "models": {"executor": executor_model, "verifier": verifier_model},
            }

        return {
            "step_id": step["id"],
            "description": step["description"],
            "status": "applied",
            "changed_files": changed_files,
            "observations": observations,
            "models": {"executor": executor_model, "verifier": verifier_model},
        }

    async def _run_tool(
        self,
        tool: str,
        args: dict[str, Any],
        user_id: str | None = None,
        memory_store: UserMemoryStore | None = None,
    ) -> Any:
        try:
            return await self._dispatch_tool(tool, args, user_id=user_id, memory_store=memory_store)
        except CommercialFallbackRequiredError:
            raise
        except Exception as exc:
            # The harness catches tool failures as tool-call errors and feeds
            # them back to the model — it never surfaces raw exceptions.
            # (Anthropic managed-agents: decoupled sandbox; if the container
            # dies the harness returns the failure as a tool result.)
            log.warning("tool %r failed: %s", tool, exc)
            return f"[tool error: {exc}]"

    async def _dispatch_tool(
        self,
        tool: str,
        args: dict[str, Any],
        user_id: str | None = None,
        memory_store: UserMemoryStore | None = None,
    ) -> Any:
        if tool == "read_file":
            return self.tools.read_file(str(args.get("path", "")))
        if tool == "head_file":
            # JIT retrieval: read only the first N lines so the context window
            # stays lean during the inspection phase.
            return self.tools.head_file(str(args.get("path", "")), int(args.get("lines", 50)))
        if tool == "file_index":
            # Lightweight index tier: always-loaded, ~150 chars per entry.
            return self.tools.file_index(str(args.get("path", ".")), int(args.get("max_entries", 100)))
        if tool == "list_files":
            return self.tools.list_files(str(args.get("path", ".")), int(args.get("limit", 200)))
        if tool == "search_code":
            return self.tools.search_code(str(args.get("query", "")), int(args.get("limit", 20)))
        if tool == "recall_memory":
            if not memory_store or not user_id:
                return "(memory not available)"
            return self.tools.recall_memory(str(args.get("key", "")), user_id=user_id, memory_store=memory_store)
        if tool == "save_memory":
            if not memory_store or not user_id:
                return "(memory not available)"
            return self.tools.save_memory(str(args.get("key", "")), str(args.get("value", "")), user_id=user_id, memory_store=memory_store)
        
        # GitHub Tools
        if tool == "github_read_repo_file":
            return await self.github.read_repo_file(
                repo_name=str(args.get("repo_name", "")),
                path=str(args.get("path", "")),
                branch=str(args.get("branch", "main"))
            )
        if tool == "github_create_branch":
            return await self.github.create_branch(
                repo_name=str(args.get("repo_name", "")),
                branch_name=str(args.get("branch_name", "")),
                base_branch=str(args.get("base_branch", "main"))
            )
        if tool == "github_commit_changes":
            return await self.github.commit_changes(
                repo_name=str(args.get("repo_name", "")),
                branch_name=str(args.get("branch_name", "")),
                message=str(args.get("message", "agent commit")),
                path=str(args.get("path", "")),
                content=str(args.get("content", ""))
            )
        if tool == "github_open_pull_request":
            return await self.github.open_pull_request(
                repo_name=str(args.get("repo_name", "")),
                title=str(args.get("title", "Pull Request from AI Agent")),
                head=str(args.get("head", "")),
                base=str(args.get("base", "main")),
                body=str(args.get("body", ""))
            )
        if tool == "github_list_repos":
            return await self.github.list_repos()
        if tool == "github_list_branches":
            return await self.github.list_branches(
                repo_name=str(args.get("repo_name", ""))
            )

        if tool == "spawn_subagent":
            return await self._spawn_subagent(
                instruction=str(args.get("instruction", "")),
                requested_model=args.get("model") or None,
                max_steps=int(args.get("max_steps", 5)),
                user_id=user_id,
                memory_store=memory_store,
            )

        raise ValueError(f"Unsupported tool: {tool}")

    # ------------------------------------------------------------------
    # Judge gate  (.claude/agents/judge.md)
    # ------------------------------------------------------------------

    async def _run_judge(
        self,
        *,
        plan: AgentPlan,
        step_results: list[dict[str, Any]],
        requested_model: str | None,
        session_id: str | None,
    ) -> dict[str, Any]:
        """Lightweight Judge agent: holistic review of completed work.

        Produces a verdict (APPROVED / APPROVED_WITH_CONDITIONS / BLOCKED) mirroring
        the .claude/agents/judge.md spec.  We use a single LLM call with the verifier
        model rather than a full council-review run.
        """
        applied = [s for s in step_results if s.get("status") == "applied"]
        failed  = [s for s in step_results if s.get("status") == "failed"]
        all_files = sorted({f for s in applied for f in s.get("changed_files", [])})

        if not applied and not failed:
            # Nothing happened — no judgement needed
            return {"verdict": "APPROVED", "notes": "No changes were made."}

        judge_model = requested_model or DEFAULT_VERIFIER_MODEL
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Judge agent. Perform a release-readiness check on the completed work.\n\n"
                    "Return ONLY JSON:\n"
                    "{\n"
                    '  "verdict": "APPROVED | APPROVED_WITH_CONDITIONS | BLOCKED",\n'
                    '  "security": "PASS | WARN | FAIL",\n'
                    '  "correctness": "PASS | WARN | FAIL",\n'
                    '  "notes": "brief explanation"\n'
                    "}\n\n"
                    "Verdict rules:\n"
                    "- BLOCKED if: any applied file contains a hardcoded secret, a broken import, "
                    "or a step explicitly failed on a risky module.\n"
                    "- APPROVED_WITH_CONDITIONS if: warnings exist but nothing is blocking.\n"
                    "- APPROVED if: all checks pass."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {plan.goal}\n"
                    f"Steps applied: {len(applied)}/{len(plan.steps)}\n"
                    f"Steps failed: {len(failed)}\n"
                    f"Files changed: {all_files}\n"
                    f"Plan risks: {plan.risks}\n"
                    f"Requires risky review: {plan.requires_risky_review}\n"
                    f"Failed steps: {[s.get('description') for s in failed]}"
                ),
            },
        ]
        _VALID_VERDICTS = {"APPROVED", "APPROVED_WITH_CONDITIONS", "BLOCKED"}
        try:
            raw = await self._chat_json(judge_model, messages)
            verdict = raw.get("verdict", "")
            if verdict not in _VALID_VERDICTS:
                log.warning(
                    "Judge returned invalid verdict %r for session %s; treating as BLOCKED",
                    verdict, session_id,
                )
                raw["verdict"] = "BLOCKED"
                raw.setdefault("notes", f"Verdict {verdict!r} is not a recognised value.")
            if raw["verdict"] == "BLOCKED":
                log.warning("Judge BLOCKED session %s: %s", session_id, raw.get("notes", ""))
            self._log_event(session_id, "assistant_message", {"judge": raw})
            return raw
        except Exception as exc:
            log.warning("Judge call failed; defaulting to BLOCKED: %s", exc)
            fallback = {
                "verdict": "BLOCKED",
                "security": "WARN",
                "correctness": "WARN",
                "notes": f"Judge unavailable: {exc}",
                "failure_phase": "judge",
            }
            self._log_event(session_id, "assistant_message", {"judge": fallback})
            return fallback

    # ------------------------------------------------------------------
    # State checkpointing  (.claude/state/)
    # ------------------------------------------------------------------

    def _write_checkpoint(self, session_id: str | None, plan: AgentPlan) -> None:
        """Persist the current plan to .claude/state/agent-state-{session_id}.json.

        Mirrors the planner.md spec: state is written before each handoff so
        sessions are resumable via scripts/ai_runner.py resume.  Each session
        gets its own file so concurrent sessions don't overwrite each other.
        """
        state_dir = self.tools.root / ".claude" / "state"
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            state = {
                "session_id": session_id or "unknown",
                "status": "running",
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "goal": plan.goal,
                "step_count": len(plan.steps),
                "risks": plan.risks,
                "requires_risky_review": plan.requires_risky_review,
            }
            # Sanitize the session_id to produce a safe filename component.
            safe_sid = re.sub(r"[^A-Za-z0-9_\-]", "_", session_id or "unknown")
            state_file = state_dir / f"agent-state-{safe_sid}.json"
            state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as exc:
            log.debug("Checkpoint write failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # Subagent delegation
    # ------------------------------------------------------------------

    async def _spawn_subagent(
        self,
        *,
        instruction: str,
        requested_model: str | None,
        max_steps: int,
        user_id: str | None = None,
        memory_store: UserMemoryStore | None = None,
    ) -> dict[str, Any]:
        """Run a child AgentRunner for a self-contained subtask and return its condensed result."""
        if not instruction.strip():
            return {"error": "spawn_subagent: instruction is empty"}
        child = AgentRunner(
            ollama_base=self.ollama_base,
            workspace_root=self.tools.root,
            provider_headers=self.provider_headers,
            provider_chain=self.provider_chain,
            allow_commercial_fallback=self.allow_commercial_fallback,
            provider_temperature=self.provider_temperature,
            github_token=self.github.token if hasattr(self.github, "token") else None,
            email=self.email,
            department=self.department,
            key_id=self.key_id,
        )
        result = await child.run(
            instruction=instruction,
            history=[],
            requested_model=requested_model,
            auto_commit=False,
            max_steps=max_steps,
            user_id=user_id,
            memory_store=memory_store,
        )
        return ContextManager.condense_step_result(result)

    # ------------------------------------------------------------------
    # Auto-parallelization
    # ------------------------------------------------------------------

    @staticmethod
    def _steps_are_independent(steps: list[Any]) -> bool:
        """Return True when no file appears in more than one step (safe to parallelize)."""
        seen: set[str] = set()
        for step in steps:
            files = list(step.files) if hasattr(step, "files") else step.get("files") or []
            for f in files:
                if f in seen:
                    return False
                seen.add(f)
        return True

    async def _maybe_run_parallel(
        self,
        *,
        plan: AgentPlan,
        instruction: str,
        requested_model: str | None,
        max_steps: int,
        auto_commit: bool,
        user_id: str | None,
        memory_store: UserMemoryStore | None,
        session_id: str | None,
        department: str | None,
        key_id: str | None,
    ) -> dict[str, Any] | None:
        """If plan steps are independent, run them concurrently via MultiAgentSwarm.

        Returns a result dict (same shape as AgentRunner.run) when parallelism was
        applied, or None to signal the caller should fall back to the sequential loop.
        """
        from agent.coordinator import AgentCoordinator, WorkerSpec

        _PARALLEL_THRESHOLD = 3
        if len(plan.steps) < _PARALLEL_THRESHOLD or not self._steps_are_independent(plan.steps):
            return None

        log.info(
            "agent: %d independent steps detected — switching to MultiAgentSwarm",
            len(plan.steps),
        )
        self._log_event(session_id, "step_start", {"parallel_steps": len(plan.steps), "mode": "swarm"})

        coordinator = AgentCoordinator(
            ollama_base=self.ollama_base,
            workspace_root=str(self.tools.root),
            github_token=self.github.token if hasattr(self.github, "token") else None,
        )
        worker_specs = [
            WorkerSpec(
                worker_id=f"step-{step.id}",
                instruction=f"Goal: {plan.goal}\n\nStep: {step.description}\nFiles: {', '.join(step.files) or '(determine from context)'}",
                model=requested_model,
                max_steps=max(2, max_steps // len(plan.steps)),
            )
            for step in plan.steps[:max_steps]
        ]
        coord_result = await coordinator.run(
            plan.goal,
            worker_specs,
            max_concurrent=min(len(worker_specs), 4),
            email=user_id,
            department=department,
            key_id=key_id,
        )

        # Flatten worker results into the standard run() return shape
        all_steps: list[dict[str, Any]] = []
        all_commits: list[str] = []
        for worker in coord_result.workers:
            inner = worker.get("result") or {}
            all_steps.extend(inner.get("steps", []))
            all_commits.extend(inner.get("commits", []))

        summary = coord_result.summary
        self._log_event(session_id, "assistant_message", {"summary": summary, "mode": "swarm"})
        return {
            "goal": plan.goal,
            "plan": plan.model_dump(),
            "steps": all_steps,
            "commits": all_commits,
            "summary": summary,
            "report": summary,
        }

    # ------------------------------------------------------------------
    # Event log helpers  (stateless harness / durable session log)
    # ------------------------------------------------------------------

    def _log_event(self, session_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        """Append an event to the durable session log if a store is wired in."""
        if session_id and self._session_store:
            try:
                self._session_store.append_event(session_id, event_type, payload)
            except Exception as exc:
                log.debug("event log write failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # Context compaction
    # ------------------------------------------------------------------

    async def _compact_history(
        self,
        history: list[dict[str, Any]],
        requested_model: str | None,
        session_id: str | None,
    ) -> list[dict[str, Any]]:
        """Summarise a long history and compact it.

        Asks the planner model to write a concise summary, then replaces the
        old messages with that summary + the most recent context.
        """
        try:
            summary_text = await self._chat_text(
                requested_model or DEFAULT_PLANNER_MODEL,
                build_compaction_prompt(history),
            )
            self._log_event(
                session_id, "compaction",
                {"original_length": len(history), "summary_length": len(summary_text)},
            )
            return self.ctx.compact_history(history, compaction_summary=summary_text)
        except CommercialFallbackRequiredError:
            raise
        except Exception as exc:
            log.warning("context compaction failed (continuing uncompacted): %s", exc)
            return history

    async def _chat_text(self, model: str, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if self.provider_temperature is not None:
            payload["temperature"] = self.provider_temperature
        start = time.perf_counter()
        # Detect provider type from URL — Nvidia NIM and other cloud APIs are
        # openai-compatible; local Ollama uses the ollama protocol.
        _is_ollama = (
            "11434" in self.ollama_base
            or "ollama" in self.ollama_base
            or "localhost" in self.ollama_base
            or "127.0.0.1" in self.ollama_base
        )
        # Only inject the NVIDIA api_key when there are no provider_headers carrying
        # auth already (e.g. DeepSeek / Anthropic pass their key via headers; adding
        # the NVIDIA key on top would clobber the Authorization header they set).
        _has_auth_headers = bool(self.provider_headers)
        _nvidia_key = (
            os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey") or None
        ) if not _is_ollama and not _has_auth_headers else None
        primary = ProviderConfig(
            provider_id="agent-primary",
            type="ollama" if _is_ollama else "openai-compatible",
            base_url=self.ollama_base,
            api_key=_nvidia_key,
            headers=dict(self.provider_headers),
            default_model=model,
            priority=0,
        )
        router = ProviderRouter([primary, *self.provider_chain]) if self.provider_chain else ProviderRouter.from_env(primary_provider=primary)
        result = await router.chat_completion(
            payload,
            allow_commercial_fallback=self.allow_commercial_fallback,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        data = result.response.json()
        out_text = data["choices"][0]["message"]["content"]
        
        # Emit Langfuse observation
        if self.email:
            usage = data.get("usage", {})
            pt = int(usage.get("prompt_tokens") or 0)
            ct = int(usage.get("completion_tokens") or 0)
            try:
                from langfuse_obs import emit_chat_observation
                import asyncio
                await asyncio.to_thread(
                    emit_chat_observation,
                    email=self.email,
                    department=self.department or "agent",
                    key_id=self.key_id,
                    model=model,
                    messages=messages,
                    output_text=out_text,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    latency_ms=duration_ms,
                    task_name="agent-task",
                )
            except CommercialFallbackRequiredError:
                raise
            except Exception as exc:
                log.debug("Agent Langfuse emit failed: %s", exc)

        return out_text

    async def _chat_json(self, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        raw = await self._chat_text(model, messages)
        for _ in range(3):
            try:
                parsed = self._extract_json(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("Model did not return a JSON object")
                return parsed
            except CommercialFallbackRequiredError:
                raise
            except Exception:
                raw = await self._chat_text(
                    model,
                    [
                        {"role": "system", "content": "Return only a valid JSON object. No prose. No code fences."},
                        {"role": "user", "content": raw},
                    ],
                )
        parsed = self._extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Model did not return a JSON object")
        return parsed

    def _extract_json(self, raw: str) -> Any:
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.S)
            if not match:
                raise
            return json.loads(match.group(0))

    def _parse_execution_response(self, raw: str, fallback_path: str) -> tuple[str, str] | None:
        match = re.search(
            r"FILE:\s*(?P<path>[^\r\n]+)\s*ACTION:\s*(?P<action>create|replace|append)\s*```[^\n]*\n(?P<content>.*?)\n```",
            raw.strip(),
            re.S,
        )
        if not match:
            return None
        path = match.group("path").strip() or fallback_path
        action = match.group("action").strip()
        content = match.group("content")
        if action == "append":
            existing = self._safe_read(path)
            content = (existing + ("\n" if existing else "") + content).rstrip("\n") + "\n"
        return path, content

    def _clean_generated_file_content(self, content: str) -> str:
        cleaned = content.replace("\r\n", "\n")
        # Remove language identifier if it leaked into the content block
        if cleaned.startswith("python\n") or cleaned.startswith("javascript\n") or cleaned.startswith("typescript\n") or cleaned.startswith("html\n") or cleaned.startswith("css\n") or cleaned.startswith("json\n") or cleaned.startswith("yaml\n") or cleaned.startswith("sh\n") or cleaned.startswith("bash\n") or cleaned.startswith("text\n"):
            cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.strip("\n")
        if cleaned and not cleaned.endswith("\n"):
            cleaned += "\n"
        return cleaned

    def _local_syntax_check(self, path: str, content: str) -> list[str]:
        issues: list[str] = []
        if path.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as exc:
                issues.append(f"Python syntax error: {exc.msg} at line {exc.lineno}")
        return issues

    def _local_safety_check(self, path: str, content: str) -> list[str]:
        issues: list[str] = []
        if not path.endswith(".py"):
            return issues

        lowered = content.lower()
        if "jwt" in lowered or "oauth2" in lowered or "authentication" in lowered:
            if re.search(r"SECRET_KEY\s*=\s*[\"'][^\"']+[\"']", content):
                issues.append("Auth/JWT code hardcodes SECRET_KEY instead of reading configuration from the environment.")
            if "fake_users_db" in lowered:
                issues.append("Auth/JWT code introduces fake in-memory users, which is not a safe default for real authentication work.")
        return issues

    def _review_step_result(self, *, step: dict[str, Any], changed_files: list[str]) -> list[str]:
        issues: list[str] = []
        desc = str(step.get("description", "")).lower()
        changed_set = {path.replace("\\", "/").lower() for path in changed_files}

        if "across this module" in desc and len(changed_files) < 2:
            issues.append("Module-wide change touched too few files to be complete.")

        if "shared logger utility" in desc:
            has_logger_utility = any(
                path.endswith(("logger.py", "logging_utils.py", "logger_util.py"))
                for path in changed_set
            )
            if not has_logger_utility:
                issues.append("Shared logger utility was requested but no logger utility file was created or updated.")
            if len(changed_files) < 2:
                issues.append("Logging task changed too few files to count as a module-wide update.")

        if "jwt" in desc or "authentication" in desc:
            if not any(path.endswith(("requirements.txt", "pyproject.toml", "poetry.lock")) for path in changed_set):
                issues.append("Auth task did not update dependency metadata for JWT/auth packages.")

            hardcoded_secret = False
            for path in changed_files:
                content = self._safe_read(path)
                if re.search(r"SECRET_KEY\s*=\s*[\"'][^\"']+[\"']", content):
                    hardcoded_secret = True
                    break
            if hardcoded_secret:
                issues.append("Auth task still contains a hardcoded SECRET_KEY.")

        return issues

    def _safe_read(self, path: str) -> str:
        try:
            return self.tools.read_file(path, max_chars=200000)
        except Exception:
            return ""

    def _commit_step(self, description: str, changed_files: list[str]) -> str | None:
        # Strip control characters (newlines, CR, tabs) so multi-line step
        # descriptions don't create malformed git commit messages.
        safe_description = " ".join(description.splitlines()).strip()[:200] or "agent change"
        try:
            subprocess.run(["git", "add", *changed_files], cwd=self.tools.root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", f"agent: {safe_description}"],
                cwd=self.tools.root,
                check=True,
                capture_output=True,
                text=True,
            )
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.tools.root,
                check=True,
                capture_output=True,
                text=True,
            )
            return proc.stdout.strip()
        except FileNotFoundError:
            # git binary not available in this environment — skip auto-commit silently.
            log.warning("Auto-commit skipped: git not found in PATH")
            return None
        except subprocess.CalledProcessError as exc:
            log.warning("Auto-commit failed: %s", exc.stderr.strip() if exc.stderr else exc)
            return None

    async def _synthesize_answer(
        self,
        goal: str,
        step: dict[str, Any],
        observations: list[dict[str, Any]],
        model: str,
    ) -> str:
        """Synthesize a human-readable answer for analyze/github steps from tool observations."""
        obs_text = json.dumps(observations, indent=2)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Based on the tool call results provided, "
                    "give a clear, comprehensive answer. Be specific and include relevant details."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {goal}\n"
                    f"Step: {step['description']}\n\n"
                    f"Tool results gathered:\n{obs_text}\n\n"
                    "Provide a complete, well-structured answer based on this information."
                ),
            },
        ]
        try:
            return await self._chat_text(model, messages)
        except Exception as exc:
            log.warning("Answer synthesis failed: %s", exc)
            # Fall back to the finish reason if the synthesis LLM call fails
            for obs in reversed(observations):
                if obs.get("tool") == "finish":
                    return str(obs.get("result", ""))
            return ""

    def _build_summary(self, goal: str, step_results: list[dict[str, Any]], commits: list[str]) -> str:
        applied = sum(1 for s in step_results if s.get("status") == "applied")
        failed  = sum(1 for s in step_results if s.get("status") == "failed")
        files_changed = sum(len(s.get("changed_files", [])) for s in step_results)

        # Surface synthesized answers from analyze/github steps when present.
        answers = [s.get("answer", "") for s in step_results if s.get("answer")]

        meta_parts = [f"Goal: {goal}", f"Steps: {applied}/{len(step_results)}"]
        if files_changed:
            meta_parts.append(f"Files modified: {files_changed}")
        if failed:
            meta_parts.append(f"Failed: {failed}")
        if commits:
            meta_parts.append(f"Commits: {len(commits)}")
        meta = " | ".join(meta_parts)

        if answers:
            return "\n\n".join(answers) + f"\n\n---\n_{meta}_"
        return meta

    def _build_rich_report(self, goal: str, step_results: list[dict[str, Any]], commits: list[str]) -> str:
        """Build a detailed markdown execution report for the task discussion comment."""
        lines: list[str] = [f"**Goal:** {goal}", ""]

        all_changed: list[str] = []
        for step in step_results:
            status = step.get("status", "unknown")
            icon = "✅" if status == "applied" else "❌" if status == "failed" else "⏭️"
            desc = step.get("description", "")
            lines.append(f"{icon} **Step {step.get('step_id', '?')}:** {desc}")

            changed = step.get("changed_files", [])
            if changed:
                all_changed.extend(changed)
                lines.append("   Files: " + ", ".join(f"`{f}`" for f in changed))
            elif status == "applied":
                answer = step.get("answer", "")
                if answer:
                    lines.append(f"   💬 {answer[:200]}")
                else:
                    lines.append("   *(analysis — no files modified)*")

            if status == "failed":
                for issue in step.get("issues", []):
                    lines.append(f"   ⚠️ {issue}")

            lines.append("")

        unique_files = sorted(set(all_changed))
        if unique_files:
            lines.append("**Files modified:**")
            for f in unique_files:
                lines.append(f"- `{f}`")
            lines.append("")
        else:
            lines.append("**No files were modified.** All steps were analysis only.")
            lines.append("")

        if commits:
            lines.append(f"**Auto-committed:** {len(commits)} commit(s)")
            lines.append("")

        applied_count = sum(1 for s in step_results if s.get("status") == "applied")
        lines.append(f"**Result:** {applied_count}/{len(step_results)} steps completed, {len(unique_files)} file(s) changed.")
        return "\n".join(lines)

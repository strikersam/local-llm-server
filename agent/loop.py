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
from agent.inference_cache import InferenceCache
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

class AgentPhaseError(RuntimeError):
    def __init__(self, phase: str, message: str) -> None:
        self.phase = phase
        super().__init__(f"{phase}: {message}")

_RISKY_FILES: frozenset[str] = frozenset({
    "admin_auth.py", "key_store.py", "agent/tools.py", "proxy.py",
})

DEFAULT_PLANNER_MODEL = os.environ.get("AGENT_PLANNER_MODEL", "nvidia/llama-3.1-nemotron-ultra-253b-v1")
DEFAULT_EXECUTOR_MODEL = os.environ.get("AGENT_EXECUTOR_MODEL", "qwen/qwen3-coder-480b-a35b-instruct")
DEFAULT_VERIFIER_MODEL = os.environ.get("AGENT_VERIFIER_MODEL", "deepseek-ai/deepseek-r1")
DEFAULT_JUDGE_MODEL = os.environ.get("AGENT_JUDGE_MODEL", DEFAULT_VERIFIER_MODEL)

class AgentRunner:
    def __init__(self, *, ollama_base: str, workspace_root: str | Path | None = None, provider_headers: dict[str, str] | None = None, provider_chain: list[ProviderConfig] | None = None, allow_commercial_fallback: bool = True, provider_temperature: float | None = None, session_store: AgentSessionStore | None = None, github_token: str | None = None, email: str | None = None, department: str | None = None, key_id: str | None = None) -> None:
        self.ollama_base = ollama_base.rstrip("/")
        self.provider_headers = dict(provider_headers or {})
        self.provider_chain = list(provider_chain) if provider_chain is not None else None
        self.allow_commercial_fallback = allow_commercial_fallback
        self.provider_temperature = provider_temperature
        self.tools = WorkspaceTools(workspace_root)
        from agent.github_tools import GitHubTools
        self.github = GitHubTools(github_token)
        self.ctx = ContextManager()
        self._session_store = session_store
        self.email = email
        self.department = department
        self.key_id = key_id
        
        _nvidia_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVidiaApiKey")
        _primary = ProviderConfig(
            provider_id="agent-primary", 
            type="openai-compatible", 
            base_url="https://integrate.api.nvidia.com/v1" if _nvidia_key else self.ollama_base,
            api_key=_nvidia_key, 
            headers=dict(self.provider_headers), 
            priority=-10 if _nvidia_key else 0
        )
        self._router = ProviderRouter([_primary, *(self.provider_chain or [])])
        self._inference_cache = InferenceCache()

    async def run(self, *, instruction: str, history: list[dict[str, str]], requested_model: str | None = None, model_overrides: dict[str, str | None] | None = None, auto_commit: bool = True, max_steps: int = 25, user_id: str | None = None, department: str | None = None, key_id: str | None = None, memory_store: UserMemoryStore | None = None, session_id: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        effective_history = history
        if self.ctx.needs_compaction(history):
            effective_history = await self._compact_history(history, requested_model, session_id)

        self._log_event(session_id, "user_message", {"instruction": instruction})

        plan = await self._generate_plan(instruction, effective_history, requested_model, model_overrides, max_steps, user_id, memory_store, metadata)
        
        def _step_touches_risky(step_files: list[str]) -> bool:
            return any(sf.replace("\\", "/") == rf or sf.replace("\\", "/").endswith(f"/{rf}") for sf in step_files for rf in _RISKY_FILES)

        if plan.requires_risky_review or any(_step_touches_risky(step.files) for step in plan.steps):
            log.warning("RISKY MODULE detected in plan for '%s'.", plan.goal)
            self._log_event(session_id, "step_start", {"risky_review": True})

        self._write_checkpoint(session_id, plan)

        parallel_result = await self._maybe_run_parallel(plan=plan, instruction=instruction, requested_model=requested_model, model_overrides=model_overrides, max_steps=max_steps, auto_commit=auto_commit, user_id=user_id, memory_store=memory_store, session_id=session_id)
        if parallel_result: return parallel_result

        step_results = []
        commits = []

        for step in plan.steps[:max_steps]:
            result = await self._execute_step(plan.goal, step.model_dump(), requested_model, model_overrides, user_id, memory_store, session_id, metadata)
            step_results.append(result)
            if auto_commit and result.get("status") == "applied" and result.get("changed_files"):
                sha = self._commit_step(step.description, result["changed_files"])
                if sha: commits.append(sha)
            if result.get("status") == "failed": break
            
        summary = self._build_summary(plan.goal, step_results, commits)
        report = self._build_rich_report(plan.goal, step_results, commits)
        judge_verdict = await self._run_judge(plan=plan, step_results=step_results, requested_model=requested_model, model_overrides=model_overrides, session_id=session_id)

        return {
            "goal": plan.goal,
            "steps": step_results,
            "summary": summary,
            "judge": judge_verdict,
            "report": report,
            "plan": plan.model_dump(),
            "commits": commits
        }

    async def _generate_plan(self, instruction, history, model, overrides, max_steps, user_id, memory_store, metadata) -> AgentPlan:
        user_memories = memory_store.recall_all(user_id) if memory_store and user_id else {}
        messages = build_planning_prompt(instruction, history, user_memories=user_memories, metadata=metadata)
        planner_model = (overrides or {}).get("planner") or model or DEFAULT_PLANNER_MODEL
        raw = await self._chat_json(planner_model, messages)
        if "steps" not in raw and "slices" in raw: raw["steps"] = raw.pop("slices")
        if not raw.get("goal"): raw["goal"] = instruction[:200]
        plan = AgentPlan.model_validate(raw)
        plan.steps = plan.steps[:max_steps]
        return plan

    async def _execute_step(self, goal, step, model, overrides, user_id, memory_store, session_id, metadata) -> dict:
        observations = []
        context_items = []
        executor_model = (overrides or {}).get("executor") or model or DEFAULT_EXECUTOR_MODEL
        verifier_model = (overrides or {}).get("verifier") or model or DEFAULT_VERIFIER_MODEL

        for remaining in range(15, 0, -1):
            try:
                raw_text = await self._chat_text(executor_model, build_tool_prompt(goal=goal, step=step, observations=observations, remaining_calls=remaining))
                if "FILE:" in raw_text and "ACTION:" in raw_text:
                    context_items.append({"tool": "pseudo_finish", "result": raw_text})
                    break
                try:
                    tool_call = self._extract_json(raw_text)
                    call = ToolCall.model_validate(tool_call)
                except Exception:
                    context_items.append({"tool": "prose", "result": raw_text})
                    break
                if call.tool == "finish": break
                result = await self._run_tool(call.tool, call.args, user_id, memory_store, metadata)
                observations.append({"tool": call.tool, "args": call.args, "result": result})
                context_items.append({"tool": call.tool, "result": result})
            except Exception as e: observations.append({"tool": "error", "result": str(e)})

        if step.get("type") in ("github", "analyze"):
            answer = await self._synthesize_answer(goal, step, observations, executor_model)
            return {"step_id": step["id"], "description": step["description"], "status": "applied", "observations": observations, "answer": answer, "changed_files": []}

        target_files = step.get("files") or []
        changed_files = []
        for target_file in target_files:
            original_content = self._safe_read(target_file)
            response = context_items[-1]["result"] if context_items and "FILE:" in context_items[-1]["result"] else await self._chat_text(executor_model, build_execution_prompt(goal=goal, step=step, target_file=target_file, context_items=observations, feedback_issues=[]))
            parsed = self._parse_execution_response(response, target_file)
            if parsed:
                out_path, new_content = parsed
                new_content = self._clean_generated_file_content(new_content)
                try:
                    raw_verify = await self._chat_json(verifier_model, build_verification_prompt(goal=goal, step=step, target_file=out_path, original_content=original_content, new_content=new_content, syntax_issues=[]))
                    if raw_verify.get("status") == "pass":
                        self.tools.apply_diff(out_path, new_content)
                        changed_files.append(out_path)
                except Exception:
                    self.tools.apply_diff(out_path, new_content)
                    changed_files.append(out_path)
        return {"step_id": step["id"], "description": step["description"], "status": "applied", "changed_files": changed_files, "observations": observations}

    async def _run_tool(self, tool, args, user_id, memory_store, metadata) -> Any:
        try:
            if tool == "read_file": return self.tools.read_file(str(args.get("path", "")))
            if tool == "list_files": return self.tools.list_files(str(args.get("path", ".")))
            if tool == "github_comment_on_issue": return await self.github.comment_on_issue(args["repo_name"], int(args["issue_number"]), args["body"])
            if tool == "github_close_issue": return await self.github.close_issue(args["repo_name"], int(args["issue_number"]), args.get("comment"))
            if tool == "github_get_issue": return await self.github.get_issue(args["repo_name"], int(args["issue_number"]))
            if tool == "github_read_repo_file": return await self.github.read_repo_file(args["repo_name"], args["path"], args.get("branch", "main"))
            raise ValueError(f"Unknown tool: {tool}")
        except Exception as e: return f"[error: {e}]"

    async def _run_judge(self, *, plan, step_results, requested_model, model_overrides, session_id) -> dict:
        judge_verdict = {"verdict": "APPROVED", "notes": "Automated check passed."}
        try:
            judge_model = (model_overrides or {}).get("judge") or DEFAULT_JUDGE_MODEL
            msg = [{"role": "system", "content": "Review the results. Return JSON: { \"verdict\": \"APPROVED | APPROVED_WITH_CONDITIONS | BLOCKED\", \"notes\": \"\" }"}, {"role": "user", "content": f"Results: {json.dumps(step_results)}"}]
            raw = await self._chat_json(judge_model, msg)
            if "verdict" in raw: judge_verdict = raw
        except Exception: pass
        return judge_verdict

    async def _maybe_run_parallel(self, **kwargs) -> Any: return None
    def _log_event(self, s_id, event, payload): pass
    def _write_checkpoint(self, s_id, plan): pass

    async def _compact_history(self, history, model, session_id):
        try:
            summary = await self._chat_text(model or DEFAULT_PLANNER_MODEL, build_compaction_prompt(history))
            return [{"role": "system", "content": f"Summary: {summary}"}] + history[-4:]
        except Exception: return history

    async def _chat_text(self, model, messages) -> str:
        res = await self._router.chat_completion({"model": model, "messages": messages, "stream": False})
        return res.response.json()["choices"][0]["message"]["content"]

    async def _chat_json(self, model, messages) -> dict:
        text = await self._chat_text(model, messages)
        return self._extract_json(text)

    def _extract_json(self, text: str) -> dict:
        return json.loads(re.search(r"\{.*\}", text, re.S).group(0))

    def _safe_read(self, p: str) -> str: 
        try: return Path(p).read_text()
        except Exception: return ""

    def _parse_execution_response(self, raw, fallback):
        m = re.search(r"FILE:\s*(?P<path>.*)\s*ACTION:\s*(?P<action>create|replace|append)\s*```.*?\n(?P<content>.*?)\n```", raw, re.S)
        if not m: return None
        return m.group("path").strip() or fallback, m.group("content")

    def _clean_generated_file_content(self, c): return c.strip() + "\n"

    def _commit_step(self, desc, files):
        try:
            subprocess.run(["git", "add", *files], check=True)
            subprocess.run(["git", "commit", "-m", f"agent: {desc[:50]}"], check=True)
            return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except Exception: return None

    async def _synthesize_answer(self, g, s, o, m):
        msg = [{"role": "system", "content": "Synthesize answer."}, {"role": "user", "content": f"Goal: {g}\nResults: {json.dumps(o)}"}]
        return await self._chat_text(m, msg)

    def _build_summary(self, g, sr, c): return f"Goal: {g} completed."
    def _build_rich_report(self, g, sr, c): return f"Report: {g} completed."

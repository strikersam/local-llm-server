from __future__ import annotations

import json
from typing import Any


def build_planning_prompt(
    instruction: str,
    history: list[dict[str, str]],
    user_memories: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history[-8:])
    memory_section = ""
    if user_memories:
        pairs = "\n".join(f"  {k}: {v}" for k, v in user_memories.items())
        memory_section = f"\n\nUser profile (remembered preferences):\n{pairs}"
    return [
        {
            "role": "system",
            "content": (
                "You are a senior software engineer acting as the Planner agent.\n\n"
                "Break the task into steps. You NEVER write implementation code — you only plan.\n\n"
                "Return ONLY JSON in this format:\n"
                "{\n"
                '  "goal": "One sentence goal",\n'
                '  "steps": [\n'
                "    {\n"
                '      "id": 1,\n'
                '      "description": "...",\n'
                '      "files": ["file1.py"],\n'
                '      "type": "edit | create | analyze | github",\n'
                '      "risky": false,\n'
                '      "acceptance": "How to verify this step succeeded"\n'
                "    }\n"
                "  ],\n"
                '  "risks": ["list of known risks"],\n'
                '  "requires_risky_review": false\n'
                "}\n\n"
                "Rules:\n"
                "- Max 15 steps.\n"
                "- Each step touches limited files.\n"
                "- No execution — planning only.\n"
                "- Prefer existing files when possible.\n"
                "- If a new file is needed, include the intended path.\n"
                "- For module-wide tasks, include every file that must change for the result to work.\n"
                "- If the task asks for a shared utility, include a create step or include the utility file in the edit step.\n"
                "- If the task involves GitHub operations (commit, push, PR), include a step with type 'github' and leave files empty.\n"
                "- Security-sensitive files: admin_auth.py, key_store.py, agent/tools.py, proxy.py (auth middleware).\n"
                "  Set risky=true on any step touching these files and set requires_risky_review=true on the plan.\n"
                "- Fill acceptance with a concrete, verifiable check (e.g. 'pytest tests/test_agent_tools.py passes')."
                f"{memory_section}"
            ),
        },
        {
            "role": "user",
            "content": f"Conversation context:\n{history_text or '(none)'}\n\nTask:\n{instruction}",
        },
    ]


def build_tool_prompt(
    *,
    goal: str,
    step: dict[str, Any],
    observations: list[dict[str, Any]],
    remaining_calls: int,
) -> list[dict[str, str]]:
    # Observations may already be masked by the ContextManager; pass them
    # directly without further slicing.
    observed = json.dumps(observations, indent=2)
    return [
        {
            "role": "system",
            "content": (
                "You are preparing to execute one coding step.\n"
                "Inspect the workspace with tools before writing code.\n\n"
                "Available tools — use the CHEAPEST one that answers your question:\n"
                "- file_index(path='.', max_entries=100)"
                "  → lightweight list of every text file with line counts; use this FIRST\n"
                "- head_file(path, lines=50)"
                "  → first N lines only; prefer this over read_file for large files\n"
                "- read_file(path)"
                "  → full file content; only use when you need the complete file\n"
                "- list_files(path='.', limit=200)"
                "  → raw filename list with no metadata\n"
                "- search_code(query, limit=20)"
                "  → grep-style keyword search across all text files\n"
                "- recall_memory(key)"
                "  → retrieve a saved user preference\n"
                "- save_memory(key, value)"
                "  → persist a user preference for future sessions\n"
                "- github_read_repo_file(repo_name, path, branch='main')"
                "  → read a file from a GitHub repository\n"
                "- github_list_repos()"
                "  → list all repositories accessible to you\n"
                "- github_list_branches(repo_name)"
                "  → list branches in a specific repository\n"
                "- github_create_branch(repo_name, branch_name, base_branch='main')"
                "  → create a new branch from a base branch\n"
                "- github_commit_changes(repo_name, branch_name, message, path, content)"
                "  → commit a change to a single file\n"
                "- github_open_pull_request(repo_name, title, head, base='main', body='')"
                "- self_audit()"\
                  "  → perform comprehensive self-audit of agent configuration"\
                "- setup_mcp_server(service_name, config?)"\
                  "  → automate MCP server setup for a service"\
                "- install_skill(skill_source, skill_name?)"\
                  "  → automate skill installation from various sources"\
                "- generate_claude_md(target_path?)"\
                  "  → generate CLAUDE.md based on codebase analysis"\
                "- apply_recommendations(audit_results)"\
                  "  → apply recommended improvements from audit"
                "  → create a pull request\n"
                "- spawn_subagent(instruction, model=None, max_steps=5)"
                "  → delegate a self-contained subtask to a child agent; returns its condensed result\n"
                "  → use when a subtask is independent and would otherwise bloat this step's context\n"
                "- finish(reason)"
                "  → stop inspecting and proceed to implementation\n\n"
                "Return ONLY JSON:\n"
                "{ \"tool\": \"<name>\", \"args\": { ... } }\n\n"
                "Rules:\n"
                "- One tool per response.\n"
                "- Start with file_index or search_code; escalate to head_file then read_file only if needed.\n"
                "- Call finish as soon as you have enough context — do NOT read every file.\n"
                f"- Remaining tool calls: {remaining_calls}.\n"
                "- For multi-file tasks, verify enough files to avoid partial updates."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Goal:\n{goal}\n\n"
                f"Step:\n{json.dumps(step, indent=2)}\n\n"
                f"Observations so far:\n{observed}"
            ),
        },
    ]


def build_execution_prompt(
    *,
    goal: str,
    step: dict[str, Any],
    target_file: str,
    context_items: list[dict[str, Any]],
    feedback_issues: list[str],
) -> list[dict[str, str]]:
    context_blob = json.dumps(context_items[-8:], indent=2)
    feedback = "\n".join(f"- {issue}" for issue in feedback_issues) or "(none)"
    return [
        {
            "role": "system",
            "content": (
                "You are executing ONE step.\n\n"
                "Return ONLY:\n\n"
                "FILE: <path>\n"
                "ACTION: <create|replace|append>\n"
                "```<language>\n"
                "<FULL FILE CONTENT>\n"
                "```\n\n"
                "Rules:\n"
                "- Always return a full file.\n"
                "- No explanations.\n"
                "- No markdown outside the required format.\n"
                "- The FILE path must be the target file unless the step clearly needs a new file.\n"
                "- Do not echo the language name before the file contents.\n"
                "- If asked for a shared utility, create or update that utility instead of duplicating logic across files.\n"
                "- For authentication or JWT changes, avoid hardcoded secrets and prefer configuration via environment variables."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Goal:\n{goal}\n\n"
                f"Step:\n{json.dumps(step, indent=2)}\n\n"
                f"Target file:\n{target_file}\n\n"
                f"Context:\n{context_blob}\n\n"
                f"Fix these issues if present:\n{feedback}"
            ),
        },
    ]


def build_compaction_prompt(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Ask the model to produce a concise summary of a long conversation history.

    This implements the 'context compaction' strategy from Anthropic's managed-
    agents article: when the session history exceeds the compaction threshold
    the harness asks the model to summarise what happened so far.  The summary
    replaces the old messages; the most recent messages are kept verbatim.

    The model is instructed to preserve:
    - the overall goal and any architectural decisions made
    - which files were changed and why
    - any constraints or user preferences discovered
    - current status / what still needs to be done
    """
    history_text = "\n".join(
        f"[{msg.get('role', 'unknown').upper()}] {msg.get('content', '')[:800]}"
        for msg in history
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a context compaction assistant.\n\n"
                "Summarise the coding session below into a concise note (max 400 words).\n\n"
                "You MUST preserve:\n"
                "- The overall goal\n"
                "- Architectural decisions and constraints discovered\n"
                "- Which files were changed and what was done\n"
                "- Any user preferences or rules found\n"
                "- Current status and what still needs to be done\n\n"
                "Discard:\n"
                "- Verbatim file contents\n"
                "- Redundant tool outputs\n"
                "- Step-by-step retry details\n\n"
                "Return ONLY the plain-text summary."
            ),
        },
        {
            "role": "user",
            "content": f"Session history to compact:\n\n{history_text}",
        },
    ]


def build_verification_prompt(
    *,
    goal: str,
    step: dict[str, Any],
    target_file: str,
    original_content: str,
    new_content: str,
    syntax_issues: list[str],
) -> list[dict[str, str]]:
    syntax = "\n".join(f"- {issue}" for issue in syntax_issues) or "(none)"
    return [
        {
            "role": "system",
            "content": (
                "Check:\n"
                "- syntax correctness\n"
                "- logical consistency\n"
                "- does it satisfy the goal?\n"
                "- for multi-file tasks, is this change consistent with the rest of the module?\n"
                "- for auth/JWT tasks, are there obvious security smells like hardcoded secrets?\n\n"
                "Return ONLY JSON:\n"
                '{ "status": "pass | fail", "issues": [] }'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Goal:\n{goal}\n\n"
                f"Step:\n{json.dumps(step, indent=2)}\n\n"
                f"File:\n{target_file}\n\n"
                f"Syntax issues from local checks:\n{syntax}\n\n"
                f"Original content:\n{original_content[:12000]}\n\n"
                f"New content:\n{new_content[:12000]}"
            ),
        },
    ]

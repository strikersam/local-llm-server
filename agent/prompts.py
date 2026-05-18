from __future__ import annotations

import json
from typing import Any


def build_planning_prompt(
    instruction: str,
    history: list[dict[str, str]],
    user_memories: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history[-8:])
    memory_section = ""
    if user_memories:
        pairs = "\n".join(f"  {k}: {v}" for k, v in user_memories.items())
        memory_section = f"\n\nUser profile (remembered preferences):\n{pairs}"
    
    metadata_section = ""
    if metadata:
        meta_json = json.dumps(metadata, indent=2)
        metadata_section = f"\n\nTask Metadata (Execute based on these parameters):\n{meta_json}"

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
                "- Max 30 steps.\n"
                "- Each step touches limited files.\n"
                "- No execution — planning only.\n"
                "- For GitHub issue tasks, include steps to comment on or close the issue using 'github' type.\n"
                "- Security-sensitive files: admin_auth.py, key_store.py, agent/tools.py, proxy.py.\n"
                "  Set risky=true on any step touching these files and set requires_risky_review=true on the plan."
                f"{memory_section}"
                f"{metadata_section}"
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
    observed = json.dumps(observations, indent=2)
    return [
        {
            "role": "system",
            "content": (
                "You are preparing to execute one coding step.\n"
                "Inspect the workspace with tools before writing code.\n\n"
                "Available tools:\n"
                "LOCAL WORKSPACE (read-only inspection):\n"
                "- get_overview(): Architecture summary, module map, and git health\n"
                "- get_context(targets, include=['source']): Pack content, metrics, or dependencies for targets\n"
                "- get_risk(targets=None, changed_files=None): Hotspot scores and impact analysis\n"
                "- get_why(target): Architectural decisions from git history for target\n"
                "- file_index(path='.', max_entries=100)\n"
                "- head_file(path, lines=50)\n"
                "- read_file(path)\n"
                "- list_files(path='.', limit=200)\n"
                "- search_code(query, limit=20)\n"
                "GITHUB API:\n"
                "- github_get_issue(repo_name, issue_number)\n"
                "- github_comment_on_issue(repo_name, issue_number, body)\n"
                "- github_close_issue(repo_name, issue_number, comment=None)\n"
                "- github_list_repos()\n"
                "- github_list_branches(repo_name)\n"
                "- github_create_branch(repo_name, branch_name, base_branch='main')\n"
                "- github_commit_changes(repo_name, branch_name, path, content, message)\n"
                "- github_open_pull_request(repo_name, title, head, base, body='')\n"
                "- github_merge_pull_request(repo_name, pull_number, merge_method='merge', commit_title=None)\n"
                "- github_read_repo_file(repo_name, path, branch='main')\n"
                "MCP CONTAINER (heavy lifting — isolated Docker container with git):\n"
                "- clone_repo(workspace_id, repo_url, branch='main'): Clone a GitHub repo into a container workspace\n"
                "- write_file(workspace_id, path, content): Write a file in the container workspace\n"
                "- run_command(workspace_id, cmd, timeout=60): Run shell command in container workspace\n"
                "- git_status(workspace_id): git status of container workspace\n"
                "- git_diff(workspace_id): git diff HEAD of container workspace\n"
                "- git_create_branch(workspace_id, branch_name): Create git branch in container\n"
                "- git_commit(workspace_id, message, paths=None): Commit changes in container\n"
                "- git_push(workspace_id, branch=None): Push branch from container to remote\n"
                "- delete_workspace(workspace_id): Remove container workspace when done\n"
                "- finish(reason)\n\n"
                "Return ONLY JSON:\n"
                '{ "tool": "<name>", "args": { ... } }\n\n'
                "Rules:\n"
                "- One tool per response.\n"
                f"- Remaining tool calls: {remaining_calls}."
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
                "```text\n"
                "<FULL FILE CONTENT>\n"
                "```\n\n"
                "Rules:\n"
                "- Always return a full file.\n"
                "- No explanations."
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
    history_text = "\n".join(f"[{msg.get('role', 'unknown').upper()}] {msg.get('content', '')[:800]}" for msg in history)
    return [
        {"role": "system", "content": "Summarise the coding session below into a concise note (max 400 words)."},
        {"role": "user", "content": f"Session history to compact:\n\n{history_text}"},
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
        {"role": "system", "content": "Check syntax and logic. Return ONLY JSON: { \"status\": \"pass | fail\", \"issues\": [] }"},
        {"role": "user", "content": f"Goal: {goal}\nStep: {json.dumps(step)}\nFile: {target_file}\nSyntax issues: {syntax}\nNew content: {new_content[:10000]}"},
    ]
from __future__ import annotations

import json
from typing import Any


def build_planning_prompt(instruction: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history[-8:])
    return [
        {
            "role": "system",
            "content": (
                "You are a senior software engineer.\n\n"
                "Break the task into steps.\n\n"
                "Return ONLY JSON in this format:\n"
                "{\n"
                '  "goal": "...",\n'
                '  "steps": [\n'
                "    {\n"
                '      "id": 1,\n'
                '      "description": "...",\n'
                '      "files": ["file1.py"],\n'
                '      "type": "edit | create | analyze"\n'
                "    }\n"
                "  ]\n"
                "}\n\n"
                "Rules:\n"
                "- Max 5 steps.\n"
                "- Each step touches limited files.\n"
                "- No execution.\n"
                "- Prefer existing files when possible.\n"
                "- If a new file is needed, include the intended path.\n"
                "- For module-wide tasks, include every file that must change for the result to work.\n"
                "- If the task asks for a shared utility, include a create step or include the utility file in the edit step."
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
    observed = json.dumps(observations[-6:], indent=2)
    return [
        {
            "role": "system",
            "content": (
                "You are preparing to execute one coding step.\n"
                "You may inspect the workspace with tools before writing code.\n\n"
                "Available tools:\n"
                "- read_file(path)\n"
                "- list_files(path='.', limit=200)\n"
                "- search_code(query, limit=20)\n"
                "- finish(reason)\n\n"
                "Return ONLY JSON:\n"
                '{ "tool": "read_file|list_files|search_code|finish", "args": { ... } }\n\n'
                "Rules:\n"
                "- Use one tool per response.\n"
                "- Prefer targeted reads.\n"
                "- Stop once you have enough context.\n"
                f"- Remaining tool calls: {remaining_calls}.\n"
                "- For multi-file tasks, inspect enough files to avoid partial updates."
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

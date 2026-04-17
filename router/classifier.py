"""Task classification from request context.

Classifies an incoming request into a task category so the router can
pick the most appropriate model. Uses lightweight regex heuristics —
no LLM call required.

Categories (in priority order):
    agent_plan       — structured planning phase of the coding agent
    agent_execute    — code-writing execution phase
    agent_verify     — verification / review phase
    tool_use         — request includes function/tool definitions
    long_context     — unusually large context (>16k estimated tokens)
    fast_response    — short, latency-sensitive interactive request
    code_debugging   — fixing bugs, errors, tracebacks
    code_review      — reviewing or analysing existing code
    data_analysis    — data science, analytics, ML/AI workloads
    code_generation  — writing new code
    reasoning        — analysis, architecture, math, explanation
    conversation     — generic chat / Q&A
"""

from __future__ import annotations

import re
from typing import Any

# ── Compiled patterns ─────────────────────────────────────────────────────────

_CODE_WRITE_RE = re.compile(
    r"\b(implement|write|create|add|generate|build|scaffold|refactor|migrate|"
    r"def |class |function|method|module|package|endpoint|api|route|handler|"
    r"import |from \w+ import)\b",
    re.IGNORECASE,
)

_CODE_DEBUG_RE = re.compile(
    r"\b(fix|debug|error|exception|traceback|bug|issue|problem|wrong|broken|"
    r"failing|crash|stacktrace|stack trace|syntax error|type error|attribute error|"
    r"undefined|not defined|cannot|can't|does not work)\b",
    re.IGNORECASE,
)

_CODE_REVIEW_RE = re.compile(
    r"\b(review|audit|check|inspect|analyze|analyse|look at|what does|explain this|"
    r"understand|code quality|best practice|improve|optimise|optimize)\b",
    re.IGNORECASE,
)

_REASONING_RE = re.compile(
    r"\b(design|architecture|plan|strategy|tradeoff|trade-off|compare|evaluate|"
    r"pros and cons|why|how does|what is the best|decision|rationale|"
    r"analyse|analyze|think through|step by step|reason|math|calculate|proof|"
    r"algorithm complexity|big.?o)\b",
    re.IGNORECASE,
)

_CODE_FENCE_RE = re.compile(r"```")

_DATA_ANALYSIS_RE = re.compile(
    r"\b(pandas|dataframe|numpy|matplotlib|seaborn|plotly|scipy|sklearn|scikit.learn|"
    r"tensorflow|pytorch|torch|keras|xgboost|lightgbm|catboost|"
    r"data.?frame|pivot.?table|groupby|resample|time.?series|"
    r"csv|parquet|feather|excel|sql.?query|aggregate|join|merge|"
    r"machine.?learning|deep.?learning|neural.?network|train.?model|"
    r"feature.?engineering|hyperparameter|cross.?validation|"
    r"correlation|regression|classification|clustering|embedding|"
    r"etl|pipeline|data.?pipeline|transform|normaliz|standardiz)\b",
    re.IGNORECASE,
)


# ── Public API ─────────────────────────────────────────────────────────────────

def classify_task(
    *,
    messages: list[dict[str, Any]] | None = None,
    system: str | None = None,
    endpoint_type: str = "chat",
    has_tools: bool = False,
    context_tokens: int | None = None,
    stream: bool = False,
) -> str:
    """Return the most likely task category for this request.

    Args:
        messages:       OpenAI-format messages list.
        system:         System prompt text (if separated from messages).
        endpoint_type:  One of "chat", "agent_plan", "agent_execute", "agent_verify".
        has_tools:      True if tool/function definitions are present.
        context_tokens: Estimated prompt token count (if known).
        stream:         True when the client requested streaming output.

    Returns:
        One of the task category strings listed in the module docstring.
    """
    # Endpoint type overrides everything for agent routes
    if endpoint_type == "agent_plan":
        return "reasoning"
    if endpoint_type in ("agent_execute", "agent_verify"):
        return "code_generation"

    # Tool definitions signal function-calling workload
    if has_tools:
        return "tool_use"

    # Large context → prioritise the model with the biggest window
    if context_tokens and context_tokens > 16_000:
        return "long_context"

    # Analyse the most recent messages (avoid large history noise)
    text = _extract_recent_text(messages)
    combined = f"{system or ''} {text}".strip()

    if not combined:
        return "conversation"

    # Fast-response: streaming + very short message with no code signals.
    # Route to the lightest available model for minimal latency.
    if stream and len(combined) < _FAST_RESPONSE_CHAR_LIMIT:
        has_fence = bool(_CODE_FENCE_RE.search(combined))
        has_write = bool(_CODE_WRITE_RE.search(combined))
        has_debug = bool(_CODE_DEBUG_RE.search(combined))
        if not has_fence and not has_write and not has_debug:
            return "fast_response"

    has_fence = bool(_CODE_FENCE_RE.search(combined))
    has_debug = bool(_CODE_DEBUG_RE.search(combined))
    has_write = bool(_CODE_WRITE_RE.search(combined))
    has_review = bool(_CODE_REVIEW_RE.search(combined))
    has_reason = bool(_REASONING_RE.search(combined))
    has_data = bool(_DATA_ANALYSIS_RE.search(combined))

    if has_debug and (has_fence or has_write):
        return "code_debugging"

    if has_review and (has_fence or has_write):
        return "code_review"

    if has_data:
        return "data_analysis"

    if has_fence or has_write:
        return "code_generation"

    if has_reason:
        return "reasoning"

    return "conversation"


# Short message threshold for fast_response routing (characters in combined text).
# Override via ROUTER_FAST_RESPONSE_CHARS env var.
import os as _os
_FAST_RESPONSE_CHAR_LIMIT: int = int(_os.environ.get("ROUTER_FAST_RESPONSE_CHARS") or "200")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_recent_text(messages: list[dict[str, Any]] | None, last_n: int = 4) -> str:
    """Concatenate plain text from the last *last_n* messages."""
    if not messages:
        return ""
    parts: list[str] = []
    for msg in messages[-last_n:]:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    return " ".join(parts)

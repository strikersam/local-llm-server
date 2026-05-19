from __future__ import annotations
import re
from typing import Any, Literal

# Intent categories
INTENT_EXECUTION = "execution"
INTENT_ANALYSIS = "analysis"
INTENT_CONVERSATION = "conversation"
INTENT_CLARIFY = "clarify"

_EXECUTION_KEYWORDS = re.compile(
    r"\b(fix|implement|create|add|generate|build|scaffold|refactor|migrate|"
    r"debug|commit|push|clone|branch|merge|pr|pull request|diff|patch|"
    r"edit|test|run|deploy|setup|install|update|change)\b",
    re.IGNORECASE,
)

_ANALYSIS_KEYWORDS = re.compile(
    r"\b(analyze|analyse|inspect|check|explain|understand|review|audit|investigate|look at|what is|search|find)\b",
    re.IGNORECASE,
)

def detect_intent(content: str) -> str:
    """Detect the user's intent from message content."""
    if not content or not isinstance(content, str):
        return INTENT_CONVERSATION

    stripped = content.strip().lower()

    # Very short messages or vague requests should probably be clarified or treated as conversation
    words = stripped.split()
    if len(words) < 3 and not _EXECUTION_KEYWORDS.search(stripped):
        return INTENT_CONVERSATION

    # Execution has priority
    if _EXECUTION_KEYWORDS.search(stripped):
        # If it's too vague, we might need clarification, but for now we'll lean towards execution
        if len(words) < 4 and any(w in stripped for w in ["fix", "edit", "change"]):
            return INTENT_CLARIFY
        return INTENT_EXECUTION

    # Analysis next
    if _ANALYSIS_KEYWORDS.search(stripped):
        return INTENT_ANALYSIS

    return INTENT_CONVERSATION

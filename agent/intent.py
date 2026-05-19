from __future__ import annotations
import re
from typing import Any

# Intent categories
INTENT_EXECUTION = "execution"
INTENT_CONVERSATION = "conversation"

_EXECUTION_KEYWORDS = re.compile(
    r"\b(fix|implement|create|add|generate|build|scaffold|refactor|migrate|"
    r"debug|error|exception|traceback|bug|issue|problem|wrong|broken|"
    r"failing|crash|stacktrace|commit|push|clone|branch|merge|pr|pull request|diff|patch|"
    r"edit|test|run|deploy|setup|install)\b",
    re.IGNORECASE,
)

def detect_intent(content: str) -> str:
    """Detect if the user content implies an execution task."""
    if not content:
        return INTENT_CONVERSATION

    # Check for execution keywords
    if _EXECUTION_KEYWORDS.search(content):
        return INTENT_EXECUTION

    return INTENT_CONVERSATION

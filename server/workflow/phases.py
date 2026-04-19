from enum import Enum

class WorkflowPhase(Enum):
    REQUEST = "request"
    CONTEXT = "context"
    RESEARCH = "research"
    INVESTIGATION = "investigation"
    STRUCTURE = "structure"
    PLAN = "plan"
    APPROVAL = "approval"
    EXECUTION = "execution"
    REVIEW = "review"
    VERIFICATION = "verification"
    MERGE_REPORT = "merge_report"

PHASE_ORDER = [
    WorkflowPhase.REQUEST,
    WorkflowPhase.CONTEXT,
    WorkflowPhase.RESEARCH,
    WorkflowPhase.INVESTIGATION,
    WorkflowPhase.STRUCTURE,
    WorkflowPhase.PLAN,
    WorkflowPhase.APPROVAL,
    WorkflowPhase.EXECUTION,
    WorkflowPhase.REVIEW,
    WorkflowPhase.VERIFICATION,
    WorkflowPhase.MERGE_REPORT
]
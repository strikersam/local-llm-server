from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

@dataclass
class WorkflowRun:
    id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    phases: List[str]
    artifacts: Dict[str, Any]
    events: List[Dict[str, Any]]

@dataclass
class Phase:
    name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    logs: List[str]

@dataclass
class Artifact:
    name: str
    type: str
    content: Any
    created_at: datetime
    last_updated: datetime
    metadata: Optional[Dict[str, Any]]

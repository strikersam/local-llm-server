from datetime import datetime
from typing import Dict, Any

def create_artifact(name: str, content: Any, metadata: Optional[Dict[str, Any]] = None) -> Dict:
    return {
        "name": name,
        "content": content,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }

def update_artifact(artifact: Dict, new_content: Any, new_metadata: Optional[Dict[str, Any]] = None) -> Dict:
    updated = artifact.copy()
    updated["content"] = new_content
    if new_metadata:
        updated["metadata"].update(new_metadata)
    updated["last_updated"] = datetime.now().isoformat()
    return updated

def validate_artifact(artifact: Dict) -> bool:
    required_fields = ["name", "content", "created_at", "last_updated"]
    return all(field in artifact for field in required_fields)
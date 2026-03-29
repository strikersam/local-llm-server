from __future__ import annotations

import difflib
import os
from pathlib import Path


TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".ps1",
    ".sh", ".bat", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".sql",
    ".xml", ".env",
}


class WorkspaceTools:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or os.environ.get("AGENT_WORKSPACE_ROOT") or ".").resolve()

    def _resolve_path(self, path: str) -> Path:
        cleaned = path.strip().replace("/", os.sep)
        resolved = (self.root / cleaned).resolve()
        if self.root not in resolved.parents and resolved != self.root:
            raise ValueError("Path escapes workspace root")
        return resolved

    def list_files(self, path: str = ".", limit: int = 200) -> list[str]:
        target = self._resolve_path(path)
        if target.is_file():
            return [str(target.relative_to(self.root))]
        output: list[str] = []
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", ".venv", "node_modules"}]
            for filename in filenames:
                rel = str((Path(dirpath) / filename).relative_to(self.root))
                output.append(rel)
                if len(output) >= limit:
                    return output
        return output

    def read_file(self, path: str, max_chars: int = 12000) -> str:
        target = self._resolve_path(path)
        return target.read_text(encoding="utf-8")[:max_chars]

    def write_file(self, path: str, content: str) -> dict[str, str | int]:
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target.relative_to(self.root)), "bytes": len(content.encode("utf-8"))}

    def apply_diff(self, path: str, new_content: str) -> dict[str, str]:
        target = self._resolve_path(path)
        old_content = target.read_text(encoding="utf-8") if target.exists() else ""
        diff = "\n".join(
            difflib.unified_diff(
                old_content.splitlines(),
                new_content.splitlines(),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        self.write_file(path, new_content)
        return {"path": str(target.relative_to(self.root)), "diff": diff}

    def search_code(self, query: str, limit: int = 20) -> list[dict[str, str | int]]:
        matches: list[dict[str, str | int]] = []
        lowered = query.lower()
        for rel_path in self.list_files(limit=1000):
            p = self.root / rel_path
            if p.suffix.lower() not in TEXT_EXTENSIONS and p.name not in {".env", ".gitignore"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                if lowered in line.lower():
                    matches.append({"path": rel_path, "line": idx, "snippet": line.strip()[:240]})
                    if len(matches) >= limit:
                        return matches
        return matches

from __future__ import annotations

import difflib
import os
from pathlib import Path
from agent.repowise import RepowiseIntelligence

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.user_memory import UserMemoryStore


TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".ps1",
    ".sh", ".bat", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".sql",
    ".xml", ".env",
}


class WorkspaceTools:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or os.environ.get("AGENT_WORKSPACE_ROOT") or ".").resolve()
        self.repowise = RepowiseIntelligence(self.root)


    def _resolve_path(self, path: str) -> Path:
        # Strictly validate input for any suspicious traversal patterns
        if ".." in path:
             raise ValueError(f"Traversal attempt detected: {path}")

        # Ensure root is absolute
        root_abs = self.root.resolve()

        # Combine and normalize. We strip leading separators to ensure
        # the path is treated as relative to the root.
        safe_relative = path.lstrip("/").lstrip("\\")
        full_path = os.path.normpath(os.path.join(str(root_abs), safe_relative))
        resolved = Path(full_path).resolve()

        # Robust prefix check to satisfy static analysis (CodeQL path injection)
        # os.path.commonpath is the most reliable way to check for path containment.
        try:
            if os.path.commonpath([str(root_abs), str(resolved)]) != str(root_abs):
                raise ValueError(f"Path escapes workspace root: {path}")
        except ValueError:
            # commonpath raises ValueError if paths are on different drives (Windows)
            raise ValueError(f"Path escapes workspace root (different drive): {path}")

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

    def recall_memory(
        self,
        key: str,
        *,
        user_id: str,
        memory_store: UserMemoryStore,
    ) -> str:
        """Return a previously saved memory value, or an empty string if absent."""
        value = memory_store.recall(user_id, key)
        return value if value is not None else ""

    def save_memory(
        self,
        key: str,
        value: str,
        *,
        user_id: str,
        memory_store: UserMemoryStore,
    ) -> str:
        """Persist a key/value pair to the user's profile store."""
        memory_store.save(user_id, key, value)
        return f"Saved '{key}' for {user_id}."

    def head_file(self, path: str, lines: int = 50) -> str:
        """Return the first *lines* lines of a file.

        Just-in-time retrieval: the executor uses this to quickly inspect a
        file's structure without loading the entire content into the context
        window.  If the full file is needed the executor can follow up with
        ``read_file``.

        Recommended by Anthropic's managed-agents article: prefer targeted
        head/search queries over full-file reads during the inspection phase.
        """
        target = self._resolve_path(path)
        text = target.read_text(encoding="utf-8")
        head = "\n".join(text.splitlines()[:lines])
        total = len(text.splitlines())
        suffix = f"\n… ({total - lines} more lines)" if total > lines else ""
        return head + suffix

    def file_index(self, path: str = ".", max_entries: int = 100) -> list[dict[str, str | int]]:
        """Return a lightweight index of files with line counts and sizes.

        This is the 'always-loaded lightweight index' tier from the
        three-tier JIT retrieval hierarchy (Anthropic managed-agents article):
        ~150 chars per entry, always in context, detailed content loaded
        on demand.
        """
        target = self._resolve_path(path)
        entries: list[dict[str, str | int]] = []
        if target.is_file():
            lines = len(target.read_text(encoding="utf-8", errors="ignore").splitlines())
            return [{"path": str(target.relative_to(self.root)), "lines": lines, "bytes": target.stat().st_size}]

        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", ".venv", "node_modules"}]
            for filename in filenames:
                full = Path(dirpath) / filename
                if full.suffix.lower() not in TEXT_EXTENSIONS and full.name not in {".env", ".gitignore"}:
                    continue
                try:
                    content = full.read_text(encoding="utf-8", errors="ignore")
                    line_count = len(content.splitlines())
                    byte_size = full.stat().st_size
                except OSError:
                    continue
                rel = str(full.relative_to(self.root))
                entries.append({"path": rel, "lines": line_count, "bytes": byte_size})
                if len(entries) >= max_entries:
                    return entries
        return entries

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

    def list_patterns(self) -> list[dict[str, str]]:
        """List all available fabric patterns with their descriptions."""
        patterns_dir = self._resolve_path(".claude/skills/fabric-patterns/patterns")
        if not patterns_dir.exists():
            return []
        
        patterns = []
        for pattern_file in patterns_dir.glob("*.md"):
            try:
                content = pattern_file.read_text(encoding="utf-8")
                # Extract frontmatter if present
                name = pattern_file.stem
                description = "No description available"
                
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        for line in frontmatter.split("\n"):
                            if line.startswith("name:"):
                                name = line.split(":", 1)[1].strip()
                            elif line.startswith("description:"):
                                description = line.split(":", 1)[1].strip()
                
                patterns.append({
                    "name": name,
                    "description": description,
                    "file": str(pattern_file.relative_to(self.root))
                })
            except Exception:
                # Skip unreadable files
                continue
        
        return sorted(patterns, key=lambda x: x["name"])

    def get_pattern(self, name: str) -> str:
        """Retrieve the raw content of a pattern by name."""
        patterns_dir = self._resolve_path(".claude/skills/fabric-patterns/patterns")
        pattern_file = patterns_dir / f"{name}.md"
        
        if not pattern_file.exists():
            raise FileNotFoundError(f"Pattern '{name}' not found")
        
        return pattern_file.read_text(encoding="utf-8")

    def apply_pattern(self, name: str, variables: dict[str, str]) -> str:
        """Apply a pattern with variable substitution."""
        content = self.get_pattern(name)
        
        # Extract template content (skip frontmatter if present)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                template = parts[2]
            else:
                template = content
        else:
            template = content
        
        # Replace variables
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", value)
        
        return result.strip()

    def stitch_patterns(self, pattern_names: list[str], initial_input: str) -> str:
        """Chain multiple patterns together, passing output of one as input to next."""
        current_input = initial_input
        
        for pattern_name in pattern_names:
            # Apply the pattern with current input as content
            variables = {"content": current_input}
            current_input = self.apply_pattern(pattern_name, variables)
        
        return current_input

    def get_overview(self) -> dict[str, Any]:
        """Provides an architecture summary, module map, and git health."""
        return self.repowise.get_overview()

    def get_context(self, targets: list[str], include: list[str] = ["source"]) -> str:
        """Workhorse tool for packing content and metrics of target files."""
        return self.repowise.get_context(targets, include)

    def get_risk(self, targets: list[str] | None = None, changed_files: list[str] | None = None) -> dict[str, Any]:
        """Hotspot scores and potential impact analysis."""
        return self.repowise.get_risk(targets, changed_files)

    def get_why(self, target: str) -> str:
        """Extracts architectural decisions related to target from git history."""
        return self.repowise.get_why(target)

    def get_answer(self, question: str) -> str:
        """One-call RAG over documentation with confidence gating."""
        return self.repowise.get_answer(question)

    def search_codebase(self, query: str) -> str:
        """Semantic search over documentation."""
        return self.repowise.search_codebase(query)

    def get_decision_flownodes(self) -> str:
        """Extract decision-linked flow nodes."""
        return self.repowise.get_decision_flownodes()

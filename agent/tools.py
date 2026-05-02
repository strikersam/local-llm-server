from __future__ import annotations

import difflib
import os
from pathlib import Path
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

    def get_overview(self) -> dict[str, any]:
        """Get architecture summary, module map, entry points, git health, community summary."""
        # This would implement the repowise get_overview functionality
        # For now, return a basic overview based on file_index
        file_index = self.file_index()
        
        # Group by directory to get module structure
        modules = {}
        for entry in file_index:
            path_parts = entry["path"].split("/")
            if len(path_parts) > 1:
                module = "/".join(path_parts[:-1]) if path_parts[:-1] else "root"
                if module not in modules:
                    modules[module] = []
                modules[module].append(entry["path"])
        
        # Count file types
        file_types = {}
        for entry in file_index:
            ext = Path(entry["path"]).suffix
            if not ext:
                ext = "(no extension)"
            file_types[ext] = file_types.get(ext, 0) + 1
        
        return {
            "total_files": len(file_index),
            "modules": {k: len(v) for k, v in modules.items()},
            "file_types": file_types,
            "git_health": "unknown",  # Would be computed from git history
            "structure_overview": f"Codebase organized into {len(modules)} modules"
        }

    def get_answer(self, question: str) -> dict[str, any]:
        """One-call RAG: retrieves over documentation, gates on confidence, synthesizes answer."""
        # Search for relevant content
        search_results = self.search_code(question, limit=10)
        
        # Simple confidence scoring based on result count and relevance
        confidence = min(0.9, len(search_results) * 0.1) if search_results else 0.0
        
        if confidence > 0.5:
            # High confidence - synthesize from top results
            top_snippets = [r["snippet"] for r in search_results[:3]]
            answer = f"Based on the codebase: {' '.join(top_snippets)}"
        else:
            # Low confidence - return ranked excerpts
            answer = f"Low confidence answer. Found {len(search_results)} potentially relevant files."
        
        return {
            "answer": answer,
            "confidence": confidence,
            "sources": [r["path"] for r in search_results[:5]],
            "query": question
        }

    def get_context(self, targets: list[str], include: list[str] | None = None) -> dict[str, any]:
        """Get context for targets: docs, symbols, ownership, freshness, etc."""
        include = include or []
        results = {}
        
        for target in targets:
            target_info = {
                "target": target,
                "files": [],
                "symbols": {},
                "includes": {}
            }
            
            # Get file information
            if "*" in target or "?" in target:
                # Glob pattern - search files
                import fnmatch
                all_files = self.list_files()
                matched_files = [f for f in all_files if fnmatch.fnmatch(f, target)]
                target_info["files"] = matched_files
            else:
                # Specific file/path
                if self._resolve_path(target).exists():
                    target_info["files"] = [target]
            
            # Get file details for included aspects
            if "source" in include:
                target_info["source"] = {}
                for file_path in target_info["files"]:
                    try:
                        target_info["source"][file_path] = self.read_file(file_path, max_chars=2000)
                    except Exception:
                        target_info["source"][file_path] = "Unable to read"
            
            if "metrics" in include:
                target_info["metrics"] = self.file_index(target) if target_info["files"] else []
            
            results[target] = target_info
        
        return results

    def search_codebase(self, query: str) -> list[dict[str, any]]:
        """Semantic search over documentation/wiki."""
        # For now, use existing search_code which is keyword-based
        # In a full implementation, this would use embeddings/semantic search
        results = self.search_code(query, limit=20)
        
        # Enhance results with relevance scoring
        enhanced_results = []
        for result in results:
            # Simple relevance: count occurrences of query words
            query_words = query.lower().split()
            snippet_lower = result["snippet"].lower()
            relevance = sum(1 for word in query_words if word in snippet_lower)
            
            enhanced_results.append({
                **result,
                "relevance_score": relevance,
                "match_type": "keyword"  # Would be "semantic" in full implementation
            })
        
        return sorted(enhanced_results, key=lambda x: x["relevance_score"], reverse=True)

    def get_risk(self, targets: list[str] | None = None, changed_files: list[str] | None = None) -> dict[str, any]:
        """Get hotspot scores, dependents, co-change pairs for risk assessment."""
        # This would integrate with git history analysis
        # For now, provide basic risk assessment based on file characteristics
        
        if changed_files is None:
            changed_files = []
        if targets is None:
            targets = changed_files
        
        risk_assessment = {
            "hotspot_files": [],
            "risky_targets": {},
            "recommendations": []
        }
        
        # Analyze targets for risk factors
        for target in targets:
            risk_factors = []
            risk_score = 0
            
            try:
                file_path = self._resolve_path(target)
                if file_path.exists():
                    # Size risk
                    size = file_path.stat().st_size
                    if size > 50000:  # > 50KB
                        risk_factors.append("large_file")
                        risk_score += 2
                    elif size > 10000:  # > 10KB
                        risk_factors.append("medium_file")
                        risk_score += 1
                    
                    # Complexity risk (rough estimate based on line count)
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        lines = len(content.splitlines())
                        if lines > 300:
                            risk_factors.append("high_line_count")
                            risk_score += 2
                        elif lines > 100:
                            risk_factors.append("medium_line_count")
                            risk_score += 1
                    except Exception:
                        pass
                    
                    # File type risk
                    if file_path.suffix in [".py", ".js", ".ts", ".java", ".cpp", ".c"]:
                        risk_factors.append("code_file")
                        risk_score += 1
                        
            except Exception:
                risk_factors.append("inaccessible")
                risk_score += 3
            
            risk_assessment["risky_targets"][target] = {
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "risk_level": "high" if risk_score >= 4 else "medium" if risk_score >= 2 else "low"
            }
        
        # Identify hotspot files (simplified)
        all_files = self.list_files(limit=100)
        for file_path in all_files:
            try:
                path_obj = self._resolve_path(file_path)
                if path_obj.exists():
                    size = path_obj.stat().st_size
                    if size > 30000:  # Large files as hotspots
                        risk_assessment["hotspot_files"].append({
                            "file": file_path,
                            "size": size,
                            "reason": "large_file_size"
                        })
            except Exception:
                continue
        
        risk_assessment["hotspot_files"] = sorted(
            risk_assessment["hotspot_files"], 
            key=lambda x: x["size"], 
            reverse=True
        )[:10]  # Top 10
        
        # Generate recommendations
        high_risk_targets = [
            target for target, data in risk_assessment["risky_targets"].items()
            if data["risk_level"] == "high"
        ]
        
        if high_risk_targets:
            risk_assessment["recommendations"].append(
                f"Consider refactoring high-risk files: {', '.join(high_risk_targets[:3])}"
            )
        
        if len(risk_assessment["hotspot_files"]) > 5:
            risk_assessment["recommendations"].append(
                "Several large files detected - consider modularization"
            )
        
        if not risk_assessment["recommendations"]:
            risk_assessment["recommendations"].append(
                "No significant risk factors detected in current targets"
            )
        
        return risk_assessment

    def get_why(self, target: str | list[str]) -> dict[str, any]:
        """Get architectural decisions related to targets."""
        # This would search through git history for decision markers
        # For now, return placeholder structure
        if isinstance(target, str):
            target = [target]
        
        why_analysis = {
            "targets": target,
            "decisions_found": [],
            "decision_summary": "No decision mining implemented yet",
            "suggestions": [
                "Add WHY/DECISION/TRADEOFF comments to git commits for decision tracking",
                "Use explicit DECISION markers in code for important architectural choices"
            ]
        }
        
        # Search for decision-like patterns in recent commits would go here
        # For now, just check for any obvious decision markers in current files
        decision_patterns = ["WHY:", "DECISION:", "TRADEOFF:", "# DECISION", "# WHY:"]
        
        for t in target:
            try:
                if self._resolve_path(t).exists():
                    content = self.read_file(t, max_chars=5000)
                    for pattern in decision_patterns:
                        if pattern in content:
                            why_analysis["decisions_found"].append({
                                "file": t,
                                "pattern": pattern,
                                "context": "Found decision marker in file"
                            })
            except Exception:
                continue
        
        if why_analysis["decisions_found"]:
            why_analysis["decision_summary"] = f"Found {len(why_analysis['decisions_found'])} decision markers"
        
        return why_analysis

    def get_decision_flownodes(self) -> list[dict[str, any]]:
        """Extract decision-linked flow nodes (would interface with call graph)."""
        # Placeholder for decision-linked flow node extraction
        return [
            {
                "node_id": "placeholder_1",
                "decision": "Example decision placeholder",
                "type": "architectural_decision",
                "confidence": 0.8,
                "related_files": ["example.py"]
            }
        ]

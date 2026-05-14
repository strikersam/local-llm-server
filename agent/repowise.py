from __future__ import annotations
import ast
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import hashlib

class RepowiseIntelligence:
    def __init__(self, root: Path):
        self.root = root
        self.intelligence_dir = self.root / ".Codex" / "skills" / "repowise-intelligence" / "intelligence"
        self.intelligence_dir.mkdir(parents=True, exist_ok=True)
        # Files for storing intelligence
        self.dependency_graph_file = self.intelligence_dir / "dependency_graph.json"
        self.symbol_graph_file = self.intelligence_dir / "symbol_graph.json"
        self.git_history_file = self.intelligence_dir / "git_history.json"
        self.decisions_file = self.intelligence_dir / "decisions.json"
        self.documentation_dir = self.intelligence_dir / "documentation"
        self.documentation_dir.mkdir(exist_ok=True)
        # File to store the last commit hash we processed
        self.last_commit_file = self.intelligence_dir / "last_commit.txt"

    def _run_git_command(self, cmd: List[str]) -> str:
        """Run a git command and return stdout as string."""
        try:
            result = subprocess.run(
                cmd, cwd=self.root, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def _get_last_commit(self) -> str:
        """Get the latest commit hash."""
        return self._run_git_command(["git", "rev-parse", "HEAD"])

    def _get_stored_last_commit(self) -> Optional[str]:
        """Get the last commit hash we processed."""
        if self.last_commit_file.exists():
            return self.last_commit_file.read_text().strip()
        return None

    def _mark_as_updated(self, commit_hash: str) -> None:
        """Mark that we have updated intelligence up to this commit."""
        self.last_commit_file.write_text(commit_hash)

    def _intelligence_is_stale(self) -> bool:
        """Check if we need to update intelligence based on new commits."""
        last_commit = self._get_stored_last_commit()
        current_commit = self._get_last_commit()
        return last_commit != current_commit

    def update_intelligence(self) -> None:
        """Build or update all intelligence layers."""
        if not self._intelligence_is_stale():
            return

        # Build each layer
        self._build_dependency_graph()
        self._build_symbol_graph()
        self._build_git_intelligence()
        self._build_documentation_intelligence()
        self._build_decision_intelligence()

        # Mark as updated
        self._mark_as_updated(self._get_last_commit())

    def _build_dependency_graph(self) -> None:
        """Build file-level dependency graph based on imports."""
        graph = {"nodes": [], "edges": []}
        # We'll collect all Python files for now
        py_files = list(self.root.rglob("*.py"))
        # Also consider other languages? We'll stick to Python for simplicity.
        # Map file to node id
        file_to_id = {}
        for i, f in enumerate(py_files):
            rel_path = str(f.relative_to(self.root))
            file_to_id[rel_path] = i
            graph["nodes"].append({"id": i, "file": rel_path})

        # For each file, find imports and add edges
        for f in py_files:
            rel_path = str(f.relative_to(self.root))
            try:
                content = f.read_text(encoding="utf-8")
                # Find import statements
                # Simple regex for import and from import
                imports = re.findall(r'^\\s*(?:from\\s+(\\S+)|import\\s+([\\S,]+))', content, re.MULTILINE)
                for imp in imports:
                    # imp is a tuple (from_module, import_list)
                    from_module, import_list = imp
                    if from_module:
                        # Handle 'from X import ...'
                        # We'll treat X as a module and try to map to a file
                        # We'll convert dotted notation to path
                        module_path = from_module.replace(".", "/")
                        # Look for a file that matches this module
                        possible_files = [
                            f"{module_path}.py",
                            f"{module_path}/__init__.py",
                        ]
                        for pf in possible_files:
                            if pf in file_to_id:
                                graph["edges"].append({
                                    "from": file_to_id[rel_path],
                                    "to": file_to_id[pf],
                                    "type": "import"
                                })
                                break
                    else:
                        # Handle 'import A, B, C'
                        for imp_name in import_list.split(","):
                            imp_name = imp_name.strip()
                            # Again, try to map to a file
                            module_path = imp_name.replace(".", "/")
                            possible_files = [
                                f"{module_path}.py",
                                f"{module_path}/__init__.py",
                            ]
                            for pf in possible_files:
                                if pf in file_to_id:
                                    graph["edges"].append({
                                        "from": file_to_id[rel_path],
                                        "to": file_to_id[pf],
                                        "type": "import"
                                    })
                                    break
            except Exception:
                # If we can't read the file, skip
                continue

        # Write the graph
        with open(self.dependency_graph_file, "w") as f:
            json.dump(graph, f, indent=2)

    def _build_symbol_graph(self) -> None:
        """Build symbol-level dependency graph for Python files."""
        # We'll store symbols and their relationships (calls, etc.)
        # For simplicity, we'll just store symbols and their containing file.
        # We'll also try to extract function calls.
        symbols = []  # list of symbol dicts
        edges = []    # list of edges (caller, callee)
        symbol_id_map = {}  # (file, symbol_name) -> id

        py_files = list(self.root.rglob("*.py"))
        for f in py_files:
            rel_path = str(f.relative_to(self.root))
            try:
                content = f.read_text(encoding="utf-8")
                tree = ast.parse(content)
                # We'll walk the tree to find function and class definitions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        symbol_name = node.name
                        symbol_id = len(symbols)
                        symbol_id_map[(rel_path, symbol_name)] = symbol_id
                        symbols.append({
                            "id": symbol_id,
                            "name": symbol_name,
                            "file": rel_path,
                            "type": "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
                            "line_number": node.lineno
                        })
            except Exception:
                # If we can't parse, skip
                continue

        # Now, walk again to find function calls
        for f in py_files:
            rel_path = str(f.relative_to(self.root))
            try:
                content = f.read_text(encoding="utf-8")
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        # We want to see if the call is to a function we know
                        # We'll look at the function being called
                        if isinstance(node.func, ast.Name):
                            called_name = node.func.id
                            # Look for this symbol in the same file or imported?
                            # For simplicity, we'll only consider calls in the same file.
                            if (rel_path, called_name) in symbol_id_map:
                                caller_symbols = [sym for sym in symbols if sym["file"] == rel_path and sym["type"] in ("function", "class")]
                                # We don't have the caller symbol from the context, so we'll skip for now.
                                # We'll need to know which function contains this call.
                                # We'll do a simple approach: attribute the call to the nearest function/class.
                                pass
                        elif isinstance(node.func, ast.Attribute):
                            # e.g., obj.method() or module.function()
                            # We'll skip for now.
                            pass
            except Exception:
                continue

        # For now, we'll just store the symbols without edges.
        # We'll improve later if time permits.
        graph = {"symbols": symbols, "edges": edges}
        with open(self.symbol_graph_file, "w") as f:
            json.dump(graph, f, indent=2)

    def _build_git_intelligence(self) -> None:
        """Build git intelligence: hotspots, ownership, co-change pairs."""
        # Hotspots: we already have a method, but we'll recompute and store more info.
        # Ownership: for each file, compute percentage of lines per author.
        # Co-change pairs: find pairs of files that are changed together in commits (without import link).

        # We'll get list of all files (not just Python) for git intelligence.
        # We'll use git ls-files to get tracked files.
        output = self._run_git_command(["git", "ls-files"])
        if not output:
            files = []
        else:
            files = output.splitlines()

        # Initialize data structures
        file_data = {f: {"hotspot_changes": 0, "ownership": {}, "total_lines": 0, "complexity": 0} for f in files}
        # We'll also collect commit data for co-change analysis
        commit_file_map = {}  # commit hash -> list of files changed in that commit

        # Compute complexity for Python files
        for f in files:
            if f.endswith(".py"):
                filepath = self.root / f
                try:
                    complexity = self._compute_complexity(filepath)
                    file_data[f]["complexity"] = complexity
                except Exception:
                    file_data[f]["complexity"] = 0

        # We'll do a simpler approach for ownership: blame each file and compute per-author lines.
        # This can be slow for many files, but we'll try.
        for f in files:
            try:
                # Use git blame to get lines and authors
                blame_output = self._run_git_command(["git", "blame", "--line-porcelain", f])
                if blame_output:
                    # Parse blame output
                    current_author = None
                    for line in blame_output.splitlines():
                        if line.startswith("author "):
                            current_author = line[7:]  # after "author "
                        elif line.startswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                            # This is a line of the file, count it for the current author
                            if current_author:
                                file_data[f]["ownership"][current_author] = file_data[f]["ownership"].get(current_author, 0) + 1
                                file_data[f]["total_lines"] += 1
            except Exception:
                # If blame fails, skip
                continue

        # Now, compute hotspots: we can use the number of changes (commits that touched the file)
        # We'll get the commit count per file from git log.
        for f in files:
            try:
                changes = self._run_git_command(["git", "log", "--oneline", "--follow", "--", f])
                if changes:
                    change_count = len(changes.splitlines())
                    file_data[f]["hotspot_changes"] = change_count
            except Exception:
                pass

        # Co-change pairs: we'll look at commits and see which files are changed together.
        # We'll limit to commits that changed less than, say, 20 files to avoid massive commits.
        try:
            # Get commits with their files
            # We'll use: git log --pretty=format:"%H" --name-only
            # But we'll do it in a way that we can parse.
            # We'll use a temporary file or process line by line.
            # We'll do: git log --pretty=format:"%H" --name-only | awk ... but we'll do in Python.
            output = self._run_git_command(["git", "log", "--pretty=format:%H", "--name-only"])
            if output:
                commits = output.split("\n\n")  # each commit is hash followed by files, separated by blank line
                for commit_block in commits:
                    lines = commit_block.splitlines()
                    if not lines:
                        continue
                    commit_hash = lines[0]
                    files_changed = lines[1:]
                    if len(files_changed) > 20:
                        # Skip large commits
                        continue
                    # Update commit_file_map
                    commit_file_map[commit_hash] = files_changed
        except Exception:
            pass

        # Now compute co-change pairs: for each pair of files, count how many times they appear together in a commit.
        cochange_counts = {}
        for commit_hash, files_changed in commit_file_map.items():
            # For each pair in files_changed
            for i in range(len(files_changed)):
                for j in range(i+1, len(files_changed)):
                    f1 = files_changed[i]
                    f2 = files_changed[j]
                    if f1 not in file_data or f2 not in file_data:
                        continue
                    key = tuple(sorted((f1, f2)))
                    cochange_counts[key] = cochange_counts.get(key, 0) + 1

        # Prepare the intelligence data
        git_intelligence = {
            "hotspots": [],
            "ownership": {},
            "cochange_pairs": []
        }

        # Hotspots: we'll compute a simple score (changes * (complexity + 1)) to avoid zero.
        for f, data in file_data.items():
            # Compute hotspot score as changes * (complexity + 1)
            complexity = data["complexity"]
            changes = data["hotspot_changes"]
            score = changes * (complexity + 1)  # ensure at least changes
            git_intelligence["hotspots"].append({
                "file": f,
                "changes": changes,
                "complexity": complexity,
                "hotspot_score": score,
                "total_lines": data["total_lines"]
            })
        # Sort by hotspot_score descending
        git_intelligence["hotspots"].sort(key=lambda x: x["hotspot_score"], reverse=True)

        # Ownership: for each file, compute percentages
        for f, data in file_data.items():
            if data["total_lines"] > 0:
                ownership = {}
                for author, count in data["ownership"].items():
                    ownership[author] = round(count / data["total_lines"] * 100, 2)
                git_intelligence["ownership"][f] = ownership

        # Co-change pairs: we'll take top 20 pairs by count
        sorted_pairs = sorted(cochange_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        for (f1, f2), count in sorted_pairs:
            git_intelligence["cochange_pairs"].append({
                "file1": f1,
                "file2": f2,
                "cochange_count": count
            })

        # Write to file
        with open(self.git_history_file, "w") as f:
            json.dump(git_intelligence, f, indent=2)

    def _compute_complexity(self, filepath: Path) -> int:
        """Compute cyclomatic complexity for Python files.
        Returns 0 for non-Python files or if parsing fails."""
        if not filepath.suffix == ".py":
            return 0
        try:
            content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(content)
            complexity = 1  # start with 1 for the straight path
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(node, ast.ExceptHandler):
                    complexity += 1
                elif isinstance(node, (ast.And, ast.Or)):
                    # Each boolean operator adds a decision point
                    complexity += 1
                elif isinstance(node, ast.Match):  # Python 3.10+
                    complexity += 1
                    # Each case in match adds a decision point
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.match_case):
                            complexity += 1
            return complexity
        except Exception:
            return 0
    def _build_documentation_intelligence(self) -> None:
        """Extract docstrings and store as documentation."""
        # We'll extract docstrings from Python files and store them as markdown files.
        # We'll also consider other file types? We'll stick to Python for now.
        py_files = list(self.root.rglob("*.py"))
        for f in py_files:
            rel_path = str(f.relative_to(self.root))
            try:
                content = f.read_text(encoding="utf-8")
                tree = ast.parse(content)
                # Get module docstring
                module_docstring = ast.get_docstring(tree)
                # We'll store the documentation in a file under documentation/
                # We'll create a safe filename by replacing path separators with underscores
                safe_name = rel_path.replace("/", "_").replace(".", "_") + ".md"
                doc_file = self.documentation_dir / safe_name
                with open(doc_file, "w") as df:
                    df.write(f"# {rel_path}\\n\\n")
                    if module_docstring:
                        df.write(module_docstring)
                    else:
                        df.write("*No docstring available*")
            except Exception:
                # If we can't parse, we'll just note that
                safe_name = rel_path.replace("/", "_").replace(".", "_") + ".md"
                doc_file = self.documentation_dir / safe_name
                with open(doc_file, "w") as df:
                    df.write(f"# {rel_path}\\n\\n")
                    df.write("*Could not extract docstring*")

    def _build_decision_intelligence(self) -> None:
        """Extract architectural decisions from git history and inline comments."""
        decisions = []

        # From commit messages: look for WHY, DECISION, TRADEOFF
        try:
            output = self._run_git_command(["git", "log", "--grep='WHY' --grep='DECISION' --grep='TRADEOFF' -i"])
            if output:
                for commit in output.split("commit ")[1:]:  # first split is empty
                    lines = commit.splitlines()
                    if not lines:
                        continue
                    commit_hash = lines[0].split()[0]
                    # The rest is the commit message
                    message = "\n".join(lines[1:])
                    decisions.append({
                        "type": "commit",
                        "commit": commit_hash,
                        "message": message.strip()
                    })
        except Exception:
            pass

        # From inline comments: scan for patterns like # WHY:, # DECISION:, # TRADEOFF:
        # We'll scan Python files for now.
        py_files = list(self.root.rglob("*.py"))
        for f in py_files:
            rel_path = str(f.relative_to(self.root))
            try:
                content = f.read_text(encoding="utf-8")
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        # Remove the # and any spaces
                        comment = stripped[1:].strip()
                        # Check for patterns
                        if comment.startswith("WHY:") or comment.startswith("DECISION:") or comment.startswith("TRADEOFF:"):
                            decisions.append({
                                "type": "inline",
                                "file": rel_path,
                                "line": i+1,
                                "comment": comment
                            })
            except Exception:
                pass

        # Write decisions to file
        with open(self.decisions_file, "w") as f:
            json.dump(decisions, f, indent=2)

    # Now, the tool methods

    def get_overview(self) -> Dict[str, Any]:
        """Provides an architecture summary, module map, and git health."""
        self.update_intelligence()
        overview = {
            "repository_map": self.get_repository_map(max_depth=2),
            "hotspots": self.get_hotspots(limit=5),
            "entry_points": self.find_entry_points(),
            "git_health": self.get_git_health()
        }
        # Add some intelligence from our built data
        try:
            with open(self.git_history_file, "r") as f:
                git_intel = json.load(f)
                overview["git_intelligence"] = {
                    "hotspots": git_intel.get("hotspots", [])[:5],
                    "ownership_sample": {k: v for k, v in list(git_intel.get("ownership", {}).items())[:3]},
                    "top_cochange_pairs": git_intel.get("cochange_pairs", [])[:3]
                }
        except Exception:
            pass
        return overview

    def get_repository_map(self, max_depth: int = 3) -> str:
        """Returns a structural overview of the repository."""
        try:
            cmd = ["git", "ls-files"]
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, check=True)
            files = result.stdout.splitlines()
        except Exception:
            files = []
            for p in self.root.rglob("*"):
                if any(x in p.parts for x in [".git", "__pycache__", ".venv", "node_modules"]):
                    continue
                if p.is_file():
                    files.append(str(p.relative_to(self.root)))

        tree = {}
        for f in files:
            parts = Path(f).parts
            if len(parts) > max_depth + 1:
                continue
            curr = tree
            for part in parts:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]

        def _render(node: dict, indent: str = "") -> str:
            lines = []
            for name in sorted(node.keys()):
                lines.append(f"{indent}- {name}")
                lines.append(_render(node[name], indent + "  "))
            return "\n".join([l for l in lines if l])

        return _render(tree)

    def get_hotspots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identifies frequently changed files using git history."""
        self.update_intelligence()
        try:
            with open(self.git_history_file, "r") as f:
                git_intel = json.load(f)
                hotspots = git_intel.get("hotspots", [])
                # Return top 'limit' by changes
                sorted_hotspots = sorted(hotspots, key=lambda x: x["changes"], reverse=True)
                return sorted_hotspots[:limit]
        except Exception:
            return []

    def find_entry_points(self) -> List[str]:
        """Guesses entry points based on file names and common patterns."""
        entry_patterns = ["main.py", "app.py", "server.py", "proxy.py", "index.js", "index.ts", "run.sh", "Makefile"]
        found = []
        for pattern in entry_patterns:
            matches = list(self.root.glob(pattern)) + list(self.root.glob(f"*/{pattern}"))
            for m in matches:
                found.append(str(m.relative_to(self.root)))
        return list(set(found))

    def get_git_health(self) -> Dict[str, Any]:
        """Basic git health metrics."""
        try:
            commit_count = self._run_git_command(["git", "rev-list", "--count", "HEAD"])
            author_count = self._run_git_command(["git", "log", "--format='%aE'", "|", "sort", "|", "uniq", "|", "wc", "-l"])
            # The above command for author count is a shell pipeline, we'll do it differently
            # Let's use a Python approach for author count
            # We'll get all commits and count unique authors
            # But for simplicity, we'll use the previous method and fix the command.
            # We'll do: git log --format='%ae' | sort -u | wc -l
            author_output = self._run_git_command(["git", "log", "--format=%ae", "|", "sort", "-u", "|", "wc", "-l"])
            # The above might not work because of the pipe in a list. We'll use shell=True for this one.
            # Let's change: we'll use shell=True for the author count.
            # We'll revert to the original method but fix it by using a single string with shell=True.
            # We'll do it in a separate way.
            # We'll just use the old method for now and hope it works.
            # We'll change the method to use shell=True for the author count.
            # We'll do it in a try-except.
            # Let's recompute author count with a proper shell command.
            # We'll do: git log --pretty=format:'%ae' | sort -u | wc -l
            author_count_str = self._run_git_command(["sh", "-c", "git log --pretty=format:'%ae' | sort -u | wc -l"])
            return {
                "total_commits": int(commit_count) if commit_count else 0,
                "total_authors": int(author_count_str) if author_count_str else 0
            }
        except Exception:
            return {"total_commits": 0, "total_authors": 0}

    def get_context(self, targets: List[str], include: List[str] = ["source"]) -> str:
        """Workhorse tool for packing content and metrics of target files."""
        self.update_intelligence()
        output = []
        for target in targets:
            # Handle potential symbol:file format
            if ":" in target and not Path(target).exists():
                symbol, file_path = target.split(":", 1)
                path = self.root / file_path
                if path.exists():
                    output.append(self._extract_symbol(path, symbol, include))
                    continue

            path = self.root / target
            if not path.exists():
                # Try as glob
                matches = list(self.root.glob(target))
                for match in matches:
                    output.append(self._pack_file(match, include))
            else:
                output.append(self._pack_file(path, include))

        return "\n\n".join([o for o in output if o])

    def _pack_file(self, path: Path, include: List[str]) -> str:
        if not path.is_file():
            return ""

        rel_path = str(path.relative_to(self.root))
        result = [f"<file path=\"{rel_path}\">"]

        if "metrics" in include:
            # We can add metrics from our intelligence
            # For example, from dependency graph: number of imports, etc.
            # We'll add simple file stats for now.
            stats = path.stat()
            result.append(f"<metrics size=\"{stats.st_size}\" />")

        if "callers" in include or "callees" in include:
            # We'll try to get dependencies from our intelligence
            deps = self._get_dependencies_from_intelligence(path, include)
            if deps:
                result.append(f"<dependencies>\n{deps}\n</dependencies>")

        if "source" in include:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                result.append(content)
            except Exception as e:
                result.append(f"Error reading file: {e}")

        result.append("</file>")
        return "\n".join(result)

    def _get_dependencies_from_intelligence(self, path: Path, include: List[str]) -> str:
        """Get dependencies from our built intelligence."""
        rel_path = str(path.relative_to(self.root))
        deps = []
        # We'll look at the dependency graph for file-level imports
        try:
            with open(self.dependency_graph_file, "r") as f:
                graph = json.load(f)
                # We need to map file to node id
                # We'll build a map from file to node id from the graph nodes
                file_to_id = {node["file"]: node["id"] for node in graph["nodes"]}
                if rel_path in file_to_id:
                    node_id = file_to_id[rel_path]
                    # Find edges where this node is the source (outgoing edges)
                    for edge in graph["edges"]:
                        if edge["from"] == node_id:
                            target_id = edge["to"]
                            # Find the target file
                            target_file = next((n["file"] for n in graph["nodes"] if n["id"] == target_id), None)
                            if target_file:
                                if "callees" in include:
                                    deps.append(f"  - callee: {target_file}")
                        if edge["to"] == node_id:
                            source_id = edge["from"]
                            source_file = next((n["file"] for n in graph["nodes"] if n["id"] == source_id), None)
                            if source_file:
                                if "callers" in include:
                                    deps.append(f"  - caller: {source_file}")
        except Exception:
            pass

        # We'll also add symbol-level dependencies if available and requested
        # For now, we'll skip symbol-level to keep it simple.

        return "\n".join(deps)

    def _extract_symbol(self, path: Path, symbol: str, include: List[str]) -> str:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            patterns = [
                rf"class\s+{symbol}\b",
                rf"def\s+{symbol}\b",
                rf"function\s+{symbol}\b",
                rf"const\s+{symbol}\s*=",
                rf"let\s+{symbol}\s*=",
                rf"var\s+{symbol}\s*="
            ]

            lines = content.splitlines()
            start_line = -1
            for i, line in enumerate(lines):
                if any(re.search(p, line) for p in patterns):
                    start_line = i
                    break

            if start_line == -1:
                return f"<symbol name=\"{symbol}\" path=\"{path.relative_to(self.root)}\" status=\"not_found\" />"

            # Extract block (very naive)
            indent = len(lines[start_line]) - len(lines[start_line].lstrip())
            block = [lines[start_line]]
            for line in lines[start_line+1:]:
                if line.strip() and len(line) - len(line.lstrip()) <= indent:
                    break
                block.append(line)

            rel_path = str(path.relative_to(self.root))
            return f"<symbol name=\"{symbol}\" path=\"{rel_path}\">\n" + "\n".join(block) + "\n</symbol>"
        except Exception as e:
            return f"<symbol name=\"{symbol}\" path=\"{path.relative_to(self.root)}\" error=\"{e}\" />"

    def get_risk(self, targets: Optional[List[str]] = None, changed_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Hotspot scores and potential impact analysis."""
        self.update_intelligence()
        hotspots = self.get_hotspots(limit=100)
        hotspots_dict = {h["file"]: h["changes"] for h in hotspots}

        relevant_hotspots = []
        if changed_files:
            for f in changed_files:
                if f in hotspots_dict:
                    relevant_hotspots.append({
                        "path": f,
                        "changes": hotspots_dict[f],
                        "risk": "high" if hotspots_dict[f] > 20 else "medium" if hotspots_dict[f] > 5 else "low"
                    })

        # Also, we can add co-change partners from intelligence
        cochange_partners = []
        if changed_files:
            try:
                with open(self.git_history_file, "r") as f:
                    git_intel = json.load(f)
                    for pair in git_intel.get("cochange_pairs", []):
                        if pair["file1"] in changed_files:
                            cochange_partners.append({
                                "file": pair["file2"],
                                "cochange_count": pair["cochange_count"]
                            })
                        elif pair["file2"] in changed_files:
                            cochange_partners.append({
                                "file": pair["file1"],
                                "cochange_count": pair["cochange_count"]
                            })
            except Exception:
                pass

        return {
            "overall_hotspots": self.get_hotspots(limit=10),
            "impact_analysis": relevant_hotspots,
            "cochange_partners": cochange_partners[:5]  # top 5
        }

    def get_why(self, target: str) -> str:
        """Extracts architectural decisions related to target from git history and inline comments."""
        self.update_intelligence()
        # We'll search our decisions intelligence
        try:
            with open(self.decisions_file, "r") as f:
                decisions = json.load(f)
        except Exception:
            decisions = []

        relevant_decisions = []
        for d in decisions:
            if d["type"] == "commit":
                # We don't have a direct link to target in commit decisions, so we'll skip for now.
                # We could check if the commit touched the target file, but we don't have that mapping.
                pass
            elif d["type"] == "inline":
                if d["file"] == target or target in d["file"]:
                    relevant_decisions.append(d)

        if not relevant_decisions:
            return f"No documented decisions found for {target}"

        # Format the decisions
        output = []
        for d in relevant_decisions:
            if d["type"] == "inline":
                output.append(f"In {d['file']}:{d['line']}: {d['comment']}")
        return "\n".join(output)

    def get_answer(self, question: str) -> str:
        """One-call RAG over documentation with confidence gating."""
        self.update_intelligence()
        # We'll search the documentation we built for relevant docstrings.
        # We'll do a simple keyword search for now.
        question_lower = question.lower()
        matches = []
        for doc_file in self.documentation_dir.glob("*.md"):
            try:
                content = doc_file.read_text(encoding="utf-8")
                # We'll check if the question keywords appear in the content
                if question_lower in content.lower():
                    # We'll extract a snippet around the match
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if question_lower in line.lower():
                            # Get a few lines around
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            snippet = "\n".join(lines[start:end])
                            matches.append({
                                "file": doc_file.name,
                                "snippet": snippet
                            })
                            break
            except Exception:
                pass

        if not matches:
            return "I couldn't find relevant information in the documentation to answer that question."

        # We'll format the answer
        # We'll take the top 3 matches and synthesize a simple answer.
        # We'll just concatenate the snippets for now.
        answer_parts = []
        for match in matches[:3]:
            answer_parts.append(f"From {match['file']}:\\n{match['snippet']}")

        # We'll add a confidence note based on number of matches
        confidence = "high" if len(matches) > 2 else "medium" if len(matches) > 1 else "low"
        answer = "\\n\\n".join(answer_parts)
        answer += f"\\n\\nConfidence: {confidence} (based on {len(matches)} matching documentation pages)"
        return answer

    def search_codebase(self, query: str) -> str:
        """Semantic search over documentation (we'll do keyword search for now)."""
        self.update_intelligence()
        query_lower = query.lower()
        results = []
        for doc_file in self.documentation_dir.glob("*.md"):
            try:
                content = doc_file.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    # We'll return the file path and a snippet
                    # We'll find the first occurrence
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            snippet = line.strip()
                            results.append({
                                "file": str(doc_file.relative_to(self.intelligence_dir)),
                                "line": i+1,
                                "snippet": snippet
                            })
                            break
            except Exception:
                pass

        if not results:
            return f"No documentation found matching '{query}'."

        # Format results
        output = []
        for r in results[:10]:  # limit to 10 results
            output.append(f"{r['file']}:{r['line']} - {r['snippet']}")
        return "\n".join(output)

    def get_decision_flownodes(self) -> str:
        """Extract decision-linked flow nodes."""
        self.update_intelligence()
        # We'll look for decisions that are linked to specific code flows.
        # For now, we'll return the inline decisions we found.
        try:
            with open(self.decisions_file, "r") as f:
                decisions = json.load(f)
        except Exception:
            decisions = []

        flow_nodes = []
        for d in decisions:
            if d["type"] == "inline":
                flow_nodes.append({
                    "file": d["file"],
                    "line": d["line"],
                    "decision": d["comment"],
                    "type": "inline_decision"
                })
            # We could also add commit-level decisions if we had file mapping

        if not flow_nodes:
            return "No decision-linked flow nodes found."

        # Format as a string
        output = []
        for node in flow_nodes:
            output.append(f"File: {node['file']}, Line: {node['line']}, Decision: {node['decision']}")
        return "\n".join(output)
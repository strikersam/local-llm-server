from __future__ import annotations
import asyncio
import os
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class RepowiseIntelligence:
    def __init__(self, root: Path):
        """
        Store the repository root path on the instance.
        
        Parameters:
            root (Path | str): Filesystem path to the repository root; converted to a `pathlib.Path` and assigned to `self.root`.
        """
        self.root = Path(root)

    async def get_overview(self) -> Dict[str, Any]:
        """
        Aggregate repository inspection results including the repository map, hotspots, entry points, git health, and architecture summary.

        Returns:
            overview (Dict[str, Any]): Dictionary with the following keys:
                - repository_map: Rendered directory/file tree limited by depth.
                - hotspots: List of frequently changed files with change counts.
                - entry_points: List of likely entry-point file paths.
                - git_health: Basic git metrics (total_commits, total_authors).
                - architecture: Summary of key modules and detected design patterns.
        """
        return {
            "repository_map": self.get_repository_map(max_depth=2),
            "hotspots": self.get_hotspots(limit=5),
            "entry_points": self.find_entry_points(),
            "git_health": self.get_git_health(),
            "architecture": await self.get_architecture_summary()
        }

    def get_repository_map(self, max_depth: int = 3) -> str:
        """
        Builds a textual tree of files and directories under the repository root.
        
        Parameters:
            max_depth (int): Maximum directory depth to include; root-level files count as depth 0.
        
        Returns:
            str: A newline-separated tree where each entry is prefixed with `- ` and indented to indicate hierarchy.
        """
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
        """
        Identify files with the most changes in the repository history.
        
        Parameters:
            limit (int): Maximum number of hotspot entries to return.
        
        Returns:
            List[Dict[str, Any]]: A list of entries sorted by change count descending. Each entry is a dict with keys:
                - "path": repository-relative file path (str)
                - "changes": number of recorded changes (int)
        On error (for example if git is unavailable), returns an empty list.
        """
        try:
            cmd = "git log --format='' --name-only | sort | uniq -c | sort -rn | head -n " + str(limit)
            result = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True)
            hotspots = []
            for line in result.stdout.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    count, path = parts
                    hotspots.append({"path": path, "changes": int(count)})
            return hotspots
        except Exception:
            return []

    def find_entry_points(self) -> List[str]:
        """
        Find candidate repository entry-point files by name in the repository root and its immediate subdirectories.
        
        Searches for common entry filenames (e.g., main.py, app.py, server.py, proxy.py, index.js, index.ts, run.sh, Makefile) at the repository root and in its immediate subdirectories.
        
        Returns:
            List[str]: Unique file paths, relative to the repository root, that match any of the entry-point filenames.
        """
        entry_patterns = ["main.py", "app.py", "server.py", "proxy.py", "index.js", "index.ts", "run.sh", "Makefile"]
        found = []
        for pattern in entry_patterns:
            matches = list(self.root.glob(pattern)) + list(self.root.glob(f"*/{pattern}"))
            for m in matches:
                found.append(str(m.relative_to(self.root)))
        return list(set(found))

    def get_git_health(self) -> Dict[str, Any]:
        """
        Compute basic git metrics for the repository at self.root.
        
        This returns counts for the repository's total commits and the number of unique author emails (as reported by git history). If git is unavailable or an error occurs, both counts will be zero.
        
        Returns:
            dict: {
                "total_commits": int - total commit count for HEAD,
                "total_authors": int - number of unique author email addresses (0 if unavailable)
            }
        """
        try:
            commit_count = subprocess.run(["git", "rev-list", "--count", "HEAD"],
                                       cwd=self.root, capture_output=True, text=True).stdout.strip()
            author_count = subprocess.run(["git", "log", "--format='%aE'", "|", "sort", "|", "uniq", "|", "wc", "-l"],
                                        shell=True, cwd=self.root, capture_output=True, text=True).stdout.strip()
            return {
                "total_commits": int(commit_count) if commit_count else 0,
                "total_authors": int(author_count) if author_count else 0
            }
        except Exception:
            return {"total_commits": 0, "total_authors": 0}

    async def get_architecture_summary(self) -> Dict[str, Any]:
        """
        Summarizes repository key modules and detected architectural patterns.
        
        Scans the repository to identify immediate subdirectories that qualify as "key modules" (directories with multiple source files) and detects common architectural or tooling patterns by searching repository files for indicative keywords.
        
        Returns:
            summary (dict): {
                "key_modules": List[dict] — each dict contains:
                    - "name" (str): directory name
                    - "files" (int): number of source files counted in that directory
                "patterns": List[str] — detected pattern labels such as "FastAPI/REST", "React/Frontend", "Docker", "Agentic"
            }
        """
        def _scan_architecture() -> Dict[str, Any]:
            """
            Scan the repository filesystem and file contents to identify key modules and detect architectural patterns.
            
            Scans immediate subdirectories to find "key modules" (directories containing more than two source files among .py, .js, .ts) and scans repository files for keyword indicators of known patterns (e.g., FastAPI/REST, React/Frontend, Docker, Agentic). Excludes common uninteresting directories from content scanning.
            
            Returns:
                summary (Dict[str, Any]): A dictionary with:
                    - "key_modules" (List[Dict[str, int]]): Entries with "name" (directory name) and "files" (number of source files).
                    - "patterns" (List[str]): Detected pattern labels present in the repository.
            """
            summary = {
                "key_modules": [],
                "patterns": []
            }

            # Look for directories with many files as key modules
            dirs = [d for d in self.root.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]
            for d in dirs:
                file_count = len(list(d.glob("**/*.py"))) + len(list(d.glob("**/*.js"))) + len(list(d.glob("**/*.ts")))
                if file_count > 2:
                    summary["key_modules"].append({"name": d.name, "files": file_count})

            # Look for common patterns by scanning files in-memory
            pattern_indicators = {
                "FastAPI/REST": ["FastAPI", "router", "endpoint"],
                "React/Frontend": ["react", "component", "useState"],
                "Docker": ["Dockerfile", "docker-compose"],
                "Agentic": ["agent", "loop", "tool", "prompt"]
            }

            # Collect all relevant files to scan
            extensions = ["*.py", "*.js", "*.ts", "Dockerfile", "*.yaml", "*.yml"]
            exclude_dirs = {".git", "__pycache__", ".venv", "node_modules"}

            files_to_scan = []
            for ext in extensions:
                for file_path in self.root.rglob(ext):
                    # Skip excluded directories
                    if any(excluded in file_path.parts for excluded in exclude_dirs):
                        continue
                    files_to_scan.append(file_path)

            # Scan files for pattern indicators
            patterns_found = set()
            for pattern_name, keywords in pattern_indicators.items():
                if pattern_name in patterns_found:
                    continue

                for file_path in files_to_scan:
                    try:
                        content = file_path.read_text(errors="ignore").lower()
                        # Check if any keyword is present (case-insensitive)
                        if any(kw.lower() in content for kw in keywords):
                            patterns_found.add(pattern_name)
                            break
                    except Exception:
                        continue

            summary["patterns"] = list(patterns_found)
            return summary

        # Run the blocking work in a background thread
        return await asyncio.to_thread(_scan_architecture)

    def get_context(self, targets: List[str], include: List[str] = ["source"]) -> str:
        """
        Assembles packed representations (source, metrics, dependencies, or extracted symbols) for a list of filesystem targets.
        
        Parameters:
        	targets (List[str]): Paths, globs, or symbol selectors of the form `Symbol:relative/path/to/file` to include in the output.
        	include (List[str]): Which sections to include for each packed item. Common values: `"source"`, `"metrics"`, `"callers"`, `"callees"`.
        
        Returns:
        	A single string containing an HTML-comment token estimate followed by packed XML-like segments for each matched target, separated by blank lines.
        """
        output = []
        total_estimated_tokens = 0

        for target in targets:
            # Handle potential symbol:file format
            if ":" in target and not Path(target).exists():
                symbol, file_path = target.split(":", 1)
                path = self.root / file_path
                if path.exists():
                    symbol_content = self._extract_symbol(path, symbol, include)
                    total_estimated_tokens += len(symbol_content) // 4
                    output.append(symbol_content)
                    continue

            path = self.root / target
            if not path.exists():
                # Try as glob
                matches = list(self.root.glob(target))
                for match in matches:
                    file_content = self._pack_file(match, include)
                    total_estimated_tokens += len(file_content) // 4
                    output.append(file_content)
            else:
                file_content = self._pack_file(path, include)
                total_estimated_tokens += len(file_content) // 4
                output.append(file_content)

        prefix = f"<!-- Estimated total tokens: {total_estimated_tokens} -->\n\n"
        return prefix + "\n\n".join([o for o in output if o])

    def _pack_file(self, path: Path, include: List[str]) -> str:
        """
        Pack a single file into an XML-like string containing optional metadata, dependencies, and source.
        
        Parameters:
            path (Path): File to pack; emitted path is relative to the instance root.
            include (List[str]): Sections to include. Recognized values:
                - "metrics": include a <metrics size="..."/> element with file size in bytes
                - "callees" / "callers": include a <dependencies> section populated from _get_dependencies
                - "source": embed the file's UTF-8-decoded contents (errors replaced)
        
        Returns:
            str: The packed file as a string. Returns an empty string if `path` is not a file. If reading the file fails, the source section contains an "Error reading file: <exception>" message.
        """
        if not path.is_file():
            return ""

        rel_path = str(path.relative_to(self.root))
        result = [f"<file path=\"{rel_path}\">"]

        if "metrics" in include:
            stats = path.stat()
            result.append(f"<metrics size=\"{stats.st_size}\" />")

        if "callers" in include or "callees" in include:
            result.append(f"<dependencies>\n{self._get_dependencies(path, include)}\n</dependencies>")

        if "source" in include:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                result.append(content)
            except Exception as e:
                result.append(f"Error reading file: {e}")

        result.append("</file>")
        return "\n".join(result)

    def _get_dependencies(self, path: Path, include: List[str]) -> str:
        """
        Collect dependency references for a source file as formatted callee and caller lines.
        
        Parameters:
            path (Path): Path to the source file to analyze; interpreted relative to the repository root.
            include (List[str]): Controls which dependency types to include. Recognized values:
                - "callees": include imported modules as `  - callee: <module>`.
                - "callers": include files that import this module as `  - caller: <path>`.
        
        Returns:
            str: Newline-separated entries such as `  - callee: <module>` and `  - caller: <path>`. Returns an empty string if no dependencies are found.
        """
        deps = []
        rel_path = str(path.relative_to(self.root))

        if "callees" in include:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                imports = re.findall(r"^(?:from|import)\s+([a-zA-Z0-9._-]+)", content, re.MULTILINE)
                for imp in imports:
                    deps.append(f"  - callee: {imp}")
            except Exception:
                pass

        if "callers" in include:
            try:
                module_name = path.stem
                if "__init__" in module_name:
                    module_name = path.parent.name

                cmd = f"grep -lE '(import|from).*\b{module_name}\b' -r . --exclude-dir={{.git,__pycache__,.venv,node_modules}}"
                result = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True)
                for caller in result.stdout.splitlines():
                    if caller.strip() and caller != rel_path:
                        deps.append(f"  - caller: {caller}")
            except Exception:
                pass

        return "\n".join(deps)

    def _extract_symbol(self, path: Path, symbol: str, include: List[str]) -> str:
        """
        Locate and extract the source declaration block for a named symbol from a file and return it as an XML-like element.
        
        Searches the file for a top-level declaration matching the given symbol (supports Python declarations `class`, `def`, `async def` and common JavaScript declaration/assignment forms `function`, `const/let/var <name> =`). If found, returns an XML-like `<symbol>` element containing the symbol name, the file path relative to the instance root, and the declaration plus its indented body (internal blank lines preserved; trailing blank lines removed). If the symbol is not found, returns a self-closing `<symbol ... status="not_found" />` element. On error, returns a self-closing `<symbol ... error="..."/>` element.
        
        Parameters:
            path (Path): Path to the source file to search.
            symbol (str): The symbol name to locate.
            include (List[str]): Ignored by this routine; accepted for interface compatibility.
        
        Returns:
            str: One of:
                - `<symbol name="..." path="...">...source...</symbol>` when the symbol is found;
                - `<symbol name="..." path="..." status="not_found" />` when not found;
                - `<symbol name="..." path="..." error="..."/>` on exception.
        """
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            # Improved regex patterns
            patterns = [
                rf"^class\s+{symbol}\b",
                rf"^def\s+{symbol}\b",
                rf"^\s*async\s+def\s+{symbol}\b",
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

            # Extract block based on indentation
            indent = len(lines[start_line]) - len(lines[start_line].lstrip())
            block = [lines[start_line]]
            for line in lines[start_line+1:]:
                if not line.strip():
                    block.append(line)
                    continue
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent:
                    break
                block.append(line)

            # Trim trailing empty lines
            while block and not block[-1].strip():
                block.pop()

            rel_path = str(path.relative_to(self.root))
            return f"<symbol name=\"{symbol}\" path=\"{rel_path}\">\n" + "\n".join(block) + "\n</symbol>"
        except Exception as e:
            return f"<symbol name=\"{symbol}\" path=\"{path.relative_to(self.root)}\" error=\"{e}\" />"

    def get_risk(self, targets: Optional[List[str]] = None, changed_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Hotspot scores and potential impact analysis."""
        hotspots = {h["path"]: h["changes"] for h in self.get_hotspots(limit=100)}

        relevant_hotspots = []
        if changed_files:
            for f in changed_files:
                if f in hotspots:
                    relevant_hotspots.append({"path": f, "changes": hotspots[f], "risk": "high"})

        return {
            "overall_hotspots": self.get_hotspots(limit=10),
            "impact_analysis": relevant_hotspots
        }

    def get_why(self, target: str) -> str:
        """Extracts architectural decisions related to target from git history."""
        try:
            cmd = f"git log --grep='WHY' --grep='DECISION' --grep='TRADEOFF' -i -- '{target}'"
            result = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True)
            if not result.stdout.strip():
                return f"No documented decisions found for {target}"
            return result.stdout
        except Exception as e:
            return f"Error retrieving decisions: {e}"

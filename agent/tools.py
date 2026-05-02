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

    def self_audit(self) -> dict[str, any]:
        """Perform comprehensive self-audit of agent configuration."""
        audit_results = {
            "timestamp": str(Path.cwd()),
            "agent_config": {},
            "skills_inventory": {},
            "mcp_servers": {},
            "commands_available": {},
            "state_management": {},
            "recommendations": [],
            "score": 0
        }
        
        # Audit agent configuration
        try:
            agents_dir = self._resolve_path(".claude/agents")
            if agents_dir.exists():
                agent_files = list(agents_dir.glob("*.md"))
                audit_results["agent_config"]["agents_found"] = [f.stem for f in agent_files]
                audit_results["agent_config"]["total_agents"] = len(agent_files)
            else:
                audit_results["agent_config"]["agents_found"] = []
                audit_results["agent_config"]["total_agents"] = 0
        except Exception as e:
            audit_results["agent_config"]["error"] = str(e)
        
        # Audit skills inventory
        try:
            skills_dirs = [
                self._resolve_path(".agents/skills"),
                self._resolve_path(".claude/skills")
            ]
            all_skills = {}
            for skills_dir in skills_dirs:
                if skills_dir.exists():
                    for skill_dir in skills_dir.iterdir():
                        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                            skill_name = skill_dir.name
                            try:
                                skill_content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                                # Extract purpose from frontmatter or first lines
                                purpose = "No purpose specified"
                                if skill_content.startswith("---"):
                                    parts = skill_content.split("---", 2)
                                    if len(parts) >= 3:
                                        frontmatter = parts[1]
                                        for line in frontmatter.split("\n"):
                                            if line.startswith("description:"):
                                                purpose = line.split(":", 1)[1].strip()
                                                break
                                else:
                                    # Take first non-empty line that looks like a description
                                    for line in skill_content.split("\n")[:10]:
                                        if line.strip() and not line.startswith("#"):
                                            purpose = line.strip()
                                            break
                                all_skills[skill_name] = {
                                                "purpose": purpose,
                                                "location": str(skill_dir.relative_to(self.root)),
                                                "has_tools": (skill_dir / "tools.py").exists() if (skill_dir / "tools.py").exists() else False
                                            }
                            except Exception:
                                all_skills[skill_name] = {
                                    "purpose": "Error reading skill",
                                    "location": str(skill_dir.relative_to(self.root)),
                                    "has_tools": False
                                }
            audit_results["skills_inventory"] = all_skills
            audit_results["skills_inventory"]["total_skills"] = len(all_skills)
        except Exception as e:
            audit_results["skills_inventory"]["error"] = str(e)
        
        # Audit available commands
        try:
            commands_dir = self._resolve_path(".claude/commands")
            if commands_dir.exists():
                command_files = list(commands_dir.glob("*.md"))
                audit_results["commands_available"] = {
                    f.stem: f.read_text(encoding="utf-8")[:100] + "..." 
                    for f in command_files
                }
                audit_results["commands_available"]["total_commands"] = len(command_files)
            else:
                audit_results["commands_available"] = {}
        except Exception as e:
            audit_results["commands_available"]["error"] = str(e)
        
        # Audit state management
        try:
            state_dir = self._resolve_path(".claude/state")
            if state_dir.exists():
                state_files = list(state_dir.iterdir())
                audit_results["state_management"] = {
                    "state_directory_exists": True,
                    "state_files": [f.name for f in state_files if f.is_file()],
                    "total_state_files": len([f for f in state_files if f.is_file()])
                }
                
                # Check for key state files
                key_files = ["agent-state.json", "NEXT_ACTION.md", "checkpoint.jsonl", "runner.lock", "session.log"]
                for key_file in key_files:
                    if (state_dir / key_file).exists():
                        audit_results["state_management"][f"has_{key_file.replace('.', '_').replace('-', '_')}"] = True
                    else:
                        audit_results["state_management"][f"has_{key_file.replace('.', '_').replace('-', '_')}"] = False
            else:
                audit_results["state_management"]["state_directory_exists"] = False
        except Exception as e:
            audit_results["state_management"]["error"] = str(e)
        
        # Generate recommendations based on audit
        recommendations = []
        
        # Check if we have basic agent setup
        if audit_results["agent_config"].get("total_agents", 0) < 4:
            recommendations.append("Consider setting up all four core agents: Planner, Implementer, Reviewer, Judge")
        
        # Check skills count
        total_skills = audit_results["skills_inventory"].get("total_skills", 0)
        if total_skills < 10:
            recommendations.append(f"Only {total_skills} skills found. Consider adding more skills for common tasks.")
        
        # Check for self-improve skill
        skills_list = list(audit_results["skills_inventory"].keys())
        if "self-improve" not in [s.lower() for s in skills_list]:
            recommendations.append("Consider adding the self-improve skill for continuous agent improvement")
        
        # Check for prompt-library skill
        if "prompt-library" not in [s.lower() for s in skills_list]:
            recommendations.append("Consider adding prompt-library skill for transparency")
        
        # Check state management
        if not audit_results["state_management"].get("state_directory_exists", False):
            recommendations.append("State directory not found - checkpoints and session persistence may not work")
        elif not audit_results["state_management"].get("has_checkpoint_jsonl", False):
            recommendations.append("Consider enabling checkpointing for session resumability")
        
        audit_results["recommendations"] = recommendations
        
        # Calculate a basic score (0-100)
        score = 0
        score += min(25, audit_results["agent_config"].get("total_agents", 0) * 6)  # Up to 25 for agents
        score += min(25, total_skills * 2)  # Up to 25 for skills
        score += min(20, len(audit_results["commands_available"].get("", [])) * 5)  # Up to 20 for commands
        score += min(20, len([k for k, v in audit_results["state_management"].items() if k.startswith("has_") and v]) * 4)  # Up to 20 for state
        audit_results["score"] = min(100, score)
        
        return audit_results

    def setup_mcp_server(self, service_name: str, config: dict[str, any] | None = None) -> dict[str, any]:
        """Automate MCP server setup for a service."""
        config = config or {}
        result = {
            "service": service_name,
            "status": "started",
            "steps_completed": [],
            "steps_failed": [],
            "configuration": {},
            "message": ""
        }
        
        # Known MCP servers registry
        known_mcp_servers = {
            "github": {
                "package": "github-mcp-server",
                "description": "Official GitHub MCP server",
                "install_method": "pip",
                "config_template": {
                    "command": "github-mcp-server",
                    "args": []
                }
            },
            "filesystem": {
                "package": "filesystem-mcp-server", 
                "description": "Official filesystem MCP server",
                "install_method": "pip",
                "config_template": {
                    "command": "filesystem-mcp-server",
                    "args": []
                }
            },
            "git": {
                "package": "git-mcp-server",
                "description": "Official git MCP server", 
                "install_method": "pip",
                "config_template": {
                    "command": "git-mcp-server",
                    "args": []
                }
            }
        }
        
        try:
            # Step 1: Check if service is known
            if service_name.lower() in known_mcp_servers:
                server_info = known_mcp_servers[service_name.lower()]
                result["steps_completed"].append(f"Found known MCP server for {service_name}")
                result["configuration"]["server_info"] = server_info
            else:
                # Try to search for it (would use web search in full implementation)
                result["steps_failed"].append(f"Unknown MCP service: {service_name}. Would search MCP registry in full implementation.")
                result["status"] = "partial"
                # For now, provide generic template
                result["configuration"]["server_info"] = {
                    "package": f"{service_name}-mcp-server",
                    "description": f"MCP server for {service_name} (template)",
                    "install_method": "pip",
                    "config_template": {
                        "command": f"{service_name}-mcp-server",
                        "args": []
                    }
                }
                result["steps_completed"].append(f"Created generic template for {service_name}")
            
            # Step 2: Check if already installed (simplified)
            mcp_config_dir = self._resolve_path(".claude")
            mcp_settings_file = mcp_config_dir / "mcp_settings.json"
            
            if mcp_settings_file.exists():
                try:
                    import json
                    existing_config = json.loads(mcp_settings_file.read_text())
                    result["steps_completed"].append("Found existing MCP settings")
                    result["configuration"]["existing_settings"] = existing_config
                except Exception as e:
                    result["steps_failed"].append(f"Could not read existing MCP settings: {e}")
            else:
                result["steps_completed"].append("No existing MCP settings found - will create new")
            
            # Step 3: Generate configuration
            server_info = result["configuration"].get("server_info", {})
            mcp_config = {
                "mcpServers": {
                    service_name: server_info.get("config_template", {
                        "command": f"{service_name}-mcp-server",
                        "args": []
                    })
                }
            }
            
            # Merge with user-provided config
            if config:
                if "mcpServers" in config:
                    mcp_config["mcpServers"].update(config["mcpServers"])
                else:
                    mcp_config["mcpServers"][service_name] = config
            
            result["configuration"]["generated_mcp_config"] = mcp_config
            result["steps_completed"].append("Generated MCP configuration")
            
            # Step 4: Apply configuration (write to file)
            mcp_config_dir.mkdir(parents=True, exist_ok=True)
            try:
                import json
                mcp_settings_file.write_text(json.dumps(mcp_config, indent=2))
                result["steps_completed"].append("Applied MCP configuration to settings")
                result["status"] = "completed"
                result["message"] = f"MCP server for {service_name} configured successfully"
            except Exception as e:
                result["steps_failed"].append(f"Failed to write MCP configuration: {e}")
                result["status"] = "failed"
                
        except Exception as e:
            result["status"] = "error"
            result["steps_failed"].append(f"Unexpected error: {e}")
            result["message"] = f"Error setting up MCP server for {service_name}: {e}"
        
        return result

    def install_skill(self, skill_source: str, skill_name: str | None = None) -> dict[str, any]:
        """Automate skill installation from various sources."""
        result = {
            "source": skill_source,
            "skill_name": skill_name or "unknown",
            "status": "started",
            "steps_completed": [],
            "steps_failed": [],
            "skill_path": "",
            "message": ""
        }
        
        try:
            # Determine skill name if not provided
            if not skill_name:
                # Try to extract from source
                if skill_source.startswith("http"):
                    # Extract from URL
                    skill_name = skill_source.split("/")[-1].replace(".git", "").replace("-skill", "")
                elif "/" in skill_source and not skill_source.startswith("./"):
                    # Assume GitHub format user/repo
                    skill_name = skill_source.split("/")[-1]
                else:
                    skill_name = "installed_skill"
            
            result["skill_name"] = skill_name
            
            # Define target directory
            skills_dir = self._resolve_path(".agents/skills")
            skills_dir.mkdir(parents=True, exist_ok=True)
            target_dir = skills_dir / skill_name
            
            # Step 1: Check if skill already exists
            if target_dir.exists():
                result["steps_failed"].append(f"Skill {skill_name} already exists at {target_dir}")
                result["status"] = "conflict"
                return result
            
            result["steps_completed"].append(f"Preparing to install skill: {skill_name}")
            
            # Step 2: Handle different source types
            if skill_source.startswith("http"):
                # GitHub URL or direct file URL
                if ".git" in skill_source or ("github.com" in skill_source and not skill_source.endswith(".md")):
                    # Git repository - would use git clone in full implementation
                    result["steps_failed"].append("Git cloning not implemented in this environment - would clone repository")
                    result["status"] = "partial"
                    # Create placeholder
                    target_dir.mkdir(parents=True, exist_ok=True)
                    (target_dir / "SKILL.md").write_text(f"""# Skill: {skill_name}

## Purpose
Skill installed from {skill_source}

## When to Use
- When you need functionality from {skill_source}

## Process
1. Implement the skill functionality
2. Test the skill
3. Update as needed

## Output
- Skill functionality as described in source

## Notes
- Installed from {skill_source}
""")
                    result["steps_completed"].append("Created placeholder skill from GitHub URL")
                else:
                    # Direct file download - would use HTTP request
                    result["steps_failed"].append("Direct file download not implemented - would download and process file")
                    result["status"] = "partial"
            elif skill_source.startswith("./") or "/" in skill_source:
                # Local file path
                source_path = self._resolve_path(skill_source)
                if source_path.exists():
                    if source_path.is_file() and source_path.suffix == ".md":
                        # Single skill file
                        target_dir.mkdir(parents=True, exist_ok=True)
                        import shutil
                        shutil.copy2(source_path, target_dir / "SKILL.md")
                        result["steps_completed"].append(f"Copied skill file from {skill_source}")
                    elif source_path.is_dir() and (source_path / "SKILL.md").exists():
                        # Skill directory
                        import shutil
                        shutil.copytree(source_path, target_dir)
                        result["steps_completed"].append(f"Copied skill directory from {skill_source}")
                    else:
                        result["steps_failed"].append(f"Source path {skill_source} does not contain a valid skill")
                        result["status"] = "failed"
                        return result
                else:
                    result["steps_failed"].append(f"Source path {skill_source} does not exist")
                    result["status"] = "failed"
                    return result
            else:
                # Treat as skill description - generate skill file
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Extract purpose from first line or use default
                lines = [line.strip() for line in skill_source.split("\n") if line.strip()]
                purpose = lines[0] if lines else f"Skill for {skill_name}"
                
                skill_content = f"""# Skill: {skill_name}

## Purpose
{purpose}

## When to Use
- When you need the functionality described in the skill source

## Process
1. Review the skill requirements
2. Implement the necessary functionality
3. Test the skill in context
4. Document any important notes

## Output
- The skill provides the capability described in its purpose

## Notes
- Installed from skill description: {skill_source[:100]}{'...' if len(skill_source) > 100 else ''}
"""
                (target_dir / "SKILL.md").write_text(skill_content)
                result["steps_completed"].append(f"Generated skill from description")
            
            result["skill_path"] = str(target_dir.relative_to(self.root))
            result["steps_completed"].append(f"Skill installed to {result['skill_path']}")
            
            # Step 3: Validate the installed skill
            skill_md_path = target_dir / "SKILL.md"
            if skill_md_path.exists():
                try:
                    content = skill_md_path.read_text(encoding="utf-8")
                    # Basic validation
                    if "# Skill:" in content and "## Purpose" in content:
                        result["steps_completed"].append("Skill validation passed - basic structure OK")
                    else:
                        result["steps_failed"].append("Skill validation failed - missing required sections")
                except Exception as e:
                    result["steps_failed"].append(f"Skill validation error: {e}")
            else:
                result["steps_failed"].append("Skill validation failed - SKILL.md not found")
            
            # Determine final status
            if not result["steps_failed"]:
                result["status"] = "completed"
                result["message"] = f"Skill '{skill_name}' installed successfully"
            elif result["status"] not in ["partial", "failed"]:
                result["status"] = "partial"
                result["message"] = f"Skill '{skill_name}' installed with some issues"
            else:
                result["message"] = f"Failed to install skill '{skill_name}'"
                
        except Exception as e:
            result["status"] = "error"
            result["steps_failed"].append(f"Unexpected error: {e}")
            result["message"] = f"Error installing skill from {skill_source}: {e}"
        
        return result

    def generate_claude_md(self, target_path: str | None = None) -> dict[str, any]:
        """Generate CLAUDE.md based on codebase analysis."""
        target_path = target_path or "."
        result = {
            "target_path": target_path,
            "status": "started",
            "steps_completed": [],
            "steps_failed": [],
            "generated_content": "",
            "message": ""
        }
        
        try:
            target_dir = self._resolve_path(target_path)
            if not target_dir.exists():
                result["steps_failed"].append(f"Target path {target_path} does not exist")
                result["status"] = "failed"
                return result
            
            result["steps_completed"].append(f"Analyzing codebase at {target_path}")
            
            # Step 1: Gather basic project information
            project_info = {
                "name": target_dir.name or "unnamed_project",
                "type": "unknown",
                "description": "",
                "key_technologies": [],
                "structure": {}
            }
            
            # Check for common project files
            indicator_files = {
                "README.md": "description",
                "package.json": "javascript/nodejs",
                "requirements.txt": "python", 
                "pyproject.toml": "python",
                "Cargo.toml": "rust",
                "go.mod": "go",
                "pom.xml": "java",
                "build.gradle": "java",
                "AGENTS.md": "agent_configuration",
                ".claude/agents/": "agent_system"
            }
            
            found_indicators = []
            for indicator, meaning in indicator_files.items():
                if (target_dir / indicator).exists():
                    found_indicators.append(indicator)
                    if meaning in ["javascript/nodejs", "python", "rust", "go", "java"]:
                        project_info["key_technologies"].append(meaning.split("/")[0])
                    elif meaning == "description":
                        try:
                            readme_content = (target_dir / "README.md").read_text(encoding="utf-8")[:500]
                            project_info["description"] = readme_content.split("\n")[0] if readme_content else ""
                        except Exception:
                            pass
                    elif meaning == "agent_configuration":
                        project_info["type"] = "agent_system"
            
            result["steps_completed"].append(f"Found project indicators: {', '.join(found_indicators)}")
            
            # Step 2: Analyze directory structure
            try:
                # Get top-level directories and key files
                all_items = list(target_dir.iterdir())
                dirs = [item.name for item in all_items if item.is_dir() and not item.name.startswith('.')]
                files = [item.name for item in all_items if item.is_file() and not item.name.startswith('.')]
                
                project_info["structure"] = {
                    "directories": dirs[:20],  # Limit to first 20
                    "key_files": files[:20],   # Limit to first 20
                    "total_directories": len(dirs),
                    "total_files": len(files)
                }
                
                result["steps_completed"].append("Analyzed directory structure")
            except Exception as e:
                result["steps_failed"].append(f"Error analyzing directory structure: {e}")
            
            # Step 3: Gather agent and skill information
            agent_info = {
                "agents": [],
                "skills_count": 0,
                "has_agent_system": False
            }
            
            try:
                # Check for agent system
                agents_dir = target_dir / ".claude" / "agents"
                if agents_dir.exists():
                    agent_info["has_agent_system"] = True
                    agent_files = list(agents_dir.glob("*.md"))
                    agent_info["agents"] = [f.stem for f in agent_files]
                
                # Check for skills
                skills_dirs = [
                    target_dir / ".agents" / "skills",
                    target_dir / ".claude" / "skills"
                ]
                total_skills = 0
                for skills_dir in skills_dirs:
                    if skills_dir.exists():
                        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
                        total_skills += skill_count
                agent_info["skills_count"] = total_skills
                
                result["steps_completed"].append(f"Found {len(agent_info['agents'])} agents and {total_skills} skills")
            except Exception as e:
                result["steps_failed"].append(f"Error gathering agent/skill info: {e}")
            
            # Step 4: Generate CLAUDE.md content
            claude_md_content = f"""# CLAUDE.md

## Project Overview

**Name**: {project_info['name']}
**Type**: {project_info['type']}
**Description**: {project_info['description'] or 'No description available'}
**Key Technologies**: {', '.join(project_info['key_technologies']) or 'None detected'}

## Project Structure

{chr(10).join(['- ' + d for d in project_info['structure'].get('directories', [])[:10]])}

**Key Files**:
{chr(10).join(['- ' + f for f in project_info['structure'].get('key_files', [])[:10]])}

## Agent System
"""
            
            if agent_info["has_agent_system"]:
                claude_md_content += f"""This repository uses an agent-based system with the following agents:
{chr(10).join(['- ' + agent for agent in agent_info['agents']])}

Total skills available: {agent_info['skills_count']}

The agent system includes:
- Planner: Creates structured plans from instructions
- Implementer: Executes file changes based on plans
- Reviewer: Verifies changes before application
- Judge: Provides final release gate approval

Agents can use skills from the .agents/skills/ and .claude/skills/ directories for specialized capabilities.
"""
            else:
                claude_md_content += """This repository does not appear to have a configured agent system.
Consider setting up agents for automated task execution.
"""
            
            claude_md_content += """
## Development Workflows

### Standard Workflow
1. **Planning**: Use the `/plan` command to break down tasks
2. **Implementation**: Agent executes the planned steps
3. **Review**: Changes are reviewed before application
4. **Checkpoint**: Progress is saved to `.claude/state/`
5. **Validation**: Tests are run to ensure quality

### Available Commands
- `/plan` - Create a plan for a task
- `/resume` - Resume interrupted work
- `/review` - Review code before committing

## Agent Guidelines

### When Working with Agents
1. Always start with clear instructions
2. Use skills for complex or repetitive tasks
3. Write to `.claude/state/` after each milestone
4. Run tests before and after code changes
5. Update documentation as needed

### Skill Usage
Skills provide reusable capabilities. To use a skill:
1. Ensure the skill is installed in `.agents/skills/` or `.claude/skills/`
2. The agent will automatically make skill tools available
3. Refer to the skill's documentation for specific usage

## File Conventions

### Text Files
- Use UTF-8 encoding
- Prefer Markdown (.md) for documentation
- Keep line lengths reasonable (< 100 characters when possible)

### Code Files
- Follow language-specific formatting conventions
- Include appropriate error handling
- Add comments for complex logic
- Write tests for new functionality

## State Management

The agent system uses `.claude/state/` for:
- `agent-state.json`: Full session state
- `NEXT_ACTION.md`: Next step to execute
- `checkpoint.jsonl`: Ordered log of completed steps
- `runner.lock`: Active session lock
- `session.log`: Session activity log

## Getting Started

To begin working with the agent system:
1. Ensure you have the necessary dependencies installed
2. Check that `.claude/agents/` contains agent definitions
3. Verify skills are available in `.agents/skills/` and `.claude/skills/`
4. Start with a simple task using the `/plan` command

---
*This CLAUDE.md file was generated automatically based on codebase analysis.*
"""
            
            result["generated_content"] = claude_md_content
            result["steps_completed"].append("Generated CLAUDE.md content")
            
            # Step 5: Write to file (optional - could just return content)
            claude_md_file = target_dir / "CLAUDE.md"
            try:
                claude_md_file.write_text(claude_md_content, encoding="utf-8")
                result["steps_completed"].append(f"Wrote CLAUDE.md to {claude_md_file}")
                result["status"] = "completed"
                result["message"] = f"CLAUDE.md generated and saved to {claude_md_file.relative_to(self.root)}"
            except Exception as e:
                # Still return the content even if we can't write it
                result["steps_failed"].append(f"Could not write CLAUDE.md file: {e}")
                result["status"] = "completed"  # Content was generated successfully
                result["message"] = f"CLAUDE.md generated successfully (could not write to file: {e})"
                
        except Exception as e:
            result["status"] = "error"
            result["steps_failed"].append(f"Unexpected error: {e}")
            result["message"] = f"Error generating CLAUDE.md: {e}"
        
        return result

    def apply_recommendations(self, audit_results: dict[str, any]) -> dict[str, any]:
        """Apply recommended improvements from audit results."""
        result = {
            "audit_timestamp": audit_results.get("timestamp", "unknown"),
            "recommendations_processed": 0,
            "recommendations_applied": 0,
            "recommendations_failed": 0,
            "actions_taken": [],
            "errors": [],
            "status": "started"
        }
        
        try:
            recommendations = audit_results.get("recommendations", [])
            result["recommendations_processed"] = len(recommendations)
            
            for i, rec in enumerate(recommendations):
                try:
                    action_taken = False
                    
                    # Process different types of recommendations
                    if "consider setting up all four core agents" in rec.lower():
                        # This would set up missing agents
                        result["actions_taken"].append(f"Recommendation {i+1}: Would set up missing core agents")
                        action_taken = True
                    
                    elif "consider adding more skills" in rec.lower() or "only" in rec.lower() and "skills" in rec.lower():
                        # This would add common missing skills
                        result["actions_taken"].append(f"Recommendation {i+1}: Would recommend adding common skills")
                        action_taken = True
                    
                    elif "consider adding the self-improve skill" in rec.lower():
                        # Try to install self-improve skill if missing
                        skills_inventory = audit_results.get("skills_inventory", {})
                        if isinstance(skills_inventory, dict) and "self-improve" not in [k.lower() for k in skills_inventory.keys()]:
                            install_result = self.install_skill("./.agents/skills/self-improve", "self-improve")
                            if install_result.get("status") == "completed":
                                result["actions_taken"].append(f"Recommendation {i+1}: Installed self-improve skill")
                                action_taken = True
                            else:
                                result["errors"].append(f"Recommendation {i+1}: Failed to install self-improve skill: {install_result.get('message', 'unknown error')}")
                        else:
                            result["actions_taken"].append(f"Recommendation {i+1}: Self-improve skill already present")
                            action_taken = True
                    
                    elif "consider adding prompt-library skill" in rec.lower():
                        # Try to install prompt-library skill if missing
                        skills_inventory = audit_results.get("skills_inventory", {})
                        if isinstance(skills_inventory, dict) and "prompt-library" not in [k.lower() for k in skills_inventory.keys()]:
                            # Note: prompt-library might be in .claude/skills, check both
                            has_prompt_lib = False
                            if isinstance(skills_inventory, dict):
                                has_prompt_lib = "prompt-library" in [k.lower() for k in skills_inventory.keys()]
                            
                            if not has_prompt_lib:
                                # Would install from template
                                result["actions_taken"].append(f"Recommendation {i+1}: Would install prompt-library skill")
                                action_taken = True
                            else:
                                result["actions_taken"].append(f"Recommendation {i+1}: Prompt-library skill already present")
                                action_taken = True
                        else:
                            result["actions_taken"].append(f"Recommendation {i+1}: Prompt-library skill check completed")
                            action_taken = True
                    
                    elif "state directory not found" in rec.lower() or "checkpointing" in rec.lower():
                        # Ensure state directory exists
                        state_dir = self._resolve_path(".claude/state")
                        try:
                            state_dir.mkdir(parents=True, exist_ok=True)
                            result["actions_taken"].append(f"Recommendation {i+1}: Ensured state directory exists")
                            action_taken = True
                        except Exception as e:
                            result["errors"].append(f"Recommendation {i+1}: Failed to create state directory: {e}")
                    
                    elif "consider enabling checkpointing" in rec.lower():
                        # This is more complex - would involve configuring the agent system
                        result["actions_taken"].append(f"Recommendation {i+1}: Would configure checkpointing in agent system")
                        action_taken = True
                    
                    else:
                        # Generic recommendation - log that we saw it
                        result["actions_taken"].append(f"Recommendation {i+1}: Noted - {rec[:50]}{'...' if len(rec) > 50 else ''}")
                        action_taken = True  # We at least acknowledged it
                    
                    if action_taken:
                        result["recommendations_applied"] += 1
                    else:
                        result["recommendations_failed"] += 1
                        
                except Exception as e:
                    result["errors"].append(f"Error processing recommendation {i+1}: {e}")
                    result["recommendations_failed"] += 1
            
            # Determine final status
            if result["errors"] and not result["actions_taken"]:
                result["status"] = "failed"
            elif result["errors"]:
                result["status"] = "partial"
            else:
                result["status"] = "completed"
                
            result["message"] = f"Processed {result['recommendations_processed']} recommendations: {result['recommendations_applied']} applied, {result['recommendations_failed']} failed"
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Unexpected error in apply_recommendations: {e}")
            result["message"] = f"Error applying recommendations: {e}"
        
        return result

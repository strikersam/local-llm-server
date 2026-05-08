"""
fabric_cli.py — Fabric-style prompt pattern CLI for local-llm-server.

Inspired by https://github.com/danielmiessler/fabric — store, retrieve,
compose, and apply reusable AI prompt patterns from the command line.

Usage:
  python scripts/fabric_cli.py list
  python scripts/fabric_cli.py show <pattern>
  python scripts/fabric_cli.py apply <pattern> [--var key=value ...] [--input "text"]
  python scripts/fabric_cli.py stitch <p1> <p2> [<p3> ...] --input "text"
  python scripts/fabric_cli.py save <name> <file>
  python scripts/fabric_cli.py new <name> [--description "desc"]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PATTERNS_DIR = REPO_ROOT / ".claude" / "skills" / "fabric-patterns" / "patterns"

_SAFE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _pattern_path(name: str) -> Path:
    """Validate name and return its resolved path, enforcing containment under PATTERNS_DIR."""
    if not _SAFE_NAME_RE.match(name):
        print(
            f"Invalid pattern name '{name}'. "
            "Names must be lowercase alphanumeric, hyphens, or underscores (max 64 chars).",
            file=sys.stderr,
        )
        sys.exit(1)
    root = PATTERNS_DIR.resolve()
    resolved = (PATTERNS_DIR / f"{name}.md").resolve()
    if not resolved.is_relative_to(root):
        print(f"Pattern name '{name}' resolves outside patterns directory.", file=sys.stderr)
        sys.exit(1)
    return resolved


def _ensure_patterns_dir() -> Path:
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    return PATTERNS_DIR


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Return (meta, body) parsed from optional YAML frontmatter."""
    meta: dict[str, str] = {}
    if not content.startswith("---"):
        return meta, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return meta, content
    for line in parts[1].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, parts[2]


def cmd_list() -> None:
    _ensure_patterns_dir()
    patterns = sorted(PATTERNS_DIR.glob("*.md"))
    if not patterns:
        print("No patterns installed. Use `save` or `new` to add one.")
        return
    for p in patterns:
        meta, _ = _parse_frontmatter(p.read_text())
        desc = meta.get("description", "—")
        print(f"  {p.stem:<24} {desc}")


def cmd_show(name: str) -> None:
    path = _pattern_path(name)
    if not path.exists():
        print(f"Pattern '{name}' not found.", file=sys.stderr)
        sys.exit(1)
    print(path.read_text())


def cmd_apply(name: str, variables: dict[str, str], input_text: str | None) -> None:
    path = _pattern_path(name)
    if not path.exists():
        print(f"Pattern '{name}' not found.", file=sys.stderr)
        sys.exit(1)
    _, body = _parse_frontmatter(path.read_text())
    merged = dict(variables)
    if input_text is not None:
        merged.setdefault("content", input_text)
    elif not sys.stdin.isatty():
        merged.setdefault("content", sys.stdin.read())
    result = body
    for k, v in merged.items():
        result = result.replace(f"{{{{{k}}}}}", v)
    print(result.strip())


def cmd_stitch(pattern_names: list[str], input_text: str) -> None:
    current = input_text
    for name in pattern_names:
        path = _pattern_path(name)
        if not path.exists():
            print(f"Pattern '{name}' not found.", file=sys.stderr)
            sys.exit(1)
        _, body = _parse_frontmatter(path.read_text())
        current = body.replace("{{content}}", current).strip()
    print(current)


def cmd_save(name: str, source: Path) -> None:
    if not source.exists():
        print(f"File '{source}' not found.", file=sys.stderr)
        sys.exit(1)
    _ensure_patterns_dir()
    dest = _pattern_path(name)
    dest.write_text(source.read_text())
    print(f"Pattern '{name}' saved to {dest}")


def cmd_new(name: str, description: str) -> None:
    _ensure_patterns_dir()
    dest = _pattern_path(name)
    if dest.exists():
        print(f"Pattern '{name}' already exists. Edit {dest} directly.")
        sys.exit(1)
    dest.write_text(
        f"---\nname: {name}\ndescription: {description}\nversion: \"1.0.0\"\n---\n"
        "{{content}}\n\n# Write your prompt template here.\n"
        "# Use {{variable_name}} for substitution variables.\n"
    )
    print(f"Created {dest} — edit it to add your prompt template.")


def _parse_vars(raw: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            print(f"Bad --var format (expected key=value): {item}", file=sys.stderr)
            sys.exit(1)
        k, _, v = item.partition("=")
        out[k.strip()] = v.strip()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fabric-style prompt pattern CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List all available patterns")

    p_show = sub.add_parser("show", help="Print raw pattern content")
    p_show.add_argument("name")

    p_apply = sub.add_parser("apply", help="Apply a pattern (renders template)")
    p_apply.add_argument("name")
    p_apply.add_argument("--var", action="append", default=[], metavar="key=value",
                         help="Variable substitution (repeatable)")
    p_apply.add_argument("--input", dest="input_text", default=None,
                         help="Input text (defaults to stdin)")

    p_stitch = sub.add_parser("stitch", help="Chain patterns in sequence")
    p_stitch.add_argument("patterns", nargs="+")
    p_stitch.add_argument("--input", dest="input_text", required=True)

    p_save = sub.add_parser("save", help="Import a pattern from a file")
    p_save.add_argument("name")
    p_save.add_argument("file", type=Path)

    p_new = sub.add_parser("new", help="Scaffold a blank pattern")
    p_new.add_argument("name")
    p_new.add_argument("--description", default="A custom prompt pattern")

    args = parser.parse_args()

    if args.cmd == "list":
        cmd_list()
    elif args.cmd == "show":
        cmd_show(args.name)
    elif args.cmd == "apply":
        cmd_apply(args.name, _parse_vars(args.var), args.input_text)
    elif args.cmd == "stitch":
        cmd_stitch(args.patterns, args.input_text)
    elif args.cmd == "save":
        cmd_save(args.name, args.file)
    elif args.cmd == "new":
        cmd_new(args.name, args.description)


if __name__ == "__main__":
    main()

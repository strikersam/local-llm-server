# Skill: sandboxed-exec

## Purpose
Run shell commands or code snippets in an isolated subprocess environment, preventing side effects from leaking into the host workspace. Mirrors the "Modal Sandbox" pattern described in the OpenAI Agents SDK blog post — give an agent a safe "home computer" to work on.

## When to Use
- You need to run untrusted or exploratory code (e.g. test a one-off script, validate a dependency, try a risky refactor) without touching the real working tree.
- You want to verify that generated code actually executes before committing it.
- You need a clean-room environment (fresh temp dir, isolated env vars) for reproducible testing.

## How It Works
1. Creates a temporary directory as the sandbox root.
2. Copies (or writes) the target files into the sandbox.
3. Executes the requested command inside that directory with a sanitised environment.
4. Captures stdout, stderr, and exit code.
5. Reports results back — nothing is written to the real workspace unless explicitly requested.

## Usage

```
@sandboxed-exec
command: <shell command to run>
files:   <optional list of workspace-relative files to copy into sandbox>
write_back: <true|false — default false>
```

### Example — validate a generated script before saving
```
@sandboxed-exec
command: python validate.py
files: [scripts/validate.py, data/sample.json]
write_back: false
```

### Example — run tests in isolation
```
@sandboxed-exec
command: npm test
files: [src/, package.json, tsconfig.json]
write_back: false
```

## Steps (for Claude to follow)

1. **Identify** the command and files from the invocation.
2. **Create sandbox**:
   ```bash
   SANDBOX=$(mktemp -d)
   ```
3. **Copy files** into `$SANDBOX` preserving relative paths.
4. **Execute** with a clean environment:
   ```bash
   cd "$SANDBOX" && env -i HOME="$SANDBOX" PATH="/usr/local/bin:/usr/bin:/bin" <command>
   ```
5. **Capture** exit code, stdout, stderr.
6. **Report** full output. If `write_back: true` and exit code is 0, copy results back to workspace.
7. **Cleanup** sandbox dir.

## Security Notes
- Never pass host secrets or API keys into the sandbox unless explicitly needed.
- `write_back` defaults to `false` — always confirm before overwriting workspace files.
- For long-running or GPU-intensive tasks, see the `parallel-agents` skill instead.

## Output Format
```
SANDBOX RESULT
==============
Exit code : 0
Command   : <command>
Stdout    :
  <stdout>
Stderr    :
  <stderr>
Write-back: false (no workspace files modified)
```

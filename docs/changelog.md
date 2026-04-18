# Changelog

## [Unreleased]

### Added
- `sandboxed-exec` skill: run commands/code in an isolated temp-dir sandbox before touching the real workspace, mirroring the Modal Sandbox isolation pattern.
- `parallel-agents` skill: decompose a task into N independent subtasks dispatched as parallel subagents with `first-wins`, `collect-all`, or `best-of` aggregation strategies — inspired by the Modal + OpenAI Agents SDK parallel coding-agent architecture.
- `agent-harness` skill: structured agent loop scaffolding (task → capabilities → iterative tool execution → stop condition) based on the OpenAI Agents SDK harness pattern.

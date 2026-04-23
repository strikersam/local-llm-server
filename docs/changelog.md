# Changelog

## [Unreleased]

### Added
- **Qwen3.6-35B model support**: Added routing and registry support for the Qwen3.6-35B multimodal model, a 35B parameter MoE model with 128K context window, superior to existing Qwen3-Coder models in general capabilities and multimodal support.
- **`task-alive-updates` skill**: Heartbeat/keep-alive for long-running agent tasks. Emits `[ALIVE]` status lines at configurable intervals so operators know tasks are still progressing; includes `heartbeat.sh` bash helper for shell-based agents. Inspired by Copilot mission control's `copilot_mission_control_task_alive_updates` feature flag.
- **`resource-panel` skill**: Single-pane-of-glass summary of all resources an agent session touched (files read/written, URLs fetched, tools called, new dependencies). Includes `summarise.sh` for git-diff-based auto-generation. Inspired by Copilot's `copilot_resource_panel` feature flag.
- **`duplicate-thread` skill**: Clone an existing plan/task thread to explore an alternative approach without losing the original. Supports fork metadata (`meta.json`), plan stamping, and merge/abandon lifecycle. Inspired by Copilot's `copilot_duplicate_thread` feature flag. Includes `duplicate.sh` shell helper.

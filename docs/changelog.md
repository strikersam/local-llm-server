# Changelog

## [Unreleased]

### Added
- **prompt-transparency skill** (`.claude/skills/prompt-transparency/SKILL.md`): New skill that audits and surfaces all implicit behavioral instructions embedded in the repo's agent/skill definitions, generating a human-readable transparency report. Inspired by the CL4R1T4S project (github.com/elder-plinius/CL4R1T4S).
- **system-prompt-audit skill** (`.claude/skills/system-prompt-audit/SKILL.md`): Audits all system-level instructions for consistency, conflicts, and safety issues. Detects duplicate roles, contradictory constraints, and missing guardrails. Can block merges when critical issues are found.
- **prompt-library skill** (`.claude/skills/prompt-library/SKILL.md`): Maintains a versioned, browsable `prompts/` directory that mirrors all active agent and skill behavioral definitions — making the repo's AI instructions fully transparent and auditable.
- **prompts/ directory**: A public, versioned library of all behavioral instructions active in this repo. Includes `README.md` (index), `TRANSPARENCY.md` (plain-language behavioral explanation), and `CHANGELOG.md` (history of prompt changes). Directly inspired by CL4R1T4S's mission of AI system prompt transparency.

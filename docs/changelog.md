# Changelog

## [Unreleased]

### Added
- `training-stability-monitor` skill: Diagnoses LLM training instability — loss spikes, gradient norm issues, LR schedule validation, and loss plateaus with recovery recommendations
- `lr-schedule-advisor` skill: Advises on learning rate schedules for transformer/LLM training including warmup strategies, cosine decay formulas, and heuristics by model size
- `data-quality-audit` skill: Audits training data and tokenizer pipelines for quality issues including token length distribution, deduplication, fertility checks, and content quality signals
- `checkpoint-strategy` skill: Designs and validates checkpointing strategies for LLM training runs with recovery playbooks and storage estimation
- `tokenizer-diagnostics` skill: Deep-dive diagnostics for tokenizer behavior including round-trip consistency, numeric tokenization, whitespace handling, and vocabulary coverage checks

These skills are inspired by advanced LLM-from-scratch practitioner insights around the underdocumented aspects of training large language models: data quality, training stability, learning rate scheduling, checkpointing, and tokenizer correctness.

# Skill: training-stability-monitor

## Purpose
Monitor and diagnose LLM/ML training instability — loss spikes, exploding gradients, dead neurons, and learning rate mismatches. Surfaces actionable fixes before they derail a training run.

## Trigger
Use when:
- A training loss curve shows spikes or divergence
- Gradients are exploding or vanishing
- Model outputs collapse (repetition, gibberish, empty)
- You want a pre-flight check before a long training run

## What It Does
1. **Scans training logs** for loss spike signatures (sudden >2x jump in loss)
2. **Checks gradient norms** — flags if norm exceeds configured threshold (default: 1.0)
3. **Validates LR schedule** — warns if no warmup is configured, or if LR is too high for model size
4. **Checks batch size vs model size ratio** — common source of instability
5. **Detects loss plateau** — flat loss for N steps may indicate dead optimizer state
6. **Recommends recovery steps** — rollback checkpoint, reduce LR, increase gradient clipping

## Usage
```
/training-stability-monitor [log_file_or_directory] [--threshold 1.0] [--window 100]
```

## Output Format
```
=== Training Stability Report ===
[PASS/WARN/FAIL] Loss Spike Detection
[PASS/WARN/FAIL] Gradient Norm
[PASS/WARN/FAIL] LR Schedule
[PASS/WARN/FAIL] Batch Size Ratio
[PASS/WARN/FAIL] Loss Plateau

CRITICAL ISSUES: N
WARNINGS: N

Recommended Actions:
1. ...
```

## Key Lessons (from LLM-from-scratch practitioners)
- **Loss spikes are normal but recoverable** — the fix is gradient clipping + LR warmup, not stopping the run
- **Gradient norm logging is non-negotiable** — without it you're flying blind
- **Warmup is mandatory** — jumping to peak LR on step 0 destabilizes attention weights
- **Save checkpoints every N steps** — not just at epoch boundaries; spikes need rollback points
- **BF16 > FP16** for stability on modern hardware; overflow is silent in FP16

## Integration Points
- Works alongside `debug-tracer` for step-level tracing
- Works alongside `insights` for surfacing patterns across runs
- Can feed into `session-handoff` to carry stability context across sessions

## Example Checks Performed

### Loss Spike Detection
```python
# Pseudocode for spike detection
window = losses[-100:]
baseline = median(window[:-10])
current = window[-1]
if current > baseline * 2.5:
    flag("LOSS_SPIKE", step=current_step, magnitude=current/baseline)
```

### Gradient Norm Check
```python
# Recommended clipping
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
# If norm frequently exceeds 5.0, reduce learning rate
```

### LR Warmup Validation
```python
# Minimum warmup = 1% of total steps, recommended = 2-5%
# Cosine decay after warmup is most stable
if warmup_steps < total_steps * 0.01:
    warn("Insufficient warmup — risk of attention instability in early steps")
```

## Notes
- This skill is read-only and diagnostic — it never modifies training code automatically
- For code-level fixes, pair with `implementer` agent
- Loss curves should be logged at every step, not averaged over epochs, for this skill to work

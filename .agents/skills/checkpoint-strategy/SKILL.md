# Skill: checkpoint-strategy

## Purpose
Design and validate checkpointing strategies for LLM training runs. One of the most painful lessons from building LLMs from scratch: losing 12 hours of compute to a spike you can't roll back from.

## Trigger
Use when:
- Starting a new training run (set checkpointing policy upfront)
- After a loss spike — determine best checkpoint to resume from
- Evaluating storage vs safety tradeoffs for checkpoint frequency
- Migrating training across hardware or cloud providers

## Background
From practitioners:

> "Checkpointing feels like overhead until you need it. Then it's the only thing that matters. Save more often than you think you need to, in at least two formats."

Key lessons:
1. **Step-based checkpointing > epoch-based** — LLM epochs are often thousands of hours
2. **Save optimizer state** — resuming without optimizer state restarts Adam's momentum from zero
3. **Rolling window** — keep last N checkpoints, not just the best; spikes happen after "best" 
4. **Two formats** — full checkpoint for resuming, sharded for fast loading at inference
5. **Validate before deleting** — always verify a checkpoint loads before removing older ones

## Usage
```
/checkpoint-strategy [total_steps] [step_duration_seconds] [storage_budget_gb] [--model_size_gb N]
```

## Checkpoint Policy Templates

### Conservative (Recommended for First Runs)
```yaml
checkpoint_policy:
  frequency: every_500_steps
  keep_last: 10
  keep_milestone: [1000, 5000, 10000, 25000, ...]  # powers of 2 * 1000
  save_optimizer: true
  save_formats:
    - full_state_dict    # for resuming
    - safetensors        # for inference/sharing
  validate_on_save: true
  async_save: true       # don't block training
```

### Aggressive (Long Runs with Stable Training)
```yaml
checkpoint_policy:
  frequency: every_2000_steps  
  keep_last: 5
  keep_milestone: [10000, 50000, 100000]
  save_optimizer: true
  emergency_save_on: 
    - loss_spike_detected    # triggers immediate save before rollback
    - gradient_norm_exceeded
```

### Storage Estimation
```
checkpoint_size ≈ model_params * 4 bytes (fp32) * 3  # weights + optimizer (2x for Adam)
Example: 1B param model ≈ 1B * 4 * 3 = 12GB per checkpoint

With keep_last=10:  120GB
With milestones:    add ~60GB
Total budget:       ~180GB for 1B model
```

## Recovery Playbook

### After a Loss Spike
```
1. DO NOT stop training immediately — wait 50-100 steps to see if it self-recovers
2. If not recovering:
   a. Identify last stable checkpoint (loss < spike_value * 1.1)
   b. Load that checkpoint (weights + optimizer state)
   c. Reduce LR by 50% for next 500 steps
   d. Skip or reshuffle the data batch that caused the spike
   e. Resume with gradient clipping set tighter (0.5 instead of 1.0)
```

### Resuming Across Hardware
```
1. Save as full state dict (not FSDP shards — these are hardware-specific)
2. Re-shard on new hardware after loading
3. Verify optimizer state loaded: check that loss continues smoothly from where it left off
   (sudden drop suggests optimizer reset)
```

## Output Format
```
=== Checkpoint Strategy Report ===
Total Steps:        [N]
Step Duration:      [seconds]
Total Training Time:[hours]
Storage Budget:     [GB]
Model Size:         [GB]

Recommended Policy:
  Frequency:        every [N] steps ([hours] apart)
  Keep Last:        [N] checkpoints ([GB] rolling)
  Milestone Steps:  [list]
  Total Storage:    [GB] estimated

Risk Assessment:
  Max Data Loss on Failure: [hours] of training
  Recovery Options:         [N] rollback points

Warnings:
  - [any issues with proposed strategy]
```

## Integration Points
- Pairs with `training-stability-monitor` — spike detection can trigger emergency checkpoint
- Pairs with `session-handoff` — checkpoint metadata should be included in handoffs
- Pairs with `release-readiness` — checkpoint validation before model release

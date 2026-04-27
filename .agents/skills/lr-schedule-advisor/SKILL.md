# Skill: lr-schedule-advisor

## Purpose
Advise on learning rate schedules for transformer/LLM training. One of the most under-documented aspects of building LLMs from scratch — the schedule matters as much as the peak LR value.

## Trigger
Use when:
- Starting a new training run and unsure about LR settings
- Training is unstable and you suspect LR is the cause
- You want to compare schedule strategies (cosine, linear, constant+decay)
- Fine-tuning a pretrained model and need different LR guidance

## Background (Why This Matters)
From practitioners who have built LLMs from scratch:

> "The learning rate schedule is not a hyperparameter you tune once. It interacts with model size, batch size, sequence length, and even your tokenizer vocabulary size. Most tutorials give you a single number and move on."

Key insights:
1. **Warmup steps prevent early attention collapse** — Q/K/V projections are random at init; high LR scrambles them before they can learn
2. **Peak LR scales with batch size** — linear scaling rule: if you 2x batch size, 2x LR (approximately)
3. **Cosine decay outperforms linear** for most transformer workloads
4. **The final LR floor matters** — 10% of peak LR is a common floor; going to zero wastes compute
5. **Cooldown phase** — last 10% of training at low LR stabilizes the model for inference

## Usage
```
/lr-schedule-advisor [model_size] [batch_size] [total_steps] [--task pretrain|finetune|rlhf]
```

## Output Format
```
=== LR Schedule Recommendation ===
Model Size:     [params]
Batch Size:     [tokens or samples]
Total Steps:    [N]
Task:           [pretrain|finetune|rlhf]

Recommended Schedule:
  Peak LR:        [value]
  Warmup Steps:   [N] ([%] of total)
  Schedule Type:  cosine
  Floor LR:       [value] ([%] of peak)
  Cooldown Steps: [N]

Formula:
  lr(step) = ...

Warnings:
  - [any detected issues]
```

## Schedule Formulas

### Cosine with Warmup (Recommended for Pretraining)
```python
def get_lr(step, warmup_steps, total_steps, max_lr, min_lr):
    if step < warmup_steps:
        # Linear warmup
        return max_lr * (step / warmup_steps)
    
    # Cosine decay
    progress = (step - warmup_steps) / (total_steps - warmup_steps)
    cosine_decay = 0.5 * (1 + math.cos(math.pi * progress))
    return min_lr + (max_lr - min_lr) * cosine_decay
```

### Peak LR Heuristics by Model Size
| Params     | Recommended Peak LR | Notes                          |
|------------|--------------------|---------------------------------|
| < 100M     | 3e-4 to 6e-4       | Standard transformer small      |
| 100M–1B    | 1e-4 to 3e-4       | Chinchilla-optimal range        |
| 1B–10B     | 5e-5 to 1e-4       | Reduce if seeing instability    |
| > 10B      | 1e-5 to 5e-5       | Requires careful monitoring     |

### Warmup Step Heuristics
| Training Duration | Warmup %  |
|-------------------|-----------|
| < 10K steps       | 5–10%     |
| 10K–100K steps    | 2–5%      |
| > 100K steps      | 1–2%      |

## Fine-tuning vs Pretraining
- **Fine-tuning**: Use 10x smaller peak LR than pretraining; shorter warmup (0.5–1%)
- **RLHF/PPO**: LR must be very small (1e-6 to 1e-5); schedule is less critical than stability
- **LoRA/PEFT**: LR can be higher (1e-4 to 1e-3) since only adapter weights update

## Common Mistakes
1. Using Adam's default LR (1e-3) for transformers — this is almost always too high
2. No warmup when resuming from checkpoint — the optimizer state is warm but LR resets cold
3. Forgetting to scale LR when changing batch size mid-training
4. Using the same schedule for encoder-only vs decoder-only models

## Integration Points
- Pairs with `training-stability-monitor` to diagnose LR-related instability
- Pairs with `insights` to compare schedule experiments across runs

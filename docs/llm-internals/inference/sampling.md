# Sampling Strategies Internals

How LLMs choose the next token from the probability distribution.

## The Output Distribution

After the final transformer layer and LM head:
```
logits = W_out · hidden_state   (shape: vocab_size, e.g., 32000)
probs  = softmax(logits)        (sums to 1.0)
```

The model outputs a probability for **every token in the vocabulary**.

## Greedy Decoding

Always pick the highest-probability token:
```python
next_token = argmax(probs)
```

**Pros:** Deterministic, fast  
**Cons:** Repetitive, locally optimal but globally suboptimal  

## Temperature Sampling

Scale logits before softmax to control "sharpness":
```python
scaled_logits = logits / temperature
probs = softmax(scaled_logits)
next_token = sample(probs)
```

| Temperature | Effect |
|---|---|
| T → 0 | → Greedy (deterministic) |
| T = 1.0 | Original distribution |
| T > 1.0 | Flatter (more random) |
| T < 1.0 | Sharper (more focused) |

## Top-k Sampling

Only sample from the `k` most likely tokens:
```python
top_k_probs, top_k_indices = topk(probs, k)
top_k_probs = top_k_probs / sum(top_k_probs)  # renormalize
next_token = sample(top_k_probs, top_k_indices)
```

**Problem:** `k` is fixed regardless of distribution shape — sometimes all probability is concentrated in 2 tokens, sometimes spread across 200.

## Top-p (Nucleus) Sampling

Dynamically choose the smallest set of tokens whose cumulative probability ≥ p:

```python
sorted_probs = sort(probs, descending=True)
cumulative = cumsum(sorted_probs)
# Keep tokens until cumulative prob >= p
cutoff_index = first_index_where(cumulative >= p)
nucleus = sorted_probs[:cutoff_index + 1]
nucleus = nucleus / sum(nucleus)  # renormalize
next_token = sample(nucleus)
```

**Example (p=0.9):**
```
Token   Prob   Cumulative
"cat"   0.45   0.45
"dog"   0.30   0.75
"bird"  0.15   0.90  ← cutoff here
"fish"  0.05   0.95
...
```
Sample from {"cat", "dog", "bird"} only.

## Min-p Sampling

Filter tokens below `min_p × max_prob`:
```python
threshold = min_p * max(probs)
filtered = probs[probs >= threshold]
```

More adaptive than top-k, simpler than top-p. Growing in popularity (e.g., in llama.cpp).

## Repetition Penalty

Reduce probability of already-generated tokens:
```python
for token_id in generated_tokens:
    if logits[token_id] > 0:
        logits[token_id] /= repetition_penalty
    else:
        logits[token_id] *= repetition_penalty
```

`repetition_penalty = 1.0` means no penalty; `1.3` is a common value.

## Beam Search

Maintain `k` candidate sequences simultaneously:
```
Beam width = 3, step 1:
  "The cat" (score: -0.5)
  "The dog" (score: -0.7)
  "A cat"   (score: -0.9)

Step 2 (expand each beam, keep top 3):
  "The cat sat"  (score: -0.8)
  "The cat is"   (score: -1.1)
  "The dog sat"  (score: -1.2)
```

**Pros:** Higher BLEU scores for translation/summarization  
**Cons:** Slow (k× more compute), often produces generic/safe text

## Typical Production Settings

| Use Case | Temperature | Top-p | Top-k |
|---|---|---|---|
| Code generation | 0.2 | 0.95 | 50 |
| Creative writing | 0.8-1.0 | 0.95 | - |
| Chat/QA | 0.7 | 0.9 | - |
| Classification | 0.0 (greedy) | - | - |

## Logit Processors (Structured Output)

For constrained generation (JSON, code, etc.), logit processors mask invalid tokens at each step:

```python
# Only allow valid JSON tokens at each position
valid_tokens = json_schema.get_valid_next_tokens(current_state)
mask = create_mask(vocab_size, valid_tokens)
logits = logits + mask  # -inf for invalid tokens
```

Used in: **Outlines**, **guidance**, **llama.cpp grammars**

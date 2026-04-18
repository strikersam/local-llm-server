# Attention Mechanisms Internals

## Why Attention?

Before attention, RNNs processed sequences step-by-step, losing long-range context. Attention allows every token to directly reference any other token in O(1) steps.

## Scaled Dot-Product Attention

```
Attention(Q, K, V) = softmax(QKᵀ / √d_k) · V
```

### Step-by-step

1. **Project** input `x` into Q, K, V using learned weight matrices:
   ```
   Q = x · Wq  (shape: seq_len × d_k)
   K = x · Wk  (shape: seq_len × d_k)
   V = x · Wv  (shape: seq_len × d_v)
   ```

2. **Compute scores** (how much each token attends to each other):
   ```
   scores = Q · Kᵀ / √d_k   (shape: seq_len × seq_len)
   ```

3. **Apply causal mask** (decoder-only): set future positions to `-inf`

4. **Softmax** to get attention weights (probabilities summing to 1)

5. **Weighted sum** of values:
   ```
   output = softmax(scores) · V
   ```

### Why √d_k scaling?

Without scaling, for large `d_k` the dot products grow in magnitude, pushing softmax into regions with very small gradients. Dividing by `√d_k` keeps gradients stable.

## Multi-Head Attention (MHA)

```python
MultiHead(Q, K, V) = Concat(head_1, ..., head_h) · Wo

where head_i = Attention(Q·Wq_i, K·Wk_i, V·Wv_i)
```

- Each head uses `d_k = d_model / h` dimensions
- Different heads can learn different types of relationships
  - Head 1: syntactic dependencies
  - Head 2: coreference
  - Head 3: positional relationships
  - etc.

### Parameter count for MHA:
```
Wq: d_model × d_model
Wk: d_model × d_model  
Wv: d_model × d_model
Wo: d_model × d_model
Total: 4 × d_model²
```

## Variants

### Grouped Query Attention (GQA)
Used in LLaMA 2/3, Mistral. Multiple query heads share a single K/V head.

```
h_q query heads → h_kv key/value heads  (h_kv < h_q)
```

**Benefits**: Reduces KV cache memory by `h_q / h_kv` factor.

### Multi-Query Attention (MQA)
Extreme case of GQA: all queries share **one** K/V head.

```
h_q query heads → 1 key head, 1 value head
```

Used in Falcon, early PaLM.

### Flash Attention
An I/O-aware exact attention algorithm that avoids materializing the full attention matrix:

- **Standard**: O(N²) memory (stores full N×N attention matrix)
- **Flash Attention**: O(N) memory by computing in tiles
- Same mathematical result, ~2-4× faster in practice

### Sliding Window Attention
Used in Mistral. Each token attends only to a window of W previous tokens:

```
Effective receptive field grows with layers:
Layer 1: window W
Layer 2: window 2W  
Layer k: window k×W
```

## Attention Complexity

| Variant | Memory | Compute |
|---|---|---|
| Standard MHA | O(N²) | O(N²d) |
| Flash Attention | O(N) | O(N²d) |
| Sliding Window | O(NW) | O(NWd) |
| Linear Attention | O(N) | O(Nd²) |

## Causal Masking

For autoregressive (decoder) models, the attention mask prevents attending to future tokens:

```
Mask:
Position: 1  2  3  4  5
Token 1:  ✓  ✗  ✗  ✗  ✗
Token 2:  ✓  ✓  ✗  ✗  ✗
Token 3:  ✓  ✓  ✓  ✗  ✗
Token 4:  ✓  ✓  ✓  ✓  ✗
Token 5:  ✓  ✓  ✓  ✓  ✓
```

This enables parallel training (all positions computed simultaneously) while maintaining autoregressive generation property.

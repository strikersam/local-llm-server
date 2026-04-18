# KV Cache Internals

KV Cache is one of the most important optimizations in LLM inference. Without it, generation would be impractically slow.

## The Problem: Redundant Computation

During autoregressive generation, each new token requires computing attention over the **entire sequence so far**.

Without caching, generating token `t` requires:
```
Compute K, V for positions 0..t
Compute attention(Q_t, K_{0..t}, V_{0..t})
```

For a sequence of length T, total compute = O(T²) — quadratic!

## The Solution: Cache K and V

Since K and V for previous tokens **never change**, we can cache them:

```
Step 1: Process "The cat"
  → Compute K,V for ["The", "cat"]
  → Cache: {K: [K_The, K_cat], V: [V_The, V_cat]}
  → Output: "sat"

Step 2: Process "sat" (new token only)
  → Compute K,V for ["sat"] only
  → Load cached K,V for ["The", "cat"]
  → Append: {K: [..., K_sat], V: [..., V_sat]}
  → Output: "on"
```

Each generation step is now O(T) instead of O(T²).

## Memory Layout

For a model with:
- `L` layers
- `H` attention heads  
- `d_k` head dimension
- `B` batch size
- `T` sequence length

KV Cache size:
```
Memory = 2 × L × H × d_k × B × T × dtype_bytes

Example (LLaMA-2 7B, fp16, batch=1, T=2048):
  = 2 × 32 × 32 × 128 × 1 × 2048 × 2 bytes
  = 2 × 32 × 32 × 128 × 2048 × 2
  ≈ 1.07 GB
```

## KV Cache with Grouped Query Attention

GQA reduces KV cache size proportionally:

```
Standard MHA (32 heads):  Cache = 2 × 32 × d_k × T
GQA (8 KV groups):        Cache = 2 × 8 × d_k × T   (4× smaller!)
MQA (1 KV group):         Cache = 2 × 1 × d_k × T   (32× smaller!)
```

This is why GQA/MQA are critical for serving large context windows.

## Paged Attention (vLLM)

Traditional KV cache requires **contiguous memory** per sequence. This causes:
- Memory fragmentation
- Inability to share prefixes across requests
- Fixed max sequence allocation

**PagedAttention** (Kwon et al., 2023) uses virtual memory paging:

```
Physical KV blocks (pages of K blocks, e.g., 16 tokens each)
     ┌────┐  ┌────┐  ┌────┐
     │ P1 │  │ P2 │  │ P3 │
     └────┘  └────┘  └────┘

Sequence A maps to: [P1, P3]       (non-contiguous OK)
Sequence B maps to: [P2, P1, ...]  (can share P1 if prefix matches)
```

**Benefits:**
- Near-zero memory waste (< 4%)
- **Prefix sharing**: multiple requests with same system prompt share KV blocks
- Higher throughput via better batch scheduling

## Quantization of KV Cache

KV cache can be stored in lower precision:

| Precision | Memory vs FP16 | Quality Impact |
|---|---|---|
| FP16 | 1× (baseline) | None |
| INT8 | 0.5× | Minimal |
| INT4 | 0.25× | Small |
| FP8 | 0.5× | Minimal |

Techniques: **SmoothQuant**, **KIVI** (INT2 KV cache), **KVSharer**

## Prefill vs Decode Phase

LLM inference has two distinct phases:

```
PREFILL (prompt processing)
├── Process all prompt tokens in parallel
├── Compute-bound (like training)
├── Build initial KV cache
└── Output: first generated token

DECODE (token generation)  
├── Process one token at a time
├── Memory-bandwidth-bound (KV cache reads dominate)
├── Update KV cache each step
└── Output: subsequent tokens
```

This asymmetry is why **speculative decoding** is effective — prefill is cheap relative to decode.

## Speculative Decoding

Use a small "draft" model to generate candidate tokens, then verify with the large model in parallel:

```
1. Draft model generates k tokens speculatively
2. Large model verifies all k tokens in ONE forward pass (prefill-like)
3. Accept tokens up to first mismatch
4. Average accepted tokens > 1 per large model call → speedup
```

Typical speedup: **2-3×** with a good draft model.

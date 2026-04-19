# Positional Encoding Internals

Transformers process all tokens in parallel — they have no inherent notion of order. Positional encoding injects position information into the model.

## Sinusoidal Positional Encoding (Original Transformer)

```
PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```

- `pos` = position in sequence
- `i` = dimension index
- `d_model` = embedding dimension

**Properties:**
- Each position has a unique encoding
- Fixed, not learned
- Can extrapolate beyond training sequence length (in theory)
- Relative positions can be computed via linear transformations

## Learned Positional Embeddings

Used in GPT-2, BERT:
```python
position_embedding = nn.Embedding(max_seq_len, d_model)
x = token_embedding + position_embedding[positions]
```

Simple and effective but **cannot extrapolate** beyond `max_seq_len`.

## Rotary Positional Embedding (RoPE)

Used in: LLaMA, GPT-NeoX, PaLM, Mistral, Qwen

Instead of adding position info to embeddings, RoPE **rotates** Q and K vectors by position-dependent angles before computing attention.

```
f(q, m) = q · e^(imθ)   (complex notation)
```

For 2D vectors:
```
[q1]   [cos(mθ)  -sin(mθ)] [q1]
[q2] = [sin(mθ)   cos(mθ)] [q2]
```

**Key properties:**
- Relative position is encoded in the dot product: `<Rₘq, Rₙk> = <q, Rₙ₋ₘk>`
- Works with **grouped query attention**
- Better length extrapolation than learned embeddings
- Efficient: only applied to Q and K, not V

### RoPE Scaling for Long Contexts

To extend context beyond training length, scale the rotation angles:

```python
# YaRN (Yet another RoPE extensioN) scaling
scaled_freqs = original_freqs / scale_factor
```

Techniques: **linear scaling**, **NTK-aware scaling**, **YaRN**, **LongRoPE**

## ALiBi (Attention with Linear Biases)

Used in: BLOOM, MPT

Instead of adding positional encoding to embeddings, add a **bias** to attention scores:

```
score(i, j) = qᵢ · kⱼᵀ / √d_k  -  m · |i - j|
```

Where `m` is a head-specific slope.

**Properties:**
- No position embeddings at all
- Strong length extrapolation
- Simple implementation

## Comparison

| Method | Learned | Extrapolates | Used In |
|---|---|---|---|
| Sinusoidal | No | Poor | Original Transformer |
| Learned | Yes | No | GPT-2, BERT |
| RoPE | No | Good (with scaling) | LLaMA, Mistral |
| ALiBi | No | Excellent | BLOOM, MPT |
| Relative PE | Partial | Moderate | T5, Transformer-XL |

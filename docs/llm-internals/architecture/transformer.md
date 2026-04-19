# Transformer Architecture Internals

The Transformer is the foundational architecture behind modern LLMs. Introduced in *"Attention Is All You Need"* (Vaswani et al., 2017).

## High-Level Structure

```
Input Tokens
    │
    ▼
Token Embeddings + Positional Encoding
    │
    ▼
┌─────────────────────────────┐
│   Transformer Block × N     │
│  ┌───────────────────────┐  │
│  │  Multi-Head Attention │  │
│  └───────────┬───────────┘  │
│              │ + Residual   │
│  ┌───────────▼───────────┐  │
│  │    Layer Norm         │  │
│  └───────────┬───────────┘  │
│              │              │
│  ┌───────────▼───────────┐  │
│  │  Feed-Forward Network │  │
│  └───────────┬───────────┘  │
│              │ + Residual   │
│  ┌───────────▼───────────┐  │
│  │    Layer Norm         │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
    │
    ▼
Linear + Softmax (LM Head)
    │
    ▼
Next Token Probabilities
```

## Key Components

### 1. Input Embedding
Each token is converted to a dense vector of dimension `d_model` (e.g., 768 for GPT-2, 12288 for GPT-4).

```python
embedding = token_embedding[token_id] + positional_encoding[position]
```

### 2. Multi-Head Self-Attention
The core innovation. Each token attends to every other token in the context.

```
Attention(Q, K, V) = softmax(QKᵀ / √d_k) · V
```

- **Q** (Query): "What am I looking for?"
- **K** (Key): "What do I contain?"
- **V** (Value): "What do I return?"

Multiple heads allow attending to different representation subspaces.

### 3. Residual Connections
Skip connections that pass the original input around each sub-layer:
```
output = LayerNorm(x + SubLayer(x))
```
This enables training very deep networks without vanishing gradients.

### 4. Feed-Forward Network (FFN)
Applied independently to each position:
```
FFN(x) = max(0, xW₁ + b₁)W₂ + b₂
```
Typically `d_ff = 4 × d_model`.

### 5. Layer Normalization
Normalizes activations across the feature dimension, stabilizing training.

## Decoder-Only vs Encoder-Decoder

| Model Type | Examples | Use Case |
|---|---|---|
| Decoder-only | GPT, LLaMA, Mistral | Text generation |
| Encoder-only | BERT, RoBERTa | Classification, embeddings |
| Encoder-Decoder | T5, BART | Translation, summarization |

Modern LLMs (GPT-4, LLaMA, Claude) use **decoder-only** architecture with **causal (masked) self-attention** — each token can only attend to previous tokens.

## Scaling Laws

Model performance scales predictably with:
- **N** — Number of parameters
- **D** — Size of training dataset  
- **C** — Compute budget

```
L(N, D) ≈ (Nc/N)^αN + (Dc/D)^αD + L∞
```

(Hoffmann et al., *Chinchilla*, 2022)

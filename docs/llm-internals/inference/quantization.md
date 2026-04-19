# Quantization Internals

Quantization reduces model precision to decrease memory usage and increase inference speed.

## Why Quantize?

LLaMA-2 70B in FP32: **280 GB** — requires 4× A100 80GB  
LLaMA-2 70B in INT4:  **35 GB** — fits on a single A100 80GB

## Data Types

| Format | Bits | Range | Typical Use |
|---|---|---|---|
| FP32 | 32 | ±3.4×10³⁸ | Training |
| BF16 | 16 | ±3.4×10³⁸ | Training/inference |
| FP16 | 16 | ±65504 | Inference |
| INT8 | 8 | -128 to 127 | Quantized inference |
| FP8 | 8 | varies | H100 training/inference |
| INT4 | 4 | -8 to 7 | Aggressive quantization |
| INT2 | 2 | -2 to 1 | Extreme quantization |

## Post-Training Quantization (PTQ)

Quantize after training, no retraining needed.

### Absmax Quantization (Symmetric)
```
scale = max(|W|) / 127
W_int8 = round(W / scale)

# Dequantize for compute:
W_float = W_int8 * scale
```

### Zero-Point Quantization (Asymmetric)
```
scale = (max(W) - min(W)) / 255
zero_point = round(-min(W) / scale)
W_int8 = round(W / scale) + zero_point
```

## GPTQ (Post-Training Quantization for GPT)

Layer-by-layer quantization that minimizes reconstruction error:

```
For each row of weight matrix W:
  For each weight w_ij:
    1. Quantize w_ij → w̃_ij
    2. Compute error: δ = w_ij - w̃_ij
    3. Compensate remaining weights using second-order info (Hessian)
    4. Update: w_ik += δ × H⁻¹_jk / H⁻¹_jj  (for k > j)
```

Uses **calibration data** (128-256 samples) to compute Hessian.  
Result: INT4 quality close to FP16 with careful compensation.

## GGUF / llama.cpp Quantization

Quantization formats used in llama.cpp:

| Format | Bits/weight | Quality |
|---|---|---|
| Q8_0 | 8 | Excellent |
| Q6_K | 6.56 | Very good |
| Q5_K_M | 5.69 | Good |
| Q4_K_M | 4.85 | Good (recommended) |
| Q4_0 | 4 | Fair |
| Q3_K_M | 3.91 | Moderate |
| Q2_K | 2.96 | Low |

`_K` = k-quants (use super-blocks for better accuracy)  
`_M` = medium variant (balances speed/quality)

## AWQ (Activation-Aware Weight Quantization)

Observation: not all weights are equally important. Weights that multiply **large activations** cause more error when quantized.

```
1. Profile activation magnitudes on calibration data
2. Scale important weights UP before quantization (so they get more precision)
3. Scale activations DOWN correspondingly (to preserve output)
4. Quantize scaled weights
```

**Key insight:** 1% of weights are "salient" — protecting them recovers most quality.

## Quantization-Aware Training (QAT)

Train the model knowing it will be quantized:

```python
# Straight-Through Estimator (STE)
# Forward pass: use quantized weights
w_quant = quantize(w)
y = x @ w_quant

# Backward pass: pretend quantize() is identity
# (gradients flow through as if no quantization)
```

More expensive (requires retraining) but higher quality than PTQ.

## Activation Quantization

Weights can be quantized offline. Activations are dynamic — harder to quantize.

**Challenges:**
- Activations have **outliers** (values 100× larger than average)
- These outliers are channel-specific (always same channels)

**Solutions:**
- **SmoothQuant**: migrate quantization difficulty from activations to weights
- **LLM.int8()**: use FP16 for outlier channels, INT8 for the rest

## Bits and Bytes (bitsandbytes)

Popular library for LLM quantization:

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# 4-bit NF4 quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",    # NormalFloat4
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,  # quantize the scale factors too
)
model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config)
```

**NF4 (NormalFloat4):** Data type optimized for normally-distributed weights (like those produced by standard weight initialization).

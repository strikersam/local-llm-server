# Device compatibility and model picks

This page complements the main [README](../README.md). The **auth proxy + Cloudflare tunnel** stack runs on the same machines as Ollama; what changes by device is **which quantized models fit in memory**, which **accelerator** (if any) is used, and how fast inference feels.

Use it when you want **local** models on everyday hardware, or when you are sizing a **home server** or **workstation** for remote access from phones and laptops.

**Official reference:** Ollama publishes up-to-date GPU and accelerator support in [Hardware support](https://docs.ollama.com/gpu) (NVIDIA, AMD ROCm, Apple Metal, experimental Vulkan). This file adds **practical model pairing**; always verify tags in the [Ollama library](https://ollama.com/library).

---

## How to read memory on different platforms

| Platform | What counts |
|----------|-------------|
| **Apple Silicon (M-series)** | **Unified memory** — CPU, GPU (Metal), and loaded weights share one pool. No separate VRAM line item; **total unified RAM** is the budget for weights, KV cache, OS, and apps. **Memory bandwidth** (not only TFLOPS) strongly affects tokens/sec on large models. |
| **Windows / Linux + NVIDIA CUDA** | **GPU VRAM** holds layers (and often KV cache) when offloaded; **system RAM** backs CPU paths and partial offload. Use **Driver 531+** and GPUs with **compute capability 5.0+** per [Ollama’s NVIDIA section](https://docs.ollama.com/gpu#nvidia). |
| **Linux + AMD Radeon / Instinct** | **ROCm** path on supported cards (see [AMD Radeon](https://docs.ollama.com/gpu#amd-radeon) tables for Linux vs Windows). VRAM rules are similar to NVIDIA for a given model size. Unsupported AMD GPUs may fall back to CPU or need community workarounds (`HSA_OVERRIDE_GFX_VERSION` is documented for some edge cases). |
| **Vulkan (experimental)** | Ollama can use **Vulkan** for extra vendor coverage on Windows/Linux when `OLLAMA_VULKAN=1` — useful for some **Intel discrete/integrated** setups where CUDA/ROCm do not apply. See [Vulkan GPU Support](https://docs.ollama.com/gpu#vulkan-gpu-support) and the [FAQ](https://docs.ollama.com/faq). |
| **CPU-only** | Uses **system RAM** only; prefer **small** instruct models (≈3B–8B) and moderate context. Slowest option but universal (including VMs with no GPU passthrough). |

---

## Acceleration at a glance

| You have | Typical Ollama path | Notes |
|----------|---------------------|--------|
| **NVIDIA GeForce / RTX / Quadro / datacenter** | CUDA | Broadest tested stack; multi-GPU: `CUDA_VISIBLE_DEVICES`. |
| **AMD RX / PRO / Instinct (supported lists)** | ROCm (Linux **ROCm v7** per docs; Windows subset) | Check [official card lists](https://docs.ollama.com/gpu#amd-radeon). |
| **Apple M1–M4 / M5 (MacBook, Mac mini, Mac Studio, etc.)** | Metal | Strong per-GB experience when unified RAM is large enough. |
| **Intel Arc / Iris Xe / integrated (some)** | Often **CPU** or **Vulkan** (experimental) | Intel-specific CUDA path is not the default story; see Vulkan docs. |
| **Snapdragon X Elite / Windows on ARM** | **ARM64 CPU** build (GPU offload landscape evolving) | Treat like a efficient laptop CPU: favour **7B and below** unless RAM is high; see [Qualcomm / WoS notes](https://www.qualcomm.com/developer/project/ollama-with-windows-on-snapdragon-wos). |
| **No usable GPU** | CPU | Works everywhere; reduce model size and context. |

---

## VRAM / unified RAM vs model tier (rule of thumb)

Quantization (e.g. **Q4_K_M**) and **context length** change memory a lot — these are **starting points**, not guarantees.

| Approx. GPU VRAM **or** unified RAM headroom | Comfortable model class (Q4 family) | Example directions (library names vary) |
|-----------------------------------------------|-------------------------------------|----------------------------------------|
| **~4 GB** | ≈3B–4B instruct | Tiny chat, scripting, experiments on old laptops. |
| **~6–8 GB** | ≈7B–9B | `qwen3-coder:7b`, `deepseek-r1:7b`, Llama 3.x 8B-class. |
| **~10–12 GB** | ≈12B–14B | Mid coding models (e.g. Gemma / Qwen mid-size tags). |
| **~16–24 GB** | ≈22B–35B | `qwen3-coder:30b`, `deepseek-r1:32b`, 27B–32B-class. |
| **~32–48 GB** | ≈40B–70B (one at a time) | Llama 3.3 70B-class, Qwen 72B-class — check tags. |
| **~64 GB+ system** | 70B + headroom, or **multiple** smaller models | Workstation / Mac Studio territory. |
| **~128 GB+ RAM + huge SSD** | **671B** with mmap | `deepseek-r1:671b` — latency from NVMe; not GPU-VRAM sized. |

**KV cache** grows with **context window**; long chats need extra headroom beyond raw weight size.

---

## Wider device coverage (illustrative profiles)

Exact fit depends on OS overhead, browser, IDE, and whether the model is **fully GPU-resident** vs **split**. Prefer pulling a **smaller** model first, then `ollama ps` / trial runs.

### Laptops and all-in-ones

| Profile | Typical specs | Suggested pulls (same stack as main README) | Notes |
|---------|----------------|---------------------------------------------|--------|
| **Ultrabook / iGPU-only (16 GB RAM)** | Intel Iris Xe, AMD 780M, no dGPU | `qwen3-coder:7b`, `deepseek-r1:7b` | CPU or Vulkan; keep context moderate. |
| **Thin gaming laptop (16 GB RAM, 6–8 GB VRAM)** | RTX 3060 laptop, RTX 4060 laptop | `qwen3-coder:7b`, `deepseek-r1:7b`; stretch to 8B–9B class | VRAM is usually the limiter. |
| **Creator laptop (32 GB RAM, 8–12 GB VRAM)** | RTX 4070 / 3080 Ti mobile | `qwen3-coder:30b` or `deepseek-r1:32b` **one at a time** | Close games / GPU apps when loading 30B+. |
| **MacBook Air / Pro (8 GB unified)** | M2 / M3 / M4 / **M5** base | 3B–4B-class only; **7B** is tight | Not ideal as primary coding host; fine for light use. |
| **MacBook Pro (16 GB unified)** | M3 Pro, M4 Pro, etc. | `qwen3-coder:7b`, `deepseek-r1:7b` | Comfortable 7B; 13B-class may fit with care. |
| **MacBook Pro (24 GB unified)** | Many Pro configs | Same as 16 GB, or **one** of `qwen3-coder:30b` / `deepseek-r1:32b` when idle | Unified RAM must cover weights + system. |
| **MacBook Pro (36–48 GB unified)** | High-end Pro / Max configs | `qwen3-coder:30b`, `deepseek-r1:32b`; explore 70B-class | Strong portable “home server” for this repo. |
| **Copilot+ PC / Snapdragon X (16–32 GB)** | Windows on ARM | `qwen3-coder:7b`, `deepseek-r1:7b` first | Prioritize RAM; GPU story is platform-specific — see Qualcomm developer materials linked above. |

### Desktops and workstations

| Profile | Typical specs | Suggested pulls | Notes |
|---------|----------------|-----------------|--------|
| **Budget desktop (16 GB RAM, GTX 1650 / 4 GB)** | Older Pascal/Turing | 3B–7B | Still CUDA-capable if driver current; upgrade RAM if possible. |
| **Mainstream gaming (32 GB RAM, RTX 3060 12G / 4060 Ti 16G)** | Common DIY | `qwen3-coder:7b`–`30b`, `deepseek-r1:7b`–`32b` | 16 GB VRAM variants handle 30B-class more comfortably. |
| **Enthusiast (32–64 GB RAM, RTX 4080 / 4090 / 5080)** | 16–24 GB VRAM | 30B–32B fast; 70B-class possible on 24G with quant + offload settings | Multi-GPU: see `CUDA_VISIBLE_DEVICES`. |
| **AMD gaming (RX 6800 XT / 7800 XT / 7900 XTX)** | Linux (full ROCm lists) or Windows (supported RX list) | Same tiers as NVIDIA by **VRAM** | Install ROCm per [docs](https://docs.ollama.com/gpu#amd-radeon). |
| **Workstation (Threadripper / Xeon, 128 GB+ RAM)** | Often A6000 / 4090 / dual GPU | `deepseek-r1:671b` + smaller models | 671B uses **RAM + NVMe** heavily; GPU helps but does not “hold” full weights in VRAM. |
| **Mac mini / Mac Studio (32–64 GB+)** | M2 Pro → **M5** class | `qwen3-coder:30b`, `deepseek-r1:32b`; 70B if RAM allows | Excellent unified-memory “appliance” for always-on tunnel. |

### Edge cases

| Profile | Typical specs | Suggested pulls | Notes |
|---------|----------------|-----------------|--------|
| **Intel Arc (A750 / A770 / B580)** | 8–16 GB VRAM | Same VRAM tier as NVIDIA table | Try stock Ollama first; **Vulkan** experimental if needed — [GPU docs](https://docs.ollama.com/gpu). Community Intel IPEX builds exist but are not the default upstream story. |
| **Steam Deck / handheld (16 GB unified)** | Linux, AMD APU | 3B–7B | Battery and thermals limit sustained load; great for tiny models. |
| **VM / Docker host (no GPU)** | N vCPU, N GB RAM | Scale with CPU table | OK for API + tunnel; size RAM to model. |
| **Single-board / very low RAM** | 8 GB or less | 1B–3B-class only | Barely practical for coding; better as **client** to a real host. |

---

## Apple Silicon: chip tier vs bandwidth (qualitative)

Within the same **RAM** size, **Pro / Max / Ultra** parts usually offer **higher memory bandwidth**, which helps token speed on large weights. **Base** M-chips are more constrained. For any Mac:

- Match **unified RAM** to the **VRAM tier** table above.
- Prefer **one large model at a time** unless you have **48 GB+** and know idle headroom.

---

## NVIDIA examples by VRAM (CUDA)

Use this only as a **shopping / sanity** map; exact tags depend on Ollama’s GGUF builds.

| VRAM | Example cards (families) | Typical sweet spot |
|------|--------------------------|--------------------|
| 4 GB | GTX 1650, old laptop GPUs | 3B–4B, tight 7B |
| 6–8 GB | RTX 2060, 3060, 4060 | 7B–8B standard |
| 10–12 GB | RTX 3080, 4070, many laptops | 12B–14B class |
| 16 GB | RTX 4080 laptop, 4060 Ti 16G, older 3080 Ti | 30B–32B with care |
| 24 GB | RTX 3090, 4090, 4080 Super, RTX 5000 Ada | 30B–32B comfortable; 70B with quant / offload |
| 48 GB+ | RTX 6000 Ada, A6000, some datacenter GPUs | 70B+; multi-model |

---

## Remote clients vs local horsepower

- **Phones and tablets** only need HTTPS + your API key — they **do not** run the model.
- **This document** targets the machine running **Ollama** (weights + inference).

If the local PC is weak, run Ollama on a **stronger box on the LAN** and keep only the **proxy + tunnel** on a small machine — same architecture as the main README.

---

## See also

- Main model tables and quick start: [README](../README.md)
- Ollama **hardware**: [https://docs.ollama.com/gpu](https://docs.ollama.com/gpu)
- Ollama **FAQ** (server env, Vulkan, etc.): [https://docs.ollama.com/faq](https://docs.ollama.com/faq)
- Ollama model library: [https://ollama.com/library](https://ollama.com/library)

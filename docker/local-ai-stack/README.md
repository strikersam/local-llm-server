# Local AI Stack with Docker

A fully self-hosted, privacy-first AI stack running locally via Docker containers. Inspired by the [XDA Developers guide](https://www.xda-developers.com/local-ai-stack-with-docker-containers/).

## Stack Components

| Service | Port | Description |
|---------|------|-------------|
| **Ollama** | 11434 | Local LLM runner — serves models like LLaMA 3.2 |
| **Open WebUI** | 3000 | ChatGPT-style UI for Ollama |
| **ChromaDB** | 8000 | Vector database for RAG / embeddings |
| **N8N** | 5678 | Workflow automation (optional) |

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- **GPU (recommended):** NVIDIA GPU with CUDA drivers + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- **CPU-only:** Works, but inference is slower

## Quick Start

### 1. Clone and configure

```bash
cd docker/local-ai-stack
cp .env.example .env
# Edit .env with your preferred values
```

### 2. Start the stack (GPU)

```bash
docker compose up -d
```

### 3. Start the stack (CPU only)

```bash
docker compose --profile cpu-only up -d ollama-cpu open-webui chromadb
```

### 4. Pull models (first run)

The `model-init` service pulls models automatically on first start. To pull manually:

```bash
# Pull a model
docker exec ollama ollama pull llama3.2:latest

# Pull embedding model for RAG
docker exec ollama ollama pull nomic-embed-text:latest

# List available models
docker exec ollama ollama list
```

### 5. Access services

- **Open WebUI:** http://localhost:3000
- **Ollama API:** http://localhost:11434
- **ChromaDB:** http://localhost:8000

## Profiles

### Default (GPU)
```bash
docker compose up -d
```

### CPU Only
```bash
docker compose --profile cpu-only up -d
```

### With Automation (N8N)
```bash
docker compose --profile automation up -d
```

## Using with the Repo's Claude Skills

Once your local stack is running, you can use the `local-ai-query` skill to route queries to Ollama instead of cloud APIs for privacy-sensitive tasks.

### Test Ollama is running

```bash
curl http://localhost:11434/api/tags
```

### Run a quick inference test

```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"llama3.2:latest","prompt":"Hello! Are you running locally?","stream":false}' \
  | jq .response
```

## Data Persistence

All data is persisted via named Docker volumes:

| Volume | Contents |
|--------|----------|
| `ollama_data` | Downloaded models |
| `open_webui_data` | Chat history, users, settings |
| `chroma_data` | Vector embeddings |
| `n8n_data` | Workflows and credentials |

## Updating

```bash
docker compose pull
docker compose up -d
```

## Stopping

```bash
docker compose down

# To also remove volumes (WARNING: deletes all data)
docker compose down -v
```

## Troubleshooting

### Ollama not starting
```bash
docker logs ollama
# Check GPU availability
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Models slow to load
- First load is slow (model loading into VRAM/RAM)
- Subsequent requests are fast
- Increase `OLLAMA_KEEP_ALIVE` to keep models warm

### Open WebUI can't connect to Ollama
```bash
# Verify Ollama is healthy
docker exec ollama curl -s http://localhost:11434/api/tags
# Check network
docker network inspect local-ai-stack_ai-network
```

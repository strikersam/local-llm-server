# Skill: local-ai-query

## Purpose
Route prompts to a **locally running Ollama instance** instead of cloud AI APIs. Use this for privacy-sensitive tasks, offline work, or cost reduction. Pairs with the Docker stack in `docker/local-ai-stack/`.

## When to Use
- Processing sensitive/proprietary code or data that shouldn't leave the machine
- Offline or air-gapped environments
- Rapid iteration where cloud latency matters
- Cost-conscious experimentation with large prompts

## Prerequisites
- Ollama running locally (see `docker/local-ai-stack/README.md`)
- At least one model pulled: `docker exec ollama ollama pull llama3.2:latest`

## Steps

### 1. Verify Ollama is available
```bash
curl -s http://localhost:11434/api/tags | jq '.models[].name'
```
If this fails, start the stack: `cd docker/local-ai-stack && docker compose up -d`

### 2. Choose appropriate model
| Task | Recommended Model |
|------|------------------|
| Code generation | `deepseek-coder-v2:latest` or `codellama:latest` |
| General chat | `llama3.2:latest` |
| Summarization | `llama3.2:latest` |
| Embeddings/RAG | `nomic-embed-text:latest` |
| Fast/small | `phi3:mini` |

Pull a model if needed:
```bash
docker exec ollama ollama pull <model-name>
```

### 3. Send query to local model

**Simple generation:**
```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "llama3.2:latest",
    "prompt": "<YOUR_PROMPT>",
    "stream": false
  }' | jq -r .response
```

**Chat format (multi-turn):**
```bash
curl http://localhost:11434/api/chat \
  -d '{
    "model": "llama3.2:latest",
    "messages": [
      {"role": "user", "content": "<YOUR_MESSAGE>"}
    ],
    "stream": false
  }' | jq -r '.message.content'
```

**With system prompt:**
```bash
curl http://localhost:11434/api/chat \
  -d '{
    "model": "llama3.2:latest",
    "messages": [
      {"role": "system", "content": "You are a senior software engineer. Be concise and technical."},
      {"role": "user", "content": "<YOUR_MESSAGE>"}
    ],
    "stream": false
  }' | jq -r '.message.content'
```

### 4. Generate embeddings (for RAG)
```bash
curl http://localhost:11434/api/embeddings \
  -d '{
    "model": "nomic-embed-text:latest",
    "prompt": "<TEXT_TO_EMBED>"
  }' | jq '.embedding | length'
```

### 5. List running models
```bash
curl -s http://localhost:11434/api/ps | jq '.models[].name'
```

## Integration with ChromaDB (RAG)

When `chromadb` is also running:

```python
import chromadb
import requests

# Embed with Ollama
def embed(text: str) -> list[float]:
    r = requests.post("http://localhost:11434/api/embeddings",
                      json={"model": "nomic-embed-text:latest", "prompt": text})
    return r.json()["embedding"]

# Store in ChromaDB
client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("knowledge")
collection.add(documents=["Your doc here"], embeddings=[embed("Your doc here")], ids=["doc1"])

# Query
results = collection.query(query_embeddings=[embed("search query")], n_results=3)
```

## Privacy Notes
- All data stays on your machine — no cloud API calls
- Models run entirely in your Docker containers
- ChromaDB vectors are stored in `chroma_data` Docker volume
- No telemetry sent externally

## Limitations
- Slower than cloud APIs (depends on hardware)
- Smaller context windows on some models
- Quality varies by model — use larger models for complex tasks

## Related Skills
- `research` — use local-ai-query for private research tasks
- `brain-dump` — process sensitive braindumps locally
- `debug-tracer` — analyze proprietary code locally

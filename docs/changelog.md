## [Unreleased]
### Added
- Basic navigation metrics and performance measurements
- `agent/rag_context.py` — advanced RAG context management layer:
  - Three retrieval modes: keyword (BM25-style), TF-IDF cosine similarity, and hybrid (Reciprocal Rank Fusion)
  - Conversation memory with exponential recency decay combined with per-turn query relevance scoring, so older unrelated turns fade naturally
  - Extractive sentence-level compression to fit a configurable token budget instead of blind truncation
  - `RAGContextBuilder.build()` returns a `ContextResult` with a `system_block` string ready for LLM injection, replacing the old flat `WIKI INDEX` dump
  - Pure Python implementation (stdlib `math` + `collections` only)

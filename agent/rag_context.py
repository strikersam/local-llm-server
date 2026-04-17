"""agent/rag_context.py — Advanced RAG context management layer.

Pipeline
--------
1. Index documents (wiki pages, ingested sources, …) using keyword + TF-IDF.
2. Retrieve the most relevant documents for the current query via one of three
   modes: ``keyword``, ``tfidf``, or ``hybrid`` (Reciprocal Rank Fusion).
3. Score every conversation-history turn with a recency-decay function combined
   with query relevance, so older unrelated turns fade naturally.
4. Compress the retrieved content to a configurable token budget using
   extractive summarisation (sentence-level selection) rather than blind
   truncation.
5. Return a :class:`ContextResult` whose ``system_block`` field is a
   drop-in replacement for the old flat ``WIKI INDEX`` string.

Pure-Python implementation — no external ML libraries required.
``math`` and ``collections`` from the standard library are the only
non-trivial dependencies.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

log = logging.getLogger("qwen-rag")

# 4 chars ≈ 1 token — same heuristic used throughout agent/context.py
_CHARS_PER_TOKEN = 4

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class Document:
    """A single knowledge-base entry (wiki page, source document, etc.)."""

    id: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryTurn:
    """One turn in the conversation history."""

    role: str        # "user" | "assistant" | "system"
    content: str
    turn_index: int  # 0 = oldest; higher = newer
    importance: float = 1.0  # caller-supplied weight override


@dataclass
class RetrievedDoc:
    """A document selected by retrieval, with its compressed excerpt."""

    doc: Document
    score: float
    excerpt: str
    token_estimate: int


@dataclass
class ContextResult:
    """Final output of the RAG pipeline."""

    retrieved_docs: list[RetrievedDoc]
    memory_turns: list[tuple[MemoryTurn, float]]  # (turn, score) — chrono order
    system_block: str                              # ready for LLM system prompt
    token_estimate: int
    tokens_from_docs: int
    tokens_from_memory: int
    docs_dropped: int   # candidates filtered by score threshold or budget
    turns_dropped: int  # history turns filtered by score threshold or budget


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of", "and",
    "or", "but", "for", "with", "by", "as", "be", "was", "are", "were",
    "this", "that", "these", "those", "i", "you", "we", "they", "he",
    "she", "do", "does", "did", "not", "no", "so", "if", "then", "than",
    "can", "will", "would", "could", "should", "have", "has", "had",
    "from", "up", "about", "into", "through", "after", "before",
})


def _tokenize(text: str) -> list[str]:
    """Return lowercase alphanumeric tokens with stop-words removed.

    Numeric tokens (status codes, version numbers, port numbers, …) are kept
    so queries like "error 429" or "port 8000" match correctly.
    """
    raw = re.findall(r"\b(?:[a-z][a-z0-9]*|\d+)\b", text.lower())
    return [t for t in raw if t not in _STOP_WORDS]


def _token_count(text: str) -> int:
    """Rough token estimate: 4 chars ≈ 1 token (minimum 1)."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on . ! ? followed by whitespace or end-of-string."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# TF-IDF index  (pure Python, sparse dict vectors)
# ---------------------------------------------------------------------------

class _TFIDFIndex:
    """Lightweight TF-IDF index over a fixed document collection.

    Sparse dict vectors make cosine similarity O(n_docs × |query_terms|)
    rather than O(n_docs × |vocab|), keeping latency low for typical
    knowledge-base sizes (tens to hundreds of documents).
    """

    def __init__(self, docs: list[Document]) -> None:
        self._docs = docs
        self._vocab: dict[str, int] = {}
        self._idf: list[float] = []
        self._rows: list[dict[int, float]] = []  # L2-normalised TF-IDF rows
        if docs:
            self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        corpus = [_tokenize(f"{d.title} {d.content}") for d in self._docs]
        n = len(self._docs)

        all_terms = sorted({t for tokens in corpus for t in tokens})
        self._vocab = {t: i for i, t in enumerate(all_terms)}

        # Sparse TF rows
        tf_rows: list[dict[int, float]] = []
        for tokens in corpus:
            if not tokens:
                tf_rows.append({})
                continue
            counts = Counter(tokens)
            total = len(tokens)
            tf_rows.append(
                {self._vocab[t]: c / total for t, c in counts.items()}
            )

        # Document frequency → IDF
        df: dict[int, int] = {}
        for row in tf_rows:
            for j in row:
                df[j] = df.get(j, 0) + 1

        self._idf = [
            math.log((1 + n) / (1 + df.get(j, 0))) + 1.0
            for j in range(len(all_terms))
        ]

        # TF-IDF, L2-normalised
        self._rows = []
        for row in tf_rows:
            tfidf = {j: tf * self._idf[j] for j, tf in row.items()}
            norm = math.sqrt(sum(v * v for v in tfidf.values())) or 1.0
            self._rows.append({j: v / norm for j, v in tfidf.items()})

    # ------------------------------------------------------------------

    def query(self, text: str, k: int) -> list[tuple[int, float]]:
        """Return ``(doc_index, cosine_score)`` pairs for the top-*k* matches."""
        if not self._rows:
            return []

        tokens = _tokenize(text)
        if not tokens:
            return []

        counts = Counter(tokens)
        total = len(tokens)
        q: dict[int, float] = {}
        for t, c in counts.items():
            j = self._vocab.get(t)
            if j is not None:
                q[j] = (c / total) * self._idf[j]

        if not q:
            return []

        q_norm = math.sqrt(sum(v * v for v in q.values())) or 1.0
        q = {j: v / q_norm for j, v in q.items()}

        scores: list[tuple[int, float]] = []
        for i, row in enumerate(self._rows):
            dot = sum(row.get(j, 0.0) * qv for j, qv in q.items())
            if dot > 0.0:
                scores.append((i, dot))

        scores.sort(key=lambda x: -x[1])
        return scores[:k]


# ---------------------------------------------------------------------------
# Keyword search  (BM25-inspired, no pre-built index)
# ---------------------------------------------------------------------------

def _keyword_search(
    query: str,
    docs: list[Document],
    k: int,
) -> list[tuple[int, float]]:
    """Score documents by query-term coverage with a title-match boost."""
    q_terms = set(_tokenize(query))
    if not q_terms:
        return []

    scores: list[tuple[int, float]] = []
    for i, doc in enumerate(docs):
        title_terms = set(_tokenize(doc.title))
        body_terms = set(_tokenize(doc.content))

        body_coverage = len(q_terms & body_terms) / len(q_terms)
        title_boost = len(q_terms & title_terms) / len(q_terms) * 0.5
        score = body_coverage + title_boost
        if score > 0.0:
            scores.append((i, score))

    scores.sort(key=lambda x: -x[1])
    return scores[:k]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def _rrf(
    rankings: list[list[tuple[int, float]]],
    rrf_k: int = 60,
) -> list[tuple[int, float]]:
    """Combine ranked lists with Reciprocal Rank Fusion."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (idx, _) in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
    return sorted(fused.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------------------
# Memory turn scoring with recency decay
# ---------------------------------------------------------------------------

def _score_turns(
    turns: list[MemoryTurn],
    query: str,
    decay_rate: float,
    relevance_weight: float,
) -> list[tuple[MemoryTurn, float]]:
    """Score each turn by exponential recency decay combined with query relevance.

    ``score = importance × ((1 − w) × decay^age + w × tfidf_relevance)``

    Turns are returned sorted by score descending so callers can take the
    top-N without further sorting.
    """
    if not turns:
        return []

    max_idx = max(t.turn_index for t in turns)

    # Mini TF-IDF index over turn contents for relevance scoring
    turn_docs = [
        Document(id=str(i), title="", content=t.content)
        for i, t in enumerate(turns)
    ]
    rel_map: dict[int, float] = dict.fromkeys(range(len(turns)), 0.0)
    for i, score in _TFIDFIndex(turn_docs).query(query, k=len(turns)):
        rel_map[i] = score

    scored: list[tuple[MemoryTurn, float]] = []
    for i, turn in enumerate(turns):
        age = max_idx - turn.turn_index
        recency = decay_rate ** age
        relevance = rel_map[i]
        final = turn.importance * (
            (1.0 - relevance_weight) * recency + relevance_weight * relevance
        )
        scored.append((turn, final))

    scored.sort(key=lambda x: -x[1])
    return scored


# ---------------------------------------------------------------------------
# Extractive sentence compression
# ---------------------------------------------------------------------------

def _extractive_compress(text: str, query: str, max_tokens: int) -> str:
    """Return the highest-value sentences from *text* within *max_tokens*.

    Each sentence is scored by three signals:

    * **Position** — earlier sentences score higher (expository writing
      front-loads key information).
    * **Query overlap** — sentences sharing tokens with the query score
      higher; this keeps the excerpt on-topic.
    * **Length** — medium-length sentences (8–35 words) are preferred over
      fragments or run-ons.

    Sentences are selected greedily by score until the token budget is
    exhausted, then re-assembled in their original order for coherence.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return ""

    budget_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= budget_chars:
        return text

    q_terms = set(_tokenize(query))
    scored: list[tuple[int, str, float]] = []

    for i, sent in enumerate(sentences):
        words = _tokenize(sent)
        wc = len(words)
        if wc == 0:
            continue

        pos_score = 1.0 / (1.0 + i * 0.3)
        overlap = len(set(words) & q_terms) / len(q_terms) if q_terms else 0.0
        length_score = 1.0 if 8 <= wc <= 35 else (0.2 if wc < 5 else 35.0 / wc)

        total = 0.4 * pos_score + 0.4 * overlap + 0.2 * length_score
        scored.append((i, sent, total))

    scored_by_value = sorted(scored, key=lambda x: -x[2])
    chosen: set[int] = set()
    chars_used = 0

    for idx, sent, _ in scored_by_value:
        cost = len(sent) + 1  # +1 for the joining space
        if chars_used + cost > budget_chars:
            continue
        chosen.add(idx)
        chars_used += cost

    if not chosen:
        # Absolute fallback: first sentence that fits
        for i, sent in enumerate(sentences):
            if len(sent) <= budget_chars:
                return sent
        return ""

    return " ".join(sentences[i] for i in sorted(chosen))


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

class RAGContextBuilder:
    """Retrieve, decay, and compress context to fit a configurable token budget.

    Usage::

        builder = RAGContextBuilder(token_budget=2000)
        result = builder.build(
            query="How do I set up streaming?",
            documents=[
                Document(id="1", title="API Guide", content="..."),
                Document(id="2", title="Auth", content="..."),
            ],
            history=[
                MemoryTurn(role="user", content="Hello", turn_index=0),
                MemoryTurn(role="assistant", content="Hi!", turn_index=1),
            ],
            retrieval_mode="hybrid",   # "keyword" | "tfidf" | "hybrid"
        )
        # Inject result.system_block into the LLM system prompt instead of
        # the old flat WIKI INDEX string.

    Token budget split
    ------------------
    ``doc_budget_fraction`` (default 0.60) of the budget is reserved for
    retrieved document excerpts; the remainder goes to conversation memory.
    Within each pool, content is compressed or dropped to fit.

    Memory decay
    ------------
    Older turns are down-weighted exponentially (``memory_decay_rate``).
    Turns that also have low query relevance fade below ``min_memory_score``
    and are filtered out entirely.
    """

    def __init__(
        self,
        *,
        token_budget: int = 2000,
        doc_budget_fraction: float = 0.6,
        memory_decay_rate: float = 0.85,
        memory_relevance_weight: float = 0.4,
        min_doc_score: float = 0.01,
        min_memory_score: float = 0.05,
    ) -> None:
        if not 0.0 < doc_budget_fraction < 1.0:
            raise ValueError("doc_budget_fraction must be between 0 and 1 (exclusive)")
        if not 0.0 < memory_decay_rate <= 1.0:
            raise ValueError("memory_decay_rate must be in (0, 1]")

        self.token_budget = token_budget
        self.doc_budget_fraction = doc_budget_fraction
        self.memory_decay_rate = memory_decay_rate
        self.memory_relevance_weight = memory_relevance_weight
        self.min_doc_score = min_doc_score
        self.min_memory_score = min_memory_score

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def build(
        self,
        query: str,
        documents: list[Document],
        history: list[MemoryTurn],
        retrieval_mode: Literal["keyword", "tfidf", "hybrid"] = "hybrid",
        top_k_docs: int = 5,
        top_k_turns: int = 8,
    ) -> ContextResult:
        """Run the full RAG pipeline and return a token-budget-respecting context.

        Parameters
        ----------
        query:
            The current user message / instruction driving this retrieval.
        documents:
            Knowledge-base documents to search (wiki pages, ingested sources).
        history:
            Conversation turns to consider for memory injection.
        retrieval_mode:
            ``"keyword"`` — fast BM25-style overlap scoring.
            ``"tfidf"``   — cosine similarity over TF-IDF vectors.
            ``"hybrid"``  — Reciprocal Rank Fusion of keyword + TF-IDF.
        top_k_docs:
            Maximum candidate documents retrieved before budget trimming.
        top_k_turns:
            Maximum candidate history turns to consider for memory injection.

        Returns
        -------
        :class:`ContextResult`
        """
        doc_budget = int(self.token_budget * self.doc_budget_fraction)
        mem_budget = self.token_budget - doc_budget

        # Step 1 — Retrieve
        candidates = self._retrieve(query, documents, retrieval_mode, top_k_docs)
        filtered_docs = [(d, s) for d, s in candidates if s >= self.min_doc_score]
        docs_dropped = len(candidates) - len(filtered_docs)

        # Step 2 — Compress docs to fit budget
        retrieved_docs = self._pack_docs(filtered_docs, query, doc_budget)

        # Step 3 — Score history turns (decay + relevance)
        scored_turns = _score_turns(
            history, query, self.memory_decay_rate, self.memory_relevance_weight
        )
        above_threshold = [(t, s) for t, s in scored_turns if s >= self.min_memory_score]
        turns_dropped_score = len(scored_turns) - len(above_threshold)

        selected_turns, turns_dropped_budget = self._pack_turns(
            above_threshold, top_k_turns, mem_budget
        )
        turns_dropped = turns_dropped_score + turns_dropped_budget

        # Step 4 — Format
        system_block = self._format(retrieved_docs, selected_turns)

        tokens_docs = sum(r.token_estimate for r in retrieved_docs)
        tokens_mem = sum(_token_count(t.content) for t, _ in selected_turns)

        log.debug(
            "rag_context: %d docs (%d tokens) + %d turns (%d tokens), budget=%d",
            len(retrieved_docs), tokens_docs,
            len(selected_turns), tokens_mem,
            self.token_budget,
        )

        return ContextResult(
            retrieved_docs=retrieved_docs,
            memory_turns=selected_turns,
            system_block=system_block,
            token_estimate=tokens_docs + tokens_mem,
            tokens_from_docs=tokens_docs,
            tokens_from_memory=tokens_mem,
            docs_dropped=docs_dropped,
            turns_dropped=turns_dropped,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def _retrieve(
        self,
        query: str,
        docs: list[Document],
        mode: str,
        k: int,
    ) -> list[tuple[Document, float]]:
        if not docs:
            return []

        if mode == "keyword":
            hits = _keyword_search(query, docs, k)
        elif mode == "tfidf":
            hits = _TFIDFIndex(docs).query(query, k)
        elif mode == "hybrid":
            kw = _keyword_search(query, docs, k)
            tf = _TFIDFIndex(docs).query(query, k)
            hits = _rrf([kw, tf])[:k]
        else:
            raise ValueError(
                f"Unknown retrieval_mode: {mode!r}. "
                "Use 'keyword', 'tfidf', or 'hybrid'."
            )

        return [(docs[i], score) for i, score in hits]

    # ------------------------------------------------------------------
    # Budget packing
    # ------------------------------------------------------------------

    def _pack_docs(
        self,
        candidates: list[tuple[Document, float]],
        query: str,
        budget: int,
    ) -> list[RetrievedDoc]:
        if not candidates:
            return []

        per_doc = max(50, budget // len(candidates))
        result: list[RetrievedDoc] = []
        tokens_used = 0

        for doc, score in candidates:
            remaining = budget - tokens_used
            if remaining <= 0:
                break
            alloc = min(per_doc, remaining)
            excerpt = _extractive_compress(doc.content, query, alloc)
            if not excerpt:
                continue
            est = _token_count(excerpt)
            result.append(
                RetrievedDoc(doc=doc, score=score, excerpt=excerpt, token_estimate=est)
            )
            tokens_used += est

        return result

    def _pack_turns(
        self,
        scored_turns: list[tuple[MemoryTurn, float]],
        top_k: int,
        budget: int,
    ) -> tuple[list[tuple[MemoryTurn, float]], int]:
        """Select up to *top_k* highest-scoring turns that fit within *budget*.

        Returns the selected list (chronological order) and the count of turns
        dropped due to budget exhaustion.
        """
        selected: list[tuple[MemoryTurn, float]] = []
        tokens_used = 0
        dropped = 0

        for turn, score in scored_turns[:top_k]:
            cost = _token_count(turn.content)
            if tokens_used + cost > budget:
                dropped += 1
                continue
            selected.append((turn, score))
            tokens_used += cost

        # Restore chronological order for readable context
        selected.sort(key=lambda x: x[0].turn_index)
        dropped += max(0, len(scored_turns) - top_k)
        return selected, dropped

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format(
        self,
        docs: list[RetrievedDoc],
        turns: list[tuple[MemoryTurn, float]],
    ) -> str:
        parts: list[str] = []

        if docs:
            parts.append("## Relevant Knowledge")
            for rd in docs:
                header = f"### {rd.doc.title}"
                if rd.doc.tags:
                    header += f"  [tags: {', '.join(rd.doc.tags)}]"
                parts.append(header)
                parts.append(rd.excerpt)

        if turns:
            parts.append("## Conversation Context")
            for turn, _ in turns:
                label = turn.role.capitalize()
                parts.append(f"**{label}:** {turn.content}")

        return "\n\n".join(parts)

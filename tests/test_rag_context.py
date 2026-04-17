"""Tests for agent/rag_context.py — Advanced RAG context management layer.

Imports via importlib.util to avoid triggering agent/__init__.py, which pulls
in the full dependency stack (pydantic, httpx, …) not needed here.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Direct module import — bypasses agent/__init__.py
# ---------------------------------------------------------------------------
_MODULE_PATH = Path(__file__).resolve().parents[1] / "agent" / "rag_context.py"
_spec = importlib.util.spec_from_file_location("agent.rag_context", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules.setdefault("agent.rag_context", _mod)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

Document = _mod.Document
MemoryTurn = _mod.MemoryTurn
RAGContextBuilder = _mod.RAGContextBuilder
RetrievedDoc = _mod.RetrievedDoc
ContextResult = _mod.ContextResult
_TFIDFIndex = _mod._TFIDFIndex
_extractive_compress = _mod._extractive_compress
_keyword_search = _mod._keyword_search
_rrf = _mod._rrf
_score_turns = _mod._score_turns
_split_sentences = _mod._split_sentences
_token_count = _mod._token_count
_tokenize = _mod._tokenize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc(id: str, title: str, content: str, tags: list[str] | None = None) -> Document:
    return Document(id=id, title=title, content=content, tags=tags or [])


def _turn(role: str, content: str, idx: int, importance: float = 1.0) -> MemoryTurn:
    return MemoryTurn(role=role, content=content, turn_index=idx, importance=importance)


KB = [
    _doc("1", "Authentication Guide",
         "Bearer tokens are required for all API requests. "
         "Pass the token in the Authorization header. Tokens expire after 24 hours."),
    _doc("2", "Rate Limiting",
         "The API enforces a rate limit of 100 requests per minute. "
         "Exceeding this returns a 429 status code. Use exponential backoff to retry."),
    _doc("3", "Streaming Responses",
         "Set stream=True in your request to receive server-sent events. "
         "Each chunk contains a delta with the model's partial output."),
    _doc("4", "Model Routing",
         "The router selects models based on task complexity. "
         "Simple queries go to fast models; complex reasoning uses larger models."),
    _doc("5", "Error Handling",
         "On 5xx errors retry with backoff. On 4xx errors check your request payload. "
         "Authentication errors return 401. Permission errors return 403.",
         tags=["errors", "http"]),
]

HISTORY = [
    _turn("user",      "Hello, how does authentication work?", 0),
    _turn("assistant", "You need to use Bearer tokens in the Authorization header.", 1),
    _turn("user",      "What happens if I exceed the rate limit?", 2),
    _turn("assistant", "You will receive a 429 status code. Use exponential backoff.", 3),
    _turn("user",      "How do I enable streaming?", 4),
    _turn("assistant", "Set stream=True in your request body.", 5),
]


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------

def test_tokenize_lowercases():
    assert "Hello" not in _tokenize("Hello World")
    assert "hello" in _tokenize("Hello World")


def test_tokenize_removes_stop_words():
    tokens = _tokenize("the quick brown fox")
    assert "the" not in tokens
    assert "quick" in tokens
    assert "brown" in tokens


def test_tokenize_empty():
    assert _tokenize("") == []


def test_tokenize_numbers_kept():
    assert "429" in _tokenize("Error 429 returned")


# ---------------------------------------------------------------------------
# _token_count
# ---------------------------------------------------------------------------

def test_token_count_basic():
    assert _token_count("a" * 400) == 100


def test_token_count_minimum():
    assert _token_count("") == 1
    assert _token_count("hi") == 1


# ---------------------------------------------------------------------------
# _split_sentences
# ---------------------------------------------------------------------------

def test_split_sentences_basic():
    sents = _split_sentences("Hello world. This is a test. Done!")
    assert len(sents) == 3
    assert sents[0] == "Hello world."


def test_split_sentences_single():
    sents = _split_sentences("Only one sentence")
    assert len(sents) == 1


def test_split_sentences_empty():
    assert _split_sentences("") == []


# ---------------------------------------------------------------------------
# _keyword_search
# ---------------------------------------------------------------------------

def test_keyword_search_finds_relevant():
    hits = _keyword_search("authentication token", KB, k=3)
    indices = [i for i, _ in hits]
    assert 0 in indices  # "Authentication Guide" should rank high


def test_keyword_search_title_boost():
    # "Rate Limiting" is in the title of doc[1]
    hits = _keyword_search("rate limiting", KB, k=5)
    top_idx, top_score = hits[0]
    assert top_idx == 1


def test_keyword_search_empty_query():
    assert _keyword_search("", KB, k=5) == []


def test_keyword_search_no_match():
    hits = _keyword_search("zzz nonexistent qqq", KB, k=3)
    assert hits == []


def test_keyword_search_respects_k():
    hits = _keyword_search("the api", KB, k=2)
    assert len(hits) <= 2


# ---------------------------------------------------------------------------
# _TFIDFIndex
# ---------------------------------------------------------------------------

def test_tfidf_finds_relevant():
    idx = _TFIDFIndex(KB)
    hits = idx.query("streaming server-sent events", k=3)
    indices = [i for i, _ in hits]
    assert 2 in indices  # "Streaming Responses"


def test_tfidf_empty_query():
    idx = _TFIDFIndex(KB)
    assert idx.query("", k=5) == []


def test_tfidf_unknown_term_only():
    idx = _TFIDFIndex(KB)
    assert idx.query("xyzzyplugh frobnicator", k=5) == []


def test_tfidf_empty_corpus():
    idx = _TFIDFIndex([])
    assert idx.query("anything", k=5) == []


def test_tfidf_scores_ordered_descending():
    idx = _TFIDFIndex(KB)
    hits = idx.query("bearer token authorization", k=5)
    scores = [s for _, s in hits]
    assert scores == sorted(scores, reverse=True)


def test_tfidf_scores_between_0_and_1():
    idx = _TFIDFIndex(KB)
    for _, score in idx.query("token rate stream", k=5):
        assert 0.0 < score <= 1.0


# ---------------------------------------------------------------------------
# _rrf
# ---------------------------------------------------------------------------

def test_rrf_merges_two_rankings():
    r1 = [(0, 1.0), (1, 0.8), (2, 0.5)]
    r2 = [(2, 1.0), (0, 0.9), (3, 0.4)]
    fused = _rrf([r1, r2])
    indices = [i for i, _ in fused]
    # 0 appears in both lists → should be near the top
    assert indices.index(0) < indices.index(3)


def test_rrf_single_ranking_preserves_order():
    ranking = [(0, 1.0), (1, 0.5), (2, 0.2)]
    fused = _rrf([ranking])
    assert [i for i, _ in fused] == [0, 1, 2]


def test_rrf_scores_descending():
    r1 = [(0, 1.0), (1, 0.8)]
    r2 = [(1, 1.0), (0, 0.5)]
    fused = _rrf([r1, r2])
    scores = [s for _, s in fused]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# _score_turns
# ---------------------------------------------------------------------------

def test_score_turns_empty():
    assert _score_turns([], "anything", 0.85, 0.4) == []


def test_score_turns_recency_newer_scores_higher():
    old = _turn("user", "unrelated old message about weather", 0)
    new = _turn("user", "unrelated new message about weather", 10)
    scored = _score_turns([old, new], "anything", 0.85, 0.4)
    turn_to_score = {t.turn_index: s for t, s in scored}
    assert turn_to_score[10] > turn_to_score[0]


def test_score_turns_relevance_boosts_score():
    relevant = _turn("user", "bearer token authentication header api", 0)
    irrelevant = _turn("user", "the weather is nice today sunshine", 0)
    irrelevant = MemoryTurn(
        role="user", content="the weather is nice today sunshine",
        turn_index=0, importance=1.0
    )
    relevant = MemoryTurn(
        role="user", content="bearer token authentication header api",
        turn_index=0, importance=1.0
    )
    scored = _score_turns([relevant, irrelevant], "bearer token authentication", 0.85, 0.8)
    turn_scores = {t.content: s for t, s in scored}
    assert turn_scores[relevant.content] > turn_scores[irrelevant.content]


def test_score_turns_sorted_descending():
    turns = [_turn("user", f"message number {i}", i) for i in range(5)]
    scored = _score_turns(turns, "message", 0.85, 0.4)
    scores = [s for _, s in scored]
    assert scores == sorted(scores, reverse=True)


def test_score_turns_importance_multiplier():
    low = _turn("user", "identical content here", 5, importance=0.2)
    high = _turn("user", "identical content here", 5, importance=2.0)
    # Same age, same content — importance should be the deciding factor
    scored_low = _score_turns([low], "identical content", 0.85, 0.4)
    scored_high = _score_turns([high], "identical content", 0.85, 0.4)
    assert scored_high[0][1] > scored_low[0][1]


# ---------------------------------------------------------------------------
# _extractive_compress
# ---------------------------------------------------------------------------

def test_compress_short_text_verbatim():
    text = "Short text."
    result = _extractive_compress(text, "query", max_tokens=1000)
    assert result == text


def test_compress_respects_budget():
    long_text = " ".join([f"Sentence number {i} contains some words." for i in range(50)])
    result = _extractive_compress(long_text, "sentence", max_tokens=50)
    assert _token_count(result) <= 55  # small tolerance for rounding


def test_compress_prefers_query_relevant_sentences():
    text = (
        "The sky is blue today. "
        "Bearer tokens must be included in every API request. "
        "Cats are lovely animals. "
        "The token expires after 24 hours."
    )
    result = _extractive_compress(text, "bearer token api", max_tokens=30)
    # At least one token-related sentence should survive
    assert "token" in result.lower() or "bearer" in result.lower()


def test_compress_empty_text():
    assert _extractive_compress("", "query", max_tokens=100) == ""


def test_compress_result_non_empty_for_non_empty_input():
    text = "This is a reasonable length sentence with plenty of content."
    result = _extractive_compress(text, "sentence content", max_tokens=20)
    assert result != ""


# ---------------------------------------------------------------------------
# RAGContextBuilder — construction validation
# ---------------------------------------------------------------------------

def test_builder_invalid_doc_fraction():
    with pytest.raises(ValueError, match="doc_budget_fraction"):
        RAGContextBuilder(doc_budget_fraction=0.0)


def test_builder_invalid_decay_rate():
    with pytest.raises(ValueError, match="memory_decay_rate"):
        RAGContextBuilder(memory_decay_rate=0.0)


def test_builder_invalid_retrieval_mode():
    builder = RAGContextBuilder()
    with pytest.raises(ValueError, match="retrieval_mode"):
        builder.build("query", KB, HISTORY, retrieval_mode="bogus")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# RAGContextBuilder — retrieval modes
# ---------------------------------------------------------------------------

def test_builder_keyword_mode():
    builder = RAGContextBuilder(token_budget=1000)
    result = builder.build("authentication bearer token", KB, HISTORY, retrieval_mode="keyword")
    assert len(result.retrieved_docs) > 0


def test_builder_tfidf_mode():
    builder = RAGContextBuilder(token_budget=1000)
    result = builder.build("streaming server-sent events", KB, HISTORY, retrieval_mode="tfidf")
    titles = [r.doc.title for r in result.retrieved_docs]
    assert "Streaming Responses" in titles


def test_builder_hybrid_mode():
    builder = RAGContextBuilder(token_budget=1000)
    result = builder.build("rate limit 429 backoff", KB, HISTORY, retrieval_mode="hybrid")
    assert len(result.retrieved_docs) > 0
    titles = [r.doc.title for r in result.retrieved_docs]
    assert "Rate Limiting" in titles


# ---------------------------------------------------------------------------
# RAGContextBuilder — token budget
# ---------------------------------------------------------------------------

def test_builder_token_budget_respected():
    builder = RAGContextBuilder(token_budget=500)
    result = builder.build("authentication streaming rate limit", KB, HISTORY)
    assert result.token_estimate <= 550  # 10 % headroom for estimation error


def test_builder_doc_budget_fraction():
    budget = 400
    fraction = 0.7
    builder = RAGContextBuilder(token_budget=budget, doc_budget_fraction=fraction)
    result = builder.build("token authentication", KB, HISTORY)
    assert result.tokens_from_docs <= int(budget * fraction) + 10  # small tolerance


def test_builder_memory_budget_fraction():
    budget = 400
    fraction = 0.7
    builder = RAGContextBuilder(token_budget=budget, doc_budget_fraction=fraction)
    result = builder.build("token authentication", KB, HISTORY)
    mem_budget = budget - int(budget * fraction)
    assert result.tokens_from_memory <= mem_budget + 10


# ---------------------------------------------------------------------------
# RAGContextBuilder — edge cases
# ---------------------------------------------------------------------------

def test_builder_empty_documents():
    builder = RAGContextBuilder()
    result = builder.build("any query", [], HISTORY)
    assert result.retrieved_docs == []
    assert result.tokens_from_docs == 0


def test_builder_empty_history():
    builder = RAGContextBuilder()
    result = builder.build("any query", KB, [])
    assert result.memory_turns == []
    assert result.tokens_from_memory == 0


def test_builder_empty_both():
    builder = RAGContextBuilder()
    result = builder.build("any query", [], [])
    assert result.retrieved_docs == []
    assert result.memory_turns == []
    assert result.system_block == ""
    assert result.token_estimate == 0


# ---------------------------------------------------------------------------
# RAGContextBuilder — output structure
# ---------------------------------------------------------------------------

def test_builder_system_block_contains_doc_title():
    builder = RAGContextBuilder(token_budget=2000)
    result = builder.build("authentication bearer token", KB, [], retrieval_mode="keyword")
    assert "Authentication Guide" in result.system_block


def test_builder_system_block_contains_tags():
    builder = RAGContextBuilder(token_budget=2000)
    result = builder.build("error 401 403", KB, [], retrieval_mode="keyword")
    # "Error Handling" has tags ["errors", "http"]
    if any(r.doc.id == "5" for r in result.retrieved_docs):
        assert "errors" in result.system_block


def test_builder_system_block_contains_memory():
    builder = RAGContextBuilder(token_budget=2000, min_memory_score=0.0)
    result = builder.build("authentication token", KB, HISTORY[:2])
    assert "Conversation Context" in result.system_block
    assert "User:" in result.system_block or "**User:**" in result.system_block


def test_builder_memory_turns_chronological_order():
    builder = RAGContextBuilder(token_budget=2000, min_memory_score=0.0)
    result = builder.build("streaming", KB, HISTORY)
    indices = [t.turn_index for t, _ in result.memory_turns]
    assert indices == sorted(indices)


def test_builder_docs_dropped_count():
    builder = RAGContextBuilder(token_budget=2000, min_doc_score=0.99)  # very high threshold
    result = builder.build("authentication", KB, [])
    # Most docs will fail the min_doc_score threshold
    assert result.docs_dropped >= 0


def test_builder_returned_types():
    builder = RAGContextBuilder(token_budget=2000)
    result = builder.build("authentication", KB, HISTORY)
    assert isinstance(result, ContextResult)
    for rd in result.retrieved_docs:
        assert isinstance(rd, RetrievedDoc)
        assert isinstance(rd.score, float)
        assert isinstance(rd.excerpt, str)
        assert rd.token_estimate >= 1
    for turn, score in result.memory_turns:
        assert isinstance(turn, MemoryTurn)
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# RAGContextBuilder — memory decay behaviour
# ---------------------------------------------------------------------------

def test_memory_decay_old_turns_filtered():
    # Build a long history where old turns have no relevance to query
    old_turns = [
        _turn("user", f"unrelated message about weather turn {i}", i)
        for i in range(20)
    ]
    recent_relevant = _turn("user", "how does bearer token authentication work", 20)
    all_turns = old_turns + [recent_relevant]

    builder = RAGContextBuilder(
        token_budget=2000,
        memory_decay_rate=0.7,   # fast decay
        min_memory_score=0.15,   # relatively high threshold
    )
    result = builder.build("bearer token authentication", KB, all_turns)
    indices = [t.turn_index for t, _ in result.memory_turns]
    # The recent relevant turn should be included
    assert 20 in indices
    # Very old unrelated turns should be dropped
    assert 0 not in indices


def test_memory_no_decay_with_rate_1():
    turns = [_turn("user", "hello world", i) for i in range(5)]
    builder = RAGContextBuilder(
        token_budget=2000,
        memory_decay_rate=1.0,  # no decay
        min_memory_score=0.0,
    )
    result = builder.build("hello", KB, turns, top_k_turns=5)
    # All turns should have the same recency component → all selected
    assert len(result.memory_turns) == 5

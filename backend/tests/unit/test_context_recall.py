"""Unit tests for context recall heuristic (no LLM / no embeddings required)."""
from unittest.mock import patch

import pytest

from app.services.context_recall import (
    compute_context_recall_heuristic,
    _significant_tokens,
)


def test_empty_inputs_return_zero():
    assert compute_context_recall_heuristic("", ["chunk"]) == 0.0
    assert compute_context_recall_heuristic("what is oauth?", []) == 0.0
    assert compute_context_recall_heuristic("what is oauth?", [""]) == 0.0


def test_full_query_term_coverage():
    query = "OAuth token refresh"
    chunks = [
        "OAuth token refresh uses the refresh_token grant to obtain a new access token."
    ]
    score = compute_context_recall_heuristic(query, chunks)
    assert score == 1.0


def test_zero_query_term_coverage():
    query = "Kubernetes horizontal pod autoscaling"
    chunks = ["The cafeteria menu for Tuesday includes pasta and salad."]
    score = compute_context_recall_heuristic(query, chunks, answer=None)
    assert score == 0.0


def test_partial_query_term_coverage():
    query = "oauth refresh tokens"
    chunks = ["Documentation about oauth login flows."]
    score = compute_context_recall_heuristic(query, chunks)
    # oauth covered; refresh/tokens not → 1/3
    assert score == pytest.approx(1 / 3, abs=0.001)


def test_answer_blend_with_lexical_fallback():
    """When embedding model is unavailable, answer path uses lexical fallback."""
    query = "refund policy timeline"
    chunks = ["Our refund policy allows returns within 30 days of purchase."]
    answer = "You can get a refund within 30 days. Shipping is free worldwide forever."

    with patch("app.services.ragas_service.get_embedding_model", return_value=None):
        score = compute_context_recall_heuristic(query, chunks, answer)

    # query coverage high + answer blend → between 0 and 1
    assert 0.0 < score <= 1.0


def test_significant_tokens_filters_stopwords():
    tokens = _significant_tokens("What is the refund policy for returns?")
    assert "what" not in tokens
    assert "the" not in tokens
    assert "refund" in tokens
    assert "policy" in tokens
    assert "returns" in tokens


def test_low_context_recall_classifies_retrieval_miss():
    from app.services.failure_classifier import classify_failure

    chunks = [{"chunk_id": "c1", "chunk_text": "partial", "similarity_score": 0.75, "was_cited": False}]
    ft, expl, _ = classify_failure(
        0.9, 0.8, 0.9, chunks, "test", "answer", context_recall_score=0.2
    )
    assert ft == "retrieval_miss"
    assert "recall" in expl.lower()


@pytest.mark.asyncio
async def test_compute_context_recall_prefers_heuristic_without_llm():
    from app.services.context_recall import compute_context_recall

    score = await compute_context_recall(
        "oauth token refresh",
        ["OAuth token refresh is documented here."],
        prefer_llm=False,
    )
    assert score == 1.0

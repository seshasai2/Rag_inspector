"""Unit tests for BM25 vs vector comparison (PRD F4)."""
from app.services.bm25_service import (
    BM25_BETTER_MARGIN,
    aggregate_bm25_outperform_rate,
    get_bm25_comparison,
    summarize_bm25_vs_vector,
)


def test_summarize_bm25_better():
    chunks = [
        {"bm25_score": 0.9, "similarity_score": 0.5},
        {"bm25_score": 0.2, "similarity_score": 0.4},
    ]
    result = summarize_bm25_vs_vector(chunks)
    assert result["comparable"] is True
    assert result["bm25_better"] is True
    assert result["top_bm25_score"] == 0.9
    assert result["top_vector_score"] == 0.5
    assert "BM25 would have been better" in result["analysis"]


def test_summarize_vector_ok():
    chunks = [
        {"bm25_score": 0.5, "similarity_score": 0.8},
    ]
    result = summarize_bm25_vs_vector(chunks)
    assert result["bm25_better"] is False
    assert "Vector search performed well" in result["analysis"]


def test_summarize_missing_scores():
    assert summarize_bm25_vs_vector([])["comparable"] is False
    assert summarize_bm25_vs_vector([{"similarity_score": 0.9}])["comparable"] is False
    assert summarize_bm25_vs_vector([{"bm25_score": 0.9}])["comparable"] is False


def test_margin_constant():
    assert BM25_BETTER_MARGIN == 0.15
    # Exactly at margin is not "better"
    chunks = [{"bm25_score": 0.65, "similarity_score": 0.5}]
    assert summarize_bm25_vs_vector(chunks)["bm25_better"] is False
    chunks2 = [{"bm25_score": 0.66, "similarity_score": 0.5}]
    assert summarize_bm25_vs_vector(chunks2)["bm25_better"] is True


def test_aggregate_empty():
    result = aggregate_bm25_outperform_rate([])
    assert result["traces_compared"] == 0
    assert result["bm25_outperform_rate"] == 0.0
    assert result["recommend_hybrid"] is False


def test_aggregate_rate_and_hybrid_recommendation():
    # 4/10 better → 40%, recommend hybrid (>=30% and >=10 comparable)
    flags = [True, True, True, True, False, False, False, False, False, False]
    result = aggregate_bm25_outperform_rate(flags)
    assert result["traces_compared"] == 10
    assert result["bm25_better_count"] == 4
    assert result["bm25_outperform_rate"] == 0.4
    assert result["recommend_hybrid"] is True
    assert "hybrid" in result["summary"].lower()


def test_aggregate_excludes_none():
    flags = [True, None, False, None]
    result = aggregate_bm25_outperform_rate(flags)
    assert result["traces_compared"] == 2
    assert result["bm25_outperform_rate"] == 0.5


def test_get_bm25_comparison_includes_chunks():
    chunks = [
        {"chunk_id": "c1", "chunk_text": "Paris capital France", "similarity_score": 0.3},
        {"chunk_id": "c2", "chunk_text": "unrelated weather", "similarity_score": 0.9},
    ]
    result = get_bm25_comparison("Paris France capital", chunks)
    assert "chunks_with_bm25" in result
    assert all("bm25_score" in c for c in result["chunks_with_bm25"])
    assert "comparable" in result

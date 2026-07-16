"""Unit tests for analysis services."""
import pytest
from app.services.grounding import check_grounding, split_into_sentences
from app.services.bm25_service import compute_bm25_scores, get_bm25_comparison
from app.services.failure_classifier import classify_failure


class TestGrounding:
    def test_split_sentences(self):
        text = "Paris is the capital of France. It is known for the Eiffel Tower. Many tourists visit each year."
        sentences = split_into_sentences(text)
        assert len(sentences) == 3

    def test_split_empty(self):
        assert split_into_sentences("") == []

    def test_check_grounding_no_answer(self):
        result = check_grounding("", [{"chunk_id": "c1", "chunk_text": "Paris is the capital"}])
        assert result["grounded_fraction"] == 0.0

    def test_check_grounding_no_chunks(self):
        result = check_grounding("Paris is the capital.", [])
        assert result["grounded_fraction"] == 0.0

    def test_check_grounding_keyword_fallback(self):
        """Uses keyword fallback when NLI model unavailable."""
        result = check_grounding(
            "Paris is the capital of France.",
            [{"chunk_id": "c1", "chunk_text": "Paris is the capital and largest city of France."}],
            threshold=0.3,
        )
        assert "grounded_fraction" in result
        assert "sentence_results" in result
        assert len(result["sentence_results"]) > 0


class TestBM25:
    def test_bm25_scores_computed(self):
        chunks = [
            {"chunk_id": "c1", "chunk_text": "Paris is the capital of France"},
            {"chunk_id": "c2", "chunk_text": "London is the capital of England"},
            {"chunk_id": "c3", "chunk_text": "The weather today is sunny"},
        ]
        result = compute_bm25_scores("capital France", chunks)
        assert len(result) == 3
        assert all("bm25_score" in c for c in result)
        assert all(0 <= c["bm25_score"] <= 1 for c in result)
        # Paris/France chunk should score highest
        paris_score = next(c["bm25_score"] for c in result if "Paris" in c["chunk_text"])
        weather_score = next(c["bm25_score"] for c in result if "weather" in c["chunk_text"])
        assert paris_score >= weather_score

    def test_bm25_empty_query(self):
        chunks = [{"chunk_id": "c1", "chunk_text": "some text"}]
        result = compute_bm25_scores("", chunks)
        assert result == chunks

    def test_bm25_comparison(self):
        chunks = [
            {"chunk_id": "c1", "chunk_text": "Paris capital France", "similarity_score": 0.3},
            {"chunk_id": "c2", "chunk_text": "London England weather", "similarity_score": 0.4},
        ]
        result = get_bm25_comparison("capital France Paris", chunks)
        assert "bm25_better" in result
        assert "top_vector_score" in result
        assert "top_bm25_score" in result
        assert "analysis" in result


class TestFailureClassifier:
    def test_classify_coverage_gap_no_chunks(self):
        ft, expl, rec = classify_failure(None, None, None, [], "test query", "test answer")
        assert ft == "coverage_gap"

    def test_classify_coverage_gap_low_similarity(self):
        chunks = [{"chunk_id": "c1", "chunk_text": "unrelated", "similarity_score": 0.1}]
        ft, _, _ = classify_failure(None, None, None, chunks, "test", "test")
        assert ft == "coverage_gap"

    def test_classify_hallucination(self):
        chunks = [{"chunk_id": "c1", "chunk_text": "relevant content", "similarity_score": 0.85, "was_cited": True}]
        ft, _, _ = classify_failure(0.3, 0.8, 0.2, chunks, "test query", "answer with hallucinations")
        assert ft == "hallucination"

    def test_classify_retrieval_irrelevant(self):
        chunks = [{"chunk_id": "c1", "chunk_text": "wrong topic", "similarity_score": 0.7, "was_cited": False}]
        ft, _, _ = classify_failure(0.8, 0.1, 0.8, chunks, "test", "test")
        assert ft == "retrieval_irrelevant"

    def test_classify_none(self):
        chunks = [{"chunk_id": "c1", "chunk_text": "relevant", "similarity_score": 0.9, "was_cited": True}]
        ft, _, _ = classify_failure(0.9, 0.8, 0.9, chunks, "test", "good answer")
        assert ft == "none"

    def test_recommendation_provided(self):
        chunks = []
        _, _, rec = classify_failure(None, None, None, chunks, "test", None)
        assert len(rec) > 10

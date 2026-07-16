"""Studio + benchmark helpers (Phase 10.6 / 10.7)."""
from app.services.studio import analyze_prompt, chunk_optimizer_suggestions, simulate_top_k


def test_analyze_prompt_flags_missing_context():
    result = analyze_prompt("Answer the question helpfully.")
    codes = {i["code"] for i in result["issues"]}
    assert "missing_context" in codes


def test_chunk_optimizer_finds_low_cite():
    out = chunk_optimizer_suggestions(
        [{"chunk_id": "c1", "retrieval_count": 20, "citation_rate": 0.05, "citation_count": 1}]
    )
    assert out["suggestion_count"] >= 1


def test_simulate_top_k():
    out = simulate_top_k(
        [
            {"similarity_score": 0.9, "was_cited": True},
            {"similarity_score": 0.5, "was_cited": False},
            {"similarity_score": 0.4, "was_cited": False},
        ],
        top_k=1,
    )
    assert out["chunks_kept"] == 1
    assert out["cited_among_kept"] == 1

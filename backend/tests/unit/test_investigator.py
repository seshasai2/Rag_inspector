"""AI Investigator deterministic citations (Phase 10.8)."""
import pytest

from app.services.ai_investigator import answer_from_facts, build_metric_pack, investigate


def test_build_metric_pack():
    facts = build_metric_pack(
        {
            "trustworthiness_score": 88,
            "hallucination_rate": 0.1,
            "total_queries": 50,
            "failure_type_counts": {"coverage_gap": 3},
        }
    )
    metrics = {f["metric"] for f in facts}
    assert "trust_score" in metrics
    assert "failure:coverage_gap" in metrics


def test_answer_from_facts_cites_trust():
    facts = [{"metric": "trust_score", "value": 77, "source": "trustworthiness_score"}]
    out = answer_from_facts("What is my trust score?", facts)
    assert "77" in out["answer"]
    assert out["citations"]


@pytest.mark.asyncio
async def test_investigate_offline():
    out = await investigate(
        "What is hallucination rate?",
        {"hallucination_rate": 0.12, "trustworthiness_score": 70, "total_queries": 10},
    )
    assert out["citations"]
    assert out["answer"]

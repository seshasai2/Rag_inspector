"""Knowledge gap detection (Phase 10.1)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.knowledge_gap import (
    detect_knowledge_gaps,
    normalize_gap_status,
    priority_for_count,
    upsert_knowledge_gaps,
)


def test_priority_for_count():
    assert priority_for_count(25) == "critical"
    assert priority_for_count(12) == "high"
    assert priority_for_count(6) == "medium"
    assert priority_for_count(2) == "low"


def test_normalize_gap_status():
    assert normalize_gap_status("Open") == "open"
    with pytest.raises(ValueError):
        normalize_gap_status("done")


def test_detect_knowledge_gaps_maps_clusters():
    queries = [{"query_text": f"how to rotate api keys {i}"} for i in range(5)]
    fake_recs = [
        {
            "recommendation_type": "coverage_gap",
            "topic_description": "Add more documentation on 'how to rotate api keys 0'",
            "affected_query_count": 5,
            "sample_queries": '["how to rotate api keys 0", "how to rotate api keys 1"]',
        }
    ]
    with patch(
        "app.services.knowledge_gap.generate_fix_recommendations",
        return_value=fake_recs,
    ):
        gaps = detect_knowledge_gaps(
            queries,
            min_cluster_size=3,
            pipeline_queries_per_month=1000,
            cost_per_wrong_answer_usd=5.0,
            total_recent_failures=10,
        )
    assert len(gaps) == 1
    assert gaps[0]["query_count"] == 5
    assert gaps[0]["priority"] == "medium"
    assert gaps[0]["failure_rate"] == 0.5
    assert gaps[0]["estimated_monthly_cost_usd"] == 2500.0


def test_upsert_knowledge_gaps_inserts_new():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    pipeline = MagicMock()
    pipeline.id = "pipe-1"
    n = upsert_knowledge_gaps(
        db,
        pipeline,
        [
            {
                "topic_label": "api key rotation",
                "representative_query": "how to rotate keys",
                "query_count": 4,
                "priority": "low",
            }
        ],
    )
    assert n == 1
    assert db.add.called

"""Unit tests for PRD F5 chunk quality / auto-flag rules."""
from app.services.chunk_quality import (
    LOW_QUALITY_MAX_CITATION_RATE,
    LOW_QUALITY_MIN_RETRIEVALS,
    apply_chunk_quality_update,
    citation_heatmap_band,
    compute_citation_rate,
    should_auto_flag_low_quality,
)


def test_prd_thresholds():
    assert LOW_QUALITY_MIN_RETRIEVALS == 50
    assert LOW_QUALITY_MAX_CITATION_RATE == 0.2


def test_should_auto_flag_rule():
    assert should_auto_flag_low_quality(50, 0.19) is True
    assert should_auto_flag_low_quality(49, 0.0) is False
    assert should_auto_flag_low_quality(100, 0.2) is False  # not < 0.2
    assert should_auto_flag_low_quality(100, 0.199) is True


def test_apply_updates_rate_and_flags():
    result = apply_chunk_quality_update(
        retrieval_count=50,
        citation_count=5,  # 10%
        currently_flagged=False,
    )
    assert result["citation_rate"] == 0.1
    assert result["is_flagged"] is True
    assert result["newly_auto_flagged"] is True


def test_flag_sticky_without_auto_unflag():
    result = apply_chunk_quality_update(
        retrieval_count=10,
        citation_count=8,
        currently_flagged=True,
        auto_unflag=False,
    )
    assert result["is_flagged"] is True  # sticky


def test_auto_unflag_when_improved():
    result = apply_chunk_quality_update(
        retrieval_count=10,
        citation_count=8,
        currently_flagged=True,
        auto_unflag=True,
    )
    assert result["is_flagged"] is False


def test_heatmap_bands():
    assert citation_heatmap_band(0.9) == "excellent"
    assert citation_heatmap_band(0.65) == "good"
    assert citation_heatmap_band(0.45) == "fair"
    assert citation_heatmap_band(0.25) == "poor"
    assert citation_heatmap_band(0.1) == "low"


def test_compute_citation_rate():
    assert compute_citation_rate(0, 0) == 0.0
    assert compute_citation_rate(10, 5) == 0.5

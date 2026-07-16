"""
Chunk quality rules (PRD F5).

Low-quality auto-flag:
  retrieval_count >= LOW_QUALITY_MIN_RETRIEVALS (50)
  AND citation_rate < LOW_QUALITY_MAX_CITATION_RATE (0.20)

Heatmap color bands (citation rate):
  >= 0.80 excellent → dark green
  >= 0.60 good
  >= 0.40 fair
  >= 0.20 poor
  <  0.20 low quality → dark red
"""

from __future__ import annotations

from typing import Any

LOW_QUALITY_MIN_RETRIEVALS = 50
LOW_QUALITY_MAX_CITATION_RATE = 0.20


def compute_citation_rate(retrieval_count: int, citation_count: int) -> float:
    if retrieval_count <= 0:
        return 0.0
    return round(citation_count / retrieval_count, 4)


def should_auto_flag_low_quality(
    retrieval_count: int,
    citation_rate: float,
    *,
    min_retrievals: int = LOW_QUALITY_MIN_RETRIEVALS,
    max_citation_rate: float = LOW_QUALITY_MAX_CITATION_RATE,
) -> bool:
    """PRD F5: flag chunks retrieved often but rarely cited."""
    return retrieval_count >= min_retrievals and citation_rate < max_citation_rate


def apply_chunk_quality_update(
    *,
    retrieval_count: int,
    citation_count: int,
    currently_flagged: bool = False,
    auto_unflag: bool = False,
) -> dict[str, Any]:
    """
    Recompute citation_rate and decide auto-flag.

    Auto-flag is sticky by default (manual unflag can clear; beat job can re-flag).
    Set ``auto_unflag=True`` to clear the flag when the chunk no longer meets
    the low-quality rule (used by the periodic refresh task).
    """
    rate = compute_citation_rate(retrieval_count, citation_count)
    meets_rule = should_auto_flag_low_quality(retrieval_count, rate)
    if meets_rule:
        flagged = True
    elif auto_unflag:
        flagged = False
    else:
        flagged = currently_flagged

    return {
        "citation_rate": rate,
        "is_flagged": flagged,
        "auto_flag_eligible": meets_rule,
        "newly_auto_flagged": meets_rule and not currently_flagged,
    }


def citation_heatmap_band(citation_rate: float) -> str:
    """Return band id for UI coloring."""
    if citation_rate >= 0.8:
        return "excellent"
    if citation_rate >= 0.6:
        return "good"
    if citation_rate >= 0.4:
        return "fair"
    if citation_rate >= 0.2:
        return "poor"
    return "low"

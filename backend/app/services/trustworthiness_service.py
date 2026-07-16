"""
Per-trace trustworthiness (stored on QueryTrace).

This is a single-query diagnostic (60% faithfulness + 40% grounding).
The dashboard / pipeline hero metric is the aggregate Trust Score in
``app.services.trust_scorer`` (30/30/20/20 over recent traces).
"""

from typing import Optional


def compute_trustworthiness(
    faithfulness_score: Optional[float] = None,
    grounded_fraction: Optional[float] = None,
) -> float:
    """
    Compute a per-trace trustworthiness score (0-100).

    Weighted average:
    - faithfulness_score (RAGAS): 60% weight
    - grounded_fraction (NLI): 40% weight

    Falls back to either if one is None.
    """
    scores = []
    weights = []

    if faithfulness_score is not None:
        scores.append(faithfulness_score)
        weights.append(0.6)

    if grounded_fraction is not None:
        scores.append(grounded_fraction)
        weights.append(0.4)

    if not scores:
        return 0.0

    # Normalize weights to sum to 1
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    score = sum(s * w for s, w in zip(scores, normalized_weights, strict=True))
    return round(score * 100, 1)  # 0-100 scale


def aggregate_trustworthiness(
    faithfulness_scores: list[float],
    grounded_fractions: list[float],
) -> float:
    """
    Legacy pairwise aggregate. Prefer ``trust_scorer.compute_trust_score``
    for dashboard / pipeline Trust Score.
    """
    if not faithfulness_scores and not grounded_fractions:
        return 0.0

    scores = []
    weights = []

    if faithfulness_scores:
        scores.append(sum(faithfulness_scores) / len(faithfulness_scores))
        weights.append(0.6)

    if grounded_fractions:
        scores.append(sum(grounded_fractions) / len(grounded_fractions))
        weights.append(0.4)

    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    aggregate = sum(s * w for s, w in zip(scores, normalized_weights, strict=True))
    return round(aggregate * 100, 1)

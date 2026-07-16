"""
Trust Score (0–100) — hiring hero metric.

Documented formula (spec v2):

    faithfulness_component = mean(faithfulness) * 30
    grounding_component    = mean(grounded_fraction) * 30
    retrieval_component    = mean(context_precision) * 20
    reliability_component  = (1 - failure_rate) * 20

    trust_score = round(sum(components), 1)

Window: most recent ``TRUST_SCORE_WINDOW`` traces (default 100).

Edge cases:
- No traces → 0.0
- Missing metric values are omitted from that component's mean
- If a component has no values, its mean is 0.0 (component contributes 0)
- ``failure_rate`` = fraction of traces with ``is_hallucination is True``
  (``None`` / ``False`` count as non-failures)
"""

from __future__ import annotations

from typing import Optional, Protocol, Sequence

TRUST_SCORE_WINDOW = 100

_FAITHFULNESS_WEIGHT = 30.0
_GROUNDING_WEIGHT = 30.0
_RETRIEVAL_WEIGHT = 20.0
_RELIABILITY_WEIGHT = 20.0


class TraceLike(Protocol):
    faithfulness_score: Optional[float]
    grounded_fraction: Optional[float]
    context_precision_score: Optional[float]
    is_hallucination: Optional[bool]


def _mean_or_zero(values: Sequence[Optional[float]]) -> float:
    present = [float(v) for v in values if v is not None]
    if not present:
        return 0.0
    return sum(present) / len(present)


def compute_trust_score_from_metrics(
    *,
    faithfulness_scores: Sequence[Optional[float]],
    grounded_fractions: Sequence[Optional[float]],
    context_precision_scores: Sequence[Optional[float]],
    is_hallucination_flags: Sequence[Optional[bool]],
) -> float:
    """
    Compute Trust Score from aligned metric sequences (same length preferred).

    Sequences may be empty (returns 0.0). Lengths need not match; means and
    failure_rate are computed independently on each sequence.
    """
    n_failure_window = len(is_hallucination_flags)
    if (
        not faithfulness_scores
        and not grounded_fractions
        and not context_precision_scores
        and n_failure_window == 0
    ):
        return 0.0

    faithfulness_component = _mean_or_zero(faithfulness_scores) * _FAITHFULNESS_WEIGHT
    grounding_component = _mean_or_zero(grounded_fractions) * _GROUNDING_WEIGHT
    retrieval_component = _mean_or_zero(context_precision_scores) * _RETRIEVAL_WEIGHT

    if n_failure_window == 0:
        failure_rate = 0.0
    else:
        failures = sum(1 for flag in is_hallucination_flags if flag is True)
        failure_rate = failures / n_failure_window

    reliability_component = (1.0 - failure_rate) * _RELIABILITY_WEIGHT

    return round(
        faithfulness_component + grounding_component + retrieval_component + reliability_component,
        1,
    )


def compute_trust_score(
    traces: Sequence[TraceLike],
    *,
    limit: int = TRUST_SCORE_WINDOW,
) -> float:
    """
    Aggregate Trust Score over the first ``limit`` traces.

    Callers should pass traces already ordered newest-first (e.g. by
    ``traced_at`` descending). Only the first ``limit`` entries are used.
    """
    window = list(traces[:limit]) if limit > 0 else []
    return compute_trust_score_from_metrics(
        faithfulness_scores=[t.faithfulness_score for t in window],
        grounded_fractions=[t.grounded_fraction for t in window],
        context_precision_scores=[t.context_precision_score for t in window],
        is_hallucination_flags=[t.is_hallucination for t in window],
    )

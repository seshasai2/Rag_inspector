"""
Hallucination Cost — hiring hero metric ($/month).

Documented formula (spec v2):

    hallucination_rate = count(hallucinated traces) / len(recent_traces)
    monthly_hallucinations = queries_per_month * hallucination_rate
    monthly_cost = monthly_hallucinations * cost_per_wrong_answer_usd

Defaults match pipeline columns: 10_000 queries/month × $5.00/wrong answer.
"""

from __future__ import annotations

from typing import Optional, Sequence

DEFAULT_QUERIES_PER_MONTH = 10_000
DEFAULT_COST_PER_WRONG_ANSWER_USD = 5.0


def hallucination_rate(
    is_hallucination_flags: Sequence[Optional[bool]],
) -> float:
    """Fraction of traces marked as hallucinations (``True`` only)."""
    n = len(is_hallucination_flags)
    if n == 0:
        return 0.0
    return sum(1 for flag in is_hallucination_flags if flag is True) / n


def estimate_hallucination_cost(
    *,
    queries_per_month: int | float,
    cost_per_wrong_answer_usd: float,
    hallucination_rate_value: float,
) -> float:
    """
    Estimated monthly USD cost of undetected hallucinations.

    Clamps rate to [0, 1]. Negative queries/cost are treated as 0.
    """
    rate = max(0.0, min(1.0, float(hallucination_rate_value)))
    queries = max(0.0, float(queries_per_month))
    unit_cost = max(0.0, float(cost_per_wrong_answer_usd))
    return round(queries * rate * unit_cost, 2)


def estimate_hallucination_cost_from_flags(
    *,
    queries_per_month: int | float = DEFAULT_QUERIES_PER_MONTH,
    cost_per_wrong_answer_usd: float = DEFAULT_COST_PER_WRONG_ANSWER_USD,
    is_hallucination_flags: Sequence[Optional[bool]],
) -> float:
    """Convenience: derive rate from flags then estimate cost."""
    return estimate_hallucination_cost(
        queries_per_month=queries_per_month,
        cost_per_wrong_answer_usd=cost_per_wrong_answer_usd,
        hallucination_rate_value=hallucination_rate(is_hallucination_flags),
    )

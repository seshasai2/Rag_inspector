"""Unit tests for Hallucination Cost hero metric."""
import pytest

from app.services.hallucination_cost import (
    DEFAULT_COST_PER_WRONG_ANSWER_USD,
    DEFAULT_QUERIES_PER_MONTH,
    estimate_hallucination_cost,
    estimate_hallucination_cost_from_flags,
    hallucination_rate,
)


def test_defaults():
    assert DEFAULT_QUERIES_PER_MONTH == 10_000
    assert DEFAULT_COST_PER_WRONG_ANSWER_USD == 5.0


def test_empty_flags_zero_rate_and_cost():
    assert hallucination_rate([]) == 0.0
    assert (
        estimate_hallucination_cost_from_flags(is_hallucination_flags=[]) == 0.0
    )


def test_documented_example():
    # 4.2% × 10_000 × $5 = $2,100
    cost = estimate_hallucination_cost(
        queries_per_month=10_000,
        cost_per_wrong_answer_usd=5.0,
        hallucination_rate_value=0.042,
    )
    assert cost == 2100.0


def test_half_rate_from_flags():
    flags = [True, False, True, False]
    assert hallucination_rate(flags) == 0.5
    assert (
        estimate_hallucination_cost_from_flags(
            queries_per_month=1000,
            cost_per_wrong_answer_usd=10.0,
            is_hallucination_flags=flags,
        )
        == 5000.0
    )


def test_none_flags_not_counted_as_failures():
    assert hallucination_rate([None, False, True]) == pytest.approx(1 / 3)


def test_clamps_rate_and_negatives():
    assert (
        estimate_hallucination_cost(
            queries_per_month=-100,
            cost_per_wrong_answer_usd=5.0,
            hallucination_rate_value=0.5,
        )
        == 0.0
    )
    assert (
        estimate_hallucination_cost(
            queries_per_month=1000,
            cost_per_wrong_answer_usd=-5.0,
            hallucination_rate_value=0.5,
        )
        == 0.0
    )
    assert (
        estimate_hallucination_cost(
            queries_per_month=1000,
            cost_per_wrong_answer_usd=5.0,
            hallucination_rate_value=2.0,  # clamp to 1.0
        )
        == 5000.0
    )


def test_zero_rate_zero_cost():
    assert (
        estimate_hallucination_cost(
            queries_per_month=50_000,
            cost_per_wrong_answer_usd=25.0,
            hallucination_rate_value=0.0,
        )
        == 0.0
    )

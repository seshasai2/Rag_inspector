"""Unit tests for Trust Score hero metric (spec v2 formula)."""
from types import SimpleNamespace

import pytest

from app.services.trust_scorer import (
    TRUST_SCORE_WINDOW,
    compute_trust_score,
    compute_trust_score_from_metrics,
)


def test_empty_traces_return_zero():
    assert compute_trust_score([]) == 0.0
    assert (
        compute_trust_score_from_metrics(
            faithfulness_scores=[],
            grounded_fractions=[],
            context_precision_scores=[],
            is_hallucination_flags=[],
        )
        == 0.0
    )


def test_perfect_scores_yield_100():
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[1.0, 1.0],
        grounded_fractions=[1.0, 1.0],
        context_precision_scores=[1.0, 1.0],
        is_hallucination_flags=[False, False],
    )
    # 1*30 + 1*30 + 1*20 + 1*20 = 100
    assert score == 100.0


def test_all_hallucinations_zero_reliability():
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[1.0],
        grounded_fractions=[1.0],
        context_precision_scores=[1.0],
        is_hallucination_flags=[True, True],
    )
    # 30 + 30 + 20 + 0 = 80
    assert score == 80.0


def test_missing_metrics_treated_as_zero_component():
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[None, None],
        grounded_fractions=[None],
        context_precision_scores=[None],
        is_hallucination_flags=[False],
    )
    # only reliability: (1 - 0) * 20 = 20
    assert score == 20.0


def test_partial_metrics_omit_nones_from_mean():
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[1.0, None],
        grounded_fractions=[0.5],
        context_precision_scores=[0.0],
        is_hallucination_flags=[False, True],  # failure_rate = 0.5
    )
    # faith 1.0*30=30; ground 0.5*30=15; ret 0*20=0; rel 0.5*20=10 → 55
    assert score == 55.0


def test_half_failure_rate_reliability():
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[0.0],
        grounded_fractions=[0.0],
        context_precision_scores=[0.0],
        is_hallucination_flags=[True, False],
    )
    assert score == 10.0  # (1 - 0.5) * 20


def test_none_hallucination_flag_not_counted_as_failure():
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[0.0],
        grounded_fractions=[0.0],
        context_precision_scores=[0.0],
        is_hallucination_flags=[None, False],
    )
    assert score == 20.0


def test_window_limit_uses_first_n_only():
    traces = [
        SimpleNamespace(
            faithfulness_score=1.0,
            grounded_fraction=1.0,
            context_precision_score=1.0,
            is_hallucination=False,
        )
        for _ in range(3)
    ] + [
        SimpleNamespace(
            faithfulness_score=0.0,
            grounded_fraction=0.0,
            context_precision_score=0.0,
            is_hallucination=True,
        )
        for _ in range(5)
    ]
    # Only first 3 (perfect) → 100
    assert compute_trust_score(traces, limit=3) == 100.0


def test_default_window_constant():
    assert TRUST_SCORE_WINDOW == 100


@pytest.mark.parametrize(
    "faith,ground,precision,fails,expected",
    [
        ([0.8], [0.8], [0.8], [False], 84.0),  # 24+24+16+20
        ([0.5], [0.5], [0.5], [False], 60.0),  # 15+15+10+20
        ([0.0], [0.0], [0.0], [True], 0.0),
    ],
)
def test_documented_weighted_formula(faith, ground, precision, fails, expected):
    assert (
        compute_trust_score_from_metrics(
            faithfulness_scores=faith,
            grounded_fractions=ground,
            context_precision_scores=precision,
            is_hallucination_flags=fails,
        )
        == expected
    )

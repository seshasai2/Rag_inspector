"""Unit tests for week-over-week metric trend helpers."""
from app.services.metric_trends import percent_change


class TestPercentChange:
    def test_increase(self):
        assert percent_change(120, 100) == 20.0

    def test_decrease(self):
        assert percent_change(80, 100) == -20.0

    def test_no_baseline_returns_none(self):
        assert percent_change(10, 0) is None
        assert percent_change(0, 0) is None

    def test_rounding(self):
        assert percent_change(1.0, 3.0) == -66.7

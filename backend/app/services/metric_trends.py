"""Helpers for dashboard metric period-over-period trends."""


def percent_change(current: float, previous: float) -> float | None:
    """Return relative percent change, or ``None`` when previous lacks a baseline.

    Avoids inventing +100% when the prior window is empty.
    """
    if previous <= 0:
        return None
    return round(((current - previous) / previous) * 100, 1)

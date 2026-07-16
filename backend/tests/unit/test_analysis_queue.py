"""Tests for analysis queue helper messaging."""
from app.services.analysis_queue import queue_unavailable_message


def test_queue_unavailable_message_includes_retry_path():
    msg = queue_unavailable_message("abc-123")
    assert "abc-123" in msg
    assert "/reanalyze" in msg
    assert "Celery" in msg or "Redis" in msg

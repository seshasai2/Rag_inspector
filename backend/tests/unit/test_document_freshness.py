"""Document freshness helpers (Phase 10.3)."""
from datetime import datetime, timezone, timedelta

from app.services.document_freshness import classify_freshness, days_since, refresh_document_freshness


def test_classify_freshness_bands():
    assert classify_freshness(0) == "fresh"
    assert classify_freshness(45) == "aging"
    assert classify_freshness(100) == "stale"
    assert classify_freshness(200) == "outdated"
    assert classify_freshness(400) == "needs_review"
    assert classify_freshness(None) == "needs_review"


def test_refresh_document_freshness():
    class Doc:
        last_modified_at = datetime.now(timezone.utc) - timedelta(days=100)
        ingested_at = datetime.now(timezone.utc)
        days_since_modified = None
        freshness_status = "fresh"
        updated_at = None

    doc = Doc()
    assert refresh_document_freshness(doc) == "stale"
    assert doc.days_since_modified == 100


def test_days_since():
    now = datetime(2026, 7, 13, tzinfo=timezone.utc)
    past = datetime(2026, 6, 13, tzinfo=timezone.utc)
    assert days_since(past, now=now) == 30

"""Document freshness classification (Phase 10.3)."""

from __future__ import annotations

from datetime import datetime, timezone


def classify_freshness(days_since_modified: int | None) -> str:
    if days_since_modified is None:
        return "needs_review"
    if days_since_modified < 30:
        return "fresh"
    if days_since_modified < 90:
        return "aging"
    if days_since_modified < 180:
        return "stale"
    if days_since_modified < 365:
        return "outdated"
    return "needs_review"


def days_since(modified_at: datetime | None, *, now: datetime | None = None) -> int | None:
    if modified_at is None:
        return None
    now = now or datetime.now(timezone.utc)
    if modified_at.tzinfo is None:
        modified_at = modified_at.replace(tzinfo=timezone.utc)
    return max(0, (now - modified_at).days)


def refresh_document_freshness(doc, *, now: datetime | None = None) -> str:
    """Update days_since_modified + freshness_status on a Document ORM row."""
    now = now or datetime.now(timezone.utc)
    days = days_since(doc.last_modified_at or doc.ingested_at, now=now)
    doc.days_since_modified = days
    status = classify_freshness(days)
    doc.freshness_status = status
    doc.updated_at = now
    return status

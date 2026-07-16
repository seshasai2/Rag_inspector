"""Autofix apply / dismiss / trust verify (Phase 10.2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import autofix as af


@pytest.mark.asyncio
async def test_apply_sets_status_and_trust_before():
    rec = MagicMock()
    rec.pipeline_id = "p1"
    rec.trust_score_before = None
    with patch.object(af, "pipeline_trust_score", new=AsyncMock(return_value=72.5)):
        out = await af.apply_recommendation(MagicMock(), rec)
    assert out.status == "applied"
    assert out.trust_score_before == 72.5
    assert out.applied_at is not None


@pytest.mark.asyncio
async def test_dismiss_sets_status():
    rec = MagicMock()
    rec.pipeline_id = "p1"
    out = await af.dismiss_recommendation(MagicMock(), rec)
    assert out.status == "dismissed"
    assert out.dismissed_at is not None


@pytest.mark.asyncio
async def test_verify_requires_applied():
    rec = MagicMock()
    rec.status = "open"
    with pytest.raises(ValueError):
        await af.verify_recommendation_trust(MagicMock(), rec)


@pytest.mark.asyncio
async def test_verify_records_delta():
    rec = MagicMock()
    rec.status = "applied"
    rec.pipeline_id = "p1"
    rec.trust_score_before = 70.0
    with patch.object(af, "pipeline_trust_score", new=AsyncMock(return_value=75.0)):
        result = await af.verify_recommendation_trust(MagicMock(), rec)
    assert result["trust_score_after"] == 75.0
    assert result["trust_delta"] == 5.0
    assert result["improved"] is True

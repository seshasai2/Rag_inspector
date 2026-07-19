"""Prometheus metrics must be plain text, not JSON-encoded strings."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import PlainTextResponse


@pytest.mark.asyncio
async def test_metrics_returns_plain_text_not_json_string():
    from app.api.v1.endpoints import ops

    db = AsyncMock()
    response = MagicMock()
    with patch.object(ops, "collect_backlog_snapshot", new=AsyncMock(return_value={
        "analysis_jobs": {},
        "trace_analysis": {},
        "celery_queues": {},
        "analysis_backlog": 0,
    })):
        with patch.object(ops, "render_prometheus_backlog_lines", return_value=[]):
            result = await ops.metrics(response=response, db=db)

    assert isinstance(result, PlainTextResponse)
    body = result.body.decode("utf-8")
    assert body.startswith("# HELP")
    assert not body.startswith('"')  # not a JSON string
    assert "raginspector_api_uptime_seconds" in body

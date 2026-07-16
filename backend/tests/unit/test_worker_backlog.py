"""Worker backlog metrics (Phase 6.6)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import worker_backlog as wb


def test_redis_queue_depths_ok():
    fake = MagicMock()
    fake.ping.return_value = True
    fake.llen.side_effect = lambda q: {"analysis": 3, "celery": 1}[q]
    with patch("app.services.worker_backlog.Redis.from_url", return_value=fake):
        depths = wb.redis_queue_depths(queues=("analysis", "celery"))
    assert depths == {"analysis": 3, "celery": 1}
    fake.close.assert_called()


def test_redis_queue_depths_fail_open():
    with patch(
        "app.services.worker_backlog.Redis.from_url",
        side_effect=ConnectionError("down"),
    ):
        depths = wb.redis_queue_depths(queues=("analysis", "celery"))
    assert depths == {"analysis": None, "celery": None}


def test_render_prometheus_backlog_lines():
    snapshot = {
        "celery_queue_depths": {"analysis": 2, "celery": 0},
        "analysis_jobs": {"pending": 4, "running": 1, "completed": 10, "failed": 2},
        "trace_analysis_status": {"pending": 3, "analyzing": 1, "failed": 2},
        "backlog_pending_or_running": 5,
    }
    text = "\n".join(wb.render_prometheus_backlog_lines(snapshot))
    assert 'raginspector_celery_queue_depth{queue="analysis"} 2' in text
    assert 'raginspector_analysis_jobs{status="pending"} 4' in text
    assert "raginspector_analysis_backlog 5" in text
    assert 'raginspector_trace_analysis{status="analyzing"} 1' in text


@pytest.mark.asyncio
async def test_collect_backlog_snapshot_shape():
    db = MagicMock()

    async def _job_counts(_db):
        return {"pending": 2, "running": 1, "completed": 0, "failed": 0}

    async def _trace_counts(_db):
        return {"pending": 2, "analyzing": 1, "failed": 0}

    with (
        patch.object(wb, "redis_queue_depths", return_value={"analysis": 7, "celery": 0}),
        patch.object(wb, "analysis_job_counts", side_effect=_job_counts),
        patch.object(wb, "trace_analysis_status_counts", side_effect=_trace_counts),
    ):
        snap = await wb.collect_backlog_snapshot(db)

    assert snap["redis_ok"] is True
    assert snap["celery_messages_waiting"] == 7
    assert snap["backlog_pending_or_running"] == 3
    assert snap["analysis_jobs"]["pending"] == 2

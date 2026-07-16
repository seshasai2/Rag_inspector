"""Trace ingest orchestration (quota, persistence, analysis enqueue)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.plan_gate import plan_quota_detail
from app.models.models import (
    AnalysisJob,
    ChunkStat,
    JobStatus,
    Pipeline,
    QueryTrace,
    RetrievedChunk,
    User,
)
from app.schemas.schemas import TraceIngest, TraceIngestResponse
from app.services.analysis_queue import enqueue_analysis, queue_unavailable_message
from app.services.chunk_quality import apply_chunk_quality_update

logger = structlog.get_logger()

PLAN_LIMITS = {
    "free": settings.FREE_TRACES_PER_MONTH,
    "starter": settings.STARTER_TRACES_PER_MONTH,
    "pro": settings.PRO_TRACES_PER_MONTH,
    "enterprise": settings.ENTERPRISE_TRACES_PER_MONTH,
}


def _check_plan_quota(user: User) -> None:
    limit = PLAN_LIMITS.get(user.subscription_plan.value, settings.FREE_TRACES_PER_MONTH)
    if user.traces_this_month >= limit:
        raise HTTPException(
            status_code=429,
            detail=plan_quota_detail(limit=limit),
        )


async def _get_or_create_pipeline(
    db: AsyncSession,
    user: User,
    pipeline_name: str,
) -> Pipeline:
    result = await db.execute(
        select(Pipeline)
        .where(
            Pipeline.user_id == user.id,
            Pipeline.name == pipeline_name,
        )
        .order_by(Pipeline.created_at.desc())
        .limit(1)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        pipeline = Pipeline(
            user_id=user.id,
            organization_id=user.organization_id,
            name=pipeline_name,
        )
        db.add(pipeline)
        await db.flush()
    elif user.organization_id and not pipeline.organization_id:
        # Backfill org tag so invites can see existing pipelines.
        pipeline.organization_id = user.organization_id
    return pipeline


async def _batch_upsert_chunk_stats(
    db: AsyncSession,
    pipeline_id: str,
    chunks: list,
) -> None:
    """Load all matching ChunkStats in one query, then update/create in memory."""
    if not chunks:
        return

    chunk_ids = list({c.chunk_id for c in chunks})
    result = await db.execute(
        select(ChunkStat).where(
            ChunkStat.pipeline_id == pipeline_id,
            ChunkStat.chunk_id.in_(chunk_ids),
        )
    )
    existing = {cs.chunk_id: cs for cs in result.scalars().all()}
    now = datetime.now(timezone.utc)

    for chunk_data in chunks:
        cs = existing.get(chunk_data.chunk_id)
        if cs:
            cs.retrieval_count += 1
            cs.last_retrieved_at = now
            updated = apply_chunk_quality_update(
                retrieval_count=cs.retrieval_count,
                citation_count=cs.citation_count,
                currently_flagged=bool(cs.is_flagged),
            )
            cs.citation_rate = updated["citation_rate"]
            cs.is_flagged = updated["is_flagged"]
        else:
            cs = ChunkStat(
                chunk_id=chunk_data.chunk_id,
                pipeline_id=pipeline_id,
                text=chunk_data.chunk_text,
                retrieval_count=1,
                last_retrieved_at=now,
            )
            db.add(cs)
            existing[chunk_data.chunk_id] = cs


async def ingest_trace(
    db: AsyncSession,
    user: User,
    payload: TraceIngest,
) -> TraceIngestResponse:
    _check_plan_quota(user)

    pipeline = await _get_or_create_pipeline(db, user, payload.pipeline_name)

    client_metadata: dict = {}
    if payload.metadata:
        client_metadata.update(payload.metadata)
    if payload.stage_latencies:
        client_metadata["stage_latencies"] = payload.stage_latencies
    client_metadata_json = json.dumps(client_metadata) if client_metadata else None

    trace = QueryTrace(
        pipeline_id=pipeline.id,
        query_text=payload.query_text,
        query_embedding=payload.query_embedding,
        answer_text=payload.answer_text,
        raw_context=payload.raw_context,
        embed_latency_ms=payload.embed_latency_ms,
        retrieve_latency_ms=payload.retrieve_latency_ms,
        generate_latency_ms=payload.generate_latency_ms,
        rank_latency_ms=payload.rank_latency_ms,
        session_id=payload.session_id,
        request_id=payload.request_id,
        client_metadata_json=client_metadata_json,
        analysis_status="pending",
    )
    db.add(trace)
    await db.flush()

    for chunk_data in payload.retrieved_chunks:
        chunk = RetrievedChunk(
            trace_id=trace.id,
            chunk_id=chunk_data.chunk_id,
            chunk_text=chunk_data.chunk_text,
            similarity_score=chunk_data.similarity_score,
            rank=chunk_data.rank,
            metadata_json=json.dumps(chunk_data.metadata) if chunk_data.metadata else None,
        )
        db.add(chunk)

    await _batch_upsert_chunk_stats(db, pipeline.id, payload.retrieved_chunks)

    job = AnalysisJob(trace_id=trace.id)
    db.add(job)

    user.traces_this_month += 1

    await db.commit()

    task_id = None
    try:
        loop = asyncio.get_running_loop()
        task_id = await asyncio.wait_for(
            loop.run_in_executor(None, enqueue_analysis, str(trace.id)),
            timeout=2.0,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Celery task queue timeout",
            trace_id=str(trace.id),
            user_id=str(user.id),
        )
    except Exception as exc:
        logger.warning(
            "Failed to queue analysis task",
            error=str(exc),
            trace_id=str(trace.id),
            user_id=str(user.id),
        )

    job_result = await db.execute(select(AnalysisJob).where(AnalysisJob.trace_id == trace.id))
    job_obj = job_result.scalar_one_or_none()
    trace_result = await db.execute(select(QueryTrace).where(QueryTrace.id == trace.id))
    trace_obj = trace_result.scalar_one_or_none()

    if task_id:
        if job_obj:
            job_obj.celery_task_id = task_id
            job_obj.status = JobStatus.pending
        status = "accepted"
        message = "Trace queued for analysis"
    else:
        failure_message = queue_unavailable_message(str(trace.id))
        if trace_obj:
            trace_obj.analysis_status = "failed"
        if job_obj:
            job_obj.status = JobStatus.failed
            job_obj.error_message = failure_message
            job_obj.completed_at = datetime.now(timezone.utc)
        status = "accepted_unanalyzed"
        message = failure_message
        logger.warning(
            "Trace stored without analysis queue",
            trace_id=str(trace.id),
            user_id=str(user.id),
        )

    await db.commit()

    logger.info(
        "Trace ingested",
        trace_id=str(trace.id),
        pipeline=payload.pipeline_name,
        user_id=str(user.id),
        celery_task_id=task_id,
        analysis_status=status,
    )

    return TraceIngestResponse(
        trace_id=trace.id,
        status=status,
        message=message,
    )

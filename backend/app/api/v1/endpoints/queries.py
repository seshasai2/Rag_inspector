import json
import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PER_PAGE,
    PageParam,
    PerPageParam,
    page_offset,
)
from app.db.session import get_db
from app.models.models import AnalysisJob, JobStatus, Pipeline, QueryTrace, User
from app.schemas.schemas import (
    BM25ComparisonOut,
    PaginatedTraces,
    QueryTraceDetail,
    QueryTraceListItem,
    RetrievedChunkOut,
)
from app.services.analysis_queue import enqueue_analysis, queue_unavailable_message
from app.services.bm25_service import summarize_bm25_vs_vector

router = APIRouter()


@router.get("", response_model=PaginatedTraces)
async def list_queries(
    pipeline_id: Optional[UUID] = Query(None),
    failure_type: Optional[str] = Query(None),
    is_hallucination: Optional[bool] = Query(None),
    faithfulness_lt: Optional[float] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: PageParam = DEFAULT_PAGE,
    per_page: PerPageParam = DEFAULT_PER_PAGE,
    sort_by: str = Query("traced_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Pipelines for ownership + names in one query (no later N+1 / second fetch)
    pipelines_result = await db.execute(
        select(Pipeline.id, Pipeline.name).where(Pipeline.user_id == current_user.id)
    )
    pipeline_rows = pipelines_result.all()
    pipeline_ids = [r[0] for r in pipeline_rows]
    pipeline_map = {str(r[0]): r[1] for r in pipeline_rows}

    if not pipeline_ids:
        return PaginatedTraces(items=[], total=0, page=page, per_page=per_page, pages=0)

    filters = [QueryTrace.pipeline_id.in_(pipeline_ids)]

    if pipeline_id:
        filters.append(QueryTrace.pipeline_id == pipeline_id)
    if failure_type:
        filters.append(QueryTrace.failure_type == failure_type)
    if is_hallucination is not None:
        filters.append(QueryTrace.is_hallucination == is_hallucination)
    if faithfulness_lt is not None:
        filters.append(QueryTrace.faithfulness_score < faithfulness_lt)
    if date_from:
        filters.append(QueryTrace.traced_at >= date_from)
    if date_to:
        filters.append(QueryTrace.traced_at <= date_to)

    count_result = await db.execute(select(func.count(QueryTrace.id)).where(and_(*filters)))
    total = count_result.scalar() or 0

    sort_col = getattr(QueryTrace, sort_by, QueryTrace.traced_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    result = await db.execute(
        select(QueryTrace)
        .where(and_(*filters))
        .order_by(order)
        .offset(page_offset(page, per_page))
        .limit(per_page)
    )
    traces = result.scalars().all()

    items = []
    for t in traces:
        item = QueryTraceListItem(
            id=t.id,
            pipeline_id=t.pipeline_id,
            pipeline_name=pipeline_map.get(str(t.pipeline_id)),
            query_text=t.query_text,
            faithfulness_score=t.faithfulness_score,
            context_precision_score=t.context_precision_score,
            grounded_fraction=t.grounded_fraction,
            is_hallucination=t.is_hallucination,
            failure_type=t.failure_type.value if t.failure_type else None,
            embed_latency_ms=t.embed_latency_ms,
            retrieve_latency_ms=t.retrieve_latency_ms,
            generate_latency_ms=t.generate_latency_ms,
            analysis_status=t.analysis_status,
            traced_at=t.traced_at,
        )
        items.append(item)

    return PaginatedTraces(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/{trace_id}", response_model=QueryTraceDetail)
async def get_query(
    trace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.repositories.pipelines import get_owned_trace_detail

    trace = await get_owned_trace_detail(db, current_user, str(trace_id))
    if not trace:
        # Distinguish not found vs forbidden without leaking ownership
        exists = await db.execute(select(QueryTrace.id).where(QueryTrace.id == str(trace_id)))
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized")
        raise HTTPException(status_code=404, detail="Trace not found")

    retrieved_chunks = []
    for chunk in trace.retrieved_chunks:
        metadata = None
        if chunk.metadata_json:
            try:
                metadata = json.loads(chunk.metadata_json)
            except json.JSONDecodeError:
                metadata = None
        retrieved_chunks.append(
            RetrievedChunkOut(
                id=chunk.id,
                chunk_id=chunk.chunk_id,
                chunk_text=chunk.chunk_text,
                similarity_score=chunk.similarity_score,
                bm25_score=chunk.bm25_score,
                rank=chunk.rank,
                was_cited=chunk.was_cited,
                metadata=metadata,
            )
        )

    bm25_summary = summarize_bm25_vs_vector(
        [
            {
                "chunk_id": c.chunk_id,
                "similarity_score": c.similarity_score,
                "bm25_score": c.bm25_score,
            }
            for c in retrieved_chunks
        ]
    )

    return QueryTraceDetail(
        id=trace.id,
        pipeline_id=trace.pipeline_id,
        pipeline_name=trace.pipeline.name if trace.pipeline else None,
        query_text=trace.query_text,
        answer_text=trace.answer_text,
        raw_context=trace.raw_context,
        query_embedding=trace.query_embedding,
        faithfulness_score=trace.faithfulness_score,
        answer_relevance_score=trace.answer_relevance_score,
        context_precision_score=trace.context_precision_score,
        context_recall_score=trace.context_recall_score,
        grounded_fraction=trace.grounded_fraction,
        trustworthiness_score=trace.trustworthiness_score,
        is_hallucination=trace.is_hallucination,
        failure_type=trace.failure_type.value if trace.failure_type else None,
        failure_explanation=trace.failure_explanation,
        recommendation=trace.recommendation,
        embed_latency_ms=trace.embed_latency_ms,
        retrieve_latency_ms=trace.retrieve_latency_ms,
        generate_latency_ms=trace.generate_latency_ms,
        analysis_status=trace.analysis_status,
        traced_at=trace.traced_at,
        retrieved_chunks=retrieved_chunks,
        grounding_results=sorted(trace.grounding_results, key=lambda x: x.sentence_index),
        bm25_comparison=BM25ComparisonOut(**bm25_summary),
    )


@router.post("/{trace_id}/reanalyze")
async def reanalyze_query(
    trace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-queue analysis for a pending/failed trace after workers are available."""
    import asyncio

    result = await db.execute(select(QueryTrace).where(QueryTrace.id == str(trace_id)))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    p_result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == trace.pipeline_id, Pipeline.user_id == current_user.id
        )
    )
    if not p_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")

    if trace.analysis_status == "analyzing":
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    job_result = await db.execute(select(AnalysisJob).where(AnalysisJob.trace_id == trace.id))
    job = job_result.scalar_one_or_none()
    if not job:
        job = AnalysisJob(trace_id=trace.id)
        db.add(job)

    trace.analysis_status = "pending"
    job.status = JobStatus.pending
    job.error_message = None
    job.celery_task_id = None
    job.started_at = None
    job.completed_at = None
    await db.commit()

    try:
        loop = asyncio.get_running_loop()
        task_id = await asyncio.wait_for(
            loop.run_in_executor(None, enqueue_analysis, str(trace.id)),
            timeout=2.0,
        )
    except Exception:
        task_id = None

    if not task_id:
        failure_message = queue_unavailable_message(str(trace.id))
        trace.analysis_status = "failed"
        job.status = JobStatus.failed
        job.error_message = failure_message
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(status_code=503, detail=failure_message)

    job.celery_task_id = task_id
    await db.commit()
    return {
        "trace_id": str(trace.id),
        "status": "queued",
        "celery_task_id": task_id,
        "message": "Trace re-queued for analysis",
    }

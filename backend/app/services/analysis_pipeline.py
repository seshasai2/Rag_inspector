"""
Sync analysis pipeline for a single query trace.

Celery ``run_analysis`` should remain a thin wrapper around ``analyze_trace``.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog
from sqlalchemy.orm import Session, joinedload

logger = structlog.get_logger()

_RUNNING_LOCK_WINDOW = timedelta(minutes=10)


@dataclass
class TraceContext:
    """Loaded trace, job, settings, and working chunk payloads."""

    trace: Any
    job: Any
    pipeline: Any
    chunks_data: list[dict]
    ollama_url: str
    ollama_model: str
    hf_token: Optional[str]
    hf_model: Optional[str]
    grounding_threshold: float
    stage_latencies: dict[str, float] = field(default_factory=dict)


def _ms_since(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 3)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def _started_within_window(started_at: Optional[datetime], window: timedelta) -> bool:
    if started_at is None:
        return False
    now = _utcnow()
    if not _is_aware(started_at):
        # SQLite / naive timestamps in tests
        now = now.replace(tzinfo=None)
        started_at = started_at.replace(tzinfo=None) if started_at.tzinfo else started_at
    return (now - started_at) <= window


def load_trace_context(db: Session, trace_id: str) -> Optional[TraceContext]:
    """Load trace + related rows needed for analysis. Returns None if missing."""
    from app.core.config import settings as app_settings
    from app.models.models import AnalysisJob, QueryTrace, UserSettings

    trace = (
        db.query(QueryTrace)
        .options(
            joinedload(QueryTrace.retrieved_chunks),
            joinedload(QueryTrace.pipeline),
        )
        .filter(QueryTrace.id == trace_id)
        .first()
    )
    if not trace:
        logger.error("Trace not found", trace_id=trace_id)
        return None

    job = db.query(AnalysisJob).filter(AnalysisJob.trace_id == trace.id).first()
    pipeline = trace.pipeline

    user_settings = None
    if pipeline:
        user_settings = (
            db.query(UserSettings).filter(UserSettings.user_id == pipeline.user_id).first()
        )

    ollama_url = (
        user_settings.ollama_url if user_settings else None
    ) or app_settings.OLLAMA_BASE_URL
    ollama_model = (
        user_settings.ollama_model if user_settings else None
    ) or app_settings.OLLAMA_MODEL
    hf_token = app_settings.HF_API_TOKEN
    hf_model = app_settings.HF_MODEL
    grounding_threshold = (user_settings.grounding_threshold if user_settings else None) or 0.5

    chunks_data = [
        {
            "chunk_id": c.chunk_id,
            "chunk_text": c.chunk_text,
            "similarity_score": c.similarity_score,
            "rank": c.rank,
            "was_cited": False,
        }
        for c in trace.retrieved_chunks
    ]

    return TraceContext(
        trace=trace,
        job=job,
        pipeline=pipeline,
        chunks_data=chunks_data,
        ollama_url=ollama_url,
        ollama_model=ollama_model,
        hf_token=hf_token,
        hf_model=hf_model,
        grounding_threshold=grounding_threshold,
    )


def stage_bm25(db: Session, ctx: TraceContext) -> dict:
    """BM25 comparison + hybrid merge; soft-fails and returns ``{}`` on error."""
    from app.core.config import settings as app_settings
    from app.services.bm25_service import get_bm25_comparison, merge_hybrid_rankings

    bm25_result: dict = {}
    trace = ctx.trace
    chunks_data = ctx.chunks_data
    if not (trace.query_text and chunks_data):
        return bm25_result

    try:
        bm25_result = get_bm25_comparison(trace.query_text, chunks_data)
        scored = bm25_result.get("chunks_with_bm25") or chunks_data
        for chunk_obj in trace.retrieved_chunks:
            for bm25_chunk in scored:
                if bm25_chunk.get("chunk_id") == chunk_obj.chunk_id:
                    chunk_obj.bm25_score = bm25_chunk.get("bm25_score")
                    break

        # Observability: hybrid ranking over the retrieved set (does not mutate customer K).
        vw = float(getattr(app_settings, "HYBRID_VECTOR_WEIGHT", 0.5))
        bw = float(getattr(app_settings, "HYBRID_BM25_WEIGHT", 0.5))
        hybrid = merge_hybrid_rankings(scored, vector_weight=vw, bm25_weight=bw)
        bm25_result["hybrid_ranking"] = [
            {
                "chunk_id": h.get("chunk_id"),
                "hybrid_score": h.get("hybrid_score"),
                "similarity_score": h.get("similarity_score"),
                "bm25_score": h.get("bm25_score"),
            }
            for h in hybrid[:20]
        ]
        bm25_result["hybrid_weights"] = {"vector": vw, "bm25": bw}

        # Keep working set scores in sync for later stages.
        by_id = {h["chunk_id"]: h for h in hybrid}
        for cd in chunks_data:
            h = by_id.get(cd["chunk_id"])
            if h:
                if h.get("bm25_score") is not None:
                    cd["bm25_score"] = h["bm25_score"]
                cd["hybrid_score"] = h.get("hybrid_score")

        db.commit()
    except Exception as e:
        logger.warning("BM25 analysis failed", error=str(e))

    return bm25_result


def stage_grounding(db: Session, ctx: TraceContext) -> dict:
    """Sentence grounding + citation / chunk-stat updates; soft-fails."""
    from app.models.models import ChunkStat, GroundingResult
    from app.services.grounding import check_grounding

    grounding_result: dict = {
        "grounded_fraction": None,
        "is_hallucination": None,
        "sentence_results": [],
    }
    trace = ctx.trace
    chunks_data = ctx.chunks_data
    pipeline = ctx.pipeline

    if not (trace.answer_text and chunks_data):
        return grounding_result

    try:
        grounding_result = check_grounding(
            trace.answer_text,
            chunks_data,
            threshold=ctx.grounding_threshold,
        )

        cited_chunk_ids = set()
        for sr in grounding_result["sentence_results"]:
            if sr["is_grounded"] and sr.get("supporting_chunk_id"):
                cited_chunk_ids.add(sr["supporting_chunk_id"])

        for chunk_obj in trace.retrieved_chunks:
            if chunk_obj.chunk_id in cited_chunk_ids:
                chunk_obj.was_cited = True

        db.commit()

        for cd in chunks_data:
            cd["was_cited"] = cd["chunk_id"] in cited_chunk_ids

        for sr in grounding_result["sentence_results"]:
            gr = GroundingResult(
                trace_id=trace.id,
                sentence_text=sr["sentence_text"],
                sentence_index=sr["sentence_index"],
                is_grounded=sr["is_grounded"],
                supporting_chunk_id=sr.get("supporting_chunk_id"),
                confidence_score=sr.get("confidence_score"),
            )
            db.add(gr)

        if pipeline:
            from app.services.chunk_quality import apply_chunk_quality_update

            cited_objs = [
                chunk_obj
                for chunk_obj in trace.retrieved_chunks
                if chunk_obj.was_cited
            ]
            cited_ids = list({c.chunk_id for c in cited_objs})
            if cited_ids:
                existing = {
                    cs.chunk_id: cs
                    for cs in db.query(ChunkStat)
                    .filter(
                        ChunkStat.pipeline_id == pipeline.id,
                        ChunkStat.chunk_id.in_(cited_ids),
                    )
                    .all()
                }
                for chunk_obj in cited_objs:
                    cs = existing.get(chunk_obj.chunk_id)
                    if not cs:
                        continue
                    cs.citation_count += 1
                    updated = apply_chunk_quality_update(
                        retrieval_count=cs.retrieval_count,
                        citation_count=cs.citation_count,
                        currently_flagged=bool(cs.is_flagged),
                    )
                    cs.citation_rate = updated["citation_rate"]
                    cs.is_flagged = updated["is_flagged"]

        db.commit()

    except Exception as e:
        logger.warning("Grounding check failed", error=str(e))

    return grounding_result


def stage_ragas(ctx: TraceContext) -> dict:
    """RAGAS metrics via a dedicated event loop; heuristic fallback on failure."""
    ragas_metrics: dict = {}
    trace = ctx.trace
    chunks_data = ctx.chunks_data

    if not (chunks_data and (trace.answer_text or trace.query_text)):
        return ragas_metrics

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from app.services.ragas_service import compute_all_metrics

            ragas_metrics = loop.run_until_complete(
                compute_all_metrics(
                    query=trace.query_text or "",
                    answer=trace.answer_text or "",
                    context_chunks=chunks_data,
                    ollama_url=ctx.ollama_url,
                    model=ctx.ollama_model,
                    hf_token=ctx.hf_token,
                    hf_model=ctx.hf_model,
                )
            )
        finally:
            loop.close()
    except Exception as e:
        logger.warning("RAGAS metrics failed", error=str(e))
        try:
            from app.services.context_recall import compute_context_recall_heuristic

            ragas_metrics["context_recall_score"] = compute_context_recall_heuristic(
                trace.query_text or "",
                [c["chunk_text"] for c in chunks_data],
                trace.answer_text,
            )
        except Exception as fallback_exc:
            logger.warning(
                "RAGAS heuristic context-recall fallback failed",
                error=str(fallback_exc),
            )

    return ragas_metrics


def stage_classify_and_persist(
    db: Session,
    ctx: TraceContext,
    *,
    grounding_result: dict,
    ragas_metrics: dict,
    bm25_result: dict,
) -> tuple[str, str, str]:
    """Trustworthiness, failure classification, fix recs, knowledge gaps, persist."""
    from sqlalchemy import desc

    from app.models.models import FixRecommendation, JobStatus, QueryTrace
    from app.services.failure_classifier import classify_failure
    from app.services.fix_recommendations import generate_fix_recommendations
    from app.services.trustworthiness_service import compute_trustworthiness

    trace = ctx.trace
    pipeline = ctx.pipeline
    chunks_data = ctx.chunks_data
    job = ctx.job

    trustworthiness_score = compute_trustworthiness(
        faithfulness_score=ragas_metrics.get("faithfulness_score"),
        grounded_fraction=grounding_result.get("grounded_fraction"),
    )
    trace.trustworthiness_score = trustworthiness_score

    failure_type, explanation, recommendation = classify_failure(
        faithfulness_score=ragas_metrics.get("faithfulness_score"),
        context_precision_score=ragas_metrics.get("context_precision_score"),
        grounded_fraction=grounding_result.get("grounded_fraction"),
        chunks=chunks_data,
        query=trace.query_text,
        answer=trace.answer_text,
        context_recall_score=ragas_metrics.get("context_recall_score"),
    )

    # Preserve original operator precedence / use pre-update faithfulness on trace
    if failure_type == "coverage_gap" or (
        trace.faithfulness_score is not None and trace.faithfulness_score < 0.5
    ):
        try:
            recent_failed_traces = (
                db.query(QueryTrace)
                .filter(
                    QueryTrace.pipeline_id == trace.pipeline_id,
                    QueryTrace.failure_type.in_(["coverage_gap", "retrieval_miss"]),
                )
                .order_by(desc(QueryTrace.traced_at))
                .limit(100)
                .all()
            )

            coverage_gap_queries = [
                {"query_text": t.query_text}
                for t in recent_failed_traces
                if t.query_text and t.failure_type == "coverage_gap"
            ]
            if coverage_gap_queries and pipeline:
                recommendations = generate_fix_recommendations(coverage_gap_queries)
                from app.services.fix_recommendations import (
                    generate_k_increase_recommendation,
                    generate_retrieval_recommendation,
                )

                miss_traces = [
                    t for t in recent_failed_traces if t.failure_type == "retrieval_miss"
                ]
                if recent_failed_traces:
                    miss_ratio = len(miss_traces) / len(recent_failed_traces)
                    k_rec = generate_k_increase_recommendation(miss_ratio)
                    if k_rec:
                        recommendations.append(k_rec)

                if bm25_result.get("bm25_better"):
                    hybrid = generate_retrieval_recommendation(
                        0.35, max(len(recent_failed_traces), 10)
                    )
                    if hybrid:
                        recommendations.append(hybrid)

                for rec in recommendations:
                    existing = (
                        db.query(FixRecommendation)
                        .filter(
                            FixRecommendation.pipeline_id == pipeline.id,
                            FixRecommendation.recommendation_type == rec["recommendation_type"],
                            FixRecommendation.topic_description == rec["topic_description"],
                        )
                        .first()
                    )
                    if not existing:
                        sample = rec.get("sample_queries")
                        if sample is not None and not isinstance(sample, str):
                            sample = json.dumps(sample)
                        fix_rec = FixRecommendation(
                            user_id=pipeline.user_id,
                            pipeline_id=pipeline.id,
                            recommendation_type=rec["recommendation_type"],
                            topic_description=rec["topic_description"],
                            affected_query_count=rec["affected_query_count"],
                            sample_queries=sample,
                        )
                        db.add(fix_rec)

                try:
                    from app.services.knowledge_gap import (
                        detect_knowledge_gaps,
                        upsert_knowledge_gaps,
                    )

                    gap_dicts = detect_knowledge_gaps(
                        coverage_gap_queries,
                        pipeline_queries_per_month=getattr(pipeline, "queries_per_month", 10000)
                        or 10000,
                        cost_per_wrong_answer_usd=getattr(
                            pipeline, "cost_per_wrong_answer_usd", 5.0
                        )
                        or 5.0,
                        total_recent_failures=len(recent_failed_traces) or None,
                    )
                    if gap_dicts:
                        upsert_knowledge_gaps(db, pipeline, gap_dicts)
                except Exception as gap_exc:
                    logger.warning(
                        "Knowledge gap detection failed",
                        error=str(gap_exc),
                    )
        except Exception as e:
            logger.warning("Fix recommendation generation failed", error=str(e))

    trace.faithfulness_score = ragas_metrics.get("faithfulness_score")
    trace.answer_relevance_score = ragas_metrics.get("answer_relevance_score")
    trace.context_precision_score = ragas_metrics.get("context_precision_score")
    trace.context_recall_score = ragas_metrics.get("context_recall_score")
    trace.grounded_fraction = grounding_result.get("grounded_fraction")
    trace.is_hallucination = grounding_result.get("is_hallucination")
    trace.failure_type = failure_type
    trace.failure_explanation = explanation
    trace.recommendation = recommendation
    trace.analysis_status = "completed"

    if hasattr(trace, "analysis_latencies_json"):
        try:
            trace.analysis_latencies_json = json.dumps(ctx.stage_latencies)
        except Exception as lat_exc:
            logger.warning(
                "Could not persist analysis_latencies_json",
                error=str(lat_exc),
            )

    if job:
        job.status = JobStatus.completed
        job.completed_at = _utcnow()

    db.commit()
    return failure_type, explanation, recommendation


def notify_slack(
    db: Session,
    ctx: TraceContext,
    *,
    grounding_result: dict,
    trace_id: str,
) -> None:
    """Optional Slack hallucination alert; always soft-fails."""
    try:
        if not grounding_result.get("is_hallucination"):
            return
        pipeline = ctx.pipeline
        if not pipeline:
            return

        from app.core.config import settings as app_settings
        from app.models.models import User as UserModel
        from app.services.slack_alerts import send_hallucination_alert_sync

        owner = db.query(UserModel).filter(UserModel.id == pipeline.user_id).first()
        if owner and owner.slack_alert_enabled and owner.slack_webhook_url:
            send_hallucination_alert_sync(
                owner.slack_webhook_url,
                pipeline.name,
                ctx.trace.query_text or "",
                grounding_result.get("grounded_fraction"),
                f"{app_settings.FRONTEND_URL}/queries/{trace_id}",
            )
    except Exception as e:
        logger.warning("Slack hallucination alert failed", error=str(e))


def _mark_failed(db: Session, trace_id: str, exc: BaseException) -> None:
    from app.models.models import AnalysisJob, JobStatus, QueryTrace

    try:
        trace = db.query(QueryTrace).filter(QueryTrace.id == trace_id).first()
        if trace:
            trace.analysis_status = "failed"
        job = db.query(AnalysisJob).filter(AnalysisJob.trace_id == trace_id).first()
        if job:
            job.status = JobStatus.failed
            job.error_message = str(exc)
        db.commit()
    except Exception:
        logger.warning("Failed to mark analysis as failed", trace_id=trace_id)


def analyze_trace(db: Session, trace_id: str) -> dict:
    """
    Run the full analysis pipeline for ``trace_id``.

    Returns a summary dict with at least ``failure_type`` and ``stage_latencies``.
    Idempotent when the job+trace are already completed, or another worker holds
    a fresh ``running`` lock (started within 10 minutes).
    """
    from app.models.models import JobStatus

    stage_latencies: dict[str, float] = {}

    t0 = time.perf_counter()
    ctx = load_trace_context(db, trace_id)
    stage_latencies["load_trace_context"] = _ms_since(t0)

    if ctx is None:
        return {
            "skipped": True,
            "reason": "not_found",
            "failure_type": None,
            "stage_latencies": stage_latencies,
        }

    ctx.stage_latencies = stage_latencies
    trace = ctx.trace
    job = ctx.job

    # Idempotency: already done
    if (
        job is not None
        and job.status == JobStatus.completed
        and trace.analysis_status == "completed"
    ):
        ft = getattr(trace.failure_type, "value", trace.failure_type)
        return {
            "skipped": True,
            "reason": "already_completed",
            "failure_type": ft,
            "stage_latencies": stage_latencies,
        }

    # Another worker holds a fresh lock
    if (
        job is not None
        and job.status == JobStatus.running
        and _started_within_window(job.started_at, _RUNNING_LOCK_WINDOW)
    ):
        ft = getattr(trace.failure_type, "value", trace.failure_type)
        return {
            "skipped": True,
            "reason": "already_running",
            "failure_type": ft,
            "stage_latencies": stage_latencies,
        }

    try:
        if job:
            job.status = JobStatus.running
            job.started_at = _utcnow()
            db.commit()

        trace.analysis_status = "analyzing"
        db.commit()

        t1 = time.perf_counter()
        bm25_result = stage_bm25(db, ctx)
        stage_latencies["bm25"] = _ms_since(t1)

        t2 = time.perf_counter()
        grounding_result = stage_grounding(db, ctx)
        stage_latencies["grounding"] = _ms_since(t2)

        t3 = time.perf_counter()
        ragas_metrics = stage_ragas(ctx)
        stage_latencies["ragas"] = _ms_since(t3)

        t4 = time.perf_counter()
        failure_type, _explanation, _recommendation = stage_classify_and_persist(
            db,
            ctx,
            grounding_result=grounding_result,
            ragas_metrics=ragas_metrics,
            bm25_result=bm25_result,
        )
        stage_latencies["classify_and_persist"] = _ms_since(t4)

        logger.info(
            "Analysis completed",
            trace_id=trace_id,
            failure_type=failure_type,
        )

        t5 = time.perf_counter()
        notify_slack(db, ctx, grounding_result=grounding_result, trace_id=trace_id)
        stage_latencies["notify_slack"] = _ms_since(t5)

        # Persist full stage latency map after all stages (including slack).
        if hasattr(trace, "analysis_latencies_json"):
            try:
                trace.analysis_latencies_json = json.dumps(stage_latencies)
                db.commit()
            except Exception as lat_exc:
                logger.warning(
                    "Could not persist final analysis_latencies_json",
                    error=str(lat_exc),
                )

        return {
            "failure_type": failure_type,
            "stage_latencies": stage_latencies,
            "skipped": False,
        }

    except Exception as exc:
        logger.error("Analysis failed", trace_id=trace_id, error=str(exc))
        _mark_failed(db, trace_id, exc)
        raise

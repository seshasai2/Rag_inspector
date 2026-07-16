"""Retrieval benchmark + LLM comparison from real traces (Phase 10.6).

No synthetic scores: uses stored chunks / faithfulness / grounding only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.models import QueryTrace
from app.services.bm25_service import compute_bm25_scores, summarize_bm25_vs_vector


def run_retrieval_benchmark(
    db: Session,
    pipeline_id: str,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    traces = (
        db.query(QueryTrace)
        .options(joinedload(QueryTrace.retrieved_chunks))
        .filter(QueryTrace.pipeline_id == pipeline_id)
        .order_by(QueryTrace.traced_at.desc())
        .limit(limit)
        .all()
    )
    comparable = 0
    bm25_wins = 0
    vector_wins = 0
    ties = 0
    per_query: list[dict[str, Any]] = []

    for trace in traces:
        chunks = [
            {
                "chunk_id": c.chunk_id,
                "chunk_text": c.chunk_text or "",
                "similarity_score": c.similarity_score,
                "bm25_score": c.bm25_score,
            }
            for c in (trace.retrieved_chunks or [])
        ]
        if not chunks or not trace.query_text:
            continue
        if all(c.get("bm25_score") is None for c in chunks):
            chunks = compute_bm25_scores(trace.query_text, chunks)
        summary = summarize_bm25_vs_vector(chunks)
        if not summary.get("comparable"):
            continue
        comparable += 1
        if summary.get("bm25_better"):
            bm25_wins += 1
            winner = "bm25"
        elif (summary.get("top_vector_score") or 0) > (summary.get("top_bm25_score") or 0):
            vector_wins += 1
            winner = "vector"
        else:
            ties += 1
            winner = "tie"
        per_query.append(
            {
                "trace_id": str(trace.id),
                "query_text": (trace.query_text or "")[:200],
                "winner": winner,
                "top_bm25_score": summary.get("top_bm25_score"),
                "top_vector_score": summary.get("top_vector_score"),
                "analysis": summary.get("analysis"),
            }
        )

    return {
        "pipeline_id": pipeline_id,
        "traces_evaluated": comparable,
        "bm25_win_rate": round(bm25_wins / comparable, 4) if comparable else 0.0,
        "vector_win_rate": round(vector_wins / comparable, 4) if comparable else 0.0,
        "tie_rate": round(ties / comparable, 4) if comparable else 0.0,
        "recommendation": (
            "Consider hybrid BM25+vector retrieval"
            if comparable and bm25_wins / comparable >= 0.3
            else "Vector retrieval is competitive on this sample"
        ),
        "samples": per_query[:20],
    }


def run_llm_comparison(
    db: Session,
    pipeline_id: str,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Compare answer quality buckets from real metrics (not two live LLM calls).

    Groups traces by whether they used higher vs lower faithfulness — useful as
    an offline model-quality lens without inventing second-model scores.
    """
    traces = (
        db.query(QueryTrace)
        .filter(
            QueryTrace.pipeline_id == pipeline_id,
            QueryTrace.faithfulness_score.isnot(None),
        )
        .order_by(QueryTrace.traced_at.desc())
        .limit(limit)
        .all()
    )
    if not traces:
        return {
            "pipeline_id": pipeline_id,
            "traces_evaluated": 0,
            "high_faithfulness_count": 0,
            "low_faithfulness_count": 0,
            "avg_grounding_high": None,
            "avg_grounding_low": None,
            "note": "Need traces with faithfulness_score from analysis",
        }

    high = [t for t in traces if (t.faithfulness_score or 0) >= 0.7]
    low = [t for t in traces if (t.faithfulness_score or 0) < 0.7]

    def _avg_ground(items: list) -> float | None:
        vals = [t.grounded_fraction for t in items if t.grounded_fraction is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "pipeline_id": pipeline_id,
        "traces_evaluated": len(traces),
        "high_faithfulness_count": len(high),
        "low_faithfulness_count": len(low),
        "avg_faithfulness_overall": round(
            sum(t.faithfulness_score for t in traces if t.faithfulness_score is not None)
            / len(traces),
            4,
        ),
        "avg_grounding_high": _avg_ground(high),
        "avg_grounding_low": _avg_ground(low),
        "hallucination_rate_high": (
            round(sum(1 for t in high if t.is_hallucination) / len(high), 4) if high else None
        ),
        "hallucination_rate_low": (
            round(sum(1 for t in low if t.is_hallucination) / len(low), 4) if low else None
        ),
        "note": "Buckets use measured faithfulness from the analysis worker (no synthetic LLM scores).",
    }

"""
BM25 vs Vector search comparison.

Runs BM25 on the corpus of retrieved chunks to compute BM25 scores
and compare against vector similarity scores.

PRD F4:
  Per query — "BM25 top: X vs Vector top: Y — BM25 would have been better…"
  Aggregate — "BM25 outperforms vector on X% of queries — consider hybrid"
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import structlog

logger = structlog.get_logger()

# BM25 is "significantly better" when top BM25 exceeds top vector by this margin
BM25_BETTER_MARGIN = 0.15


def compute_bm25_scores(query: str, chunks: list[dict]) -> list[dict]:
    """
    Given a query and list of chunks, compute BM25 scores for each chunk.
    Returns chunks with bm25_score added (normalized 0–1).
    """
    if not chunks or not query:
        return chunks

    try:
        from rank_bm25 import BM25Okapi

        tokenized_corpus = [chunk["chunk_text"].lower().split() for chunk in chunks]
        tokenized_query = query.lower().split()

        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            normalized = [1.0 for _ in scores]
        else:
            normalized = [float(s - min_score) / (max_score - min_score) for s in scores]

        result = []
        for i, chunk in enumerate(chunks):
            c = dict(chunk)
            c["bm25_score"] = round(normalized[i], 3)
            result.append(c)

        return result

    except Exception as e:
        logger.warning("BM25 computation failed", error=str(e))
        return chunks


def summarize_bm25_vs_vector(
    chunks: Sequence[dict[str, Any]],
    *,
    margin: float = BM25_BETTER_MARGIN,
) -> dict[str, Any]:
    """
    Compare BM25 vs vector using scores already present on chunks.

    Expects optional ``similarity_score`` and ``bm25_score`` (0–1).
    Does not recompute BM25.
    """
    if not chunks:
        return {
            "bm25_better": False,
            "top_vector_score": None,
            "top_bm25_score": None,
            "analysis": "No chunks to compare",
            "comparable": False,
        }

    vector_scores = [
        float(c["similarity_score"]) for c in chunks if c.get("similarity_score") is not None
    ]
    bm25_scores = [float(c["bm25_score"]) for c in chunks if c.get("bm25_score") is not None]

    if not vector_scores:
        return {
            "bm25_better": False,
            "top_vector_score": None,
            "top_bm25_score": round(max(bm25_scores), 3) if bm25_scores else None,
            "analysis": "No vector scores available",
            "comparable": False,
        }

    if not bm25_scores:
        return {
            "bm25_better": False,
            "top_vector_score": round(max(vector_scores), 3),
            "top_bm25_score": None,
            "analysis": "No BM25 scores available (run analysis to compute)",
            "comparable": False,
        }

    top_vector_score = max(vector_scores)
    top_bm25_score = max(bm25_scores)
    bm25_better = top_bm25_score > top_vector_score + margin

    return {
        "bm25_better": bm25_better,
        "top_vector_score": round(top_vector_score, 3),
        "top_bm25_score": round(top_bm25_score, 3),
        "comparable": True,
        "analysis": (
            f"BM25 top result relevance: {top_bm25_score:.2f} vs "
            f"Vector top result relevance: {top_vector_score:.2f} — "
            + (
                "BM25 would have been better for this query"
                if bm25_better
                else "Vector search performed well for this query"
            )
        ),
    }


def get_bm25_comparison(query: str, chunks: list[dict]) -> dict:
    """
    Compute BM25 scores then compare against vector retrieval.
    """
    if not chunks:
        return {
            "bm25_better": False,
            "top_vector_score": None,
            "top_bm25_score": None,
            "comparable": False,
            "analysis": "No chunks to compare",
            "chunks_with_bm25": [],
        }

    chunks_with_bm25 = compute_bm25_scores(query, chunks)
    summary = summarize_bm25_vs_vector(chunks_with_bm25)
    summary["chunks_with_bm25"] = chunks_with_bm25
    return summary


def aggregate_bm25_outperform_rate(
    per_trace_flags: Sequence[Optional[bool]],
) -> dict[str, Any]:
    """
    Aggregate PRD F4 stat from per-trace ``bm25_better`` flags.

    ``None`` means the trace was not comparable (excluded from denominator).
    """
    comparable = [f for f in per_trace_flags if f is not None]
    if not comparable:
        return {
            "traces_compared": 0,
            "bm25_better_count": 0,
            "bm25_outperform_rate": 0.0,
            "recommend_hybrid": False,
            "summary": "Not enough traces with BM25 and vector scores to compare.",
        }

    better = sum(1 for f in comparable if f is True)
    rate = better / len(comparable)
    recommend = rate >= 0.3 and len(comparable) >= 10
    return {
        "traces_compared": len(comparable),
        "bm25_better_count": better,
        "bm25_outperform_rate": round(rate, 3),
        "recommend_hybrid": recommend,
        "summary": (
            f"BM25 outperforms vector search on {rate:.0%} of queries "
            f"({better}/{len(comparable)})"
            + (" — consider hybrid retrieval (BM25 + vector)" if recommend else "")
        ),
    }


def _clamp_weight(value: float) -> float:
    return max(0.0, float(value))


def _normalize_score_list(scores: list[float]) -> list[float]:
    """Min-max normalize to 0–1 when any score falls outside [0, 1]."""
    if not scores:
        return scores
    lo, hi = min(scores), max(scores)
    if lo >= 0.0 and hi <= 1.0:
        return scores
    if hi == lo:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def merge_hybrid_rankings(
    chunks: list[dict],
    *,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
) -> list[dict]:
    """
    Merge vector + BM25 rankings into a single hybrid ranking.

    Normalizes similarity_score / bm25_score to 0–1 when needed, computes
    hybrid_score, dedupes by chunk_id (best hybrid wins), sorts by
    (-hybrid_score, chunk_id).
    """
    if not chunks:
        return []

    vw = _clamp_weight(vector_weight)
    bw = _clamp_weight(bm25_weight)
    if vw > 0 and bw > 0:
        total = vw + bw
        vw, bw = vw / total, bw / total

    sim_raw = [
        float(c["similarity_score"]) if c.get("similarity_score") is not None else 0.0
        for c in chunks
    ]
    bm25_raw = [float(c["bm25_score"]) if c.get("bm25_score") is not None else 0.0 for c in chunks]
    sims = _normalize_score_list(sim_raw)
    bm25s = _normalize_score_list(bm25_raw)

    best: dict[str, dict] = {}
    for i, chunk in enumerate(chunks):
        chunk_id = str(chunk.get("chunk_id", ""))
        hybrid = vw * sims[i] + bw * bm25s[i]
        merged = dict(chunk)
        merged["hybrid_score"] = round(hybrid, 6)
        prev = best.get(chunk_id)
        if prev is None or hybrid > float(prev["hybrid_score"]):
            best[chunk_id] = merged

    return sorted(
        best.values(),
        key=lambda c: (-float(c["hybrid_score"]), str(c.get("chunk_id", ""))),
    )

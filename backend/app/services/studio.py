"""Studio tools with measured / heuristic outputs only (Phase 10.7)."""

from __future__ import annotations

import re
from typing import Any


def analyze_prompt(prompt_text: str) -> dict[str, Any]:
    """Rule-based prompt critique — no invented quality scores."""
    text = (prompt_text or "").strip()
    issues: list[dict[str, str]] = []
    if not text:
        return {"issues": [{"code": "empty", "detail": "Prompt is empty"}], "ok": False}

    lower = text.lower()
    if "context" not in lower and "{context}" not in lower and "{{context}}" not in lower:
        issues.append(
            {
                "code": "missing_context",
                "detail": "Prompt does not reference retrieved context — model may ignore RAG chunks.",
            }
        )
    if len(re.findall(r"\b(do not|don't|never|always|must)\b", lower)) >= 4:
        issues.append(
            {
                "code": "conflicting_instructions",
                "detail": "Many hard constraints — check for contradictions.",
            }
        )
    if len(text) < 40:
        issues.append(
            {"code": "too_short", "detail": "Prompt is very short; add role + grounding rules."}
        )
    if "json" in lower and "only" not in lower:
        issues.append(
            {
                "code": "ambiguity",
                "detail": "Mentions JSON without requiring JSON-only output.",
            }
        )
    if "cite" not in lower and "source" not in lower and "according to" not in lower:
        issues.append(
            {
                "code": "retrieval_inefficiency",
                "detail": "No citation / attribution instruction — weak grounding pressure.",
            }
        )

    return {
        "ok": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "char_length": len(text),
    }


def chunk_optimizer_suggestions(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Suggest actions from real citation_rate / retrieval_count (ChunkStat rows)."""
    suggestions: list[dict[str, Any]] = []
    low_cite = [
        c
        for c in chunks
        if (c.get("retrieval_count") or 0) >= 10 and (c.get("citation_rate") or 0) < 0.2
    ]
    for c in low_cite[:20]:
        suggestions.append(
            {
                "action": "rewrite_or_split_chunk",
                "chunk_id": c.get("chunk_id"),
                "reason": (
                    f"Retrieved {c.get('retrieval_count')} times but citation_rate="
                    f"{round(float(c.get('citation_rate') or 0), 3)}"
                ),
            }
        )
    never_cited = [
        c
        for c in chunks
        if (c.get("retrieval_count") or 0) >= 5 and (c.get("citation_count") or 0) == 0
    ]
    for c in never_cited[:10]:
        suggestions.append(
            {
                "action": "consider_removing",
                "chunk_id": c.get("chunk_id"),
                "reason": "Retrieved repeatedly but never cited",
            }
        )
    return {
        "chunks_scanned": len(chunks),
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
    }


def simulate_top_k(chunks: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    """
    Simulate keeping only top-k by similarity — reports measured citation density.

    Does not invent trust scores; uses was_cited / similarity already on chunks.
    """
    k = max(1, int(top_k))
    ranked = sorted(
        chunks,
        key=lambda c: float(c.get("similarity_score") or 0),
        reverse=True,
    )
    kept = ranked[:k]
    cited = sum(1 for c in kept if c.get("was_cited"))
    return {
        "top_k": k,
        "chunks_kept": len(kept),
        "cited_among_kept": cited,
        "citation_density": round(cited / len(kept), 4) if kept else 0.0,
        "dropped": max(0, len(ranked) - len(kept)),
        "note": "Simulation uses stored similarity_score and was_cited flags only.",
    }

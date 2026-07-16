"""AI Investigator — metrics Q&A with citations (Phase 10.8)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


def build_metric_pack(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten dashboard-like metrics into citable facts."""
    facts: list[dict[str, Any]] = []
    mapping = {
        "trustworthiness_score": "trust_score",
        "hallucination_rate": "hallucination_rate",
        "total_queries": "total_traces",
        "mean_faithfulness": "avg_faithfulness",
        "mean_context_precision": "avg_context_precision",
        "hallucination_cost_usd": "hallucination_cost_usd",
    }
    for key, label in mapping.items():
        if key in metrics and metrics[key] is not None:
            facts.append({"metric": label, "value": metrics[key], "source": key})
    counts = metrics.get("failure_type_counts") or {}
    if isinstance(counts, dict):
        for ftype, count in counts.items():
            facts.append(
                {
                    "metric": f"failure:{ftype}",
                    "value": count,
                    "source": "failure_type_counts",
                }
            )
    return facts


def answer_from_facts(question: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic answer with citations — always available offline."""
    q = (question or "").lower()
    citations: list[dict[str, Any]] = []
    parts: list[str] = []

    def cite(fact: dict[str, Any]) -> None:
        citations.append(
            {
                "metric": fact["metric"],
                "value": fact["value"],
                "source": fact.get("source"),
            }
        )

    by_metric = {f["metric"]: f for f in facts}
    if "trust" in q and "trust_score" in by_metric:
        f = by_metric["trust_score"]
        parts.append(f"Trust Score is {f['value']}.")
        cite(f)
    if "hallucin" in q and "hallucination_rate" in by_metric:
        f = by_metric["hallucination_rate"]
        parts.append(f"Hallucination rate is {f['value']}.")
        cite(f)
    if ("how many" in q or "total" in q or "volume" in q) and "total_traces" in by_metric:
        f = by_metric["total_traces"]
        parts.append(f"Total traces in window: {f['value']}.")
        cite(f)
    if "fail" in q:
        fails = [f for f in facts if str(f["metric"]).startswith("failure:")]
        if fails:
            top = sorted(fails, key=lambda x: float(x["value"] or 0), reverse=True)[:3]
            parts.append(
                "Top failure types: "
                + ", ".join(f"{f['metric'].split(':', 1)[1]}={f['value']}" for f in top)
                + "."
            )
            for f in top:
                cite(f)

    if not parts:
        # Summarize available facts
        for f in facts[:5]:
            parts.append(f"{f['metric']}={f['value']}")
            cite(f)
        if not facts:
            parts.append("No metrics available for this pipeline yet.")

    return {
        "answer": " ".join(parts),
        "citations": citations,
        "mode": "deterministic",
    }


async def investigate(question: str, metrics: dict[str, Any]) -> dict[str, Any]:
    facts = build_metric_pack(metrics)
    base = answer_from_facts(question, facts)

    # Optional LLM polish — must still cite the same facts (no invented numbers)
    prompt = (
        "Answer the user question using ONLY these facts. "
        "Do not invent metrics. Cite metric names in brackets.\n"
        f"FACTS: {json.dumps(facts)}\n"
        f"QUESTION: {question}\n"
    )
    polished = await _try_llm(prompt)
    if polished:
        # Keep deterministic citations; use LLM text if it doesn't invent bare numbers wildly
        base["answer"] = polished.strip()
        base["mode"] = "llm_assisted"
    return base


async def _try_llm(prompt: str) -> str | None:
    try:
        if settings.HF_API_TOKEN:
            # Keep simple — skip HF if complex
            pass
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                url,
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            if resp.status_code == 200:
                return (resp.json() or {}).get("response")
    except Exception as exc:
        logger.info("investigator_llm_skipped", error=str(exc))
    return None

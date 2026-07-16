"""Haystack component wrapper for RAGInspector (Phase 10.12)."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from raginspector.tracer import RAGInspector

logger = logging.getLogger("raginspector")

try:
    from haystack import component
except ImportError:  # pragma: no cover

    def component(cls=None, **kwargs):  # type: ignore
        def wrap(c):
            c.output_types = lambda **kw: (lambda f: f)
            return c

        if cls is not None:
            return wrap(cls)
        return wrap


def _component(cls):
    return component(cls)


@_component
class RAGInspectorHaystackTracer:
    """
    Haystack-friendly tracer that sends query/docs/answer to RAGInspector.

    Usage::

        tracer = RAGInspectorHaystackTracer(api_key="ri-...", pipeline_name="hs-rag")
        tracer.run(query=..., documents=..., answer=...)
    """

    def __init__(
        self,
        api_key: str,
        pipeline_name: str,
        base_url: str = "http://localhost:8000",
        enabled: bool = True,
        inspector: Optional[RAGInspector] = None,
    ):
        self.enabled = enabled
        self._inspector = inspector or RAGInspector(
            api_key=api_key,
            pipeline_name=pipeline_name,
            base_url=base_url,
            enabled=enabled,
        )

    def run(
        self,
        query: str,
        documents: Optional[list] = None,
        answer: str = "",
    ) -> dict[str, Any]:
        docs = documents or []
        chunks = []
        for i, doc in enumerate(docs):
            content = getattr(doc, "content", None) or getattr(doc, "text", None) or str(doc)
            score = None
            meta = getattr(doc, "meta", None) or {}
            if isinstance(meta, dict):
                score = meta.get("score") or meta.get("similarity")
            chunks.append(
                {
                    "chunk_id": getattr(doc, "id", None) or f"hs-{i}",
                    "chunk_text": content,
                    "similarity_score": float(score) if score is not None else None,
                }
            )
        if self.enabled and query:
            try:
                self._inspector.send_trace(
                    query=query,
                    retrieved_chunks=chunks,
                    answer=answer or "",
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("Haystack trace send failed: %s", exc)
        return {"answer": answer}

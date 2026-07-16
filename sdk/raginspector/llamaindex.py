"""LlamaIndex callback integration for RAGInspector (Phase 10.12)."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from raginspector.tracer import RAGInspector

logger = logging.getLogger("raginspector")

try:
    from llama_index.core.callbacks import CallbackManager, CBEventType, EventPayload
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler
except ImportError:  # pragma: no cover - optional dependency

    class BaseCallbackHandler:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class CBEventType:  # type: ignore[no-redef]
        RETRIEVE = "retrieve"
        LLM = "llm"

    class EventPayload:  # type: ignore[no-redef]
        QUERY_STR = "query_str"
        NODES = "nodes"
        RESPONSE = "response"


class RAGInspectorLlamaIndexHandler(BaseCallbackHandler):
    """
    LlamaIndex event handler → RAGInspector ingest.

    Usage::

        handler = RAGInspectorLlamaIndexHandler(api_key="ri-...", pipeline_name="li-rag")
        # attach via CallbackManager([handler]) when constructing index/query engine
    """

    def __init__(
        self,
        api_key: str,
        pipeline_name: str,
        base_url: str = "http://localhost:8000",
        enabled: bool = True,
        inspector: Optional[RAGInspector] = None,
        event_starts_to_ignore: Optional[list] = None,
        event_ends_to_ignore: Optional[list] = None,
    ):
        try:
            super().__init__(
                event_starts_to_ignore=event_starts_to_ignore or [],
                event_ends_to_ignore=event_ends_to_ignore or [],
            )
        except TypeError:
            super().__init__()
        self.enabled = enabled
        self._inspector = inspector or RAGInspector(
            api_key=api_key,
            pipeline_name=pipeline_name,
            base_url=base_url,
            enabled=enabled,
        )
        self._query = ""
        self._chunks: list[dict[str, Any]] = []
        self._answer: Optional[str] = None
        self._t0: Optional[float] = None

    def on_event_start(self, event_type, payload=None, event_id="", parent_id="", **kwargs):
        if not self.enabled:
            return event_id
        self._t0 = time.perf_counter()
        payload = payload or {}
        if event_type == CBEventType.RETRIEVE or str(event_type).lower().endswith("retrieve"):
            self._query = str(payload.get(EventPayload.QUERY_STR) or payload.get("query") or self._query)
        return event_id

    def on_event_end(self, event_type, payload=None, event_id="", **kwargs):
        if not self.enabled:
            return
        payload = payload or {}
        et = str(event_type)
        if event_type == CBEventType.RETRIEVE or et.lower().endswith("retrieve"):
            nodes = payload.get(EventPayload.NODES) or payload.get("nodes") or []
            self._chunks = []
            for i, node in enumerate(nodes):
                text = getattr(node, "text", None) or getattr(getattr(node, "node", None), "text", None) or str(node)
                score = getattr(node, "score", None)
                self._chunks.append(
                    {
                        "chunk_id": getattr(node, "node_id", None) or f"li-{i}",
                        "chunk_text": text,
                        "similarity_score": float(score) if score is not None else None,
                    }
                )
        if event_type == CBEventType.LLM or "llm" in et.lower():
            resp = payload.get(EventPayload.RESPONSE) or payload.get("response")
            self._answer = str(resp) if resp is not None else self._answer
            self._flush()

    def _flush(self) -> None:
        if not self._query:
            return
        try:
            latency = None
            if self._t0 is not None:
                latency = (time.perf_counter() - self._t0) * 1000
            self._inspector.send_trace(
                query=self._query,
                retrieved_chunks=self._chunks,
                answer=self._answer or "",
                retrieve_latency_ms=latency,
                generate_latency_ms=None,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("LlamaIndex trace send failed: %s", exc)
        finally:
            self._query = ""
            self._chunks = []
            self._answer = None
            self._t0 = None

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        return None

    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[dict] = None) -> None:
        return None

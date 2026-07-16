"""RAGInspector tracer with decorators for instrumenting RAG pipelines."""

import asyncio
import functools
import inspect
import logging
import threading
import time
from typing import Any, Callable, Optional

from raginspector.client import RAGInspectorClient

logger = logging.getLogger("raginspector")


def _is_async_callable(func: Callable) -> bool:
    return inspect.iscoroutinefunction(func)


def _capture_embedding(result) -> Optional[list]:
    """Normalize embedding function return values to a flat vector list."""
    if isinstance(result, (list, tuple)) and len(result) > 0:
        if not isinstance(result[0], (list, tuple)):
            return list(result)
        return list(result[0])
    return None


class RAGInspector:
    """
    Main RAGInspector client for instrumenting RAG pipelines.

    Args:
        api_key: Your RAGInspector API key (starts with 'ri-')
        pipeline_name: Name to identify this pipeline in the dashboard
        base_url: RAGInspector server URL (default: http://localhost:8000)
        timeout: HTTP timeout for sending traces (default: 5s, non-blocking)
        enabled: Set to False to disable tracing (useful for tests)
        max_retries: Retry count for 5xx/network errors (default: 3)
        retry_backoff: Base backoff in seconds between retries (default: 0.5)
        batch_size: When set, queue traces and flush at this size (default: None)
        batch_flush_interval: Max seconds before flushing a partial batch (default: 1.0)
    """

    def __init__(
        self,
        api_key: str,
        pipeline_name: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 5.0,
        enabled: bool = True,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        batch_size: Optional[int] = None,
        batch_flush_interval: float = 1.0,
    ):
        self.api_key = api_key
        self.pipeline_name = pipeline_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.enabled = enabled

        self._client = RAGInspectorClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            batch_size=batch_size,
            batch_flush_interval=batch_flush_interval,
        )

        self._trace_state = threading.local()

    @property
    def client(self) -> RAGInspectorClient:
        """Underlying HTTP client (useful for LangChain integration and tests)."""
        return self._client

    def _get_state(self) -> dict:
        if not hasattr(self._trace_state, "data"):
            self._trace_state.data = {}
        return self._trace_state.data

    def _reset_state(self) -> None:
        """Reset per-query fields while preserving set_context values."""
        existing = getattr(self._trace_state, "data", None) or {}
        metadata = existing.get("metadata")
        self._trace_state.data = {
            "query_text": None,
            "query_embedding": None,
            "retrieved_chunks": [],
            "raw_context": None,
            "answer_text": None,
            "embed_latency_ms": None,
            "retrieve_latency_ms": None,
            "generate_latency_ms": None,
            "rank_latency_ms": None,
            "session_id": existing.get("session_id"),
            "request_id": existing.get("request_id"),
            "metadata": dict(metadata) if isinstance(metadata, dict) else None,
            "stage_latencies": {},
        }

    def set_context(
        self,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Attach session/request context and merge metadata into thread-local state.

        Does not wipe query/retrieval/generation fields already captured for the
        current trace.
        """
        state = self._get_state()
        if session_id is not None:
            state["session_id"] = session_id
        if request_id is not None:
            state["request_id"] = request_id
        if metadata is not None:
            existing = state.get("metadata")
            if not isinstance(existing, dict):
                existing = {}
            existing.update(metadata)
            state["metadata"] = existing

    def trace_retrieval(self, func: Callable) -> Callable:
        """
        Decorator to trace retrieval functions.
        The decorated function should accept (query: str) as first argument
        and return a list of dicts with at minimum 'chunk_text' key.
        """

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)
            self._reset_state()
            state = self._get_state()
            query = args[0] if args else kwargs.get("query", "")
            state["query_text"] = str(query)

            t0 = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except Exception:
                raise
            finally:
                state["retrieve_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)

            state["retrieved_chunks"] = self._parse_chunks(result)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.enabled:
                return await func(*args, **kwargs)
            self._reset_state()
            state = self._get_state()
            query = args[0] if args else kwargs.get("query", "")
            state["query_text"] = str(query)

            t0 = time.monotonic()
            try:
                result = await func(*args, **kwargs)
            except Exception:
                raise
            finally:
                state["retrieve_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)

            state["retrieved_chunks"] = self._parse_chunks(result)
            return result

        if _is_async_callable(func):
            return async_wrapper
        return sync_wrapper

    def _enqueue_trace_safely(self, payload: dict) -> None:
        """Queue/send a trace without raising into the caller's RAG path."""
        try:
            self._client.queue_trace(payload)
        except Exception:
            logger.exception("RAGInspector: failed to enqueue trace")

    async def _send_trace_async_safely(self, payload: dict) -> None:
        try:
            await self._client.send_trace_async(payload)
        except Exception:
            logger.exception("RAGInspector: failed to send async trace")

    def _schedule_trace_send(self, state: dict, *, async_mode: bool) -> None:
        """Build and dispatch a trace; never raise into the decorated function."""
        try:
            payload = self._build_payload(state)
            if async_mode:
                asyncio.create_task(self._send_trace_async_safely(payload))
            else:
                threading.Thread(
                    target=self._enqueue_trace_safely,
                    args=(payload,),
                    daemon=True,
                ).start()
        except Exception:
            logger.exception("RAGInspector: failed to schedule trace send")

    def trace_generation(self, func: Callable) -> Callable:
        """
        Decorator to trace generation functions.
        The decorated function should accept (query, context) and return a string answer.
        After generation completes, sends the full trace to RAGInspector asynchronously.
        """

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)
            state = self._get_state()

            if len(args) >= 2:
                raw_context = args[1]
            else:
                raw_context = kwargs.get("context", "")

            if isinstance(raw_context, list):
                state["raw_context"] = "\n\n".join(
                    str(c.get("chunk_text", c)) if isinstance(c, dict) else str(c)
                    for c in raw_context
                )
            else:
                state["raw_context"] = str(raw_context) if raw_context else None

            t0 = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except Exception:
                raise
            finally:
                state["generate_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)

            state["answer_text"] = str(result) if result else None
            self._schedule_trace_send(state, async_mode=False)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.enabled:
                return await func(*args, **kwargs)
            state = self._get_state()

            if len(args) >= 2:
                raw_context = args[1]
            else:
                raw_context = kwargs.get("context", "")

            if isinstance(raw_context, list):
                state["raw_context"] = "\n\n".join(
                    str(c.get("chunk_text", c)) if isinstance(c, dict) else str(c)
                    for c in raw_context
                )
            else:
                state["raw_context"] = str(raw_context) if raw_context else None

            t0 = time.monotonic()
            try:
                result = await func(*args, **kwargs)
            except Exception:
                raise
            finally:
                state["generate_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)

            state["answer_text"] = str(result) if result else None
            self._schedule_trace_send(state, async_mode=True)
            return result

        if _is_async_callable(func):
            return async_wrapper
        return sync_wrapper

    def trace_stage(self, name: str) -> Callable:
        """
        Decorator to time a custom pipeline stage.

        Records elapsed milliseconds into ``state["stage_latencies"][name]``
        without sending a trace by itself.
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                state = self._get_state()
                stages = state.get("stage_latencies")
                if not isinstance(stages, dict):
                    stages = {}
                    state["stage_latencies"] = stages
                t0 = time.monotonic()
                try:
                    return func(*args, **kwargs)
                finally:
                    stages[name] = round((time.monotonic() - t0) * 1000, 2)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                state = self._get_state()
                stages = state.get("stage_latencies")
                if not isinstance(stages, dict):
                    stages = {}
                    state["stage_latencies"] = stages
                t0 = time.monotonic()
                try:
                    return await func(*args, **kwargs)
                finally:
                    stages[name] = round((time.monotonic() - t0) * 1000, 2)

            if _is_async_callable(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    def trace_reranking(self, func: Callable) -> Callable:
        """Decorator to record rank_latency_ms for a reranking step."""

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)
            state = self._get_state()
            t0 = time.monotonic()
            try:
                return func(*args, **kwargs)
            finally:
                state["rank_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.enabled:
                return await func(*args, **kwargs)
            state = self._get_state()
            t0 = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                state["rank_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)

        if _is_async_callable(func):
            return async_wrapper
        return sync_wrapper

    def _parse_chunks(self, result) -> list:
        """Convert various return formats to standard chunk list."""
        if not result:
            return []
        if isinstance(result, list):
            chunks = []
            for i, item in enumerate(result):
                if isinstance(item, dict):
                    chunk = {
                        "chunk_id": item.get("id") or item.get("chunk_id") or f"chunk_{i}",
                        "chunk_text": item.get("text")
                        or item.get("chunk_text")
                        or item.get("page_content")
                        or str(item),
                        "similarity_score": item.get("score") or item.get("similarity_score"),
                        "rank": item.get("rank", i + 1),
                        "metadata": {
                            k: v
                            for k, v in item.items()
                            if k
                            not in (
                                "text",
                                "chunk_text",
                                "page_content",
                                "score",
                                "similarity_score",
                                "id",
                                "chunk_id",
                                "rank",
                            )
                        },
                    }
                    chunks.append(chunk)
                elif isinstance(item, str):
                    chunks.append({"chunk_id": f"chunk_{i}", "chunk_text": item, "rank": i + 1})
                else:
                    try:
                        chunks.append(
                            {
                                "chunk_id": f"chunk_{i}",
                                "chunk_text": item.page_content,
                                "metadata": item.metadata if hasattr(item, "metadata") else {},
                                "rank": i + 1,
                            }
                        )
                    except AttributeError:
                        chunks.append(
                            {"chunk_id": f"chunk_{i}", "chunk_text": str(item), "rank": i + 1}
                        )
            return chunks
        return []

    def _build_payload(self, state: dict) -> dict:
        payload: dict[str, Any] = {
            "pipeline_name": self.pipeline_name,
            "query_text": state.get("query_text") or "",
            "query_embedding": state.get("query_embedding"),
            "retrieved_chunks": state.get("retrieved_chunks") or [],
            "raw_context": state.get("raw_context"),
            "answer_text": state.get("answer_text"),
            "embed_latency_ms": state.get("embed_latency_ms"),
            "retrieve_latency_ms": state.get("retrieve_latency_ms"),
            "generate_latency_ms": state.get("generate_latency_ms"),
        }

        for key in ("rank_latency_ms", "session_id", "request_id"):
            value = state.get(key)
            if value is not None:
                payload[key] = value

        metadata = state.get("metadata")
        if metadata:
            payload["metadata"] = metadata

        stage_latencies = state.get("stage_latencies")
        if stage_latencies:
            payload["stage_latencies"] = stage_latencies

        return payload

    def _send_trace_sync_with_state(self, state: dict) -> None:
        try:
            payload = self._build_payload(state)
            self._enqueue_trace_safely(payload)
        except Exception:
            logger.exception("RAGInspector: failed to send manual trace")

    def trace_embedding(self, func: Callable) -> Callable:
        """Optional: trace embedding step to capture embed latency and vector."""

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)
            state = self._get_state()
            t0 = time.monotonic()
            result = func(*args, **kwargs)
            state["embed_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)
            embedding = _capture_embedding(result)
            if embedding is not None:
                state["query_embedding"] = embedding
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self.enabled:
                return await func(*args, **kwargs)
            state = self._get_state()
            t0 = time.monotonic()
            result = await func(*args, **kwargs)
            state["embed_latency_ms"] = round((time.monotonic() - t0) * 1000, 2)
            embedding = _capture_embedding(result)
            if embedding is not None:
                state["query_embedding"] = embedding
            return result

        if _is_async_callable(func):
            return async_wrapper
        return sync_wrapper

    def send_trace(
        self,
        query: str,
        retrieved_chunks: list,
        answer: str,
        context: Optional[str] = None,
        embed_latency_ms: Optional[float] = None,
        retrieve_latency_ms: Optional[float] = None,
        generate_latency_ms: Optional[float] = None,
        rank_latency_ms: Optional[float] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        stage_latencies: Optional[dict] = None,
    ) -> None:
        """
        Manual trace sending (alternative to decorators).
        Use when you need full control over what gets sent.
        """
        if not self.enabled:
            return
        state = {
            "query_text": query,
            "retrieved_chunks": self._parse_chunks(retrieved_chunks),
            "answer_text": answer,
            "raw_context": context,
            "embed_latency_ms": embed_latency_ms,
            "retrieve_latency_ms": retrieve_latency_ms,
            "generate_latency_ms": generate_latency_ms,
            "rank_latency_ms": rank_latency_ms,
            "session_id": session_id,
            "request_id": request_id,
            "metadata": metadata,
            "stage_latencies": stage_latencies,
            "query_embedding": None,
        }
        t = threading.Thread(
            target=self._send_trace_sync_with_state,
            args=(state,),
            daemon=True,
        )
        t.start()

    def flush(self) -> None:
        """Flush any batched traces."""
        self._client.flush()

    def close(self) -> None:
        """Flush pending traces and release client resources."""
        self._client.close()

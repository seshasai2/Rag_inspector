"""LangChain callback integration for RAGInspector."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from raginspector.client import RAGInspectorClient
from raginspector.tracer import RAGInspector

logger = logging.getLogger("raginspector")

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover - optional dependency

    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Duck-typed fallback when langchain-core is not installed."""

        pass


class RAGInspectorCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that collects retrieve/generate events
    and sends traces to RAGInspector.

    Usage:
        handler = RAGInspectorCallbackHandler(
            api_key="ri-your-key",
            pipeline_name="langchain-rag",
        )
        chain.invoke({"query": "..."}, config={"callbacks": [handler]})
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
        inspector: Optional[RAGInspector] = None,
    ):
        super().__init__()
        self.enabled = enabled
        self._inspector = inspector or RAGInspector(
            api_key=api_key,
            pipeline_name=pipeline_name,
            base_url=base_url,
            timeout=timeout,
            enabled=enabled,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            batch_size=batch_size,
            batch_flush_interval=batch_flush_interval,
        )
        self._client: RAGInspectorClient = self._inspector.client

        self._query: str = ""
        self._retrieved_chunks: list[dict[str, Any]] = []
        self._raw_context: Optional[str] = None
        self._answer_text: Optional[str] = None
        self._retrieve_latency_ms: Optional[float] = None
        self._generate_latency_ms: Optional[float] = None
        self._retrieve_started_at: Optional[float] = None
        self._generate_started_at: Optional[float] = None

    @property
    def inspector(self) -> RAGInspector:
        return self._inspector

    def _reset_run(self) -> None:
        self._query = ""
        self._retrieved_chunks = []
        self._raw_context = None
        self._answer_text = None
        self._retrieve_latency_ms = None
        self._generate_latency_ms = None
        self._retrieve_started_at = None
        self._generate_started_at = None

    def _extract_query(self, inputs: Any) -> str:
        if isinstance(inputs, dict):
            for key in ("query", "question", "input", "input_str"):
                if key in inputs and inputs[key]:
                    return str(inputs[key])
        return str(inputs) if inputs is not None else ""

    def _extract_answer(self, outputs: Any) -> str:
        if isinstance(outputs, dict):
            for key in ("result", "answer", "output", "text"):
                if key in outputs and outputs[key] is not None:
                    return str(outputs[key])
            if len(outputs) == 1:
                return str(next(iter(outputs.values())))
        return str(outputs) if outputs is not None else ""

    def _parse_documents(self, documents: list) -> list[dict[str, Any]]:
        return self._inspector._parse_chunks(documents)

    def _build_payload(self) -> dict:
        return self._inspector._build_payload(
            {
                "query_text": self._query,
                "query_embedding": None,
                "retrieved_chunks": self._retrieved_chunks,
                "raw_context": self._raw_context,
                "answer_text": self._answer_text,
                "embed_latency_ms": None,
                "retrieve_latency_ms": self._retrieve_latency_ms,
                "generate_latency_ms": self._generate_latency_ms,
            }
        )

    def _send_trace_background(self) -> None:
        if not self.enabled:
            return
        if not self._query or not self._answer_text:
            return
        payload = self._build_payload()
        t = threading.Thread(
            target=self._client.queue_trace,
            args=(payload,),
            daemon=True,
        )
        t.start()

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        if not self.enabled:
            return
        self._reset_run()
        self._query = self._extract_query(inputs)

    def on_retriever_start(self, serialized: dict[str, Any], query: str, **kwargs: Any) -> None:
        if not self.enabled:
            return
        if not self._query:
            self._query = str(query)
        self._retrieve_started_at = time.monotonic()

    def on_retriever_end(self, documents: list, **kwargs: Any) -> None:
        if not self.enabled:
            return
        if self._retrieve_started_at is not None:
            self._retrieve_latency_ms = round(
                (time.monotonic() - self._retrieve_started_at) * 1000,
                2,
            )
        self._retrieved_chunks = self._parse_documents(documents)
        if documents:
            self._raw_context = "\n\n".join(
                doc.page_content if hasattr(doc, "page_content") else str(doc)
                for doc in documents
            )

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        if not self.enabled:
            return
        self._generate_started_at = time.monotonic()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        if not self.enabled:
            return
        if self._generate_started_at is not None:
            self._generate_latency_ms = round(
                (time.monotonic() - self._generate_started_at) * 1000,
                2,
            )

        text = None
        generations = getattr(response, "generations", None)
        if generations and generations[0]:
            generation = generations[0][0]
            text = getattr(generation, "text", None)
            if text is None and hasattr(generation, "message"):
                text = getattr(generation.message, "content", None)
        if text is None:
            text = str(response)
        self._answer_text = str(text)

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        if not self.enabled:
            return
        if not self._answer_text:
            self._answer_text = self._extract_answer(outputs)
        if self._retrieved_chunks and self._query:
            self._send_trace_background()
            self._reset_run()

    def flush(self) -> None:
        self._client.flush()

    def close(self) -> None:
        self._inspector.close()

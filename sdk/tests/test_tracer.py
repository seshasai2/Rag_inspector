"""Tests for RAGInspector tracer decorators."""

import asyncio
import threading
import time
import unittest
from unittest.mock import patch

import httpx

from raginspector.tracer import RAGInspector


class TestRAGInspectorTracer(unittest.TestCase):
    def setUp(self):
        self.sent_payloads: list[dict] = []
        self._lock = threading.Lock()

    def _capture_send(self, payload: dict) -> None:
        with self._lock:
            self.sent_payloads.append(payload)

    def _make_inspector(self, **kwargs) -> RAGInspector:
        defaults = {
            "api_key": "ri-test-key",
            "pipeline_name": "test-pipeline",
            "base_url": "http://testserver",
            "enabled": True,
            "max_retries": 0,
        }
        defaults.update(kwargs)
        inspector = RAGInspector(**defaults)
        inspector._client.queue_trace = self._capture_send  # type: ignore[method-assign]
        inspector._client.send_trace = self._capture_send  # type: ignore[method-assign]
        return inspector

    def test_trace_retrieval_and_generation_sync(self):
        inspector = self._make_inspector()

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc one", "score": 0.9}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "generated answer"

        chunks = retrieve("what is RAG?")
        answer = generate("what is RAG?", chunks)

        self.assertEqual(answer, "generated answer")
        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        payload = self.sent_payloads[0]
        self.assertEqual(payload["pipeline_name"], "test-pipeline")
        self.assertEqual(payload["query_text"], "what is RAG?")
        self.assertEqual(payload["answer_text"], "generated answer")
        self.assertEqual(len(payload["retrieved_chunks"]), 1)
        self.assertEqual(payload["retrieved_chunks"][0]["chunk_text"], "doc one")
        self.assertIsNotNone(payload["retrieve_latency_ms"])
        self.assertIsNotNone(payload["generate_latency_ms"])

    def test_disabled_inspector_skips_tracing(self):
        inspector = self._make_inspector(enabled=False)

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer"

        generate("q", retrieve("q"))
        time.sleep(0.05)
        self.assertEqual(len(self.sent_payloads), 0)

    def test_trace_embedding(self):
        inspector = self._make_inspector()

        @inspector.trace_embedding
        def embed(text: str):
            return [0.1, 0.2, 0.3]

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer"

        # Embed after retrieval so reset_state does not clear the embedding.
        chunks = retrieve("hello")
        embed("hello")
        generate("hello", chunks)
        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self.sent_payloads[0]["query_embedding"], [0.1, 0.2, 0.3])
        self.assertIsNotNone(self.sent_payloads[0]["embed_latency_ms"])

    def test_send_trace_manual(self):
        inspector = self._make_inspector()
        inspector.send_trace(
            query="manual q",
            retrieved_chunks=[{"text": "chunk"}],
            answer="manual answer",
            context="ctx",
            retrieve_latency_ms=12.5,
        )
        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        payload = self.sent_payloads[0]
        self.assertEqual(payload["query_text"], "manual q")
        self.assertEqual(payload["answer_text"], "manual answer")
        self.assertEqual(payload["raw_context"], "ctx")
        self.assertEqual(payload["retrieve_latency_ms"], 12.5)

    def test_parse_chunks_various_formats(self):
        inspector = self._make_inspector()

        class FakeDocument:
            page_content = "lc content"
            metadata = {"source": "test"}

        chunks = inspector._parse_chunks(
            [
                {"text": "from text key", "score": 0.5},
                "plain string",
                FakeDocument(),
            ]
        )
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["chunk_text"], "from text key")
        self.assertEqual(chunks[0]["similarity_score"], 0.5)
        self.assertEqual(chunks[1]["chunk_text"], "plain string")
        self.assertEqual(chunks[2]["chunk_text"], "lc content")

    def test_async_decorators(self):
        inspector = self._make_inspector()

        async def mock_send_async(payload):
            self._capture_send(payload)

        inspector._client.send_trace_async = mock_send_async  # type: ignore[method-assign]

        @inspector.trace_retrieval
        async def retrieve(query: str):
            return [{"chunk_text": "async doc"}]

        @inspector.trace_generation
        async def generate(query: str, context):
            return "async answer"

        async def run():
            chunks = await retrieve("async q")
            return await generate("async q", chunks)

        result = asyncio.run(run())
        self.assertEqual(result, "async answer")
        time.sleep(0.1)
        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self.sent_payloads[0]["answer_text"], "async answer")

    def test_send_failure_does_not_break_sync_generation(self):
        inspector = self._make_inspector()

        def boom(_payload):
            raise RuntimeError("ingest down")

        inspector._client.queue_trace = boom  # type: ignore[method-assign]

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "still works"

        answer = generate("q", retrieve("q"))
        time.sleep(0.1)
        self.assertEqual(answer, "still works")

    def test_build_payload_failure_does_not_break_generation(self):
        inspector = self._make_inspector()

        def boom(_state):
            raise RuntimeError("payload broken")

        inspector._build_payload = boom  # type: ignore[method-assign]

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer preserved"

        answer = generate("q", retrieve("q"))
        self.assertEqual(answer, "answer preserved")
        self.assertEqual(len(self.sent_payloads), 0)

    def test_async_send_failure_does_not_break_generation(self):
        inspector = self._make_inspector()

        async def boom(_payload):
            raise RuntimeError("async ingest down")

        inspector._client.send_trace_async = boom  # type: ignore[method-assign]

        @inspector.trace_retrieval
        async def retrieve(query: str):
            return [{"chunk_text": "async doc"}]

        @inspector.trace_generation
        async def generate(query: str, context):
            return "async still works"

        async def run():
            chunks = await retrieve("async q")
            return await generate("async q", chunks)

        result = asyncio.run(run())
        time.sleep(0.1)
        self.assertEqual(result, "async still works")

    def test_public_import(self):
        from raginspector import RAGInspector as ImportedInspector

        self.assertIs(ImportedInspector, RAGInspector)

    def test_set_context_appears_in_payload(self):
        inspector = self._make_inspector()
        inspector.set_context(
            session_id="sess-1",
            request_id="req-42",
            metadata={"model": "gpt-test", "vector_db": "pinecone"},
        )

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer"

        generate("q", retrieve("q"))
        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        payload = self.sent_payloads[0]
        self.assertEqual(payload["session_id"], "sess-1")
        self.assertEqual(payload["request_id"], "req-42")
        self.assertEqual(payload["metadata"]["model"], "gpt-test")
        self.assertEqual(payload["metadata"]["vector_db"], "pinecone")

    def test_set_context_merges_metadata_without_wiping_query(self):
        inspector = self._make_inspector()

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer"

        chunks = retrieve("hello query")
        inspector.set_context(session_id="s1", metadata={"tag": "a"})
        inspector.set_context(metadata={"env": "test"})
        state = inspector._get_state()
        self.assertEqual(state["query_text"], "hello query")
        self.assertEqual(state["metadata"], {"tag": "a", "env": "test"})

        generate("hello query", chunks)
        time.sleep(0.1)
        self.assertEqual(self.sent_payloads[0]["session_id"], "s1")
        self.assertEqual(self.sent_payloads[0]["metadata"]["env"], "test")

    def test_trace_stage_timing(self):
        inspector = self._make_inspector()

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_stage("preprocess")
        def preprocess(text: str):
            time.sleep(0.02)
            return text

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer"

        chunks = retrieve("q")
        preprocess("q")
        generate("q", chunks)
        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        stages = self.sent_payloads[0]["stage_latencies"]
        self.assertIn("preprocess", stages)
        self.assertGreaterEqual(stages["preprocess"], 15)

    def test_trace_reranking_records_rank_latency(self):
        inspector = self._make_inspector()

        @inspector.trace_retrieval
        def retrieve(query: str):
            return [{"chunk_text": "doc"}]

        @inspector.trace_reranking
        def rerank(chunks):
            time.sleep(0.01)
            return chunks

        @inspector.trace_generation
        def generate(query: str, context):
            return "answer"

        chunks = retrieve("q")
        rerank(chunks)
        generate("q", chunks)
        time.sleep(0.1)

        self.assertIsNotNone(self.sent_payloads[0].get("rank_latency_ms"))
        self.assertGreaterEqual(self.sent_payloads[0]["rank_latency_ms"], 5)

    def test_async_embedding_captures_vector(self):
        inspector = self._make_inspector()

        async def mock_send_async(payload):
            self._capture_send(payload)

        inspector._client.send_trace_async = mock_send_async  # type: ignore[method-assign]

        @inspector.trace_retrieval
        async def retrieve(query: str):
            return [{"chunk_text": "async doc"}]

        @inspector.trace_embedding
        async def embed(text: str):
            return [0.4, 0.5, 0.6]

        @inspector.trace_generation
        async def generate(query: str, context):
            return "async answer"

        async def run():
            chunks = await retrieve("async q")
            await embed("async q")
            return await generate("async q", chunks)

        result = asyncio.run(run())
        self.assertEqual(result, "async answer")
        time.sleep(0.1)
        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self.sent_payloads[0]["query_embedding"], [0.4, 0.5, 0.6])
        self.assertIsNotNone(self.sent_payloads[0]["embed_latency_ms"])

    def test_send_trace_optional_fields(self):
        inspector = self._make_inspector()
        inspector.send_trace(
            query="manual q",
            retrieved_chunks=[{"text": "chunk"}],
            answer="manual answer",
            rank_latency_ms=3.5,
            session_id="sess-m",
            request_id="req-m",
            metadata={"source": "manual"},
            stage_latencies={"prep": 1.0},
        )
        time.sleep(0.1)

        payload = self.sent_payloads[0]
        self.assertEqual(payload["rank_latency_ms"], 3.5)
        self.assertEqual(payload["session_id"], "sess-m")
        self.assertEqual(payload["request_id"], "req-m")
        self.assertEqual(payload["metadata"]["source"], "manual")
        self.assertEqual(payload["stage_latencies"]["prep"], 1.0)

    def test_build_payload_omits_unset_optionals(self):
        inspector = self._make_inspector()
        payload = inspector._build_payload(
            {
                "query_text": "q",
                "retrieved_chunks": [],
                "answer_text": "a",
                "raw_context": None,
                "embed_latency_ms": None,
                "retrieve_latency_ms": None,
                "generate_latency_ms": None,
                "query_embedding": None,
                "rank_latency_ms": None,
                "session_id": None,
                "request_id": None,
                "metadata": None,
                "stage_latencies": {},
            }
        )
        self.assertNotIn("rank_latency_ms", payload)
        self.assertNotIn("session_id", payload)
        self.assertNotIn("request_id", payload)
        self.assertNotIn("metadata", payload)
        self.assertNotIn("stage_latencies", payload)


if __name__ == "__main__":
    unittest.main()

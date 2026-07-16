"""Tests for LangChain callback handler."""

import threading
import time
import unittest
from unittest.mock import patch

from raginspector.langchain import RAGInspectorCallbackHandler


class FakeDocument:
    def __init__(self, page_content: str, metadata: dict | None = None):
        self.page_content = page_content
        self.metadata = metadata or {}


class FakeGeneration:
    def __init__(self, text: str):
        self.text = text


class FakeLLMResponse:
    def __init__(self, text: str):
        self.generations = [[FakeGeneration(text)]]


class TestRAGInspectorCallbackHandler(unittest.TestCase):
    def setUp(self):
        self.sent_payloads: list[dict] = []
        self._lock = threading.Lock()

    def _capture_send(self, payload: dict) -> None:
        with self._lock:
            self.sent_payloads.append(payload)

    def _make_handler(self, **kwargs) -> RAGInspectorCallbackHandler:
        defaults = {
            "api_key": "ri-test-key",
            "pipeline_name": "lc-pipeline",
            "base_url": "http://testserver",
            "enabled": True,
            "max_retries": 0,
        }
        defaults.update(kwargs)
        handler = RAGInspectorCallbackHandler(**defaults)
        handler._client.queue_trace = self._capture_send  # type: ignore[method-assign]
        return handler

    def test_collects_retrieve_and_generate_events(self):
        handler = self._make_handler()

        handler.on_chain_start({}, {"query": "What is RAG?"})
        handler.on_retriever_start({}, "What is RAG?")
        handler.on_retriever_end(
            [
                FakeDocument("chunk one", {"id": "c1", "score": 0.9}),
                FakeDocument("chunk two"),
            ]
        )
        handler.on_llm_start({}, ["prompt"])
        handler.on_llm_end(FakeLLMResponse("RAG stands for retrieval augmented generation."))
        handler.on_chain_end({"result": "RAG stands for retrieval augmented generation."})

        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        payload = self.sent_payloads[0]
        self.assertEqual(payload["pipeline_name"], "lc-pipeline")
        self.assertEqual(payload["query_text"], "What is RAG?")
        self.assertEqual(
            payload["answer_text"],
            "RAG stands for retrieval augmented generation.",
        )
        self.assertEqual(len(payload["retrieved_chunks"]), 2)
        self.assertEqual(payload["retrieved_chunks"][0]["chunk_text"], "chunk one")
        self.assertIsNotNone(payload["retrieve_latency_ms"])
        self.assertIsNotNone(payload["generate_latency_ms"])
        self.assertIn("chunk one", payload["raw_context"])

    def test_chain_end_extracts_answer_from_outputs(self):
        handler = self._make_handler()

        handler.on_chain_start({}, {"question": "capital of France?"})
        handler.on_retriever_end([FakeDocument("Paris is the capital.")])
        handler.on_chain_end({"answer": "Paris"})

        time.sleep(0.1)

        self.assertEqual(len(self.sent_payloads), 1)
        self.assertEqual(self.sent_payloads[0]["query_text"], "capital of France?")
        self.assertEqual(self.sent_payloads[0]["answer_text"], "Paris")

    def test_disabled_handler_does_not_send(self):
        handler = self._make_handler(enabled=False)

        handler.on_chain_start({}, {"query": "q"})
        handler.on_retriever_end([FakeDocument("doc")])
        handler.on_chain_end({"result": "a"})

        time.sleep(0.05)
        self.assertEqual(len(self.sent_payloads), 0)

    def test_optional_export_from_package(self):
        from raginspector import RAGInspectorCallbackHandler as ExportedHandler

        self.assertIs(ExportedHandler, RAGInspectorCallbackHandler)

    def test_works_without_langchain_installed(self):
        with patch.dict("sys.modules", {"langchain_core.callbacks": None}):
            import importlib

            import raginspector.langchain as lc_module

            importlib.reload(lc_module)
            handler = lc_module.RAGInspectorCallbackHandler(
                api_key="ri-test",
                pipeline_name="p",
            )
            self.assertTrue(hasattr(handler, "on_chain_end"))


if __name__ == "__main__":
    unittest.main()

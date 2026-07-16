"""SDK LlamaIndex / Haystack adapters (Phase 10.12) — unittest-compatible for CI."""
from __future__ import annotations

import unittest

from raginspector.haystack import RAGInspectorHaystackTracer
from raginspector.llamaindex import RAGInspectorLlamaIndexHandler


class FakeInspector:
    def __init__(self):
        self.sent = None

    def send_trace(self, **kwargs):
        self.sent = kwargs


class TestFrameworkAdapters(unittest.TestCase):
    def test_llamaindex_handler_constructs_disabled(self):
        h = RAGInspectorLlamaIndexHandler(
            api_key="ri-test",
            pipeline_name="t",
            enabled=False,
            inspector=FakeInspector(),  # type: ignore[arg-type]
        )
        self.assertFalse(h.enabled)
        # Disabled handler must not send
        h.on_event_start("retrieve", payload={"query": "q"})
        h.on_event_end("llm", payload={"response": "a"})
        self.assertIsNone(h._inspector.sent if hasattr(h._inspector, "sent") else None)

    def test_haystack_tracer_run_sends(self):
        fake = FakeInspector()
        t = RAGInspectorHaystackTracer(
            api_key="ri-test",
            pipeline_name="t",
            inspector=fake,  # type: ignore[arg-type]
        )
        out = t.run(query="q", documents=[], answer="a")
        self.assertEqual(out["answer"], "a")
        self.assertEqual(fake.sent["query"], "q")

    def test_haystack_disabled_skips_send(self):
        fake = FakeInspector()
        t = RAGInspectorHaystackTracer(
            api_key="ri-test",
            pipeline_name="t",
            enabled=False,
            inspector=fake,  # type: ignore[arg-type]
        )
        t.run(query="q", documents=[], answer="a")
        self.assertIsNone(fake.sent)

    def test_llamaindex_flush_on_llm_end(self):
        fake = FakeInspector()
        h = RAGInspectorLlamaIndexHandler(
            api_key="ri-test",
            pipeline_name="t",
            inspector=fake,  # type: ignore[arg-type]
        )
        h.on_event_start("retrieve", payload={"query": "what is refund"})
        h.on_event_end(
            "retrieve",
            payload={"nodes": [type("N", (), {"text": "refund policy", "score": 0.9, "node_id": "n1"})()]},
        )
        h.on_event_end("llm", payload={"response": "You get a refund"})
        self.assertIsNotNone(fake.sent)
        self.assertEqual(fake.sent["query"], "what is refund")
        self.assertEqual(fake.sent["answer"], "You get a refund")


if __name__ == "__main__":
    unittest.main()

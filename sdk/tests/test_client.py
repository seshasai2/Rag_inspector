"""Tests for RAGInspector HTTP client."""

import json
import unittest
from unittest.mock import patch

import httpx

from raginspector.client import BATCH_ENDPOINT, RAGInspectorClient, TRACE_ENDPOINT


class TestRAGInspectorClient(unittest.TestCase):
    def _make_client(self, **kwargs) -> RAGInspectorClient:
        defaults = {
            "api_key": "ri-test-key",
            "base_url": "http://testserver",
            "timeout": 1.0,
            "max_retries": 2,
            "retry_backoff": 0.01,
        }
        defaults.update(kwargs)
        return RAGInspectorClient(**defaults)

    def _patch_client(self, transport: httpx.MockTransport):
        """Patch httpx.Client to inject MockTransport into the pooled client."""
        real_client = httpx.Client

        def factory(*args, **kwargs):
            kwargs["transport"] = transport
            kwargs.setdefault("timeout", 1.0)
            return real_client(*args, **kwargs)

        return patch("raginspector.client.httpx.Client", side_effect=factory)

    def test_send_trace_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.path, TRACE_ENDPOINT)
            self.assertEqual(request.headers["X-API-Key"], "ri-test-key")
            return httpx.Response(202, json={"trace_id": "abc123"})

        client = self._make_client(max_retries=0)
        with self._patch_client(httpx.MockTransport(handler)):
            client.send_trace({"pipeline_name": "p", "query_text": "q"})
        client.close()

    def test_retries_on_5xx(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(503, text="unavailable")
            return httpx.Response(202, json={"trace_id": "retry-ok"})

        client = self._make_client(max_retries=2, retry_backoff=0.01)
        with self._patch_client(httpx.MockTransport(handler)):
            client.send_trace({"pipeline_name": "p", "query_text": "q"})

        self.assertEqual(calls["count"], 2)
        client.close()

    def test_retries_on_network_error(self):
        calls = {"count": 0}

        class FlakyClient:
            def post(self, *args, **kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise httpx.ConnectError("connection refused")
                return httpx.Response(202, json={"trace_id": "net-ok"})

            def close(self):
                pass

        client = self._make_client(max_retries=2, retry_backoff=0.01)
        with patch("raginspector.client.httpx.Client", return_value=FlakyClient()):
            client.send_trace({"pipeline_name": "p", "query_text": "q"})

        self.assertEqual(calls["count"], 2)
        client.close()

    def test_batch_queue_flushes_on_size(self):
        sent_paths: list[str] = []
        bodies: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent_paths.append(request.url.path)
            bodies.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"accepted": 2, "queued_for_analysis": 2, "results": []})

        client = self._make_client(batch_size=2, max_retries=0)
        with self._patch_client(httpx.MockTransport(handler)):
            client.queue_trace({"pipeline_name": "p", "query_text": "one"})
            client.queue_trace({"pipeline_name": "p", "query_text": "two"})

        self.assertEqual(sent_paths, [BATCH_ENDPOINT])
        self.assertEqual(len(bodies[0]["traces"]), 2)
        client.close()

    def test_flush_sends_queued_traces(self):
        sent = {"count": 0, "path": None}

        def handler(request: httpx.Request) -> httpx.Response:
            sent["count"] += 1
            sent["path"] = request.url.path
            return httpx.Response(202, json={"trace_id": "flushed"})

        client = self._make_client(batch_size=10, max_retries=0)
        with self._patch_client(httpx.MockTransport(handler)):
            client.queue_trace({"pipeline_name": "p", "query_text": "queued"})
            client.flush()

        # Single queued item uses the single-trace endpoint
        self.assertEqual(sent["count"], 1)
        self.assertEqual(sent["path"], TRACE_ENDPOINT)
        client.close()

    def test_no_retry_on_4xx(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(400, text="bad request")

        client = self._make_client(max_retries=3, retry_backoff=0.01)
        with self._patch_client(httpx.MockTransport(handler)):
            client.send_trace({"pipeline_name": "p", "query_text": "q"})

        self.assertEqual(calls["count"], 1)
        client.close()

    def test_exhausted_retries_never_raise(self):
        """Failure isolation: HTTP/network errors must not propagate to callers."""
        calls = {"count": 0}

        class AlwaysDown:
            def post(self, *args, **kwargs):
                calls["count"] += 1
                raise httpx.ConnectError("connection refused")

            def close(self):
                pass

        client = self._make_client(max_retries=1, retry_backoff=0.01)
        with patch("raginspector.client.httpx.Client", return_value=AlwaysDown()):
            client.send_trace({"pipeline_name": "p", "query_text": "q"})

        self.assertEqual(calls["count"], 2)
        client.close()

    def test_batch_fallback_to_individual_on_failure(self):
        sent_paths: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent_paths.append(request.url.path)
            if request.url.path == BATCH_ENDPOINT:
                return httpx.Response(500, text="batch fail")
            return httpx.Response(202, json={"trace_id": "ok"})

        client = self._make_client(batch_size=10, max_retries=0)
        with self._patch_client(httpx.MockTransport(handler)):
            client.queue_trace({"pipeline_name": "p", "query_text": "one"})
            client.queue_trace({"pipeline_name": "p", "query_text": "two"})
            client.flush()

        self.assertEqual(sent_paths[0], BATCH_ENDPOINT)
        self.assertEqual(sent_paths.count(TRACE_ENDPOINT), 2)
        client.close()

    def test_pooled_client_reused_and_closed(self):
        """Persistent sync client is created once and cleared on close()."""
        creations = {"count": 0}
        closed = {"count": 0}

        class TrackingClient:
            def __init__(self, *args, **kwargs):
                creations["count"] += 1

            def post(self, *args, **kwargs):
                return httpx.Response(202, json={"trace_id": "pooled"})

            def close(self):
                closed["count"] += 1

        client = self._make_client(max_retries=0)
        with patch("raginspector.client.httpx.Client", side_effect=TrackingClient):
            client.send_trace({"pipeline_name": "p", "query_text": "a"})
            client.send_trace({"pipeline_name": "p", "query_text": "b"})
            self.assertEqual(creations["count"], 1)
            self.assertIsNotNone(client._sync_client)
            client.close()

        self.assertIsNone(client._sync_client)
        self.assertEqual(closed["count"], 1)

    def test_batch_still_works_with_pooled_client(self):
        """Batch endpoint behavior is unchanged with persistent clients."""
        bodies: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            bodies.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"accepted": 3, "queued_for_analysis": 3, "results": []})

        client = self._make_client(batch_size=3, max_retries=0)
        with self._patch_client(httpx.MockTransport(handler)):
            for i in range(3):
                client.queue_trace({"pipeline_name": "p", "query_text": f"q{i}"})
            self.assertEqual(len(bodies), 1)
            self.assertEqual(len(bodies[0]["traces"]), 3)
            # Same pooled client handles the flush
            self.assertIsNotNone(client._sync_client)
        client.close()


if __name__ == "__main__":
    unittest.main()

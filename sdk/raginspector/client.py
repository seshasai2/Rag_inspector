"""HTTP client for sending traces to RAGInspector with retries and optional batching."""

import asyncio
import logging
import threading
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("raginspector")

TRACE_ENDPOINT = "/api/v1/ingest/trace"
BATCH_ENDPOINT = "/api/v1/traces/batch"

# Connection pool defaults — reusable across sync/async clients.
_DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)


class RAGInspectorClient:
    """
    HTTP client for RAGInspector trace ingestion.

    Features:
    - Persistent httpx clients with connection pooling
    - Retries on 5xx responses and network errors with exponential backoff
    - Optional batch queue that flushes via POST /api/v1/traces/batch
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 5.0,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        batch_size: Optional[int] = None,
        batch_flush_interval: float = 1.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.batch_size = batch_size
        self.batch_flush_interval = batch_flush_interval

        self._headers = {"X-API-Key": self.api_key}
        self._trace_url = f"{self.base_url}{TRACE_ENDPOINT}"
        self._batch_url = f"{self.base_url}{BATCH_ENDPOINT}"

        self._batch_lock = threading.RLock()
        self._batch_queue: list[dict[str, Any]] = []
        self._flush_timer: Optional[threading.Timer] = None
        self._closed = False

        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client_lock = threading.Lock()
        self._limits = _DEFAULT_LIMITS

    def _get_sync_client(self) -> httpx.Client:
        """Lazily create a thread-safe persistent sync HTTP client."""
        if self._sync_client is None:
            with self._sync_client_lock:
                if self._sync_client is None:
                    self._sync_client = httpx.Client(
                        timeout=self.timeout,
                        limits=self._limits,
                        http2=False,
                    )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        """Lazily create a persistent async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self._limits,
                http2=False,
            )
        return self._async_client

    def _should_retry(self, status_code: Optional[int], exc: Optional[Exception]) -> bool:
        if exc is not None:
            return True
        if status_code is None:
            return False
        return status_code >= 500

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self.retry_backoff * (2 ** attempt))

    async def _async_sleep_backoff(self, attempt: int) -> None:
        await asyncio.sleep(self.retry_backoff * (2 ** attempt))

    def _log_response(self, resp: httpx.Response, *, batch: bool = False) -> None:
        if resp.status_code in (200, 202):
            try:
                body = resp.json()
            except Exception:
                body = {}
            if batch:
                logger.debug(
                    "Batch sent successfully",
                    extra={"accepted": body.get("accepted"), "queued": body.get("queued_for_analysis")},
                )
            else:
                logger.debug("Trace sent successfully", extra={"trace_id": body.get("trace_id")})
        else:
            logger.warning(
                "RAGInspector: %s send failed with status %s: %s",
                "batch" if batch else "trace",
                resp.status_code,
                resp.text,
            )

    def _post_with_retry(
        self,
        client: httpx.Client,
        url: str,
        payload: dict,
        *,
        batch: bool = False,
    ) -> bool:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = client.post(url, json=payload, headers=self._headers)
                if self._should_retry(resp.status_code, None):
                    if attempt < self.max_retries:
                        self._sleep_backoff(attempt)
                        continue
                    self._log_response(resp, batch=batch)
                    return False
                self._log_response(resp, batch=batch)
                return resp.status_code in (200, 202)
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                logger.warning("RAGInspector: failed to send %s: %s", "batch" if batch else "trace", exc)
                return False
        if last_exc is not None:
            logger.warning("RAGInspector: failed to send %s: %s", "batch" if batch else "trace", last_exc)
        return False

    async def _post_with_retry_async(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict,
        *,
        batch: bool = False,
    ) -> bool:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await client.post(url, json=payload, headers=self._headers)
                if self._should_retry(resp.status_code, None):
                    if attempt < self.max_retries:
                        await self._async_sleep_backoff(attempt)
                        continue
                    self._log_response(resp, batch=batch)
                    return False
                self._log_response(resp, batch=batch)
                return resp.status_code in (200, 202)
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    await self._async_sleep_backoff(attempt)
                    continue
                logger.warning("RAGInspector: failed to send %s: %s", "batch" if batch else "trace", exc)
                return False
        if last_exc is not None:
            logger.warning("RAGInspector: failed to send %s: %s", "batch" if batch else "trace", last_exc)
        return False

    def _schedule_flush_timer(self) -> None:
        if self.batch_size is None or self._closed:
            return
        with self._batch_lock:
            if self._flush_timer is not None:
                return
            self._flush_timer = threading.Timer(
                self.batch_flush_interval,
                self._flush_timer_callback,
            )
            self._flush_timer.daemon = True
            self._flush_timer.start()

    def _cancel_flush_timer(self) -> None:
        with self._batch_lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None

    def _flush_timer_callback(self) -> None:
        self.flush()

    def _enqueue_or_send(self, payload: dict) -> None:
        if self.batch_size is None:
            self.send_trace(payload)
            return

        should_flush = False
        with self._batch_lock:
            self._batch_queue.append(payload)
            if len(self._batch_queue) >= self.batch_size:
                should_flush = True
            else:
                self._schedule_flush_timer()

        if should_flush:
            self.flush()

    def send_trace(self, payload: dict) -> None:
        """Send a single trace synchronously with retries."""
        try:
            client = self._get_sync_client()
            self._post_with_retry(client, self._trace_url, payload)
        except Exception as exc:
            logger.warning("RAGInspector: failed to send trace: %s", exc)

    def send_trace_batch(self, payloads: list[dict]) -> None:
        """Send multiple traces via the batch ingest endpoint.

        Falls back to individual ``/ingest/trace`` posts if the batch call fails
        after retries (preserves per-trace delivery where possible).
        """
        if not payloads:
            return
        if len(payloads) == 1:
            self.send_trace(payloads[0])
            return
        try:
            client = self._get_sync_client()
            ok = self._post_with_retry(
                client,
                self._batch_url,
                {"traces": payloads},
                batch=True,
            )
            if not ok:
                for payload in payloads:
                    self._post_with_retry(client, self._trace_url, payload)
        except Exception as exc:
            logger.warning("RAGInspector: failed to send batch: %s", exc)
            for payload in payloads:
                self.send_trace(payload)

    async def send_trace_async(self, payload: dict) -> None:
        """Send a single trace asynchronously with retries."""
        try:
            client = self._get_async_client()
            await self._post_with_retry_async(client, self._trace_url, payload)
        except Exception as exc:
            logger.warning("RAGInspector: failed to send trace: %s", exc)

    def queue_trace(self, payload: dict) -> None:
        """Queue a trace for batched delivery, or send immediately if batching is disabled."""
        self._enqueue_or_send(payload)

    def flush(self) -> None:
        """Flush any queued traces via the batch ingest API."""
        self._cancel_flush_timer()

        with self._batch_lock:
            payloads = self._batch_queue[:]
            self._batch_queue.clear()

        self.send_trace_batch(payloads)

    def close(self) -> None:
        """Flush pending traces and close persistent HTTP clients."""
        self._closed = True
        self.flush()

        with self._sync_client_lock:
            if self._sync_client is not None:
                try:
                    self._sync_client.close()
                except Exception as exc:
                    logger.debug("RAGInspector: error closing sync client: %s", exc)
                self._sync_client = None

        async_client = self._async_client
        self._async_client = None
        if async_client is not None:
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(async_client.aclose())
                else:
                    loop.create_task(async_client.aclose())
            except Exception as exc:
                logger.debug("RAGInspector: error closing async client: %s", exc)

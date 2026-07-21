# Chat Completions API

The chat completions endpoint returns a single JSON response.

Streaming (SSE) is on the roadmap and **not yet available**.

## Exactly-once delivery

The API does **not** guarantee exactly-once delivery. Clients should use idempotency keys for retries.

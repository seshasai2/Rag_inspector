# ADR 0003: PostgreSQL + Redis as core infrastructure

- **Status:** Accepted  
- **Date:** 2026-07

## Context

Need durable traces/chunks/jobs, transactional integrity, and a broker/cache for Celery and short-TTL dashboard aggregates.

## Decision

- **PostgreSQL 16** (+ pgvector image) as system of record; Alembic owns schema.  
- **Redis** as Celery broker and optional JSON cache; denylist / SSO nonce storage.

## Alternatives considered

| Option | Trade-off |
|--------|-----------|
| MongoDB for traces | Weaker relational joins for ownership/org ACL |
| SQLite only | Fine for unit tests; not for concurrent workers |
| RabbitMQ instead of Redis | Extra moving part for OSS Compose; Redis already needed for cache |

## Consequences

- Async SQLAlchemy for API; sync sessions in Celery workers.  
- Production compose requires passwords; fail-closed settings validation.

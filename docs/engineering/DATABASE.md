# Database

Operational and design notes for PostgreSQL (production) and SQLite (local/test).

## Engines

| Environment | Engine | Notes |
|-------------|--------|-------|
| Production / Compose | PostgreSQL 16 + asyncpg | Schema owned by Alembic |
| Local Windows / unit | SQLite aiosqlite | `create_all` allowed non-prod |
| Selection | `should_use_sqlite()` in `db/session.py` | Env and URL driven |

Never run `create_all` against production Postgres — ENUM/type races with migrations.

## Migrations

- Tool: Alembic under `backend/alembic/`.
- Apply: `make migrate` or `alembic upgrade head`.
- List-filter indexes: [INDEXES.md](../INDEXES.md) (e.g. migration `013_list_filter_indexes`).
- UUID strategy documented in models: VARCHAR(36).

## Core entities

See [11-database-er.md](../architecture/11-database-er.md): organizations, users, pipelines, query_traces, retrieved_chunks, analysis_jobs, api_keys, refresh_tokens.

## Performance practices

1. Batch dashboard aggregates — avoid N+1 per pipeline (Phase 6.2 patterns).
2. `selectinload` on trace detail relationships.
3. Cap list `per_page` ≤ 100.
4. Optional `vector` extension when using embedding columns in Postgres tests/CI.
5. Connection pools sized × API replica count carefully.

## Backups & restore

Follow [BACKUP.md](../BACKUP.md) and [DISASTER_RECOVERY.md](../DISASTER_RECOVERY.md). Practice restore on staging before trusting RPO/RTO numbers.

## Data retention

Define product retention for traces (e.g. 30–90 days) at the org level; large JSON chunk text dominates storage. Archive or prune with jobs rather than unbounded growth.

## Local reset

Compose: `docker compose down -v` deletes volumes. SQLite: delete `raginspector*.db` files used by tests/apps.

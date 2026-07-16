# Database indexes (Phase 6.1)

Audit of **list filter** access paths for queries (traces) and chunks. Single-column FK indexes from earlier migrations remain; this note justifies **new composite indexes** in migration `013_list_filter_indexes`.

## Access paths

### `GET /api/v1/queries`

| Filter / sort | SQL shape | Index |
|---------------|-----------|--------|
| Ownership | `pipelines.user_id = ?` then `query_traces.pipeline_id IN (…)` | `ix_pipelines_user_id` **(new)** |
| Default list | `pipeline_id IN (…)` + `ORDER BY traced_at DESC` + limit | `ix_query_traces_pipeline_id_traced_at` **(new)** |
| Date range | `pipeline_id` + `traced_at >= / <=` | same composite (range on 2nd column) |
| `failure_type` | `pipeline_id` + `failure_type = ?` | `ix_query_traces_pipeline_id_failure_type` **(new)** |
| `is_hallucination` | `pipeline_id` + `is_hallucination = ?` | `ix_query_traces_pipeline_id_is_hallucination` **(new)** |
| `faithfulness_lt` | `faithfulness_score < ?` | **No new index** — low-cardinality float range; selective only with pipeline filter; avoid write cost until metrics prove need |
| Existing | `pipeline_id`, `traced_at` alone | Kept (`ix_query_traces_pipeline_id`, `ix_query_traces_traced_at`) for FK / ad-hoc date scans |

### `GET /api/v1/chunks` (+ summary / flag)

| Filter / sort | SQL shape | Index |
|---------------|-----------|--------|
| Ownership | `pipelines.user_id` | `ix_pipelines_user_id` |
| Default list | `pipeline_id IN (…)` + `ORDER BY retrieval_count DESC` | `ix_chunk_stats_pipeline_id_retrieval_count` **(new)** |
| `flagged_only` / summary flagged count | `pipeline_id` + `is_flagged` | `ix_chunk_stats_pipeline_id_is_flagged` **(new)** |
| Flag toggle / by id | `pipeline_id` + `chunk_id` | `ix_chunk_stats_pipeline_id_chunk_id` **(new)** |
| `search` (`ILIKE %…%`) | leading-wildcard text | **No B-tree index** — needs trigram/`pg_trgm` later if search volume grows |
| Existing | `pipeline_id`, `chunk_id` alone | Kept |

## Intentionally not indexed

- `query_text` / `answer_text` / `chunk_stats.text` full-text — product search is optional `ILIKE`; defer FTS.
- `analysis_status` on traces — not exposed as a list filter today.
- Standalone `is_flagged` / `failure_type` without `pipeline_id` — all tenant queries are pipeline-scoped.

## Apply

```bash
cd backend && alembic upgrade head
```

Models declare the same composites in `__table_args__` so local `create_all` stays aligned.

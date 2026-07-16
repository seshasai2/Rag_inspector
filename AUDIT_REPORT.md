# RAGInspector — Part 1 Enterprise Audit Report

**Date:** 2026-07-14  
**Scope:** Full repository architecture, code quality, and technical-debt remediation (Part 1)  
**Out of scope (later parts):** CI/CD hardening, deploy/observability build-out, security program, test expansion, benchmarking, documentation rewrite  

---

## 1. Executive Verdict

RAGInspector is a **real, layered RAG observability product** (FastAPI + Celery + Next.js + Python SDK), not a chatbot or prototype shell. The analysis pipeline (ingest → BM25 → grounding → RAGAS-style metrics → failure classification → autofix/gaps) is implemented and demo-ready.

It is **not yet staff-engineer production SaaS** end-to-end: enterprise stubs (SCIM/SAML depth), async I/O debt, fat workers, frontend inconsistency, and token-handling patterns still need subsequent phases. Part 1 audited the tree, removed/fixed clear debt, and consolidated hot-path duplication without redesigning the product.

---

## 2. Repository Map

| Area | Role |
|------|------|
| `backend/app/` | FastAPI API, services, workers, models, core |
| `backend/migrations/` | Alembic 001–019 |
| `frontend/src/` | Next.js 15 App Router + TanStack Query + Zustand |
| `sdk/raginspector/` | Tracing decorators + HTTP client + framework adapters |
| `docker/`, `nginx/`, compose files | Local + prod Compose deployment |
| `docs/` | Architecture / ops / honesty layers |
| `examples/` | Minimal SDK demo |
| `infra/` | Placeholder only (no Terraform/K8s) |

---

## 3. Architecture Review

### Current pattern

```
SDK / HTTP ingest → API (auth, plan gates) → Postgres
                         ↓
                   Celery analysis worker
                         ↓
              Metrics / grounding / failure types
                         ↓
                   Dashboard / Queries UI
```

Layered modular monolith with Celery — appropriate for this stage. Not strict Clean / Hexagonal Architecture.

### Strengths

- Clear `core` / `services` / `endpoints` / `workers` separation
- Production settings validation (`validate_production_settings`)
- Dual async API + sync Celery DB sessions
- Experimental honesty (`docs/EXPERIMENTAL.md`, `/enterprise` quarantine, now also `/api/v1/ops/experimental`)
- Real RAG evaluation path (not mocked end-to-end)

### Violations / structural risks (documented for later)

| Issue | Location | Severity |
|-------|----------|----------|
| God worker `run_analysis` (~329 lines) | `workers/tasks.py` | P0 maintainability |
| Fat endpoints (SQL in routes) | auth, billing, ingest, … | P1 |
| Vestigial repository usage (partially fixed in Part 1) | `repositories/pipelines.py` | P1 → improved |
| Models + schemas mega-files | `models/models.py`, `schemas/schemas.py` | P2 |
| `get_db` auto-commit + manual commits | `db/session.py` | P1 |
| Sync Redis / historical sync SMTP on async path | `redis_cache.py` / email (SMTP now async) | P1 |

---

## 4. RAG Pipeline Completeness

| Stage | Status |
|-------|--------|
| SDK instrumentation | Complete (sync/async); batch now hits `/traces/batch` |
| Trace ingest + chunks | Complete |
| BM25 vs vector | Complete (worker) |
| Grounding / hallucination | Complete |
| Faithfulness / answer relevance | Partial (LLM optional + embedding fallback) |
| Context precision / recall | Complete / heuristic+optional LLM |
| Failure classification | Complete |
| Trust score (per-trace + aggregate) | Complete |
| Autofix / knowledge gaps | Scoped (recommendations, not live KB edits) |
| Monitoring / regression / freshness | Complete (scoped) |
| Benchmark / studio / investigator | Heuristic / console-like UI |
| Weekly executive email | **Fixed in Part 1** (was log-only stub) |

---

## 5. Findings Inventory (pre-remediation)

### P0

1. SCIM users created with hardcoded shared password  
2. `scripts/setup.sh` SECRET_KEY placeholder mismatched `.env.example`  
3. Weekly Celery beat task was a no-op  
4. SDK “batching” performed N× single-trace POSTs (ignored `/traces/batch`)  

### P1

5. Duplicated `_owned_pipeline` across studio/monitoring/regression/benchmark/documents  
6. Async event-loop blocked by sync SMTP (`aiosmtplib` unused)  
7. Unused `passlib` dependency  
8. `experimental_manifest` never exposed  
9. Frontend unused Radix / CVA / date-fns; dead hook; non-functional dashboard buttons  
10. Logout did not clear `mfa_device_token`  
11. Demo example email drift (`demo@raginspector.local`)  

### P2+ (documented, not all fixed)

- Split `run_analysis`; ingest ChunkStat N+1  
- Async Redis client  
- Dead models without routes (`AlertRule`, `IPAllowlistEntry`, `InvoiceRecord`)  
- Frontend pipeline filter dualism (shell `?pipeline_id=` vs local selects)  
- Light-theme badges on dark UI  
- Token cookies XSS surface (security phase)  
- Empty `infra/`; missing README screenshot PNG  
- PRD/doc sprawl (`08_*` trio)  

---

## 6. Remediation Completed in Part 1

| Change | Files |
|--------|-------|
| SCIM provisions random unusable password | `backend/app/api/v1/endpoints/scim.py` |
| setup.sh secret placeholder aligned | `scripts/setup.sh` |
| Shared `require_owned_pipeline` / `list_pipeline_ids_for_user` adopted | `repositories/pipelines.py`, studio, monitoring, regression, benchmark, documents |
| Weekly reports actually deliver email | `services/weekly_reports.py`, `workers/tasks.py` |
| SMTP uses `aiosmtplib`; sync helper for Celery | `services/email_service.py` |
| Removed unused `passlib` from `requirements.in` | `backend/requirements.in` |
| Ops experimental manifest endpoint | `endpoints/ops.py` + `experimental.py` |
| SDK flush → `POST /api/v1/traces/batch` with single-trace fallback | `sdk/raginspector/client.py`, tests |
| Example demo email + `flush()` | `examples/demo_send_trace.py` |
| Frontend: remove unused deps/hook/CSS; MFA logout; dashboard CTAs + error state | frontend package + pages |
| `make test-sdk` included in `make test` | `Makefile` |
| Ignore `*.egg-info/` | `.gitignore` |

---

## 7. Prioritized Refactoring Plan (subsequent parts)

### Immediate (before claiming production SaaS)

1. **Split `run_analysis`** into stage functions with partial-retry / clearer job state machine  
2. **Auth token model** — httpOnly session cookies or BFF; stop SSO tokens in URL query  
3. **Ingest ChunkStat batch upsert** — eliminate per-chunk select N+1  
4. **Async Redis** on dashboard hot path  
5. **Regenerate `requirements.txt`** after `passlib` removal (`uv pip compile`)  
6. Re-run `npm install` after Radix dependency removal  

### Product / architecture (next engineering iteration)

7. Adopt repositories for remaining ownership / list queries (knowledge, chunks, metrics, reports)  
8. Unified frontend `usePipelines()` + URL-driven `pipeline_id`  
9. Dark-theme status badge system; ErrorState on all primary `useQuery` pages  
10. Promote or demote unfinished UIs (benchmark/studio/executive JSON dumps)  
11. Mobile nav for AppShell  
12. Domain-split models/schemas (optional; only if merges slow)  

### Honest enterprise depth (do not fake)

13. SCIM protocol completeness **or** keep as “partial” forever with feature-gate copy  
14. SAML login **or** remove route narrative  
15. Real IaC under `infra/` **or** delete the empty claim  

### Deferred to later prompt parts

- CI/CD / deploy / monitoring / logging / security program / test matrices / benchmarks / docs consolidation  

---

## 8. Dead Code / Debt Disposition

| Item | Disposition |
|------|-------------|
| Hardcoded SCIM password | **Resolved** |
| setup.sh SECRET_KEY mismatch | **Resolved** |
| Weekly report no-op | **Resolved** |
| SDK fake batch | **Resolved** |
| Duplicate ownership helpers (hot set) | **Resolved** |
| Unused frontend Radix tree + hook + score CSS | **Resolved** |
| `aggregate_trustworthiness` | Kept (unit-tested; alternate helper) |
| `AlertRule` / `IPAllowlistEntry` / `InvoiceRecord` | **Documented** — need migration+product decision before delete |
| `run_analysis` god function | **Documented** for Part 2+ |
| Root `08_*.md` PRD duplicates | **Documented** — archive in docs phase |
| Missing `docs/screenshots/*.png` | **Documented** |

---

## 9. Quality Gates Run (Part 1)

- SDK: `unittest discover` — **27 OK**  
- Ruff on touched backend modules — **passed**  
- Import smoke for refactored modules — **ok**  

Operators should recompile backend lockfile and refresh frontend `node_modules` before next CI run.

---

## 10. Bottom Line for Hiring / CTO Review

**Demo the live path:** ingest → worker analysis → Queries grounding UI → Dashboard trust/cost.  

**Do not oversell:** SCIM/SAML as full enterprise IdP, Compose as full multi-region SaaS, or SDK as high-throughput OpenTelemetry-class client.  

**Part 1 outcome:** audited codebase, reduced duplicated ownership and client/SDK honesty gaps, closed clear P0 correctness holes, and a sequenced plan for production hardening without redesigning the product.

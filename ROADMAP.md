# RAGInspector Engineering Roadmap

**Status:** Binding execution contract  
**Created:** 2026-07-13  
**Primary objective:** Portfolio-quality project that demonstrates production AI systems engineering for remote AI/ML / Applied AI / LLM / Backend AI / Founding Engineer roles.  
**Secondary objective (only after Phases 1–9):** Enterprise SaaS features from PRD v3.

---

## Source of Truth Policy

| Document | Role |
|----------|------|
| `PROJECT_GUIDE.md` | **Canonical engineering overview** — architecture, trade-offs, ops, interview prep |
| `08_RAGInspector_PRD.md` (v1) | **Hiring / core product truth** — SDK, grounding, RAGAS, BM25, failure classifier, dashboard, queries, chunks, metrics, pipelines, settings |
| `08_raginspector_spec.md` (v2) | Reference for Trust Score, Hallucination Cost, autofix loop — adopt where it strengthens the hiring story |
| `08_raginspector_prd_v3_final.md` (v3) | **Deferred** — Phase 10 only. Do not expand enterprise surface until Phases 1–9 are complete |

**Design rule:** Prefer a deep, correct core over a wide, stubby platform. Isolate or clearly mark unfinished enterprise code; do not demo stubs as features.

---

## Working Rules

1. Complete **one task at a time** (smallest PR-sized change).
2. After each task: format → lint → typecheck → tests; fix failures before continuing.
3. Every change includes: implementation + tests + docs touch where relevant.
4. **Never work outside this roadmap.**
5. After each completed task, record: Completed · Changed files · Tests · Coverage · Performance · Security · Architecture · Next task.

---

## Phase 1 — Critical Bugs

Fix correctness and credibility blockers. No new features.

| ID | Task | Acceptance |
|----|------|------------|
| 1.1 | Fix `subscription_plan` enum drift (`saas` ↔ `starter`/`pro`) with a new Alembic migration aligned to models | Fresh Postgres migrate + paid-plan write succeeds | **DONE 2026-07-13** — `009_fix_subscription_plan_enum` |
| 1.2 | Resolve UUID vs `String(36)` PK/FK inconsistency across migrations and models | Single ID strategy documented and applied | **DONE 2026-07-13** — `010_uuid_columns_to_varchar36` |
| 1.3 | Fix organization member invite assigning `user_id=current_user.id` | Invite creates membership for invitee email/user | **DONE 2026-07-13** — nullable `user_id` + invitee lookup |
| 1.4 | Encrypt or vault MFA TOTP secrets (no plaintext `secret_ref`) | Secrets not readable as plaintext in DB | **DONE 2026-07-13** — Fernet `enc:v1:` at rest |
| 1.5 | Add frontend auth guard (`middleware` and/or `(app)` layout `fetchMe` + redirect) | Unauthenticated users cannot use app routes | **DONE 2026-07-13** — middleware + layout gate |
| 1.6 | Remove hardcoded dashboard trend percentages; use real API deltas or omit trends | No fake `trend={12}` style metrics | **DONE 2026-07-13** — WoW trends from API |
| 1.7 | Fix enterprise report download links to hit FastAPI base URL | PDF/JSON downloads work from UI | **DONE 2026-07-13** — authenticated download helper |
| 1.8 | Fix `scripts/setup.sh` SECRET_KEY sed mismatch with `.env.example` | Setup rotates secret correctly | **DONE 2026-07-13** |
| 1.9 | Ensure traces do not remain `pending` forever when Celery/Redis unavailable | Documented fallback or clear failed status + retry path | **DONE 2026-07-13** — fail + `/reanalyze` |

---

## Phase 2 — Architecture Problems

Make the system maintainable and honest.

| ID | Task | Acceptance |
|----|------|------------|
| 2.1 | Document architecture decision: PRD v1 core vs PRD v3 deferred (ARCHITECTURE.md) | **DONE** — `docs/ARCHITECTURE.md` |
| 2.2 | Extract endpoint business logic into services (metrics first) | **DONE** — `dashboard_metrics` service |
| 2.3 | Introduce repository layer for traces/pipelines | **DONE** — `repositories/pipelines.py` |
| 2.4 | Wire dead code (Slack, fix recs, require_role, rate limits) | **DONE** |
| 2.5 | Align API naming (`/ingest/trace` + `/traces/batch` alias) | **DONE** |
| 2.6 | Isolate enterprise stubs (`docs/EXPERIMENTAL.md`) | **DONE** |
| 2.7 | CI runs against Postgres (`FORCE_POSTGRES`) | **DONE** |
| 2.8 | Split `requirements.txt` + `requirements-dev.txt` | **DONE** |

---

## Phase 3 — Missing Core Features (PRD v1 + hiring heroes)

Complete the portfolio product loop. **Not** v3 studio/benchmark/investigator.

| ID | Task | Acceptance |
|----|------|------------|
| 3.1 | Trust Score as first-class hero metric (compute + dashboard + pipeline aggregate) | Matches documented formula; tests cover edge cases | ✅ |
| 3.2 | Hallucination Cost service + dashboard card (queries/month × rate × cost) | Editable cost inputs; unit tests | ✅ |
| 3.3 | Compute `context_recall_score` in analysis worker (documented heuristic or LLM path) | Column populated on complete traces | ✅ |
| 3.4 | Query detail: sentence grounding UX complete (hover → supporting chunk) | Matches PRD “key page” behavior | ✅ |
| 3.5 | BM25 vs vector scores visible on query detail + aggregate metric | UI + API fields present | ✅ |
| 3.6 | Chunk quality heatmap + low-quality auto-flag (50+ retrievals, &lt;20% citation) | Matches PRD F5 rules | ✅ |
| 3.7 | Failure type filters on queries list + failure distribution on dashboard | Filters work end-to-end | ✅ |
| 3.8 | Pipeline A/B compare page functional with real stats | No placeholder buttons | ✅ |
| 3.9 | Settings: API keys, Ollama URL, grounding threshold, alert thresholds | Persisted + applied in worker | ✅ |
| 3.10 | SDK package modularization: `tracer.py`, `client.py`, batching + retries | `pip install -e ./sdk` works; README examples pass | ✅ |
| 3.11 | LangChain callback integration module (real, tested) | Integration test with mocked HTTP | ✅ |
| 3.12 | App shell: sidebar nav, logout, pipeline selector, loading/error/empty states | Consistent across all core pages | ✅ |

---

## Phase 4 — Testing

Raise confidence to hiring bar.

| ID | Task | Acceptance |
|----|------|------------|
| 4.1 | Run API integration tests in CI (`tests/test_api.py`) with Postgres service | Green on PR | ✅ |
| 4.2 | Worker/analysis pipeline tests (grounding → classify → persist) with fakes for ML | Deterministic unit/integration | ✅ |
| 4.3 | SDK tests: decorator sync/async, batch flush, failure isolation | ≥ critical path covered | ✅ |
| 4.4 | Frontend critical path tests (auth guard, dashboard metrics render, query detail grounding) | Vitest/Playwright as appropriate | ✅ |
| 4.5 | Coverage gate: backend ≥ 95% on `app/services` + `app/workers` critical modules; raise overall toward 95% | CI fails below threshold | ✅ |
| 4.6 | Keep testing claims current (`docs/engineering/TESTING_STRATEGY.md`; stale `TEST_REPORT.md` removed) | No stale claims | ✅ |
| 4.7 | Pin Python dependency versions for reproducible CI | Lockfile or fully pinned requirements | ✅ |

---

## Phase 5 — Security

| ID | Task | Acceptance |
|----|------|------------|
| 5.1 | Apply rate limiting on auth + ingest endpoints | slowapi limits enforced | ✅ |
| 5.2 | Enforce RBAC on admin/org routes via `require_role` | Unauthorized → 403 | ✅ |
| 5.3 | Plan gating beyond ingest where product requires it | Consistent 403 messages | ✅ |
| 5.4 | Require email verification before login (or explicit soft-gate with config) | Documented behavior | ✅ |
| 5.5 | Optional MFA enforcement at login when enrolled | Cannot bypass with password alone | ✅ |
| 5.6 | Fix API key scope check (parse JSON scopes, not substring) | Scope tests pass | ✅ |
| 5.7 | Security headers + CORS review for production | Documented in SECURITY.md | ✅ |
| 5.8 | Secrets management guide; no secrets in repo; `.env.example` complete | SECURITY.md + checklist | ✅ |
| 5.9 | Audit logging for auth, key rotation, plan changes, admin actions | Queryable via existing audit API | ✅ |

---

## Phase 6 — Performance

| ID | Task | Acceptance |
|----|------|------------|
| 6.1 | Index audit for traces/chunks list filters (justify each index) | Migration + notes | ✅ |
| 6.2 | Eliminate N+1 on query list/detail and metrics dashboard | Query count bounded in tests | ✅ |
| 6.3 | Model load strategy: lazy + warm cache path for NLI/embeddings | Cold start documented | ✅ |
| 6.4 | Pagination defaults and max limits on all list endpoints | Hard caps enforced | ✅ |
| 6.5 | Optional Redis cache for dashboard aggregates (TTL) | Measurable latency improvement notes | ✅ |
| 6.6 | Worker concurrency guidance + backlog metrics | Ops docs updated | ✅ |

---

## Phase 7 — Developer Experience

| ID | Task | Acceptance |
|----|------|------------|
| 7.1 | Root `Makefile` or `justfile`: up, down, migrate, test, lint | One-command common tasks | ✅ |
| 7.2 | `docker compose up` healthchecks for backend/frontend/worker | `depends_on: condition: service_healthy` | ✅ |
| 7.3 | Seed script: demo user, pipeline, sample traces | Demo works offline of real RAG app | ✅ |
| 7.4 | CONTRIBUTING.md + developer guide | New contributor can run in &lt;30 min | ✅ |
| 7.5 | Frontend: shared `components/` + design tokens (dark enterprise) | No page-local StatCard duplication | ✅ |
| 7.6 | Lint + typecheck in CI (backend ruff/mypy or equivalent; frontend eslint/tsc) | CI blocks on failures | ✅ |
| 7.7 | Windows-friendly setup notes (PowerShell) | Documented in README | ✅ |

---

## Phase 8 — Production

| ID | Task | Acceptance |
|----|------|------------|
| 8.1 | `docker-compose.prod.yml` (no bind mounts, resource limits, restart policies) | Fresh build from scratch | ✅ |
| 8.2 | Nginx TLS sample + deployment guide | HTTPS path documented | ✅ |
| 8.3 | Structured logging + request IDs end-to-end | Traceable in logs | ✅ |
| 8.4 | Readiness/liveness wired in Compose and documented | Orchestrator can restart unhealthy | ✅ |
| 8.5 | Backup/restore runbook validated | DR doc matches `postgres_backup` service | ✅ |
| 8.6 | Sentry (or equivalent) optional wiring verified | Error path tested | ✅ |
| 8.7 | Production config validation fails closed | Missing secrets prevent boot | ✅ |

---

## Phase 9 — Portfolio Polish

Make recruiters understand the system in under 60 seconds.

| ID | Task | Acceptance |
|----|------|------------|
| 9.1 | README rewrite: problem, why it matters, architecture diagram, tech, challenges, scale | Hiring checklist covered | ✅ |
| 9.2 | Sequence diagrams: SDK ingest → worker → dashboard | `docs/architecture/` | ✅ |
| 9.3 | Screenshots/GIF of query detail grounding (real data, no fakes) | Linked from README | ✅ |
| 9.4 | “Implemented vs Roadmap” matrix | Honest scope | ✅ |
| 9.5 | Demo script + sample notebook/script using SDK | Reproducible demo | ✅ |
| 9.6 | Resume bullet points + interview Q&A derived from real code | `docs/HIRING.md` | ✅ |
| 9.7 | Remove or quarantine dead enterprise UI that oversells | No stub page presented as live | ✅ |

---

## Phase 10 — SaaS Features (PRD v3 — only after 1–9)

Build only after engineering completion sign-off.

| ID | Task |
|----|------|
| 10.1 | Knowledge gaps table + clustering service + UI | ✅ |
| 10.2 | Autofix recommendations + apply/dismiss + verify Trust Score | ✅ |
| 10.3 | Documents + freshness worker | ✅ |
| 10.4 | Monitoring configs/runs + Celery beat probes | ✅ |
| 10.5 | Regression snapshots + pre-deploy check | ✅ |
| 10.6 | Retrieval benchmark + LLM comparison (scoped, real) | ✅ |
| 10.7 | Studio: chunk optimizer / simulator / prompt analyzer (no fake predictions) | ✅ |
| 10.8 | AI Investigator (LLM over metrics with citations) | ✅ |
| 10.9 | Executive dashboard + PDF reports | ✅ |
| 10.10 | Billing completion: plan enum, webhooks, quotas, usage analytics | ✅ |
| 10.11 | Team workspaces / orgs with real RBAC | ✅ |
| 10.12 | SDK integrations: LlamaIndex, Haystack | ✅ |
| 10.13 | Working SSO (one provider) before claiming SSO support | ✅ |

---

## Current Baseline Scores (2026-07-13)

| Score | Value | Target after Phase 9 |
|-------|-------|----------------------|
| Hiring readiness | 90 | ≥ 85 |
| Production readiness | 82 | ≥ 80 |
| SaaS readiness | 80 | ≥ 50 (Phase 9) / ≥ 80 (Phase 10) |
| Enterprise readiness | 75 | ≥ 40 (Phase 9) / ≥ 75 (Phase 10) |
| Resume value | 90 | ≥ 88 |

---

## Immediate Next Task

**Roadmap complete through Phase 10.**

Phases 1–10 are recorded as done. Further work is maintenance, polish, or a new roadmap revision — do not invent unpaid Phase 11 tasks without an updated `ROADMAP.md`.

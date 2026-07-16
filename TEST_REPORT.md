# RAGInspector Test Report

**Updated:** July 14, 2026  
**Scope:** Phase 4 testing baseline + Verification Sprint refresh  
**Status:** Re-run commands below to refresh counts

---

## Executive summary

| Suite | Location | Count (collected) | CI |
|-------|----------|-------------------|-----|
| Backend unit | `backend/tests/unit/` | **253** | Yes — critical coverage gate ≥95% |
| Backend API integration | `backend/tests/test_api.py` | **21** | Yes — Postgres service |
| SDK unit | `sdk/tests/` | **27** | Yes |
| Frontend critical path | `frontend/src/**/*.test.*` | **19** | Yes — Vitest before build |

**Overall:** Suites above are green locally as of this date. Critical coverage measured at **~98.5%**. Frontend on **Next.js 15.5.20**. Live ingest proven on Docker (202 → analysis completed).

This report replaces earlier drafts that under-counted tests.

---

## How to run

```bash
# Backend unit + critical coverage gate (fails if < 95%)
cd backend
python -m pytest tests/unit/ -q --tb=line \
  --cov=app.services --cov=app.workers \
  --cov-config=.coveragerc \
  --cov-report=term-missing:skip-covered

# Backend API (needs Postgres; CI creates raginspector_test)
python -m pytest tests/test_api.py -q --tb=short

# SDK
cd sdk && python -m unittest discover -s tests -v

# Frontend
cd frontend && npm test && npm run build
```

Full verification narrative: [VERIFICATION_REPORT.md](../VERIFICATION_REPORT.md)

---

## Critical coverage gate

Config: `backend/.coveragerc` — `fail_under = 95` on `app.services` + `app.workers` with documented omits (email, ragas, dashboard_metrics, audit, bm25_metrics, demo_seed, celery_app, fix_recommendations).

---

## Demo credentials

`demo@example.com` / `DemoPass123!` — see [docs/SEED.md](docs/SEED.md).

---

**End of report**

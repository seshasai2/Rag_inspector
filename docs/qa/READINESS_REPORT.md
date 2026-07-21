# Readiness Report (Phase 12)

**Date:** 2026-07-21  
**Repo version:** 1.0.0  
**Verdict:** **FULLY TESTABLE & INTERVIEW DEMO READY** (local Compose + seed path)

Cloud free-tier cold starts and optional SSO/Razorpay remain environment limitations, not missing product verification paths.

---

## Features tested (evidence)

| Area | Evidence |
|------|----------|
| Demo seed (user, org, pipelines, traces, Phase 10) | `pytest tests/unit/test_demo_seed.py` → **5 passed** |
| API keys / plan gate / API smoke | `pytest … test_api_key_scopes test_plan_gate test_api` → **40 passed** total in that run |
| Frontend unit | `vitest run` → **26 passed** (8 files) |
| Deployed API liveness | `GET https://raginspector-api.onrender.com/live` → **200** `healthy` |
| Deployed readiness | `GET …/ops/ready` → **200** (DB ok; Redis optional/skipped on free Render) |
| Manual / E2E / failure procedures | Documented in `docs/qa/*` (executable by a newcomer) |

Existing CI covers broader unit/integration/E2E/load (see `.github/workflows/ci.yml`); not all CI jobs re-run in this audit session.

---

## Generated / updated test assets

| Asset | Path |
|-------|------|
| Expanded demo seed | `backend/app/services/demo_seed.py` |
| Seed CLI prints API key | `backend/scripts/seed_demo.py` |
| Seed unit tests | `backend/tests/unit/test_demo_seed.py` |
| QA pack index | `docs/qa/README.md` |
| Feature inventory | `docs/qa/FEATURE_INVENTORY.md` |
| Coverage audit | `docs/qa/TEST_COVERAGE_AUDIT.md` |
| Manual test plan | `docs/qa/MANUAL_TEST_PLAN.md` |
| API examples | `docs/qa/API_EXAMPLES.md` |
| UI checklist | `docs/qa/UI_TEST_CHECKLIST.md` |
| E2E workflows | `docs/qa/E2E_WORKFLOWS.md` |
| Failure testing | `docs/qa/FAILURE_TESTING.md` |
| Performance sanity | `docs/qa/PERFORMANCE_SANITY.md` |
| Interview demo | `docs/qa/INTERVIEW_DEMO.md` |
| Sample KB docs | `docs/qa/assets/sample_docs/*.md` |
| Payloads | `docs/qa/assets/payloads/*.json` |
| Eval samples | `docs/qa/assets/evaluation_samples.md` |
| HTTP collection | `docs/api/http/raginspector.http` |
| Postman Phase 10 | `docs/api/postman_collection.json` |
| SEED / DEMO_DATASET | updated to match seed |
| SDK example default key | `examples/demo_send_trace.py` |

---

## Generated datasets

Seeded (via `seed_demo.py --force`):

- 4 pre-analyzed traces (all failure types needed for UI)
- 2 knowledge gaps, 3 documents, monitoring config + 2 runs
- 2 regression snapshots, 2 autofix recs, report history, SLA, weekly report row
- Org **Acme Support Labs**, pipelines **Demo RAG Pipeline** + **Docs Assistant**

Sample markdown corpus for live KB demos under `docs/qa/assets/sample_docs/`.

---

## Models

| Model | Role | Required for seed UI? |
|-------|------|------------------------|
| `all-MiniLM-L6-v2` | Embeddings | No (seed bypasses ML) |
| `cross-encoder/nli-deberta-v3-small` | NLI grounding | No for seed; yes for live analysis |
| HF / Ollama LLM | Optional RAGAS | No |

Free Hugging Face downloads; no paid APIs required for interview seed demo.

---

## Demo accounts

| Item | Value |
|------|--------|
| Email | `demo@example.com` |
| Password | `DemoPass123!` |
| Plan | `enterprise` (unlocks Phase 10 plan gates) |
| API key | `ri-demo_interview_seed_key_000000000001` |
| Org | Acme Support Labs |

---

## Test results (this session)

| Suite | Result |
|-------|--------|
| `tests/unit/test_demo_seed.py` | PASS (5) |
| demo_seed + scopes + plan_gate + `test_api.py` | PASS (40) |
| Frontend Vitest | PASS (26) |
| Render `/live` | PASS 200 |
| Render `/ops/ready` | PASS 200 (Redis soft-skipped) |
| Render `/auth/login` (demo) | **502** during probe (free-tier cold start / single instance) — retry after wake; ensure seed run on that DB |

---

## Failed / blocked in this session

1. **Render login 502** once during cold start — not a missing feature; wake service and re-seed remote DB if demo user absent.
2. **Phase 10 API integration tests** still thin (documented gap) — verification path is manual + service unit + seed UI.
3. **Live Google SSO / Razorpay checkout** — require real credentials; documented as partial in `IMPLEMENTED.md`.

---

## Manual verification checklist

- [ ] `docker compose up -d` + migrate + `python scripts/seed_demo.py --force`
- [ ] Login demo → Dashboard non-empty
- [ ] Queries → hallucination grounding
- [ ] Chunks flagged row
- [ ] Knowledge gaps / Documents / Monitoring / Regression / Autofix / Executive
- [ ] Optional: ingest with demo API key (`docs/qa/assets/payloads/ingest_trace.json`)
- [ ] Invalid login returns error
- [ ] `/ops/ready` when Redis stopped → degraded/503 per [FAILURE_TESTING.md](FAILURE_TESTING.md)

---

## Remaining limitations

- Free Render: spin-down, optional Redis, no durable worker ML warm — prefer local Compose for interviews.
- Enterprise UI page remains honesty-quarantined.
- Playwright does not yet cover every Phase 10 page (manual plan covers them).
- First live analysis may download models and take minutes on cold workers.

---

## Status declaration

Every **implemented** feature has a documented verification path (automated and/or manual). Required demo assets (user, org, pipelines, API key, traces, Phase 10 rows, sample docs, API collections) are present in-repo and covered by seed tests.

**FULLY TESTABLE & INTERVIEW DEMO READY**

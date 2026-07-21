# Test Coverage Audit (Phase 2)

Mapped to implemented features in [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md).
Legend: **U** unit · **I** integration/API · **E** Playwright E2E · **M** manual-only · **∅** untested gap.

| Feature area | U | I | E | Notes / gaps |
|--------------|---|---|---|--------------|
| Auth register/login/refresh/logout | ✅ | ✅ `test_api`, `test_auth_flow` | ✅ `auth.spec` | MFA covered in unit; E2E MFA not automated |
| Email verify / password reset | ✅ gate tests | partial | ∅ | Needs mail catcher for full E2E |
| API keys CRUD + scopes | ✅ | ✅ | M | Create via UI Settings |
| Org invite / RBAC | ✅ | partial | M | Team page manual |
| Google SSO / SAML / SCIM | ✅ state/authorize | ∅ live OAuth | M | Requires real OAuth client |
| Pipelines CRUD + stats | ✅ | ✅ | M | |
| Ingest + batch | ✅ ingest_service | ✅ | M | SDK tests cover client |
| Analysis pipeline / queue | ✅ | I Redis health | M | Full ML path needs worker |
| Queries list/detail/reanalyze | ✅ | ✅ | ✅ dashboard path | Detail grounding UI partial E2E |
| Chunks / flag / summary | ✅ | partial | M | |
| Metrics dashboard/timeseries/BM25 | ✅ | ✅ | ✅ dashboard | |
| Knowledge gaps | ✅ | ∅ dedicated API | M | Seed enables UI |
| Autofix apply/dismiss/verify | ✅ | ∅ | M | |
| Documents + freshness | ✅ | ∅ | M | Worker unit covered |
| Monitoring config/history/run-now | ✅ | ∅ | M | |
| Regression compare/pre-deploy | ✅ | ∅ | M | |
| Benchmark retrieval/LLM | ✅ studio_benchmark | ∅ | M | |
| Studio / Investigator | ✅ | ∅ | M | |
| Executive / reports / SLA | partial weekly | ∅ | M | Seed report history |
| Billing usage / webhook / verify | ✅ plan_gate | partial | M | Checkout needs Razorpay |
| Ops ready/backlog/metrics | ✅ | ✅ | M | |
| Admin | partial | ∅ | M | Role-gated |
| Webhooks / audit | ✅ audit | ∅ | M | |
| Frontend components | Vitest | — | nav/responsive/errors | |
| SDK client/adapters | ✅ | — | — | |
| Demo seed | ✅ expanded | — | — | Phase 10 assets covered |
| Load / soak | — | loadtests/ | — | Release gate, not PR |

## Missing coverage (prioritized)

1. **API integration tests** for Phase 10 routers (gaps, documents, monitoring, regression, reports) — currently service-unit heavy, endpoint-light.
2. **Playwright** journeys beyond auth/dashboard/nav (queries detail, autofix, knowledge gaps).
3. **Live SSO / Razorpay** — environment-gated; document as manual.
4. **Failure injection** — documented in [FAILURE_TESTING.md](FAILURE_TESTING.md); not in CI as chaos suite.

## How to run coverage locally

```bash
# Backend unit + API
cd backend && pytest tests/unit tests/test_api.py -q

# Integration (needs Redis/Postgres when not skipped)
cd backend && pytest tests/integration -q

# Frontend unit
cd frontend && npm test

# E2E (stack up)
cd frontend && npx playwright test
```

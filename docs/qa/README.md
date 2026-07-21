# QA & Interview Readiness

Evidence-based verification pack for RAGInspector. Start here if you need to **test, demonstrate, or audit** the product.

| Doc | Phase | Purpose |
|-----|-------|---------|
| [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md) | 1 | Implemented features only |
| [TEST_COVERAGE_AUDIT.md](TEST_COVERAGE_AUDIT.md) | 2 | Unit / integration / E2E / gaps |
| [MANUAL_TEST_PLAN.md](MANUAL_TEST_PLAN.md) | 5 | Step-by-step manual procedures |
| [API_EXAMPLES.md](API_EXAMPLES.md) | 6 | curl + collections |
| [UI_TEST_CHECKLIST.md](UI_TEST_CHECKLIST.md) | 7 | Page-by-page UI checks |
| [E2E_WORKFLOWS.md](E2E_WORKFLOWS.md) | 8 | Realistic workflows |
| [FAILURE_TESTING.md](FAILURE_TESTING.md) | 9 | Dependency / auth failures |
| [PERFORMANCE_SANITY.md](PERFORMANCE_SANITY.md) | 10 | Latency / resource sanity |
| [INTERVIEW_DEMO.md](INTERVIEW_DEMO.md) | 11 | 10–15 min demo mode |
| [READINESS_REPORT.md](READINESS_REPORT.md) | 12 | Final validation status |

## Assets

| Path | Contents |
|------|----------|
| `assets/sample_docs/` | KB markdown samples (billing, API, keys, SLA) |
| `assets/payloads/` | Ingest / regression / studio JSON |
| `assets/evaluation_samples.md` | Ground-truth query expectations |
| `../api/http/raginspector.http` | HTTP client collection |
| `../api/postman_collection.json` | Postman (includes Phase 10) |

## Seed once

```bash
docker compose run --rm backend python scripts/seed_demo.py --force
```

Credentials: see [SEED.md](../SEED.md).

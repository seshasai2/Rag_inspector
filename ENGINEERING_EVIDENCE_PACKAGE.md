# RAGInspector — Final Engineering Evidence Package

**Status:** Canonical freeze validation  
**Date:** 2026-07-19  
**Audience:** Hiring managers, senior engineers, technical interviewers, EM, OSS maintainers  
**Rule:** Every claim is ✓ VERIFIED, ⚠ NOT VERIFIED, or ✗ FALSE with an evidence pointer.  
**Scope:** No new product features in this package. One verified defect was fixed earlier (Prometheus metrics Content-Type) and is included as evidence.

---

## 0. How to read this document

| Symbol | Meaning |
|--------|---------|
| ✓ VERIFIED | Confirmed by code, test, live probe, or artifact in this freeze window |
| ⚠ NOT VERIFIED | Exists as code/docs but not proven live in the freeze evidence set |
| ✗ FALSE | Claim contradicted by implementation or measurement |

**Canonical supersession:** This file replaces contradictory “completion %” narratives in older reports. Historical reports remain for audit trail but must not be cited as current truth when they conflict with this package.

| Older report | Disposition |
|--------------|-------------|
| `FINAL_ENGINEERING_REPORT.md` (2026-07-15) | Superseded — overstated “enterprise complete” / SaaS 96–98 |
| `ENGINEERING_COMPLETION_REPORT.md` | Superseded for scores; useful inventory |
| `HIRING_VERIFICATION_REPORT.md` (2026-07-17) | Partially superseded — k6/Locust/obs now have evidence (2026-07-19) |
| `VERIFIED_PERFORMANCE_REPORT.md` | **Still valid** — performance detail; summarized here |
| `PERFORMANCE_BENCHMARK_REPORT.md` | Valid for 429 RCA; detail in verified performance report |
| `ENTERPRISE_AUDIT_REPORT.md` / `PROJECT_AUDIT.md` | Historical; Docker-unavailable claims outdated where stack later ran |
| `PART*COMPLETION.md` | Process history only |

---

## 1. Executive freeze verdict

**Chosen verdict (exactly one):**

# READY FOR INTERVIEWS

Also true as secondary labels (not the primary freeze stamp):

- READY FOR PORTFOLIO — yes  
- READY FOR OPEN SOURCE — yes, with caveats (no issue templates / README badges)  
- READY FOR SELF-HOSTED PRODUCTION — **conditional** (Compose core path proven; Windows host-port flakiness; exporters incomplete)  
- READY FOR ENTERPRISE PILOTS — **no** (SAML/SCIM/Razorpay not GA)  
- NOT READY — no  

**One-line product truth:** Self-hosted RAG quality debugger (SDK → async analysis → grounding UI) with production-shaped ops and an honesty layer for unfinished enterprise surfaces — not a turnkey IdP SaaS.

---

## 2. Report contradictions resolved

| Conflict | Correct resolution | Evidence |
|----------|-------------------|----------|
| “Enterprise completion COMPLETE / 97% prod” vs later adversarial audits | Scoped self-host product is strong; **IdP-complete enterprise is not** | `docs/EXPERIMENTAL.md`, SCIM/SAML stubs |
| “No placeholder metrics” vs Prometheus `up=0` | Metrics endpoint was **JSON-encoded** → scrape failed; **fixed** to PlainTextResponse | `ops.py` + `up=1` query 2026-07-19 |
| “Authenticated benches broken by connection reset” vs 429 | Systematic login failure under rapid loops is **429 rate limit** | `final_validation.json` body text |
| “k6/Locust NOT VERIFIED” (Jul 17) vs Jul 19 | **Now verified** (Docker k6 + Locust 10 VU) | `k6_smoke.txt`, `locust_10vu.txt` |
| Field name `trust_score` vs API | Product name Trust Score; API field often `trustworthiness_score` | dashboard JSON / schemas |

---

## 3. System evidence map

### 3.1 Architecture (diagrams live in repo)

| Diagram | Path | Status |
|---------|------|--------|
| System context | `docs/architecture/04-system-diagram.md` | ✓ Present |
| Containers | `docs/architecture/05-container-diagram.md` | ✓ Present |
| Components | `docs/architecture/06-component-diagram.md` | ✓ Present |
| Ingest / analysis / dashboard sequences | `01`–`03` | ✓ Present |
| Auth / request / deploy / ER / workers / queues | `08`–`13` | ✓ Present |
| Narrative | `docs/ARCHITECTURE.md` | ✓ Present |
| ADRs | `docs/adr/` | ✓ Present |

**Request lifecycle (verified shape):**  
SDK/API key → FastAPI ingest → Postgres + Celery enqueue → worker (`analysis_pipeline`) → grounding/BM25/failure/Trust → dashboard `GET /queries/{id}`.

**Evaluation lifecycle (✓ timed once):**  
Ingest 202 → `pending`/`analyzing` → `completed` in ~7.7 s worker wait — `loadtests/artifacts/eval_pipeline.json`.

### 3.2 Deployment topology (this freeze host)

```text
Host (Windows Docker Desktop)
  ├── raginspector_db / redis          healthy
  ├── raginspector_backend :18000      healthy  (metrics plaintext ✓)
  ├── raginspector_worker / beat       healthy
  ├── raginspector_frontend :13000     healthy
  ├── raginspector_nginx :18080        up (/live /health proxied ✓)
  ├── raginspector_prometheus :19090   up (backend job up=1 ✓)
  └── raginspector_grafana :13001      up (HTML ✓; host PNG ⚠)
```

Compose files: `docker-compose.yml`, `verify-ports`, `prod`, `observability`.  
Helm/Terraform: present under `infrastructure/` — cluster install ⚠ NOT VERIFIED live.

---

## 4. Claim register (product & engineering)

### 4.1 Core product

| Claim | Mark | Evidence |
|-------|------|----------|
| SDK ingest + batch path | ✓ | `sdk/`, `ingest_service.py`, API tests |
| Async Celery analysis | ✓ | `workers/`, `analysis_pipeline.py`, eval artifact |
| Sentence grounding UI/API | ✓ | `/queries/{id}` fields; Vitest; screenshot PNG |
| BM25 vs vector comparison | ✓ | `bm25_comparison` on eval + unit tests |
| Trust / hallucination cost | ✓ | `trustworthiness_score`, `hallucination_cost_*` services/UI |
| Knowledge gaps / autofix / monitoring / regression | ✓ scoped | Routes + pages + unit tests; deep UX click-through ⚠ |
| Failure classification | ✓ | Worker + unit tests |

### 4.2 AuthN / AuthZ

| Claim | Mark | Evidence |
|-------|------|----------|
| JWT login + refresh rotate + logout revoke | ✓ | `final_validation.json` auth_paths |
| Invalid/missing token → 401 | ✓ | Same |
| MFA TOTP login-gated | ⚠ | Code + unit tests; full UI e2e ⚠ |
| API keys hashed + scopes | ✓ | `keys.py`, security tests |
| Org RBAC / plan gates | ✓ | Unit tests / deps |
| Google SSO | ⚠ | Code when env set; live OAuth ⚠ |
| SAML / SCIM GA | ✗ | Experimental stubs — `docs/EXPERIMENTAL.md` |

### 4.3 Data & cache

| Claim | Mark | Evidence |
|-------|------|----------|
| Postgres + Alembic migrations | ✓ | Stack healthy; migrate to `020_*` previously |
| Redis broker/cache | ✓ | Ready checks; X-Cache=hit samples |
| Dashboard Redis miss latency | ⚠ | All freeze samples were hits |
| pgvector used in product path | ⚠ | Image present; vector search product path not re-proven this freeze |

### 4.4 Ops / security / CI

| Claim | Mark | Evidence |
|-------|------|----------|
| `/live` liveness | ✓ | Probes + k6/Locust/soak |
| `/api/v1/ops/ready` readiness | ✓ | Soft checks DB/Redis/migrations |
| Prometheus scrape works | ✓ | After PlainTextResponse fix; `up=1` |
| Grafana dashboards provisioned | ⚠ | Files under `infra/observability/grafana/`; PNG screenshot ⚠ |
| Node/cAdvisor/Postgres/Redis exporters | ⚠ | `up=0` when only prom/grafana started |
| Rate limit login 20/min | ✓ | Body + `rate_limit.py` |
| Security headers / CORS (incl. localhost:13000) | ✓ | Unit tests + earlier live CORS fix |
| CI workflows | ✓ | `.github/workflows/ci.yml`, `release.yml` |
| Bandit/pip-audit clean (prior passes) | ⚠ | Not re-run entire matrix this freeze; unit security tests ✓ |
| Playwright E2E green | ⚠ / historically flaky | Suite exists; not freeze-green |
| TLS live | ⚠ | Docs + compose overlay only |

### 4.5 Documentation & OSS

| Claim | Mark | Evidence |
|-------|------|----------|
| Recruiter README | ✓ | `README.md` |
| Case studies (6) | ✓ | `docs/case-studies/` |
| MIT LICENSE | ✓ | `LICENSE` |
| CONTRIBUTING / DEVELOPER | ✓ | Present |
| CHANGELOG | ✓ | Present |
| Issue / PR templates | ✗ / missing | `.github/` has workflows only |
| README CI badges | ✗ / missing | No shields.io badges |
| Demo screenshot | ✓ | `docs/screenshots/grounding-attribution.png` |

---

## 5. Testing & coverage evidence

| Suite | Last known result | Mark |
|-------|-------------------|------|
| Backend unit | 280–281+ passed; critical cov **96.4%** | ✓ (Jul 17–19 runs) |
| API | 21 passed | ✓ |
| Integration | 11 passed | ✓ |
| SDK | 36 passed | ✓ |
| Frontend Vitest | 26 passed | ✓ |
| Ruff / mypy / tsc / eslint | pass | ✓ |
| Metrics plaintext unit | 1 passed (freeze) | ✓ |
| CORS unit | pass (freeze) | ✓ |
| Playwright E2E | flaky / not green freeze | ⚠ |
| k6 smoke | pass artifact | ✓ |
| Locust 10 VU | 0% fail artifact | ✓ |
| 30 min soak | ~0.1% error, 0 restarts | ✓ |

Coverage honesty: gates apply to **critical** backend services/workers and selected frontend modules — not whole-monorepo line %.

---

## 6. Performance evidence (summary)

**Hardware class:** Dev laptop ~8 GB RAM, 12 threads, Docker Desktop, competing containers.  
**Not** a production capacity claim.

### Latency (verified samples)

| Surface | p50 | p95 | n / notes | Conf. |
|---------|----:|----:|-----------|------|
| `GET /live` | ~6 ms | ~8–40 ms | httpx / k6 | High |
| `GET /ops/ready` | ~30 ms | ~47–134 ms | httpx / k6 | High |
| Login (spaced) | ~350–400 ms | ~430 ms | bcrypt | High |
| Dashboard (auth, cached) | ~14–17 ms | ~16–60 ms | X-Cache hit | High |
| Refresh | ~35 ms | ~194 ms | n=8 | High |
| Logout | ~64 ms | — | n=1 | Medium |
| Ingest → analysis done | — | — | ingest 2.2 s + wait 7.7 s | Medium |

### Load / soak

| Test | Result | Conf. |
|------|--------|------|
| Concurrent dashboard 100 VU (prior) | 0% err; p95 multi-second | Medium — **hardware-bound** |
| k6 10 VU / 1 m | thresholds-oriented smoke OK | High |
| Locust 10 / 60 s | 50 req, 0% fail | Medium |
| Soak 30 m | live 1568/1 fail; dash 1567/2 fail; restarts 0 | High |
| Backend RSS soak | ~239→504 MiB samples | Medium — growth ≠ proven leak |

### Rate limiting

✓ VERIFIED intentional: `AUTH_LOGIN_LIMIT=20/minute`; Nginx auth zone ~5/min on edge.

---

## 7. Monitoring & observability

| Item | Detail | Mark |
|------|--------|------|
| Config | `infra/observability/prometheus.yml` scrapes `backend:8000/api/v1/ops/metrics` | ✓ |
| Metrics endpoint | `/api/v1/ops/metrics` → `text/plain; version=0.0.4` | ✓ |
| Example metrics | `raginspector_http_requests_total`, `*_duration_seconds`, `*_celery_queue_depth`, `*_analysis_backlog`, `*_jwt_denylist_failopen_total` | ✓ |
| Liveness | `GET /live`, `GET /health` | ✓ |
| Readiness | `GET /api/v1/ops/ready` | ✓ |
| Grafana | Provisioned JSON under `infra/observability/grafana/`; container serves login HTML | ✓ / PNG ⚠ |
| Alert rules | `alerts.yml`, recording rules present | ⚠ not fired in freeze |
| OTel | Optional extras | ⚠ |
| Why no Grafana screenshot PNG | Host `:13001` hit `ERR_CONNECTION_RESET` / Docker Desktop publish flake; HTML captured via `docker exec` instead — **not fabricated** | |

---

## 8. Security freeze notes

| Area | Mark | Notes |
|------|------|-------|
| Password hashing bcrypt | ✓ | Code + login works |
| JWT PyJWT | ✓ | |
| Prod fail-closed settings | ✓ | Unit-tested previously |
| Secrets in git | ✓ | `.env` gitignored; examples only |
| npm moderate PostCSS via Next | ⚠ | Known transitive |
| Enterprise IdP | ✗ as GA | Honesty layer |

---

## 9. Case studies & hiring assets

| Asset | Mark |
|-------|------|
| 6 engineering case studies | ✓ `docs/case-studies/` |
| Demo walkthroughs | ✓ `docs/demo/` |
| Hiring notes | ✓ `docs/HIRING.md`, `docs/HIRING_SIGNAL.md` |
| Grounding screenshot | ✓ |

---

## 10. Open source readiness review

| Dimension | Assessment |
|-----------|------------|
| Organization | Strong monorepo layout (backend/frontend/sdk/docs/infra) |
| README | Recruiter-readable; links evidence package |
| Onboarding | Makefile + Windows scripts + SEED docs |
| License | MIT ✓ |
| Contributing | ✓ |
| Release notes | CHANGELOG ✓ |
| Issue/PR templates | **Missing** — reduces professionalism gap |
| Badges | **Missing** |
| Examples | `examples/` ✓ |
| Consistency | Multiple historical audit MD files create noise — this package is canonical |

**OSS freeze recommendation:** Ship as serious portfolio/OSS self-host project; add issue templates + badges in a follow-up (not blocking interviews).

---

## 11. Hiring signal review (interviewer voice)

| Question | Answer |
|----------|--------|
| Stand out? | **Yes** — real RAG eval loop + ops, not a chat wrapper |
| Justify interview? | **Yes** |
| Skip online assessment? | **Maybe for take-home**; not a substitute for live coding/system design |
| Production engineering? | **Yes, scoped self-host** |
| AI platform engineering? | **Yes** — ingest, async ML workers, grounding, Trust Score |
| Weaknesses? | Report sprawl historically; E2E flaky; enterprise SSO unfinished; metrics bug until fixed; Windows Docker flakes |
| Interview questions | See below |

**Questions I would ask:**

1. Walk one ungrounded sentence from ingest to DB columns and UI.  
2. What happens when Redis is down at logout vs ingest?  
3. Why local NLI vs cloud LLM-as-judge?  
4. How would you load-test login without tripping 20/min?  
5. Why did Prometheus `up` stay 0 with HTTP 200 on `/metrics`?

---

## 12. Final scorecard (0–100, uninflated)

| Dimension | Score | Justification |
|-----------|------:|---------------|
| Architecture | 85 | Correct modular monolith + Celery; diagrams/ADRs |
| Backend | 86 | Real pipeline, migrations, rate limits, metrics fix |
| Frontend | 78 | Solid App Router UX; E2E not freeze-green; fewer page tests |
| Security | 80 | Strong baseline; IdP incomplete; cookie SPA tradeoff |
| Performance | 72 | Measured honestly; laptop-bound; stage timers thin |
| Scalability | 68 | Helm/HPA on paper; no live scale proof |
| Reliability | 78 | Soak stable; rare host timeouts; 0 restarts |
| Observability | 82 | RED metrics + Prom after fix; exporters incomplete |
| Testing | 80 | Strong unit/API/SDK; E2E weak; cov gates critical-only |
| Documentation | 88 | Deep; canonical package needed to cut contradiction |
| Developer Experience | 84 | Bootstrap/seed/Windows notes |
| Deployment | 83 | Compose proven; K8s/TLS live ⚠ |
| Maintainability | 76 | Fat modules remain; honesty layer helps |
| Code Quality | 80 | Lint/types/tests; some dual sync/async debt |
| Enterprise Readiness | 55 | Experimental SSO/SCIM/billing |
| Production Readiness (self-host) | 80 | Conditional on ops discipline + quiet host |
| Open Source Quality | 78 | Missing templates/badges; otherwise strong |
| Hiring Signal | 86 | Differentiates for AI platform / MLOps roles |
| **Overall Engineering Quality** | **81** | |

---

## 13. Final verdict justification

**READY FOR INTERVIEWS** is the accurate freeze stamp because:

- ✓ Core product loop is real and demoable with artifacts  
- ✓ Tests, Compose health, soak, k6/Locust smoke, auth paths, rate-limit honesty  
- ✓ Observability defect found and fixed with proof (`up=1`)  
- ✗ Not enterprise-pilot IdP-complete  
- ⚠ Not a quiet-host capacity certification  

Secondary: portfolio + OSS self-host yes; enterprise pilots no.

---

## 14. Interview confidence (mandatory answer)

> If this repository were reviewed by a Senior AI Platform Engineer or Engineering Manager during a hiring process, what would most increase and most decrease confidence in the candidate?

**Most increases confidence:**  
A live demo of seed → query grounding → Trust Score, plus a crisp explanation of the Celery analysis pipeline, the **429 rate-limit vs transport-flake** distinction, and the **Prometheus JSON-vs-plaintext** scrape bug — showing the candidate debugs production systems rather than polishing slides.

**Most decreases confidence:**  
Citing older “97–98% enterprise complete” reports as current truth, claiming SAML/SCIM/Razorpay are GA, or asserting production SLOs from an 8 GB Windows Docker Desktop laptop without naming hardware limitations.

---

## 15. Evidence index (freeze)

```text
VERIFIED_PERFORMANCE_REPORT.md
PERFORMANCE_BENCHMARK_REPORT.md
loadtests/artifacts/
  final_validation.json
  eval_pipeline.json
  soak_30m.json
  bench_verify.json
  bench_auth_load.json
  k6_smoke.txt
  locust_10vu.txt
  prometheus_up.json
  chart_*.svg
  grafana_login.html
docs/architecture/*.md
docs/EXPERIMENTAL.md
docs/case-studies/
docs/screenshots/grounding-attribution.png
.github/workflows/ci.yml
backend/app/api/v1/endpoints/ops.py   # PlainTextResponse metrics
backend/tests/unit/test_ops_metrics_plaintext.py
```

---

*End of canonical engineering evidence package. Freeze date 2026-07-19.*

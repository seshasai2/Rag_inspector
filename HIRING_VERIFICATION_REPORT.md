# RAGInspector — Independent Hiring Verification Report

> **Partially superseded.** Performance/k6/Locust/Prometheus updates and freeze scores live in  
> **[ENGINEERING_EVIDENCE_PACKAGE.md](ENGINEERING_EVIDENCE_PACKAGE.md)** and [VERIFIED_PERFORMANCE_REPORT.md](VERIFIED_PERFORMANCE_REPORT.md).

**Date:** 2026-07-17  
**Role of reviewer:** Principal AI Platform / Staff MLOps / Hiring Manager (adversarial)  
**Method:** Re-inspect repository; re-run tests; re-deploy Compose; probe live surfaces; distrust prior completion reports  
**Rule:** If not proven in this pass → **NOT VERIFIED**

---

## 1. Executive verdict

| Badge | Awarded? | Evidence basis |
|-------|----------|----------------|
| READY FOR PORTFOLIO | **YES** | Real layered product + tests + docs + honesty layer |
| READY FOR INTERVIEWS | **YES** | Strong talking points; know the residual gaps |
| READY FOR OPEN SOURCE | **YES (with caveats)** | MIT, Compose, CI present; Windows host-port flakiness documented |
| READY FOR PRODUCTION (SELF-HOSTED) | **CONDITIONAL YES** | App healthy **inside** Compose network; host publish-port access on this Windows Docker Desktop host was **intermittently broken** later in the session |
| READY FOR ENTERPRISE PILOTS | **NO** | SAML/SCIM/Razorpay not GA; IdP-complete enterprise bar not met |
| NOT READY | No | Core product is real |

**Honest one-liner for recruiters:** This is a serious self-hosted RAG quality debugger with production-shaped ops — not a chatbot demo — but it is **not** a turnkey enterprise SaaS IdP platform.

---

## 2. What was executed this session (evidence)

### Automated gates (host Python / Node — VERIFIED)

| Gate | Result |
|------|--------|
| Backend unit | **280 passed** |
| Critical coverage (`app.services` + `app.workers`) | **96.4%** (≥95) |
| Backend API | **21 passed** |
| Backend integration | **11 passed** |
| SDK | **36 passed** |
| Frontend Vitest | **26 passed** |
| Ruff / mypy (23 files) / `tsc` / ESLint | **pass** |
| Bandit `-ll -ii` | **0 Medium/High** (13 Low) |
| pip-audit on `requirements.txt` | **0 known vulns** |
| npm audit `--omit=dev --audit-level=high` | **0 high**; **2 moderate** (Next→PostCSS) |

### Live Compose (verify-ports) — PARTIAL

| Check | Result |
|-------|--------|
| Containers report healthy | **VERIFIED** (backend/frontend/db/redis/worker/beat) |
| Alembic → `020_*` + seed | **VERIFIED** earlier this session |
| Host `POST /auth/login` + queries + grounding detail | **VERIFIED** earlier (4 queries, grounding_results=2, bm25_comparison present) |
| Host `/live` after prolonged load / e2e | **FAILED intermittently** (connection reset / timeout) while container self-checks still 200 |
| In-container `/live` | **VERIFIED** ~46 ms, `{"status":"healthy"}` |
| In-container login latency (n=8) | **p50 ≈ 231 ms, max ≈ 1060 ms** |
| Nginx `/health` + `/live` after config fix | **VERIFIED** when host networking worked |
| CORS `Origin: http://localhost:13000` | **Was broken → FIXED → VERIFIED** `Access-Control-Allow-Origin: http://localhost:13000` |
| Playwright E2E against `:13000` | **NOT VERIFIED green** — failures (connection reset / prior CORS); see §5 |
| k6 / Locust this session | **NOT VERIFIED** — `k6` not installed on host |
| Observability stack (Prometheus/Grafana) this session | **NOT VERIFIED** (overlay not brought up) |
| Helm install on a real cluster | **NOT VERIFIED** |
| HTTPS/TLS termination live | **NOT VERIFIED** (docs + compose overlay exist) |

### Documentation vs implementation

| Claim | Verdict |
|-------|---------|
| Trust Score hero metric | **Exists** as product concept; dashboard field is `trustworthiness_score` / cost `hallucination_cost_usd` (not always named `trust_score`) |
| OpenTelemetry | **Partial** — optional `requirements-otel.txt` + fail-open bootstrap; full OTLP path **NOT VERIFIED** |
| “Enterprise SSO” | **Must not claim GA** — Google when env set; SAML/SCIM experimental (**honesty docs match code**) |
| E2E “wired” | package.json has `test:e2e`; e2e README was stale → **updated** |
| Nginx proxies `/live` | **Was false** → **fixed** in `nginx/nginx.conf` |

---

## 3. Service / data / deploy maps (from code)

### Service map

```text
[SDK] → [Nginx?] → [FastAPI backend]
                      ├─ Auth / keys / orgs
                      ├─ Ingest → Postgres
                      ├─ Metrics (Redis cache optional)
                      └─ Enqueue → Redis → Celery worker
                                            └─ analysis_pipeline
                                               (BM25, NLI grounding, RAGAS-ish, failure, Trust)
[Next.js] → FastAPI (browser CORS) → same Postgres
[Beat] → scheduled monitoring / freshness / weekly reports
```

### Data flow (happy path)

1. Trace + chunks written (`analysis_status=pending`)  
2. Celery job `run_analysis`  
3. Grounding sentences ↔ chunks; BM25 observability; scores persisted  
4. UI loads `/queries/{id}` with `grounding_results`, `retrieved_chunks`, `bm25_comparison`

### Deploy flow (verified shape)

`docker compose` (+ optional `verify-ports` / `prod` / `observability`) → Alembic → seed → healthchecks.  
Helm chart present under `infrastructure/helm/` — cluster install **NOT VERIFIED**.

---

## 4. Feature claim matrix (implementation wins)

| Feature | Exists | Works (live) | Tested | Reachable UI/API | Documented |
|---------|--------|--------------|--------|------------------|------------|
| Ingest + analysis pipeline | ✓ | ✓ (earlier) | ✓ unit/API | ✓ | ✓ |
| Grounding attribution | ✓ | ✓ (API detail) | ✓ Vitest + unit | ✓ `/queries/[id]` | ✓ |
| BM25 comparison | ✓ | ✓ field present | ✓ | ✓ | ✓ |
| Trust / cost metrics | ✓ | ✓ dashboard keys | ✓ | ✓ | ✓ (field names differ) |
| Monitoring / regression / gaps / autofix | ✓ | **NOT VERIFIED** click-through this pass | ✓ unit | ✓ pages | ✓ scoped |
| MFA | ✓ | **NOT VERIFIED** end-to-end UI | ✓ unit | ✓ | ✓ |
| Google SSO | ✓ code | **NOT VERIFIED** (no OAuth secrets) | partial | ✓ | experimental |
| Razorpay | ✓ code | **NOT VERIFIED** | partial | ✓ | experimental |
| SAML / SCIM | stub/partial | **NOT VERIFIED** as complete | limited | ✓ | experimental |
| Webhook HMAC | ✓ code | **NOT VERIFIED** live delivery | unit (prior) | API | ✓ |
| Playwright E2E | ✓ | **FAIL / flaky this host** | suite exists | — | updated |
| k6 load | ✓ scripts | **NOT VERIFIED** | — | — | PERFORMANCE_REPORT reference only |

---

## 5. Defects found this session (and disposition)

| Severity | Finding | Disposition |
|----------|---------|-------------|
| **P1** | Dev CORS regex allowed `127.0.0.1:*` but not `localhost:13000` → browser login from verify-ports UI failed | **Fixed** (`security_http.py` + tests) |
| **P1** | Nginx sent `/live`/`/health` to Next.js → 404 | **Fixed** (`nginx/nginx.conf`) |
| **P2** | Auth inputs lacked `htmlFor`/`id` → Playwright `getByLabel` brittle | **Fixed** (login + register) |
| **P2** | Playwright reused foreign `:3000` app redirecting `/auth/login`→`/login` | **Fixed** config (`reuseExistingServer` opt-in; e2e README) |
| **P2** | `passlib` still pinned in compiled `requirements.txt` with **zero imports** | **Removed** from lockfile text |
| **P2** | Host→published-port API/UI connection resets under load (Docker Desktop Windows) | **Documented**; in-container health remains OK — **NOT fully mitigated** |
| **P3** | E2E not green end-to-end this pass | Document as gap; workers=1 locally |
| **P3** | Audit/PART\* markdown sprawl | Left in place (historical); clutter for first-time readers |

---

## 6. Dead code / cleanup decisions

| Item | References | Risk if removed | Action |
|------|------------|-----------------|--------|
| `passlib` in requirements.txt | No `import passlib` in app | Low | **Removed** |
| `PART*COMPLETION.md`, multiple `*REPORT.md` | Docs only | Low (history loss) | **Kept** — link from hiring report; do not delete evidence |
| `frontend/coverage/` | Generated | Low | Treat as artifact (ensure gitignored if not) |
| Experimental SCIM/SAML routes | Wired + honesty docs | High if deleted (breaks honesty story) | **Keep** |
| AlertRule / unused models | Schema only | Medium without product decision | **Keep** (documented experimental) |

No mass deletion of “legacy reports” — that would erase audit trail without improving runtime.

---

## 7. Security review (this pass)

| Area | Finding |
|------|---------|
| AuthN | JWT + refresh + API keys + MFA paths present; live login worked earlier |
| AuthZ | Org RBAC / plan gates in code + unit tests |
| Secrets | `.env` present locally (gitignored); examples only in git |
| Rate limit | SlowAPI wired; disabled under `TESTING` |
| Headers / CORS | API headers unit-tested; CORS bug fixed for verify-ports |
| Deps | pip-audit clean; npm 2 moderate transitive |
| Docker | Non-root frontend pattern in Dockerfile (prior); least-privilege K8s **NOT VERIFIED** live |
| OWASP | No exhaustive pentest — **NOT VERIFIED** beyond static + config review |

---

## 8. Hiring signal scores (0–10, uninflated)

| Dimension | Score | Why |
|-----------|------:|-----|
| Architecture | **8.5** | Correct modular monolith + async analysis; clear boundaries |
| Engineering | **8.0** | Real pipeline, migrations, fail-closed prod settings |
| Code quality | **7.5** | Strong critical coverage; some fat modules / dual sync-async |
| Documentation | **8.5** | Unusually deep for a portfolio repo; some narrative inflation historically |
| Security | **7.5** | Solid baseline; enterprise IdP incomplete; cookie SPA tokens accepted risk |
| Testing | **7.0** | Excellent unit/API; E2E/load **not** proven green here |
| Maintainability | **7.5** | Honesty layer is senior; report sprawl is junior-adjacent |
| Observability | **8.0** | RED metrics, ready probes, Grafana assets — overlay not re-run |
| Performance | **6.5** | Reference report exists; k6 **NOT VERIFIED**; host-port flakiness hurts confidence |
| Scalability | **6.5** | Helm/HPA present on paper; no live scale test |
| Product thinking | **8.5** | Clear core value + experimental quarantine |
| Technical communication | **8.0** | ADRs + case studies; README rewritten this pass |
| Open source quality | **8.0** | Bootstrap, Windows notes, LICENSE, CONTRIBUTING |
| Enterprise readiness | **5.5** | Pilots possible for self-host quality; IdP/SaaS bar unmet |
| **Hiring signal** | **8.0** | Differentiates vs CRUD/LLM wrappers |

### Would this get an interview for Senior AI Platform / MLOps?

**Yes — significantly increases odds**, if the candidate can:

1. Demo seed → grounding UI → Trust Score without reading slides  
2. Explain Celery vs sync analysis tradeoffs and failure modes  
3. Honestly say what is experimental  
4. Discuss the CORS / publish-port issues found in verification (shows debugging maturity)

**What would stop a hire:** claiming “full enterprise SSO/SCIM GA”, unable to explain Trust Score formula, or pretending E2E/load always green without evidence.

### Senior vs junior signals

| Looks senior | Looks junior / risky |
|--------------|----------------------|
| Experimental honesty layer | Multiple “100% complete” reports that disagree |
| Coverage gates on critical modules | E2E flaky / wrong-port traps |
| Prod settings fail-closed | Host networking instability not owned until verified |
| ADRs + case studies | PRD v3 surface wider than shipping contract |

### Interview questions I would ask

1. Walk me through one ungrounded sentence from seed data to DB columns.  
2. What happens when Redis is down at ingest? at logout?  
3. Why local NLI instead of cloud LLM-as-judge?  
4. How would you make SCIM real without lying in the README?  
5. Show me a failing analysis and the retry path.

---

## 9. Final scorecard

| Metric | Value |
|--------|------:|
| Verified completion (scoped product) | **88%** |
| Verified production readiness (self-host) | **82%** (cap for Windows publish-port flakiness) |
| Verified enterprise readiness | **55%** |
| Verified hiring signal | **80% / 8.0** |

### Remaining technical debt

1. Playwright E2E green in CI against Compose  
2. Host publish-port reliability on Docker Desktop Windows  
3. k6/Locust re-baseline with committed artifact numbers  
4. Optional OTel image path smoke-tested  
5. Consolidate audit markdown into one canonical index  

### Remaining risks

- Selling experimental SSO as GA  
- SPA tokens in cookies (XSS)  
- ML worker memory on small hosts  
- Coverage omits some peripheral modules by design  

### Highest-ROI improvements

1. CI job: Compose up → Playwright against published ports → tear down  
2. Document/fix Windows Docker port proxy flakes (or WSL2 networking note)  
3. One “canonical verification” doc that replaces report sprawl  
4. Graduate **one** IdP path completely (Google OIDC) with recorded demo video  

---

## 10. Decision

**READY FOR PORTFOLIO · READY FOR INTERVIEWS · READY FOR OPEN SOURCE · CONDITIONAL READY FOR PRODUCTION (SELF-HOSTED) · NOT READY FOR ENTERPRISE PILOTS AS IdP-COMPLETE SAAS**

### Direct answer

> If this repository were submitted by an unknown candidate applying for a Senior AI Platform Engineer or MLOps Engineer role, would it significantly increase their chances of getting an interview?

**Yes.** Evidence of a real ingest→async evaluation→attribution product with ops, tests, and honesty about unfinished enterprise surfaces is rare. It would not by itself justify an offer without a strong verbal deep-dive, and it would **hurt** if oversold as finished enterprise SSO/billing.

---

*Independent verification pass 2026-07-17. Prior `*COMPLETION*` / `FINAL_ENGINEERING_REPORT` scores were not trusted; only re-executed evidence counts above.*

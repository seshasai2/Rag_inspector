# Feature Inventory (Phase 1)

Evidence-based catalog of **implemented** RAGInspector features only.
Sources: `docs/IMPLEMENTED.md`, `backend/app/api/v1/router.py`, `frontend/src/app/`, `sdk/`.

## How to use

For each feature: purpose → dependencies → inputs → outputs → config → expected behaviour.

Quarantined / partial: **Enterprise Console marketing page**, live Razorpay checkout (needs keys), Google SSO (needs `GOOGLE_OAUTH_*`).

---

## A. Platform & auth

| Feature | Purpose | Dependencies | Inputs | Outputs | Config | Expected behaviour |
|---------|---------|--------------|--------|---------|--------|--------------------|
| Register | Create account | Postgres | email, password, name | user + tokens or verify email | `REQUIRE_EMAIL_VERIFICATION` | 201 or verification message |
| Login / refresh / logout | Session | Postgres, Redis (denylist optional) | credentials / refresh JWT | access + refresh | `SECRET_KEY`, TTLs | 200 with tokens; 401 invalid |
| MFA login | Second factor | MFA tables | mfa_token + TOTP | session tokens | enrolled factor | Blocks until verified |
| Email verify / reset | Account recovery | Email provider | token / email | status | Resend/SMTP | Token consumed once |
| API keys | SDK auth | Postgres | name, scopes | raw key once | — | `X-API-Key` works for ingest |
| Org members / invite | Team RBAC | org tables | email, role | membership | — | Accept invite links user |
| Google SSO | Enterprise login | OAuth | authorize → callback | session | `GOOGLE_OAUTH_*` | Redirects when configured |
| SCIM Users | Provisioning | SCIM auth | SCIM payload | User resource | enterprise plan | CRUD subset |

## B. Core RAG observability

| Feature | Purpose | Dependencies | Inputs | Outputs | Config | Expected behaviour |
|---------|---------|--------------|--------|---------|--------|--------------------|
| Pipelines CRUD | Scope traces | Postgres | name, costs | pipeline | — | Isolated per user/org |
| Ingest trace | Capture RAG turn | API key, Redis, Celery | query, answer, chunks | trace_id, queued job | plan quotas | Persist + enqueue analysis |
| Batch traces | Bulk ingest | same | array of traces | accepted count | — | Partial OK per item |
| Analysis pipeline | Score quality | Worker, models, Redis | trace_id | metrics, grounding, failure | `EMBEDDING_*`, `NLI_*` | Status → completed/failed |
| Reanalyze | Re-run analysis | Worker | trace_id | new job | — | Resets status, requeues |
| Query list/detail | Inspect results | JWT | filters, id | traces + grounding | — | Pre-analyzed seed works offline |
| Chunks / flag | Citation quality | JWT | pipeline | stats, flags | — | Flagged chunk visible |
| Metrics dashboard | Aggregate health | JWT, optional Redis cache | pipeline, days | cards + series | `DASHBOARD_CACHE_*` | Non-zero after seed |
| Settings | User prefs | JWT | thresholds, Ollama URL | settings | — | Persist round-trip |

## C. Phase 10 product surfaces

| Feature | Purpose | Dependencies | Inputs | Outputs | Config | Expected behaviour |
|---------|---------|--------------|--------|---------|--------|--------------------|
| Knowledge gaps | Cluster coverage misses | traces | pipeline | gap list | — | Seed shows open gaps |
| Autofix apply/dismiss/verify | Act on recommendations | JWT | rec_id | status change | — | Status transitions |
| Documents + freshness | Track KB staleness | JWT | title, url, hash | freshness status | worker beat | Stale/critical rows |
| Monitoring probes | Continuous quality | Celery beat | config, probes | runs + alerts | interval | History after seed/run-now |
| Regression snapshots | Pre-deploy compare | JWT | label / compare body | delta metrics | — | Baseline vs candidate |
| Retrieval/LLM benchmark | Measured benchmarks | real traces | pipeline | scores | — | Uses stored traces only |
| Studio (prompt/chunks/simulate) | Heuristic tools | JWT | prompt / pipeline | suggestions | — | Heuristic, not invented forecasts |
| AI Investigator | Ask metrics questions | JWT | question | cited answer | — | Grounded in metrics |
| Executive / weekly / SLA reports | Leadership view | JWT | — | JSON/PDF history | email for send | Seed report history |
| Billing usage / verify | Quotas + Razorpay | keys optional | plan | usage | Razorpay env | Usage works without checkout |

## D. Ops & integrations

| Feature | Purpose | Dependencies | Inputs | Outputs | Config | Expected behaviour |
|---------|---------|--------------|--------|---------|--------|--------------------|
| `/health` `/live` | Liveness | — | — | JSON | — | 200 always if process up |
| `/ops/ready` | Readiness | DB + Redis | — | checks | — | 503 if DB/Redis down |
| `/ops/backlog` | Queue depth | Redis | — | pending/running | — | Reflects Celery |
| `/ops/metrics` | Prometheus | — | — | text | — | Scrapable |
| Webhooks | Outbound events | Celery | URL, events | deliveries | — | Test endpoint fires |
| Audit logs | Security trail | JWT | filters | events | — | Login/actions appear |
| Admin summary | Support console | admin role | — | users/jobs | `SUPPORT_ADMIN_*` | Restricted |

## E. Frontend routes (implemented pages)

`/`, `/auth/*`, `/dashboard`, `/queries`, `/queries/[id]`, `/chunks`, `/knowledge/gaps`, `/autofix`, `/documents`, `/monitoring`, `/regression`, `/benchmark`, `/studio`, `/investigator`, `/executive`, `/team`, `/metrics`, `/pipelines`, `/settings`, `/admin`, `/enterprise` (quarantined notice), `/privacy`, `/terms`, `/refund-policy`.

## F. SDK

`raginspector` client + LangChain / LlamaIndex / Haystack adapters — ingest traces with API key.

## Demo credentials (seed)

| Item | Value |
|------|-------|
| Email | `demo@example.com` |
| Password | `DemoPass123!` |
| API key | `ri-demo_interview_seed_key_000000000001` |
| Org | Acme Support Labs (`acme-support-labs`) |
| Pipelines | Demo RAG Pipeline, Docs Assistant |

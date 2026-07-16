# RAGInspector

**Find why your RAG app fails — in under 30 seconds.**

RAGInspector is an open-source **RAG pipeline debugger**: instrument retrieval + generation with a free Python SDK, analyze traces asynchronously (grounding NLI, BM25 vs vector, failure class, Trust Score), and inspect sentence-level attribution in a Next.js dashboard.

Built for production-grade local/self-hosted deployment using **only free open-source tooling** (Docker Compose, Prometheus, Grafana, GitHub Actions, Playwright, k6, Locust).

![Sentence grounding (demo seed data)](docs/screenshots/grounding-attribution.png)

---

## The business problem (60-second brief)

| | |
|--|--|
| **Problem** | RAG products fail in production without visibility into *retrieval* vs *generation*. Teams debug via logs and guesswork. |
| **Customer** | ML/backend engineers and platform teams shipping support bots, internal knowledge Q&A, and search+answer apps. |
| **Why existing tools fall short** | Many observability tools center LLM spans and prompts; they rarely show sentence↔chunk grounding, BM25 vs vector ranking, or a Trust Score tied to hallucination cost. |
| **Success metrics** | Time-to-root-cause (&lt;30s on seeded traces); Trust Score / grounded-fraction trends; analysis backlog SLO; optional $/wrong-answer cost signal. |
| **ROI** | Fewer escalations from wrong answers; faster iteration on chunking/retrieval; executives see quality as dollars, not only F1. |
| **Pricing (OSS)** | Free to self-host. Optional Razorpay plans exist for a future SaaS lane — **not required** locally ([EXPERIMENTAL.md](docs/EXPERIMENTAL.md)). |

Case studies: [docs/case-studies/](docs/case-studies/) · Why these designs: [docs/adr/](docs/adr/) · Hiring review: [docs/HIRING_SIGNAL.md](docs/HIRING_SIGNAL.md)

---

## Project overview

| Capability | What you get |
|------------|--------------|
| Trace ingest | SDK + API keys → FastAPI → Postgres |
| Async analysis | Celery workers (NLI grounding, BM25, Trust Score) |
| Dashboard | Queries, chunks, metrics, autofix, monitoring |
| Ops | Nginx, health probes, Prometheus/Grafana overlay |
| Enterprise honesty | Partial SSO/SCIM clearly labeled — see [docs/EXPERIMENTAL.md](docs/EXPERIMENTAL.md) |

---

## Screenshots

| Surface | Asset |
|---------|-------|
| Grounding attribution | [docs/screenshots/grounding-attribution.png](docs/screenshots/grounding-attribution.png) |
| Capture notes | [docs/screenshots/](docs/screenshots/) |

Demo walkthroughs: [docs/demo/](docs/demo/)

---

## Architecture

```text
Your RAG app ──SDK──► Nginx/FastAPI ──► PostgreSQL
                           │
                           ▼
                     Celery + Redis
                     (NLI, BM25, Trust Score)
                           │
                           ▼
                     Next.js dashboard
```

Full Mermaid pack: [docs/architecture/](docs/architecture/) · Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Tech stack

| Layer | Choice (free/OSS) |
|-------|-------------------|
| API | FastAPI, SQLAlchemy, Alembic |
| Workers | Celery, Redis, local sentence-transformers |
| UI | Next.js 15, TanStack Query, Tailwind |
| Data | PostgreSQL 16 + pgvector |
| Edge | Nginx |
| Observability | Prometheus, Grafana, node-exporter, cAdvisor |
| CI | GitHub Actions |
| Load | k6, Locust |
| E2E | Playwright |

---

## Features

- Sentence ↔ chunk grounding UI
- BM25 vs vector ranking comparison
- Failure classification + hallucination cost signals
- Trust Score dashboard + Redis-cached aggregates
- API keys, JWT + MFA TOTP, audit logs
- Monitoring probes, regression snapshots, knowledge gaps
- Webhook deliveries with HMAC signatures
- Production fail-closed settings validation

---

## Installation (local)

```bash
git clone <this-repo>
cd raginspector
cp .env.example .env          # set SECRET_KEY (≥32 characters)
make bootstrap                # build → start → migrate → health
make seed                     # optional demo data
```

Windows: `.\scripts\setup.ps1` then `.\scripts\bootstrap.ps1` (Make recipes need a POSIX shell — see [docs/WINDOWS.md](docs/WINDOWS.md)).

Open **http://localhost:3000** → `demo@example.com` / `DemoPass123!`  
API docs (dev): **http://localhost:8000/docs** (Swagger) · **/redoc**

---

## Docker

```bash
docker compose up -d --build
docker compose run --rm backend alembic upgrade head
```

Production:

```bash
cp .env.production.example .env.production   # fill secrets including OPS_SHARED_TOKEN
./scripts/deploy.sh                          # or .\scripts\deploy.ps1
./scripts/deploy.sh --obs                    # + Prometheus/Grafana/exporters
```

Compose files: `docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.observability.yml`, `nginx/nginx.conf`

---

## Development

```bash
make lint typecheck test
cd backend && pytest tests/unit/ tests/integration/ -q
cd frontend && npm test && npm run test:e2e
```

Coding standards: [docs/engineering/CODING_STANDARDS.md](docs/engineering/CODING_STANDARDS.md)

---

## Deployment

| Target | Guide |
|--------|-------|
| Compose prod | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), `scripts/deploy.sh` / `deploy.ps1` |
| TLS | [docs/TLS.md](docs/TLS.md) |
| Kubernetes / Helm | [docs/KUBERNETES.md](docs/KUBERNETES.md), [docs/HELM.md](docs/HELM.md) |
| Frontend free host | Vercel / Cloudflare Pages — point `NEXT_PUBLIC_API_URL` at your API; see Deployment walkthrough |

---

## Testing

| Suite | Command |
|-------|---------|
| Backend unit | `cd backend && pytest tests/unit/ -q` |
| Integration | `cd backend && pytest tests/integration/ -q` |
| Frontend unit | `cd frontend && npm test` |
| E2E | `cd frontend && npm run test:e2e` |
| Load (k6) | `k6 run loadtests/k6/smoke.js` |
| Load (Locust) | see [loadtests/README.md](loadtests/README.md) |

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (lint, types, security, tests, coverage, Docker, Helm, SBOM, e2e, k6 inspect)

---

## Monitoring

```bash
make up-obs
# Prometheus http://localhost:19090
# Grafana    http://localhost:13001  (admin / admin)
```

Scrapes: API metrics, node-exporter, cAdvisor, Redis exporter, Postgres exporter.  
Dashboard JSON: `infra/observability/grafana/dashboards/`

---

## Configuration

See `.env.example` and `.env.production.example`. Critical production keys:

- `SECRET_KEY` (≥32)
- `OPS_SHARED_TOKEN` (≥16) — gates `/api/v1/ops/backlog` and `/experimental`
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`
- `FRONTEND_URL` (https), `ALLOWED_HOSTS`

Secrets guide: [docs/SECRETS.md](docs/SECRETS.md) · [SECURITY.md](SECURITY.md)

---

## API

- OpenAPI: `http://localhost:8000/openapi.json` (dev)
- Guide: [docs/API.md](docs/API.md)
- Postman: [docs/api/postman_collection.json](docs/api/postman_collection.json)
- Insomnia: [docs/api/insomnia_collection.json](docs/api/insomnia_collection.json)

SDK:

```python
from raginspector import RAGInspector

inspector = RAGInspector(api_key="ri-...", pipeline_name="my-rag", base_url="http://localhost:8000")
```

---

## Troubleshooting

- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- [docs/demo/TROUBLESHOOTING.md](docs/demo/TROUBLESHOOTING.md)
- [docs/RUNBOOKS.md](docs/RUNBOOKS.md)
- Windows notes: [docs/WINDOWS.md](docs/WINDOWS.md)

---

## Performance

See [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) and re-run [loadtests/](loadtests/).

---

## FAQ

See **[docs/FAQ.md](docs/FAQ.md)** (setup, architecture, security, interview talking points).

Quick answers:

- **Billing required?** No — local free tier works without Razorpay.  
- **Google SSO required?** No — optional when `GOOGLE_OAUTH_*` is set.  
- **Free hosting?** Yes — Compose/VPS + Vercel/Cloudflare Pages free tiers.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) and honest scope in [docs/IMPLEMENTED.md](docs/IMPLEMENTED.md).

---

## License

[MIT](LICENSE)

---

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) · [docs/DEVELOPER.md](docs/DEVELOPER.md) · [docs/engineering/](docs/engineering/) · ADRs: [docs/adr/](docs/adr/)

---

## Case studies & demos

- [docs/case-studies/](docs/case-studies/) (5 enterprise narratives)
- [docs/demo/](docs/demo/)
- Hiring notes: [docs/HIRING.md](docs/HIRING.md) · Scorecard: [docs/HIRING_SIGNAL.md](docs/HIRING_SIGNAL.md)
- Audits: [ENTERPRISE_AUDIT_REPORT.md](ENTERPRISE_AUDIT_REPORT.md) · [FINAL_ENGINEERING_REPORT.md](FINAL_ENGINEERING_REPORT.md)

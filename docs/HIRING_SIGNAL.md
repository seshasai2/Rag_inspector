# Hiring signal scorecard — RAGInspector

Mapped to a production-engineering hiring checklist. **Optimize for being able to answer *why*** — not for buzzword count.

Last review: 2026-07-15

## Weighted score (internal)

| Category | Weight | Score (0–10) | Notes |
|----------|-------:|-------------:|-------|
| Business value | 10% | 9 | Problem/customer/ROI now on README; 5 case studies |
| Architecture | 15% | 9.5 | Mermaid pack + ADRs + DESIGN_DECISIONS |
| Code quality | 15% | 8.5 | Layered services/repos; some fat modules remain |
| Testing | 10% | 9 | Unit/API/integration/SDK/FE + coverage gates |
| Security | 10% | 9 | JWT/MFA/keys, headers, secrets fail-closed, audit |
| DevOps & CI/CD | 10% | 9.5 | Compose, Helm, GH Actions, SBOM, Trivy |
| Observability | 5% | 9 | Structlog IDs, Prom/Grafana, RED, alerts |
| Documentation | 10% | 9.5 | Strong; FAQ/ADRs/LICENSE filled this pass |
| Performance & scalability | 10% | 8.5 | Async workers, cache, loadtests; soak evidence optional |
| Developer experience | 5% | 9 | One-command bootstrap (Make / PowerShell) |
| **Weighted total** | 100% | **~9.1 / 10** | |

## Checklist (quick)

| # | Signal | Status |
|---|--------|--------|
| 1 | Business problem | **Strong** — README section |
| 2 | System design diagrams | **Strong** — `docs/architecture/` |
| 3 | Code quality | **Good** — not perfect Clean/Hex everywhere; honest modular monolith |
| 4 | Repo structure | **Strong** |
| 5 | Documentation | **Strong** — FAQ, LICENSE, ADRs added |
| 6 | API design | **Strong** — versioned `/api/v1`, OpenAPI, pagination |
| 7 | Database | **Strong** — Alembic, indexes docs, pooling |
| 8 | Security | **Strong** |
| 9 | Logging | **Strong** — request/correlation/trace IDs |
| 10 | Monitoring | **Strong** |
| 11 | Testing | **Strong** |
| 12 | Performance | **Good** — benchmarks + load scripts |
| 13 | Scalability | **Good** — queues, HPA docs, low worker concurrency by design |
| 14 | DevOps | **Strong** |
| 15 | Cloud readiness | **Strong** — Helm/K8s docs |
| 16 | AI/ML engineering | **Strong** — grounding, eval metrics, fallbacks, cost signal |
| 17 | Frontend | **Good** — dark/light, empty/error states |
| 18 | DX clone→up | **Strong** |
| 19 | Git quality | **Gap if unpublished** — init git, meaningful commits, tags before public GitHub |
| 20 | Production readiness | **Strong** — health, retries, runbooks, DR |
| 21 | Realism | **Strong** — real NLI path; honesty on experimental IdP |
| 22 | Case studies | **Strong** — ×5 |
| 23 | Portfolio polish | **Good** — screenshot; add short demo GIF/video when possible |
| 24 | Decision records | **Strong** — `docs/adr/` |

## Gaps that still raise signal (do these, not more features)

1. **`git init` + publish** with meaningful history and a `v1.0.0` tag (this tree may still be ungitted locally).  
2. **60–90s demo GIF or Loom** linked from README (seeded grounding hover).  
3. **Live deploy** only if free-tier stable (optional; Compose self-host is enough).  
4. In interviews: defend ADRs 0001–0005 and experimental honesty — recruiters remember judgment.

## What *not* to do

- Do not bolt on a fake “full MLOps / Airflow / Kafka” platform to chase buzzwords.  
- Do not demo SAML/SCIM as GA.  
- Do not inflate coverage claims beyond critical-module gates.

## Reviewer path (5–15 minutes)

1. README business table + screenshot  
2. `docs/adr/0001` + `docs/architecture/04-system-diagram.md`  
3. Skim `backend/app/services/analysis_pipeline.py` stages + `ingest_service.py`  
4. `.github/workflows/ci.yml` job names  
5. Seed grounding page mentally from [demo/DEMO_WALKTHROUGH.md](demo/DEMO_WALKTHROUGH.md)

---

*Hiring signal comes from engineering quality and tradeoff clarity — not feature count.*

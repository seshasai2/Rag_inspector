# Implemented vs Roadmap

Honest scope for recruiters and contributors. Source of truth for **execution** remains [ROADMAP.md](../ROADMAP.md); design boundary [ARCHITECTURE.md](ARCHITECTURE.md); stubs [EXPERIMENTAL.md](EXPERIMENTAL.md).

## Phase summary

| Phase | Theme | Status |
|-------|--------|--------|
| 1–5 | Core product, security, quality | ✅ Complete |
| 6 | Performance (pagination, cache, backlog) | ✅ Complete |
| 7 | Developer experience | ✅ Complete |
| 8 | Production hardening | ✅ Complete |
| 9 | Portfolio polish | ✅ Complete |
| 10 | SaaS / enterprise PRD v3 | ✅ Complete (scoped implementations) |

## Product surfaces

| Surface | Status | Notes |
|---------|--------|-------|
| Python SDK ingest | ✅ | `sdk/raginspector` + LangChain / LlamaIndex / Haystack adapters |
| Trace ingest + reanalyze | ✅ | API key auth, plan limits |
| Celery analysis (grounding, BM25, failure class, Trust) | ✅ | Local NLI; LLM metrics optional |
| Query detail grounding UI | ✅ | `/queries/[id]` |
| Knowledge gaps | ✅ 10.1 | `/knowledge/gaps` |
| Autofix apply/dismiss/verify | ✅ 10.2 | `/autofix` |
| Documents + freshness | ✅ 10.3 | `/documents` |
| Monitoring probes | ✅ 10.4 | `/monitoring` |
| Regression / pre-deploy | ✅ 10.5 | `/regression` |
| Retrieval + LLM benchmark | ✅ 10.6 | Real traces only — `/benchmark` |
| Studio tools | ✅ 10.7 | Heuristic/measured — `/studio` |
| AI Investigator | ✅ 10.8 | Cited metrics — `/investigator` |
| Executive + PDF | ✅ 10.9 | `/executive` + `/reports/executive` |
| Billing usage / verify / failed webhooks | ✅ 10.10 | `/billing/usage`, `verify-payment` |
| Team invite accept / RBAC | ✅ 10.11 | `/team` + org member APIs |
| Google SSO | ✅ 10.13 | Live when `GOOGLE_OAUTH_*` set |
| Enterprise Console marketing page | 🚫 Quarantined | Honesty notice |

## How to read claims

- Benchmark/studio/investigator use **measured** data or heuristics — not invented forecasts.
- Google SSO requires real OAuth client credentials in env.
- Razorpay still needs live keys for checkout; usage quotas are enforced on ingest.

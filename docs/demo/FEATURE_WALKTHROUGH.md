# Feature walkthrough

Product features mapped to UI routes and API surfaces for demos.

## Core heroes

| Feature | UI | API / service |
|---------|----|---------------|
| Trust Score | `/dashboard` | `trust_scorer.py`, metrics dashboard |
| Hallucination Cost | Dashboard cost card | `hallucination_cost.py`, pipeline PATCH |
| Sentence grounding | `/queries/[id]` | `grounding.py`, query detail |
| Context recall | Query detail / metrics | `context_recall.py` |
| BM25 vs vector | Query + `/metrics` | `bm25_service.py`, `/metrics/bm25-comparison` |
| Chunk quality | `/chunks` | `chunk_quality.py`, `/chunks/summary` |

## Instrumentation & ingest

| Feature | Where |
|---------|-------|
| Python SDK | `sdk/raginspector` |
| Trace ingest | `POST /api/v1/ingest/trace` |
| Reanalyze | `POST /api/v1/queries/{id}/reanalyze` |

## Platform

| Feature | UI | API |
|---------|----|-----|
| Pipelines CRUD | `/pipelines` | `/api/v1/pipelines` |
| API keys | Settings / keys | `/api/v1/keys` |
| Auth (register/login/MFA) | `/auth/*` | `/api/v1/auth/*` |
| User settings | `/settings` | `/api/v1/settings` |
| Metrics timeseries | `/metrics` | `/api/v1/metrics/*` |

## Extended (show briefly)

| Feature | Route | Notes |
|---------|-------|-------|
| Knowledge gaps | `/knowledge/gaps` | Coverage analytics |
| Autofix | `/autofix` | Fix recommendations |
| Regression | `/regression` | Pre-deploy checks |
| Monitoring / alerts | `/monitoring` | Slack / rules |
| Investigator / Studio | `/investigator`, `/studio` | Experimental / enterprise roadmap tone |
| Executive reports | `/executive` | ROI-style summaries |
| Team / enterprise | `/team`, `/enterprise` | SSO, memberships, audit |

## Demo order that works

1. Trust + cost on dashboard  
2. One grounding query  
3. Chunks heatmap  
4. Live ingest → backlog → new query  
5. Optional MFA/SSO slide if audience is enterprise  

Related: [FEATURE set in ARCHITECTURE.md](../ARCHITECTURE.md), [IMPLEMENTED.md](../IMPLEMENTED.md).

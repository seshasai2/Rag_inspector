# Design decisions

Notable architectural choices and alternatives considered. Binding product framing: [ARCHITECTURE.md](../ARCHITECTURE.md).

## 1. Async analysis via Celery (not inline FastAPI)

**Decision:** Ingest persists traces and enqueues `run_analysis`; API returns 202.  
**Why:** NLI/embeddings are multi-second and memory-heavy; blocking HTTP would destroy tail latency.  
**Rejected:** Inline thread-pool analysis — harder to scale and warm models across replicas.

## 2. Dual auth: JWT + API keys

**Decision:** Humans use JWT; SDK uses `X-API-Key`.  
**Why:** Fits browser and CI/service accounts without putting long-lived passwords in apps.  
**Rejected:** mTLS-only for v1 — higher ops cost for open-source adopters.

## 3. VARCHAR(36) UUID strings

**Decision:** Primary keys as `String(36)` UUID text.  
**Why:** Cross-dialect friendliness (SQLite tests + Postgres) and simpler client handling.  
**Trade-off:** Slightly wider indexes than native UUID.

## 4. Separate `analysis` and `celery` queues

**Decision:** ML work on `analysis`; beat/webhooks on `celery`.  
**Why:** Prevent light tasks from starving behind long ML jobs and vice versa.  
**Ops implication:** Workers must subscribe to the right queues ([WORKER.md](../WORKER.md)).

## 5. Trust Score & Hallucination Cost as hero metrics

**Decision:** Weighted trust over last 100 traces; cost = rate × volume × unit cost.  
**Why:** Portfolio/hiring narrative and executive translation of quality → dollars.  
**Rejected:** Exposing only raw RAGAS numbers without aggregation.

## 6. Heuristic context recall by default

**Decision:** Term coverage + attribution heuristics; optional HF LLM path.  
**Why:** Works offline and in CI without API tokens.  
**Trade-off:** LLM judges can be sharper but cost and variance.

## 7. Low worker concurrency

**Decision:** Default analysis concurrency 1–2 with model warm-on-start.  
**Why:** Each process holds model weights; high concurrency OOMs commodity nodes.  
**Scale out:** More pods, not more threads.

## 8. Production OpenAPI UI disabled

**Decision:** `docs_url`/`redoc_url` null in production.  
**Why:** Reduce attack surface and accidental data exposure in try-it-out.  
**Mitigation:** Ship Postman/Insomnia collections and internal staging docs.

## 9. Dashboard Redis cache

**Decision:** TTL cache for expensive aggregates.  
**Why:** Leadership dashboards are read-heavy and compute-heavy.  
**Trade-off:** Brief staleness acceptable; invalidate on demand if needed.

## 10. Hiring-first scope over unfinished SaaS surface

**Decision:** Core loop (instrument→ingest→analyze→inspect) prioritized over incomplete enterprise studio sprawl.  
**Why:** Deep correct debugger beats shallow stubs for credibility.  
**Roadmap:** Enterprise SSO/audit continue behind plan gates.

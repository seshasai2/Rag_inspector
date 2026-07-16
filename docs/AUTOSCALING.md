# Autoscaling strategy

## Goals

Scale API for request load; scale workers for analysis queue depth; avoid flapping.

## API (backend)

| Signal | Mechanism |
|--------|-----------|
| CPU | HPA `targetCPUUtilizationPercentage` (prod ~65%) |
| Memory | HPA memory utilization (prod ~75%) |
| Request rate / latency | Prefer Ingress/APM metrics → custom HPA metrics or KEDA later |

Stabilization: scale-down window **300s**, scale-up **60s** (see chart `backend.autoscaling.behavior`).

Assumptions: ~2 uvicorn workers per pod; connection pools sized for replica count × workers; avoid over-allocating CPU limits to prevent noisy-neighbor throttling on shared nodes.

## Frontend

CPU HPA; lighter resources (SSR/standalone). Scale with user dashboard traffic.

## Workers

| Signal | Mechanism |
|--------|-----------|
| CPU | Default HPA when `keda.enabled=false` |
| Queue depth | Enable `keda.enabled=true` + Prometheus metric `raginspector_celery_queue_depth` |
| Memory | Soft — ML models fixed cost per pod; prefer scale-out over raising concurrency |

Default concurrency **2** (see `docs/WORKER.md`). Raising concurrency increases RAM sharply — prefer more replicas.

Cooldown: KEDA `cooldownPeriod: 300`; HPA scale-down at most 1 pod / 120s.

## Beat

**Do not autoscale.** Always 1 replica (`Recreate`).

## Capacity planning assumptions

| Component | Request | Limit | Why |
|-----------|---------|-------|-----|
| API | 250m–500m / 512Mi–1Gi | 2 CPU / 2Gi | JSON + DB; no heavy ML in API path |
| Worker | 500m–1 CPU / 2–3Gi | 2–4 CPU / 6–8Gi | sentence-transformers + torch CPU |
| Frontend | 100m / 256Mi | 1 CPU / 1Gi | Node standalone |
| Redis (in-cluster) | 50m / 128Mi | 500m / 512Mi | Cache/broker |
| Postgres (dev) | 250m / 512Mi | 1 CPU / 2Gi | Not for prod load |

Tune after 7 days of Prometheus histograms.

## Preventing oscillation

- Prefer one primary scale signal for workers (queue **or** CPU, not conflicting aggressive both).
- Stabilization windows ≥ 60–300s.
- Match HPA minReplicas to PDB minAvailable.

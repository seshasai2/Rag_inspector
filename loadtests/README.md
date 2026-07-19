# Load testing

Synthetic load against RAGInspector health and readiness endpoints using open-source tools:

- [k6](https://k6.io/) (Grafana Labs, AGPL)
- [Locust](https://locust.io/) (MIT)
- Python evidence harness: `bench_verify.py`, `bench_auth_load.py` (httpx; no k6 required)

Default target: `BASE_URL=http://localhost:8000`. Start the stack with `make up` (or `make bootstrap`) before running scripts.

## Critical: login rate limits

`POST /api/v1/auth/login` is limited to **20/minute per IP** (SlowAPI: `AUTH_LOGIN_LIMIT`).  
Nginx edge also applies **~5/minute** on `/api/v1/auth/login` when traffic goes through the proxy.

Rapid login loops in benchmarks will return **HTTP 429** and look like “auth broken.”  
For authenticated latency/load: obtain **one** token, reuse `Authorization: Bearer …`, and space login samples (≥4s apart under the 20/min budget).

See [PERFORMANCE_BENCHMARK_REPORT.md](../PERFORMANCE_BENCHMARK_REPORT.md) for the verification pass.

## Prerequisites

```bash
# k6 — see https://grafana.com/docs/k6/latest/set-up/install-k6/
k6 version

# Locust
pip install locust
```

Ensure `/live` returns 200 before ramping to 500–1000 VUs.

## k6 scenarios

| Script | VUs | Purpose |
|--------|-----|---------|
| `k6/smoke.js` | 10 | Sanity after deploy |
| `k6/load_100.js` | 100 | Steady load |
| `k6/load_500.js` | 500 | Elevated load |
| `k6/stress_1000.js` | 1000 | Stress / saturation |

Each script hits `/live`, `/health`, and `/api/v1/ops/ready`, records custom Trends, and prints p50 / p95 / p99 in `handleSummary`.

```bash
cd /path/to/raginspector

k6 run loadtests/k6/smoke.js
k6 run -e BASE_URL=http://localhost:8000 loadtests/k6/load_100.js
k6 run loadtests/k6/load_500.js
k6 run loadtests/k6/stress_1000.js
```

Example thresholds (smoke): p50 < 200 ms, p95 < 500 ms, p99 < 1000 ms, error rate < 1%.

## Locust

`locust/locustfile.py` defines:

- **HealthUser** — `/live`, `/health`, `/ops/ready`
- **AuthShapeUser** — login POST shape (200 / 401 / 429 accepted)
- **MetricsUser** — dashboard / timeseries when demo credentials or `ACCESS_TOKEN` work

### Stage sizing comments

| Stage | Users | Suggested spawn rate | Command sketch |
|-------|-------|----------------------|----------------|
| Smoke | 10 | 2 | `--users 10 --spawn-rate 2` |
| Load | 100 | 10 | `--users 100 --spawn-rate 10` |
| Elevated | 500 | 25 | `--users 500 --spawn-rate 25` |
| Stress | 1000 | 50 | `--users 1000 --spawn-rate 50` |

```bash
# UI
locust -f loadtests/locust/locustfile.py --host http://localhost:8000

# Headless 100 VU for 3 minutes
locust -f loadtests/locust/locustfile.py --host http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 3m --headless

# Optional auth context
DEMO_EMAIL=demo@example.com DEMO_PASSWORD=DemoPass123! \
  locust -f loadtests/locust/locustfile.py --host http://localhost:8000
```

## Interpreting results

1. Compare p50/p95/p99 across smoke → stress; large jumps on `/ops/ready` usually indicate DB or Redis saturation.
2. Cross-check `GET /api/v1/ops/backlog` during runs that also ingest traffic.
3. Re-run after worker/API replica changes; numbers in root `PERFORMANCE_REPORT.md` are reference baselines only.

## Related

- [PERFORMANCE_REPORT.md](../PERFORMANCE_REPORT.md)
- [docs/API.md](../docs/API.md)
- [docs/AUTOSCALING.md](../docs/AUTOSCALING.md)

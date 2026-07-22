# Render keep-alive

Keep the **Render Free** RAGInspector API from spinning down during demos and development by pinging a lightweight health endpoint every 5 minutes.

## Purpose

Render Free web services sleep after ~15 minutes of inactivity. The first request after sleep can take 30–60+ seconds (cold start), which hurts interview demos.

This keep-alive system:

1. Uses the existing unauthenticated `GET /health` probe (no DB, Redis, auth, or ML).
2. Runs a GitHub Actions workflow on a 5-minute cron (+ manual dispatch).
3. Retries through cold-start 502s, then confirms with a second ping.
4. Optionally pairs with an external uptime monitor for redundancy.

## Architecture

```text
GitHub Actions (cron */5)
        │
        │  GET ${BACKEND_URL}/health  (retry through 502s)
        │  (secret — never hardcoded)
        ▼
Render Free web service (raginspector-api)
        │
        ▼
FastAPI /health  →  {"status":"healthy","service":"raginspector",...}
```

Related probes:

| Path | Role |
|------|------|
| `/health` | Liveness / keep-alive (this doc) |
| `/live` | Alias of `/health` (Render `healthCheckPath` in `render.yaml`) |
| `/api/v1/ops/ready` | Readiness (DB / Redis) — **do not** use for keep-alive |

## How it works

1. Workflow: [`.github/workflows/render-keepalive.yml`](../.github/workflows/render-keepalive.yml)
2. Trigger: `schedule` every 5 minutes (`*/5 * * * *`) and `workflow_dispatch`
3. Reads repository secret `BACKEND_URL` (base URL only, no path, no credentials)
4. Retries `GET ${BACKEND_URL}/health` through cold-start 502s (up to ~90s each)
5. Confirms with a second ping so a flaky wake does not look “green”
6. Fails the job if wake + confirm do not both return HTTP 200

Scheduled workflows only run on the repository **default branch** after the workflow file is merged.

## How to configure

### 1. Confirm the health endpoint

Locally:

```bash
curl -sS http://localhost:8000/health
```

Deployed:

```bash
curl -sS "${BACKEND_URL}/health"
```

Expected JSON shape (status remains `healthy` for backward compatibility):

```json
{
  "status": "healthy",
  "service": "raginspector",
  "version": "1.0.0",
  "timestamp": "2026-07-21T07:00:00.000000+00:00"
}
```

### 2. Add the GitHub secret

1. Open the GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. Name: `BACKEND_URL`
4. Value: your Render **HTTPS origin only**, for example:
   - `https://raginspector-api.onrender.com`
5. Do **not** include:
   - A trailing path (`/health`)
   - API keys or tokens
   - A trailing slash (the workflow strips one if present)

### 3. Merge the workflow to the default branch

Push/merge `.github/workflows/render-keepalive.yml` to `main` (or your default branch). Cron schedules do not run from feature branches alone.

### 4. Trigger manually (optional)

**Actions** → **Render keep-alive** → **Run workflow**.

## How to manually test

```bash
# From any machine with network access to Render
export BACKEND_URL="https://YOUR_SERVICE.onrender.com"   # no trailing slash
curl --silent --show-error \
  --max-time 90 \
  --write-out "\nHTTP:%{http_code} time_total:%{time_total}s\n" \
  "${BACKEND_URL}/health"
```

Validate workflow YAML (optional, if [actionlint](https://github.com/rhysd/actionlint) is installed):

```bash
actionlint .github/workflows/render-keepalive.yml
```

## Expected logs

### GitHub Actions

```text
UTC time: 2026-07-21T12:10:00Z
Target:   https://…onrender.com/health
Status code: 200
Response time (ms): 842
Response body:
{"status":"healthy","service":"raginspector","version":"1.0.0","timestamp":"…"}
```

### Render

Dashboard → your web service → **Logs**: periodic `GET /health` (or `/live`) with 200 responses around the cron times.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Workflow fails: secret not set | Missing `BACKEND_URL` | Add the Actions secret |
| curl exit 22 / HTTP non-200 | Service down or wrong URL | Check Render dashboard; fix secret |
| curl timeout / connection refused | Cold start longer than 90s, or service deleted | Check Render logs/deploy; confirm `BACKEND_URL` |
| Workflow never runs on schedule | File not on default branch; Actions disabled; GitHub cron drift | Merge to `main`; enable Actions; GitHub may delay cron several minutes |
| Still spins down | Cron gap + Render idle policy | Add Better Stack / UptimeRobot / cron-job.org staggered off GitHub |
| 403 / TrustedHost | `ALLOWED_HOSTS` missing your hostname | Add hostname in Render env vars |

## Redundant keep-alive (added)

Three layers ping `/health` so a missed GitHub cron does not let Render Free sleep:

| Layer | Schedule | Workflow / tool |
|-------|----------|-----------------|
| Primary GitHub | every 5 min (`*/5`) | `.github/workflows/render-keepalive.yml` |
| Staggered GitHub | `:02,:07,:12,…` | `.github/workflows/render-keepalive-staggered.yml` |
| UptimeRobot | every 5 min (free) | agentic setup → confirm email |
| cron-job.org | every 7 min | `scripts/keepalive/setup_cron_job_org.py` |

Target URL:

`https://raginspector-api.onrender.com/health`

### UptimeRobot (agentic — no API key)

Already submitted for the production `/health` URL. **You must click Activate in the email** (inbox used for the request).

Re-run locally:

```bash
python scripts/keepalive/setup_uptimerobot_agentic.py \
  --email "you@example.com" \
  --url "https://raginspector-api.onrender.com/health"
```

Or open:

`https://uptimerobot.com/quick-start?url=https://raginspector-api.onrender.com/health&email=you@example.com`

Or Actions → **Provision external keep-alive** → set `alert_email` → Run.

### cron-job.org

1. Create a free account at [cron-job.org](https://cron-job.org/)
2. **Settings** → create an API key
3. Add GitHub Actions secret `CRON_JOB_ORG_API_KEY`
4. Run locally or via Actions:

```bash
export CRON_JOB_ORG_API_KEY="…"
python scripts/keepalive/setup_cron_job_org.py \
  --url "https://raginspector-api.onrender.com/health" \
  --every-minutes 7
```

Or Actions → **Provision external keep-alive** (uses the secret automatically).

Optional secret `KEEPALIVE_ALERT_EMAIL` = default inbox for the UptimeRobot provision workflow.

## Security

- Never put API keys in `BACKEND_URL`.
- `/health` is intentionally public and dependency-free.
- Do not point keep-alive at authenticated or expensive routes (`/api/v1/...` analysis, metrics with heavy queries, etc.).

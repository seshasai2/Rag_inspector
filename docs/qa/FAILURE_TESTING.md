# Failure Testing (Phase 9)

Documented expected behaviour from code paths (`/ops/ready`, auth deps, ingest, workers).
Do not treat unpaid SaaS outages as product bugs.

| Scenario | How to simulate | Expected behaviour | Recovery |
|----------|-----------------|--------------------|----------|
| Database unavailable | `docker stop raginspector_db` | `/ops/ready` → 503; API errors on DB routes; `/live` may still 200 | Start DB; wait healthy |
| Redis unavailable | `docker stop raginspector_redis` | ready soft/hard fail on redis; ingest may fail enqueue; backlog degraded | Start Redis |
| Worker unavailable | `docker stop raginspector_worker` | Ingest accepts; traces stuck `pending`/`queued`; backlog pending rises | Start worker; reanalyze |
| Invalid login | Wrong password | 401; no tokens | Correct password |
| Expired / bad token | `Authorization: Bearer expired` | 401; frontend refresh then login redirect | Re-login |
| Missing API key | Omit `X-API-Key` on ingest | 401/403 | Use demo key |
| Wrong API key | `ri-nope` | 401 | Use seeded key |
| Network timeout | Low client `--max-time 1` during cold start | Client timeout; server may still process | Retry; warm models |
| Invalid payload | `{}` to ingest | 422 validation | Fix schema |
| Permission denied | Access other user’s pipeline UUID | 403 or 404 | Use own resources |
| Missing files / models | Empty HF cache; warm disabled | Analysis slow/fail; heuristic fallbacks where coded | Pre-download MiniLM + NLI; see COLD_START.md |
| Corrupted data | Manually null critical trace fields | Detail page error or partial; reanalyze | Re-seed `--force` |
| Plan quota exceeded | Free plan spam ingest | 402/403 plan gate | Upgrade plan or reset counter (admin/dev) |
| Email verification gate | `REQUIRE_EMAIL_VERIFICATION=true` unverified user | Login blocked | Verify or disable flag for demo |

## Evidence notes

Prior local runs (Compose verify-ports) observed: ready reports redis failure when Redis stopped; queries persist across backend restart; worker health independent of API liveness.

## What not to claim

Chaos “full resilience” is not guaranteed on free Render (single instance, ephemeral FS, cold start). Failure tests prove **honest degradation**, not HA.

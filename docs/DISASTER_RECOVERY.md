# Disaster Recovery (Phase 8.5)

## Objectives

Define RPO and RTO per customer tier before enterprise launch.

Suggested starting point:

- RPO: 24 hours for standard plans (matches daily `postgres_backup` dumps), shorter for enterprise.
- RTO: 4 hours for standard plans, contract-specific for enterprise.

## Backup service (`postgres_backup`)

Compose services (dev + prod) run a sidecar that:

1. `pg_dump` from host `db` as `$POSTGRES_USER` / `$POSTGRES_DB`
2. Writes `/backups/raginspector_YYYYMMDD_HHMMSS.sql.gz`
3. Deletes dumps older than `BACKUP_RETENTION_DAYS` (default **14**)
4. Sleeps 86400 seconds and repeats

| | Dev | Prod |
|---|-----|------|
| Service | `postgres_backup` | `postgres_backup` |
| Container | `raginspector_backup` | `raginspector_prod_backup` |
| Volume | `postgres_backups` | `postgres_backups` |
| Depends on | `db` healthy | `db` healthy |
| Password | `POSTGRES_PASSWORD` | required via `${POSTGRES_PASSWORD:?…}` |

Dumps live **only on the Compose host volume**. Copy them off-box for real DR.

## List backups

```bash
# Dev
docker compose exec postgres_backup ls -lah /backups

# Prod
docker compose -f docker-compose.prod.yml --env-file .env.production \
  exec postgres_backup ls -lah /backups
```

Windows helper: `.\scripts\list_backups.ps1`  
Shell helper: `./scripts/list_backups.sh`

## Copy a dump to the host

```bash
mkdir -p ./tmp-backups
docker compose cp postgres_backup:/backups/raginspector_YYYYMMDD_HHMMSS.sql.gz ./tmp-backups/
```

## Restore test (non-destructive)

Creates `raginspector_restore_test`, loads a dump, checks readiness, then drops the DB.

```bash
# 1) Pick a dump inside the volume
DUMP=raginspector_YYYYMMDD_HHMMSS.sql.gz
docker compose exec postgres_backup test -f /backups/$DUMP

# 2) Create empty DB
docker compose exec db \
  createdb -U raginspector raginspector_restore_test

# 3) Stream dump into test DB (run from a container that can see both)
docker compose exec -T postgres_backup \
  sh -c "gzip -dc /backups/$DUMP" \
  | docker compose exec -T db \
    psql -U raginspector -d raginspector_restore_test -v ON_ERROR_STOP=1

# 4) Smoke checks
docker compose exec db \
  psql -U raginspector -d raginspector_restore_test -c '\dt'
curl -fsS http://localhost:8000/api/v1/ops/ready   # live stack still healthy

# 5) Cleanup
docker compose exec db \
  dropdb -U raginspector raginspector_restore_test
```

Prod: prefix compose with `-f docker-compose.prod.yml --env-file .env.production`.  
Helper: `./scripts/restore_test.sh <dump-filename>` / `.\scripts\restore_test.ps1 <dump-filename>`.

### Validation checklist

- [ ] At least one `*.sql.gz` exists under `/backups` after the sidecar has run once
- [ ] Restore into `raginspector_restore_test` completes without `ON_ERROR_STOP` errors
- [ ] `\dt` shows expected app tables
- [ ] Live `/api/v1/ops/ready` still returns ready (restore did not touch primary DB)
- [ ] Test DB dropped

**Validated procedure:** commands above match the `postgres_backup` service definition in `docker-compose.yml` / `docker-compose.prod.yml` (Phase 8.5). Run the checklist on your host before go-live and after compose changes to the backup sidecar.

## Kubernetes / managed failure modes

| Failure | Response |
|---------|----------|
| Database corruption | Restore PITR or latest encrypted dump to new instance; update Secret URLs; rolling restart; validate |
| Redis failure | API readiness 503; fail over managed Redis; restart API/workers if connections sticky |
| Worker failure | PDB + restart; scale out; inspect OOM; drain backlog |
| Application failure | Rollout undo / `helm rollback`; check validate Job logs |
| Node failure | Cluster reschedule; PDB keeps quorum |
| Cluster failure | DR region restore from backups + Helm install; DNS cutover |
| Config rollback | `helm rollback`; Secrets from manager previous version |
| Secret compromise | Rotate all keys (`docs/SECRETS.md`); invalidate sessions; audit logs |

RPO/RTO: see Objectives above; Kubernetes production should target **PITR RPO ≤ 5–15 minutes** on managed Postgres.

## Full restore (primary DB — downtime)

1. Stop traffic (LB / nginx).
2. `docker compose stop backend celery_worker celery_beat frontend`
3. Drop/recreate primary DB or restore over a fresh volume (prefer restore to a new volume, then swap).
4. Load dump into `raginspector` (same pipe as restore test, target DB = production name).
5. `alembic upgrade head` if the dump is older than current migrations (usually dumps already include schema).
6. Start services; verify `/api/v1/ops/ready` and login.
7. Resume traffic.

## Rollback (app deploy)

1. Stop traffic at the load balancer.
2. Deploy the previous image.
3. Run migration rollback only if the migration is explicitly reversible and tested.
4. Validate `/api/v1/ops/ready`.
5. Resume traffic.

## Zero-downtime deploys

Use a managed orchestrator or blue-green deployment. Run migrations before shifting traffic, and keep migrations backward-compatible whenever possible.

## Related

- [COMPOSE_PROD.md](COMPOSE_PROD.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [COMPOSE_HEALTH.md](COMPOSE_HEALTH.md)
- [BACKUP.md](BACKUP.md)
- [KUBERNETES.md](KUBERNETES.md)
- [RUNBOOKS.md](RUNBOOKS.md)

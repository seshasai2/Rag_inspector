# Backup strategy

Extends Compose procedures in `docs/DISASTER_RECOVERY.md` for enterprise / Kubernetes.

## What to back up

| Asset | Method | Frequency | Retention |
|-------|--------|-----------|-----------|
| PostgreSQL | Managed PITR + logical `pg_dump` | Continuous PITR + daily dump | PITR ≥ 7d; dumps ≥ 14–30d |
| Redis | AOF/RDB on managed Redis **or** treat as disposable (rehydratable) | Provider default | Match broker durability needs |
| Helm values / ConfigMaps | Git | On change | Forever (git) |
| Secrets | Secret manager versioning | On change | Per policy |
| Model cache PVC | Optional; rebuildable from Hugging Face | Weekly optional | 7d |
| TLS certs | cert-manager / ACM | Automatic | N/A |

## Encryption

- At rest: storage/PITR encryption (provider KMS).
- In transit: TLS to managed DB/Redis.
- Dump objects: SSE-KMS on object storage.

## Verification

Weekly: restore dump into isolated DB (`raginspector_restore_test`), run `\dt`, optional Alembic `current`, destroy test DB. Record in ops calendar.

## Kubernetes / managed

Prefer **provider backups** (RDS/Azure PG/Cloud SQL) over in-cluster CronJobs for production. Optional CronJob pattern:

```bash
# Example only — wire cloud credentials via Secret
kubectl -n raginspector create cronjob pg-dump --image=postgres:16 \
  --schedule="0 2 * * *" -- /bin/sh -c 'pg_dump "$DATABASE_SYNC_URL" | gzip > /backup/…'
```

Compose still provides `postgres_backup` sidecar for single-node prod compose.

## Configuration backups

- Chart values live in git (no secrets).
- Export live ConfigMaps: `kubectl get cm -n raginspector -o yaml > config-backup.yaml` (strip annotations if needed).
- Secrets: export **names/keys only** inventory; restore from secret manager.

# Production Compose (`docker-compose.prod.yml`) — Phase 8.1

Hardened stack for a **fresh build from scratch** (image layers only — no live code bind mounts).

## Differences vs `docker-compose.yml` (dev)

| | Dev | Prod |
|---|-----|------|
| Code | Bind-mount `./backend` | Baked into images |
| Nginx / DB init | Host bind mounts | Baked (`nginx/Dockerfile`, `docker/Dockerfile.db`) |
| Ports | DB/Redis/API/UI published | Only nginx `${HTTP_PORT:-80}` published |
| Secrets | Soft defaults | `${VAR:?required}` for passwords |
| `ENVIRONMENT` | `development` | `production` |
| Worker | `--concurrency=2` | `--concurrency=1` + 3G RAM limit |
| Resources | Unbounded | `deploy.resources` limits on every service |
| Restart | `unless-stopped` | `unless-stopped` (all services) |

Named volumes only: `postgres_data`, `postgres_backups`, `redis_data`, `model_cache`.

## Fresh deploy

```bash
cp .env.production.example .env.production
# Fill SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD, FRONTEND_URL,
# NEXT_PUBLIC_API_URL, ALLOWED_HOSTS, etc.

docker compose -f docker-compose.prod.yml --env-file .env.production config --quiet
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend python scripts/seed_demo.py   # optional
```

Open `http://localhost` (or your host/`HTTP_PORT`).

## Required env (minimum)

From `.env.production.example`:

- `SECRET_KEY` (long random)
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `FRONTEND_URL` (https in real prod)
- `NEXT_PUBLIC_API_URL`
- `ALLOWED_HOSTS`

Compose will refuse to start if `POSTGRES_PASSWORD` / `REDIS_PASSWORD` are unset.

## Resource defaults (tune as needed)

| Service | CPU limit | Memory limit |
|---------|-----------|--------------|
| db | 1.0 | 1G |
| redis | 0.5 | 512M |
| backend | 1.5 | 1G |
| celery_worker | 2.0 | 3G |
| celery_beat | 0.25 | 256M |
| frontend | 0.75 | 512M |
| nginx | 0.5 | 128M |
| postgres_backup | 0.5 | 512M |

Worker memory is sized for local NLI + embedding models ([COLD_START.md](COLD_START.md)).

## Verify

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl -fsS http://localhost/api/v1/ops/ready   # via nginx → backend
```

## Related

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [COMPOSE_HEALTH.md](COMPOSE_HEALTH.md)
- [WORKER.md](WORKER.md)
- HTTPS: [TLS.md](TLS.md) + `docker-compose.prod.tls.yml`

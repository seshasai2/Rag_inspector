# Release process

Path from main branch to a tagged release.

## Preconditions

- `make check-versions` — VERSION aligned across packages
- `make lint` && `make typecheck` && `make test`
- `make release-check` — versions + package SDK + compose config
- Optional: `make helm-validate`, `make sbom`, `make security-bandit`
- `make ci-local` for a broader local gate

## Versioning

Semantic versioning for SDK and API `version` field. Bump:

1. Root / package VERSION files (see `scripts/check_versions.py`)
2. Changelog entry (if maintained)
3. OpenAPI version in FastAPI app when cutting majors

## Build artifacts

| Artifact | Command / path |
|----------|----------------|
| Docker images | Compose / CI build of backend, frontend, worker |
| SDK | `make package-sdk` → wheel/sdist |
| SBOM | `make sbom` (CycloneDX) |

## Deploy sequence

1. Backup Postgres ([BACKUP.md](../BACKUP.md)).
2. Apply migrations (`alembic upgrade head`) before or as init job.
3. Roll API/frontend; then workers; beat last (single replica).
4. `make validate-release` or scripted `/live` + UI checks.
5. Watch `/ops/backlog` and error logs for 30–60 minutes.

## Rollback

1. Redeploy previous image tags.
2. Avoid downgrading migrations unless a tested down revision exists — prefer forward fixes.
3. Invalidate dashboard cache if stale aggregates confuse operators.

## Communication

- Note feature flags / experimental routes ([EXPERIMENTAL.md](../EXPERIMENTAL.md)).
- Attach loadtest smoke results for high-risk releases.
- Enterprise customers: mention SSO/SCIM changes explicitly in release notes.

Related: [OPERATIONS.md](OPERATIONS.md), [SUPPLY_CHAIN.md](../SUPPLY_CHAIN.md).

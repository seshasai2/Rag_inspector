# Folder structure

Repository layout for contributors. Trimmed to durable packages (ignore build artifacts and `node_modules`).

```text
raginspector/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # HTTP routers
│   │   ├── core/               # config, security, rate limit, pagination
│   │   ├── db/                 # engine + session
│   │   ├── models/             # SQLAlchemy models
│   │   ├── repositories/       # optional query helpers
│   │   ├── schemas/            # Pydantic I/O
│   │   ├── services/           # domain logic
│   │   └── workers/            # Celery app + tasks
│   ├── alembic/                # migrations
│   ├── scripts/                # seed, utilities
│   └── tests/                  # unit + integration
├── frontend/
│   ├── src/app/                # Next.js App Router
│   ├── src/components/         # UI including grounding
│   └── e2e/                    # Playwright (optional scripts)
├── sdk/                        # Python client /decorators
├── docs/                       # architecture, demos, engineering
├── loadtests/                  # k6 + Locust
├── infrastructure/             # Terraform, Kubernetes, Helm bits
├── infra/                      # Observability assets
├── docker-compose*.yml
├── Makefile
├── PROJECT_GUIDE.md          # canonical engineering guide
└── docs/engineering/PERFORMANCE.md
```

## Placement rules

| Change | Put it in |
|--------|-----------|
| New REST route | `backend/app/api/v1/endpoints/` + router include |
| Business rule | `backend/app/services/` |
| Table / column | `models/` + Alembic revision |
| Background job | `workers/tasks.py` or dedicated worker module |
| Dashboard page | `frontend/src/app/(app)/...` |
| Shared widget | `frontend/src/components/` |
| Public API docs | `docs/API.md` + collections |
| Architecture diagram | `docs/architecture/` |

Do not add parallel `utils/` dumping grounds; prefer named services.

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    audit,
    auth,
    autofix,
    benchmark,
    billing,
    chunks,
    documents,
    identity,
    ingest,
    integrations,
    investigator,
    keys,
    knowledge,
    metrics,
    monitoring,
    ops,
    organizations,
    pipelines,
    queries,
    regression,
    reports,
    scim,
    settings,
    studio,
    traces,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(keys.router, prefix="/keys", tags=["API Keys"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["SDK Ingest"])
api_router.include_router(traces.router, prefix="/traces", tags=["SDK Ingest"])
api_router.include_router(queries.router, prefix="/queries", tags=["Query Traces"])
api_router.include_router(chunks.router, prefix="/chunks", tags=["Chunks"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Gaps"])
api_router.include_router(autofix.router, prefix="/autofix", tags=["Autofix"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(regression.router, prefix="/regression", tags=["Regression"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])
api_router.include_router(studio.router, prefix="/studio", tags=["Studio"])
api_router.include_router(investigator.router, prefix="/investigator", tags=["Investigator"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(ops.router, prefix="/ops", tags=["Operations"])
api_router.include_router(admin.router, prefix="/admin", tags=["Support Admin"])
api_router.include_router(identity.router, prefix="/identity", tags=["Identity"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(scim.router, prefix="/scim/v2", tags=["SCIM"])

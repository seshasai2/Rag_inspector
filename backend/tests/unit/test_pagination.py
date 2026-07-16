"""Pagination hard caps (Phase 6.4)."""
from __future__ import annotations

import inspect

from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from app.core import pagination as pg
from app.api.v1.endpoints import (
    admin,
    audit,
    chunks,
    identity,
    integrations,
    keys,
    organizations,
    pipelines,
    queries,
    reports,
    scim,
)


def test_pagination_constants():
    assert pg.DEFAULT_PER_PAGE == 20
    assert pg.MAX_PER_PAGE == 100
    assert pg.DEFAULT_LIMIT == 50
    assert pg.MAX_LIMIT == 100
    assert pg.MAX_ADMIN_LIMIT == 200
    assert pg.page_offset(2, 20) == 20


def test_oversize_per_page_rejected_by_fastapi():
    app = FastAPI()

    @app.get("/items")
    async def items(per_page: pg.PerPageParam = pg.DEFAULT_PER_PAGE):
        return {"per_page": per_page}

    client = TestClient(app)
    assert client.get("/items").json()["per_page"] == 20
    assert client.get("/items", params={"per_page": 100}).status_code == 200
    blocked = client.get("/items", params={"per_page": 101})
    assert blocked.status_code == 422


def test_oversize_admin_limit_rejected():
    app = FastAPI()

    @app.get("/rows")
    async def rows(limit: pg.AdminLimitParam = pg.DEFAULT_LIMIT):
        return {"limit": limit}

    client = TestClient(app)
    assert client.get("/rows", params={"limit": 200}).status_code == 200
    assert client.get("/rows", params={"limit": 201}).status_code == 422


def _has_capped_limit_or_per_page(fn) -> bool:
    capped = (pg.LimitParam, pg.PerPageParam, pg.AdminLimitParam)
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if name not in {"limit", "per_page"}:
            continue
        ann = param.annotation
        if ann in capped:
            return True
        ann_s = str(ann)
        if "LimitParam" in ann_s or "PerPageParam" in ann_s or "AdminLimitParam" in ann_s:
            return True
    return False


def test_list_endpoints_declare_capped_params():
    for fn in (
        queries.list_queries,
        chunks.list_chunks,
        keys.list_keys,
        pipelines.list_pipelines,
        organizations.list_members,
        scim.list_scim_users,
        integrations.list_webhooks,
        integrations.list_deliveries,
        identity.list_sso_connections,
        reports.report_history,
        admin.list_users,
        admin.failed_jobs,
        admin.recent_webhooks,
        audit.list_audit_logs,
    ):
        assert _has_capped_limit_or_per_page(fn), f"{fn.__name__} missing capped limit/per_page"

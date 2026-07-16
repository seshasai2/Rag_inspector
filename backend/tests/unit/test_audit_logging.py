"""Audit logging coverage (Phase 5.9)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints import audit as audit_endpoint
from app.api.v1.endpoints import keys as keys_endpoint
from app.services.audit import AuditAction, record_audit


@pytest.mark.asyncio
async def test_record_audit_persists_canonical_action():
    db = MagicMock()
    db.add = MagicMock()
    user = MagicMock()
    user.id = "u1"
    user.organization_id = "org1"

    entry = await record_audit(
        db,
        user,
        AuditAction.AUTH_LOGIN,
        "user",
        "u1",
        {"via": "password"},
        ip_address="1.2.3.4",
    )
    db.add.assert_called_once()
    assert entry.action == AuditAction.AUTH_LOGIN
    assert entry.user_id == "u1"
    assert entry.organization_id == "org1"
    assert json.loads(entry.metadata_json) == {"via": "password"}
    assert entry.ip_address == "1.2.3.4"


@pytest.mark.asyncio
async def test_list_audit_logs_filters_by_action():
    row = MagicMock()
    row.id = "a1"
    row.organization_id = "org1"
    row.user_id = "u1"
    row.action = AuditAction.API_KEY_ROTATED
    row.target_type = "api_key"
    row.target_id = "k2"
    row.metadata_json = json.dumps({"revoked_key_id": "k1"})
    row.ip_address = None
    row.user_agent = None
    row.created_at = "2026-01-01T00:00:00Z"

    result = MagicMock()
    result.scalars.return_value.all.return_value = [row]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    current = MagicMock()
    current.organization_id = "org1"
    current.id = "u1"

    with patch.object(audit_endpoint, "require_role", return_value=lambda: current):
        rows = await audit_endpoint.list_audit_logs(
            current_user=current,
            _=current,
            db=db,
            limit=50,
            action=AuditAction.API_KEY_ROTATED,
            target_type="api_key",
            since=None,
        )
    assert len(rows) == 1
    assert rows[0]["action"] == AuditAction.API_KEY_ROTATED
    assert rows[0]["metadata"]["revoked_key_id"] == "k1"


@pytest.mark.asyncio
async def test_rotate_key_revokes_old_and_audits():
    from datetime import datetime, timezone
    import uuid

    old = MagicMock()
    old.id = "old-id"
    old.is_active = True
    old.name = "prod"
    old.scopes = json.dumps(["ingest:write"])

    result = MagicMock()
    result.scalar_one_or_none.return_value = old
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh(obj):
        obj.id = str(uuid.uuid4())
        obj.is_active = True
        obj.created_at = datetime.now(timezone.utc)
        obj.last_used_at = None

    db.refresh = AsyncMock(side_effect=_refresh)

    user = MagicMock()
    user.id = "u1"
    user.organization_id = "org1"

    with (
        patch.object(keys_endpoint, "generate_api_key", return_value=("ri-new", "hash")),
        patch.object(keys_endpoint, "get_key_prefix", return_value="ri-newxxxx"),
        patch.object(keys_endpoint, "record_audit", AsyncMock()) as audit,
    ):
        created = await keys_endpoint.rotate_key(
            key_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            current_user=user,
            db=db,
        )

    assert old.is_active is False
    assert created.raw_key == "ri-new"
    audit.assert_awaited()
    assert audit.await_args.args[2] == AuditAction.API_KEY_ROTATED


def test_canonical_actions_cover_roadmap_surfaces():
    assert AuditAction.AUTH_LOGIN.startswith("auth.")
    assert AuditAction.API_KEY_ROTATED.startswith("api_key.")
    assert AuditAction.BILLING_PLAN_CHANGED.startswith("billing.")
    assert AuditAction.SUPPORT_USER_STATUS.startswith("support.")

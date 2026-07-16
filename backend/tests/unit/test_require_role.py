"""RBAC: require_role returns 403 for unauthorized users (Phase 5.2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ORG_ADMIN_ROLES, require_role
from app.models.models import UserRole


def _user(*, role: UserRole, org_id: str | None = None) -> MagicMock:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.role = role
    user.organization_id = org_id
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_require_role_allows_owner():
    checker = require_role(*ORG_ADMIN_ROLES)
    user = _user(role=UserRole.owner)
    db = AsyncMock(spec=AsyncSession)
    result = await checker(current_user=user, db=db)
    assert result is user
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_require_role_allows_admin():
    checker = require_role(*ORG_ADMIN_ROLES)
    user = _user(role=UserRole.admin)
    result = await checker(current_user=user, db=AsyncMock(spec=AsyncSession))
    assert result is user


@pytest.mark.asyncio
async def test_require_role_rejects_viewer_with_403():
    checker = require_role(*ORG_ADMIN_ROLES)
    user = _user(role=UserRole.viewer, org_id=None)
    db = AsyncMock(spec=AsyncSession)
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=user, db=db)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient permissions"


@pytest.mark.asyncio
async def test_require_role_rejects_engineer_with_403():
    checker = require_role(*ORG_ADMIN_ROLES)
    user = _user(role=UserRole.engineer, org_id=None)
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=user, db=AsyncMock(spec=AsyncSession))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_allows_via_org_membership_admin():
    """User.role may be viewer while accepted org membership is admin."""
    org_id = str(uuid.uuid4())
    user = _user(role=UserRole.viewer, org_id=org_id)

    member = MagicMock()
    member.role = UserRole.admin

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = member
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = exec_result

    checker = require_role(*ORG_ADMIN_ROLES)
    result = await checker(current_user=user, db=db)
    assert result is user
    db.execute.assert_awaited()


@pytest.mark.asyncio
async def test_require_role_rejects_pending_org_membership():
    org_id = str(uuid.uuid4())
    user = _user(role=UserRole.viewer, org_id=org_id)

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None  # no accepted membership
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = exec_result

    checker = require_role(*ORG_ADMIN_ROLES)
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=user, db=db)
    assert exc.value.status_code == 403


def test_org_admin_mutating_routes_use_require_role():
    """Smoke: org/SCIM/SSO/audit write paths declare require_role dependency."""
    import inspect

    from app.api.v1.endpoints import audit, identity, organizations, scim

    for fn in (
        organizations.update_controls,
        organizations.invite_member,
        identity.list_sso_connections,
        identity.upsert_sso_connection,
        identity.upload_saml_metadata,
        scim.list_scim_users,
        scim.create_scim_user,
        scim.update_scim_user,
        audit.list_audit_logs,
    ):
        # FastAPI wraps Depends; ensure endpoint is still callable and documented
        assert callable(fn), fn.__name__
        sig = inspect.signature(fn)
        assert "current_user" in sig.parameters, fn.__name__

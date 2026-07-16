"""Email verification login gate (Phase 5.4)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.api.v1.endpoints import auth as auth_endpoints
from tests.conftest import make_http_request


def test_require_email_verification_defaults_false_outside_production():
    s = Settings(
        ENVIRONMENT="development",
        REQUIRE_EMAIL_VERIFICATION=None,
        SECRET_KEY="x" * 32,
    )
    assert s.email_verification_required() is False


def test_require_email_verification_defaults_true_in_production():
    s = Settings(
        ENVIRONMENT="production",
        REQUIRE_EMAIL_VERIFICATION=None,
        SECRET_KEY="x" * 32,
    )
    assert s.email_verification_required() is True


def test_require_email_verification_explicit_override():
    soft = Settings(
        ENVIRONMENT="production",
        REQUIRE_EMAIL_VERIFICATION=False,
        SECRET_KEY="x" * 32,
    )
    hard = Settings(
        ENVIRONMENT="development",
        REQUIRE_EMAIL_VERIFICATION=True,
        SECRET_KEY="x" * 32,
    )
    assert soft.email_verification_required() is False
    assert hard.email_verification_required() is True


@pytest.mark.asyncio
async def test_login_blocks_unverified_when_gate_enabled():
    user = MagicMock()
    user.password_hash = "hashed"
    user.is_active = True
    user.email_verified = False
    user.id = "u1"

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    payload = MagicMock()
    payload.email = "a@example.com"
    payload.password = "Password1"

    with (
        patch.object(auth_endpoints, "verify_password", return_value=True),
        patch.object(auth_endpoints.app_settings, "REQUIRE_EMAIL_VERIFICATION", True),
    ):
        with pytest.raises(HTTPException) as exc:
            await auth_endpoints.login(request=make_http_request("/api/v1/auth/login"), payload=payload, db=db)

    assert exc.value.status_code == 403
    assert "Email not verified" in exc.value.detail


@pytest.mark.asyncio
async def test_login_allows_unverified_when_soft_gate():
    user = MagicMock()
    user.password_hash = "hashed"
    user.is_active = True
    user.email_verified = False
    user.id = "u1"

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    payload = MagicMock()
    payload.email = "a@example.com"
    payload.password = "Password1"
    payload.mfa_code = None
    payload.device_token = None

    async def _audit(*_a, **_k):
        return None

    with (
        patch.object(auth_endpoints, "verify_password", return_value=True),
        patch.object(auth_endpoints, "create_access_token", return_value="access"),
        patch.object(auth_endpoints, "create_refresh_token", return_value="refresh"),
        patch.object(auth_endpoints, "record_audit", side_effect=_audit),
        patch.object(auth_endpoints, "user_has_enabled_mfa", AsyncMock(return_value=False)),
        patch.object(auth_endpoints.app_settings, "REQUIRE_EMAIL_VERIFICATION", False),
        patch.object(auth_endpoints.app_settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7),
    ):
        tokens = await auth_endpoints.login(
            request=make_http_request("/api/v1/auth/login"), payload=payload, db=db
        )

    assert tokens.access_token == "access"
    assert tokens.refresh_token == "refresh"

"""MFA login enforcement (Phase 5.5)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import auth as auth_endpoints
from app.core.security import create_mfa_challenge_token, encrypt_secret
from app.services import mfa as mfa_service
from tests.conftest import make_http_request


@pytest.mark.asyncio
async def test_user_has_enabled_mfa():
    result = MagicMock()
    result.scalar_one_or_none.return_value = "factor-id"
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    assert await mfa_service.user_has_enabled_mfa(db, "u1") is True

    result.scalar_one_or_none.return_value = None
    assert await mfa_service.user_has_enabled_mfa(db, "u1") is False


@pytest.mark.asyncio
async def test_verify_totp_against_enabled_factor():
    secret = pyotp.random_base32()
    factor = MagicMock()
    factor.secret_ref = encrypt_secret(secret)

    factors = MagicMock()
    factors.scalars.return_value.all.return_value = [factor]
    recovery = MagicMock()
    recovery.scalar_one_or_none.return_value = None

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[factors, recovery])

    code = pyotp.TOTP(secret).now()
    assert await mfa_service.verify_totp_or_recovery(db, "u1", code) is True


@pytest.mark.asyncio
async def test_login_returns_mfa_challenge_without_tokens():
    user = MagicMock()
    user.password_hash = "hashed"
    user.is_active = True
    user.email_verified = True
    user.id = "u-mfa"

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    payload = MagicMock()
    payload.email = "a@example.com"
    payload.password = "Password1"
    payload.mfa_code = None
    payload.device_token = None

    with (
        patch.object(auth_endpoints, "verify_password", return_value=True),
        patch.object(auth_endpoints.app_settings, "REQUIRE_EMAIL_VERIFICATION", False),
        patch.object(auth_endpoints, "user_has_enabled_mfa", AsyncMock(return_value=True)),
        patch.object(auth_endpoints, "remembered_device_valid", AsyncMock(return_value=False)),
        patch.object(auth_endpoints, "create_mfa_challenge_token", return_value="challenge-jwt"),
    ):
        response = await auth_endpoints.login(request=make_http_request("/api/v1/auth/login"), payload=payload, db=db)

    assert response.mfa_required is True
    assert response.mfa_token == "challenge-jwt"
    assert response.access_token is None
    assert response.refresh_token is None


@pytest.mark.asyncio
async def test_login_with_valid_mfa_code_issues_tokens():
    user = MagicMock()
    user.password_hash = "hashed"
    user.is_active = True
    user.email_verified = True
    user.id = "u-mfa"

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    payload = MagicMock()
    payload.email = "a@example.com"
    payload.password = "Password1"
    payload.mfa_code = "123456"
    payload.device_token = None

    async def _audit(*_a, **_k):
        return None

    with (
        patch.object(auth_endpoints, "verify_password", return_value=True),
        patch.object(auth_endpoints.app_settings, "REQUIRE_EMAIL_VERIFICATION", False),
        patch.object(auth_endpoints, "user_has_enabled_mfa", AsyncMock(return_value=True)),
        patch.object(auth_endpoints, "remembered_device_valid", AsyncMock(return_value=False)),
        patch.object(auth_endpoints, "verify_totp_or_recovery", AsyncMock(return_value=True)),
        patch.object(auth_endpoints, "create_access_token", return_value="access"),
        patch.object(auth_endpoints, "create_refresh_token", return_value="refresh"),
        patch.object(auth_endpoints, "record_audit", side_effect=_audit),
        patch.object(auth_endpoints.app_settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7),
    ):
        response = await auth_endpoints.login(request=make_http_request("/api/v1/auth/login"), payload=payload, db=db)

    assert response.mfa_required is False
    assert response.access_token == "access"
    assert response.refresh_token == "refresh"


@pytest.mark.asyncio
async def test_login_mfa_rejects_password_bypass_via_access_token_type():
    """mfa_challenge tokens must not be accepted as refresh/access."""
    token = create_mfa_challenge_token("u1")
    payload = MagicMock()
    payload.mfa_token = token
    payload.code = "000000"
    payload.remember_device = False

    db = MagicMock()
    db.execute = AsyncMock()

    with patch.object(auth_endpoints, "user_has_enabled_mfa", AsyncMock(return_value=True)):
        with patch.object(auth_endpoints, "verify_totp_or_recovery", AsyncMock(return_value=False)):
            # Need user lookup to succeed first
            user = MagicMock()
            user.id = "u1"
            user.is_active = True
            result = MagicMock()
            result.scalar_one_or_none.return_value = user
            db.execute = AsyncMock(return_value=result)

            with pytest.raises(HTTPException) as exc:
                await auth_endpoints.login_mfa(request=make_http_request("/api/v1/auth/login"), payload=payload, db=db)
            assert exc.value.status_code == 401
            assert "Invalid MFA code" in exc.value.detail


@pytest.mark.asyncio
async def test_login_mfa_completes_with_valid_code():
    user = MagicMock()
    user.id = "u1"
    user.is_active = True

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    payload = MagicMock()
    payload.mfa_token = create_mfa_challenge_token("u1")
    payload.code = "123456"
    payload.remember_device = False

    async def _audit(*_a, **_k):
        return None

    with (
        patch.object(auth_endpoints, "user_has_enabled_mfa", AsyncMock(return_value=True)),
        patch.object(auth_endpoints, "verify_totp_or_recovery", AsyncMock(return_value=True)),
        patch.object(auth_endpoints, "create_access_token", return_value="access"),
        patch.object(auth_endpoints, "create_refresh_token", return_value="refresh"),
        patch.object(auth_endpoints, "record_audit", side_effect=_audit),
        patch.object(auth_endpoints.app_settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7),
    ):
        response = await auth_endpoints.login_mfa(request=make_http_request("/api/v1/auth/login"), payload=payload, db=db)

    assert response.access_token == "access"
    assert response.refresh_token == "refresh"
    assert response.mfa_required is False

"""Audit log writer + canonical action names (Phase 5.9)."""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog, User


# Canonical actions — keep stable for filtering via GET /audit-logs?action=
class AuditAction:
    AUTH_REGISTER = "auth.register"
    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_MFA_FAILED = "auth.mfa_failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_EMAIL_VERIFIED = "auth.email_verified"
    AUTH_PASSWORD_CHANGED = "auth.password_changed"
    AUTH_PASSWORD_RESET = "auth.password_reset"

    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    API_KEY_ROTATED = "api_key.rotated"

    BILLING_SUBSCRIPTION_CREATED = "billing.subscription_created"
    BILLING_SUBSCRIPTION_CANCELLED = "billing.subscription_cancelled"
    BILLING_PLAN_CHANGED = "billing.plan_changed"

    SUPPORT_USER_STATUS = "support.user_status_changed"
    SUPPORT_IMPERSONATION = "support.impersonation_requested"


def request_client_meta(request: Request | None) -> tuple[Optional[str], Optional[str]]:
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("user-agent")
    return ip, ua


async def record_audit(
    db: AsyncSession,
    user: Optional[User],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=getattr(user, "organization_id", None),
        user_id=getattr(user, "id", None),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        metadata_json=json.dumps(metadata or {}),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    return entry

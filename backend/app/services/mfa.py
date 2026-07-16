"""MFA helpers for login enforcement (TOTP + recovery codes)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.models.models import MFAFactor, MFARecoveryCode, RememberedDevice


async def user_has_enabled_mfa(db: AsyncSession, user_id: str) -> bool:
    result = await db.execute(
        select(MFAFactor.id)
        .where(
            MFAFactor.user_id == user_id,
            MFAFactor.enabled.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def verify_totp_or_recovery(db: AsyncSession, user_id: str, code: str) -> bool:
    """Validate a TOTP code against any enabled factor, or a single-use recovery code."""
    code = (code or "").strip()
    if not code:
        return False

    result = await db.execute(
        select(MFAFactor).where(
            MFAFactor.user_id == user_id,
            MFAFactor.enabled.is_(True),
        )
    )
    for factor in result.scalars().all():
        if not factor.secret_ref:
            continue
        try:
            secret = decrypt_secret(factor.secret_ref)
            if pyotp.TOTP(secret).verify(code, valid_window=1):
                return True
        except Exception:
            continue

    code_hash = hashlib.sha256(code.encode()).hexdigest()
    result = await db.execute(
        select(MFARecoveryCode).where(
            MFARecoveryCode.user_id == user_id,
            MFARecoveryCode.code_hash == code_hash,
            MFARecoveryCode.used_at.is_(None),
        )
    )
    recovery = result.scalar_one_or_none()
    if not recovery:
        return False
    recovery.used_at = datetime.now(timezone.utc)
    return True


async def remembered_device_valid(
    db: AsyncSession,
    user_id: str,
    device_token: str | None,
) -> bool:
    if not isinstance(device_token, str) or not device_token.strip():
        return False
    device_hash = hashlib.sha256(device_token.encode()).hexdigest()
    result = await db.execute(
        select(RememberedDevice).where(
            RememberedDevice.user_id == user_id,
            RememberedDevice.device_hash == device_hash,
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return False
    expires = device.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires >= datetime.now(timezone.utc)


async def create_remembered_device(db: AsyncSession, user_id: str) -> str:
    """Persist a remembered device and return the raw device token (show once)."""
    import secrets
    from datetime import timedelta

    raw = secrets.token_urlsafe(32)
    db.add(
        RememberedDevice(
            user_id=user_id,
            device_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
    )
    return raw

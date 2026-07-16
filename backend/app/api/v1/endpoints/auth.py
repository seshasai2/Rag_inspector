import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings as app_settings
from app.core.rate_limit import (
    AUTH_LOGIN_LIMIT,
    AUTH_PASSWORD_RESET_LIMIT,
    AUTH_REFRESH_LIMIT,
    AUTH_REGISTER_LIMIT,
    AUTH_RESEND_VERIFY_LIMIT,
    AUTH_VERIFY_EMAIL_LIMIT,
    limiter,
)
from app.core.jwt_denylist import deny_access_jti, remaining_ttl_seconds
from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.models import (
    Organization,
    OrganizationMember,
    RefreshToken,
    User,
    UserRole,
    UserSettings,
)
from app.schemas.schemas import (
    LoginResponse,
    LogoutRequest,
    MFALoginComplete,
    PasswordChange,
    RefreshRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
    UserUpdate,
)
from app.services.audit import AuditAction, record_audit, request_client_meta
from app.services.email_service import (
    render_password_reset_email,
    render_verification_email,
    render_welcome_email,
    send_email,
)
from app.services.mfa import (
    create_remembered_device,
    remembered_device_valid,
    user_has_enabled_mfa,
    verify_totp_or_recovery,
)

router = APIRouter()
logger = structlog.get_logger()


def make_org_slug(name: str, email: str) -> str:
    base = name or email.split("@")[0]
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return f"{slug or 'workspace'}-{secrets.token_hex(3)}"


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit(AUTH_REGISTER_LIMIT)
async def register(payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    verification_token_hash = hash_token(verification_token)

    organization = Organization(
        name=f"{payload.name}'s workspace",
        slug=make_org_slug(payload.name, payload.email),
    )
    db.add(organization)
    await db.flush()

    user = User(
        organization_id=organization.id,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        email_verified=False,
        email_verification_token=verification_token_hash,
        email_verification_sent_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    db.add(
        OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=UserRole.owner,
            accepted_at=datetime.now(timezone.utc),
        )
    )

    # Create default settings (handle orphaned records)
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    existing_settings = result.scalar_one_or_none()
    if not existing_settings:
        user_settings = UserSettings(user_id=user.id)
        db.add(user_settings)

    ip, ua = request_client_meta(request)
    await record_audit(
        db, user, AuditAction.AUTH_REGISTER, "user", user.id, ip_address=ip, user_agent=ua
    )
    await db.commit()
    await db.refresh(user)

    # Send verification email (fire-and-forget style via background)
    verification_url = f"{app_settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
    html_body = render_verification_email(user.name, verification_url)
    await send_email(
        to_email=user.email,
        subject="Verify your email — RAGInspector",
        html_body=html_body,
    )

    logger.info("User registered", user_id=str(user.id), email=user.email, verification_sent=True)
    return user


@router.get("/verify-email")
@limiter.limit(AUTH_VERIFY_EMAIL_LIMIT)
async def verify_email(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    """Verify email address via token."""
    result = await db.execute(
        select(User).where(
            User.email_verification_token == hash_token(token),
            User.email_verified == False,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    # Check if token is expired (24 hours)
    if user.email_verification_sent_at:
        sent_at = user.email_verification_sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - sent_at > timedelta(hours=24):
            raise HTTPException(
                status_code=400, detail="Verification link expired. Please request a new one."
            )

    user.email_verified = True
    user.email_verification_token = None
    ip, ua = request_client_meta(request)
    await record_audit(
        db, user, AuditAction.AUTH_EMAIL_VERIFIED, "user", user.id, ip_address=ip, user_agent=ua
    )
    await db.commit()

    # Send welcome email
    dashboard_url = f"{app_settings.FRONTEND_URL}/dashboard"
    html_body = render_welcome_email(user.name, dashboard_url)
    await send_email(
        to_email=user.email,
        subject="Welcome to RAGInspector!",
        html_body=html_body,
    )

    logger.info("Email verified", user_id=str(user.id))
    return {"message": "Email verified successfully! Welcome to RAGInspector."}


@router.post("/resend-verification")
@limiter.limit(AUTH_RESEND_VERIFY_LIMIT)
async def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resend verification email (public — login may be blocked until verified)."""
    # Do not reveal whether the account exists or is already verified.
    generic = {"message": "If an unverified account exists, a verification email has been sent"}

    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user or user.email_verified:
        return generic

    verification_token = secrets.token_urlsafe(32)
    user.email_verification_token = hash_token(verification_token)
    user.email_verification_sent_at = datetime.now(timezone.utc)
    await db.commit()

    verification_url = f"{app_settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
    html_body = render_verification_email(user.name, verification_url)
    await send_email(
        to_email=user.email,
        subject="Verify your email — RAGInspector",
        html_body=html_body,
    )

    return generic


@router.post("/forgot-password")
@limiter.limit(AUTH_PASSWORD_RESET_LIMIT)
async def forgot_password(request: Request, email: str, db: AsyncSession = Depends(get_db)):
    """Send password reset email."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        # Don't reveal if email exists
        return {"message": "If an account exists, a password reset email has been sent"}

    # Generate reset token (expires in 1 hour)
    reset_token = secrets.token_urlsafe(32)
    user.password_reset_token = hash_token(reset_token)
    user.password_reset_sent_at = datetime.now(timezone.utc)
    await db.commit()

    reset_url = f"{app_settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
    html_body = render_password_reset_email(user.name, reset_url)
    await send_email(
        to_email=user.email,
        subject="Reset your password — RAGInspector",
        html_body=html_body,
    )

    logger.info("Password reset email sent", user_id=str(user.id))
    return {"message": "If an account exists, a password reset email has been sent"}


@router.post("/reset-password")
@limiter.limit(AUTH_PASSWORD_RESET_LIMIT)
async def reset_password(
    request: Request,
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token."""
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    result = await db.execute(
        select(User).where(
            User.password_reset_token == hash_token(token),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Check if token is expired (1 hour)
    if user.password_reset_sent_at:
        sent_at = user.password_reset_sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - sent_at > timedelta(hours=1):
            raise HTTPException(
                status_code=400, detail="Reset link expired. Please request a new one."
            )

    user.password_hash = get_password_hash(new_password)
    user.password_reset_token = None
    ip, ua = request_client_meta(request)
    await record_audit(
        db, user, AuditAction.AUTH_PASSWORD_RESET, "user", user.id, ip_address=ip, user_agent=ua
    )
    await db.commit()

    logger.info("Password reset completed", user_id=str(user.id))
    return {"message": "Password reset successfully"}


@router.post("/login", response_model=LoginResponse)
@limiter.limit(AUTH_LOGIN_LIMIT)
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        ip, ua = request_client_meta(request)
        await record_audit(
            db,
            None,
            AuditAction.AUTH_LOGIN_FAILED,
            target_type="user",
            metadata={"email": payload.email.lower()[:120]},
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    if app_settings.email_verification_required() and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Email not verified. Check your inbox for the verification link, "
                "or POST /api/v1/auth/resend-verification with your email."
            ),
        )

    mfa_enabled = await user_has_enabled_mfa(db, user.id)
    if mfa_enabled:
        device_ok = await remembered_device_valid(db, user.id, payload.device_token)
        if not device_ok:
            if payload.mfa_code:
                if not await verify_totp_or_recovery(db, user.id, payload.mfa_code):
                    ip, ua = request_client_meta(request)
                    await record_audit(
                        db,
                        user,
                        AuditAction.AUTH_MFA_FAILED,
                        target_type="user",
                        target_id=str(user.id),
                        ip_address=ip,
                        user_agent=ua,
                    )
                    await db.commit()
                    raise HTTPException(status_code=401, detail="Invalid MFA code")
            else:
                # Password alone is not enough — return challenge, no session tokens.
                return LoginResponse(
                    mfa_required=True,
                    mfa_token=create_mfa_challenge_token(user.id),
                )

    return await _issue_login_tokens(db, user, request=request)


@router.post("/login/mfa", response_model=LoginResponse)
@limiter.limit(AUTH_LOGIN_LIMIT)
async def login_mfa(
    request: Request,
    payload: MFALoginComplete,
    db: AsyncSession = Depends(get_db),
):
    """Complete login after password step when MFA is enrolled."""
    try:
        data = decode_token(payload.mfa_token)
        if data.get("type") != "mfa_challenge":
            raise HTTPException(status_code=401, detail="Invalid MFA challenge")
        user_id = data.get("sub")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA challenge")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid MFA challenge")
    if not await user_has_enabled_mfa(db, user.id):
        raise HTTPException(status_code=400, detail="MFA is not enabled for this account")
    if not await verify_totp_or_recovery(db, user.id, payload.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    device_token = None
    if payload.remember_device:
        device_token = await create_remembered_device(db, user.id)

    response = await _issue_login_tokens(db, user, request=request)
    response.device_token = device_token
    return response


async def _issue_login_tokens(
    db: AsyncSession,
    user: User,
    *,
    request: Request | None = None,
) -> LoginResponse:
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_raw = create_refresh_token({"sub": str(user.id)})

    token_hash = hashlib.sha256(refresh_token_raw.encode()).hexdigest()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=app_settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    ip, ua = request_client_meta(request)
    await record_audit(
        db, user, AuditAction.AUTH_LOGIN, "user", user.id, ip_address=ip, user_agent=ua
    )
    await db.commit()

    return LoginResponse(access_token=access_token, refresh_token=refresh_token_raw)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def refresh(request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = data.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at == None,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")
    # Handle timezone-naive comparison (SQLite stores naive datetimes)
    now = datetime.now(timezone.utc)
    expires = rt.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    # Rotate token
    rt.revoked_at = now

    access_token = create_access_token({"sub": user_id})
    new_refresh_raw = create_refresh_token({"sub": user_id})
    new_hash = hashlib.sha256(new_refresh_raw.encode()).hexdigest()
    new_rt = RefreshToken(
        user_id=user_id,
        token_hash=new_hash,
        expires_at=now + timedelta(days=app_settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_rt)
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_raw)


@router.post("/logout")
async def logout(request: Request, payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    user = None
    if rt:
        rt.revoked_at = now
        user_result = await db.execute(select(User).where(User.id == rt.user_id))
        user = user_result.scalar_one_or_none()
        if payload.revoke_all_sessions and user:
            all_tokens = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at == None,
                )
            )
            for other in all_tokens.scalars().all():
                other.revoked_at = now
        ip, ua = request_client_meta(request)
        await record_audit(
            db,
            user,
            AuditAction.AUTH_LOGOUT,
            "user",
            getattr(user, "id", None),
            ip_address=ip,
            user_agent=ua,
            metadata={
                "revoke_all_sessions": payload.revoke_all_sessions,
                "access_denylisted": bool(payload.access_token),
            },
        )
        await db.commit()

    # Denylist access jti until natural expiry (best-effort if Redis available).
    if payload.access_token:
        try:
            access_payload = decode_token(payload.access_token)
            if access_payload.get("type") == "access" and access_payload.get("jti"):
                ttl = remaining_ttl_seconds(access_payload.get("exp"))
                deny_access_jti(str(access_payload["jti"]), ttl)
        except Exception:
            pass

    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.name:
        current_user.name = payload.name
    if payload.email:
        current_user.email = payload.email.lower()
    await record_audit(
        db,
        current_user,
        "configuration.changed",
        "user",
        current_user.id,
        {"fields": [f for f in ("name", "email") if getattr(payload, f)]},
    )
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(payload.new_password)
    await record_audit(db, current_user, AuditAction.AUTH_PASSWORD_CHANGED, "user", current_user.id)
    await db.commit()
    return {"message": "Password updated"}


@router.post("/complete-onboarding")
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.onboarding_completed = True
    await db.commit()
    return {"message": "Onboarding completed"}

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ORG_ADMIN_ROLES, get_current_user, require_min_plan, require_role
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.core.security import decrypt_secret, encrypt_secret
from app.db.session import get_db
from app.models.models import (
    MFAFactor,
    MFARecoveryCode,
    Organization,
    RememberedDevice,
    SSOConnection,
    User,
)
from app.services.audit import record_audit

router = APIRouter()

SSO_PROVIDERS = {"google", "microsoft", "github", "okta"}
_SSO_PLAN = FEATURE_MIN_PLAN["sso"]


class SSOConnectionIn(BaseModel):
    provider: str
    issuer_url: str | None = None
    client_id: str | None = None
    client_secret_ref: str | None = None
    enabled: bool = False


class MFAEnrollIn(BaseModel):
    factor_type: str = Field(default="totp")


class MFAVerifyIn(BaseModel):
    code: str
    remember_device: bool = False


@router.get("/sso/providers")
async def sso_providers():
    return {"providers": sorted(SSO_PROVIDERS)}


@router.get("/sso/connections")
async def list_sso_connections(
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_SSO_PLAN)),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    if not current_user.organization_id:
        return []
    result = await db.execute(
        select(SSOConnection)
        .where(SSOConnection.organization_id == current_user.organization_id)
        .order_by(SSOConnection.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/sso/connections", status_code=201)
async def upsert_sso_connection(
    payload: SSOConnectionIn,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_SSO_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    provider = payload.provider.lower()
    if provider not in SSO_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported SSO provider")
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User does not belong to an organization")

    result = await db.execute(
        select(SSOConnection).where(
            SSOConnection.organization_id == current_user.organization_id,
            SSOConnection.provider == provider,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        conn = SSOConnection(organization_id=current_user.organization_id, provider=provider)
        db.add(conn)
    conn.issuer_url = payload.issuer_url
    conn.client_id = payload.client_id
    conn.client_secret_ref = payload.client_secret_ref
    conn.enabled = payload.enabled
    await record_audit(
        db, current_user, "configuration.changed", "sso_connection", conn.id, {"provider": provider}
    )
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/sso/{provider}/authorize")
async def start_sso(provider: str, db: AsyncSession = Depends(get_db)):
    provider = provider.lower()
    if provider not in SSO_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported SSO provider")

    # Phase 10.13 — working Google OAuth when credentials are configured
    if provider == "google":
        import urllib.parse

        from app.core.config import settings
        from app.core.sso_state import mint_oauth_state

        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
        if client_id and redirect_uri and settings.GOOGLE_OAUTH_CLIENT_SECRET:
            state = mint_oauth_state("google")
            params = urllib.parse.urlencode(
                {
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "response_type": "code",
                    "scope": "openid email profile",
                    "access_type": "online",
                    "state": state,
                    "prompt": "select_account",
                }
            )
            return {
                "provider": "google",
                "authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
                "state": state,
                "status": "ready",
            }

    return {
        "provider": provider,
        "authorization_url_template": "/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=openid email profile&state={state}",
        "status": "ready_for_provider_credentials",
        "hint": "Set GOOGLE_OAUTH_CLIENT_ID / SECRET / REDIRECT_URI for live Google login",
    }


@router.get("/sso/google/callback")
async def google_sso_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange Google auth code for tokens and issue RAGInspector JWTs."""
    import hashlib
    from datetime import timedelta

    import httpx

    from app.core.config import settings
    from app.core.security import create_access_token, create_refresh_token, get_password_hash
    from app.core.sso_state import consume_oauth_state
    from app.models.models import RefreshToken

    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    if not consume_oauth_state(state, expected_provider="google"):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    if not (
        settings.GOOGLE_OAUTH_CLIENT_ID
        and settings.GOOGLE_OAUTH_CLIENT_SECRET
        and settings.GOOGLE_OAUTH_REDIRECT_URI
    ):
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Google code")
        tokens = token_resp.json()
        access = tokens.get("access_token")
        userinfo = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access}"},
        )
        if userinfo.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to load Google profile")
        profile = userinfo.json()

    email = (profile.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    if profile.get("email_verified") is False:
        raise HTTPException(status_code=400, detail="Google email not verified")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        from app.api.v1.endpoints.auth import make_org_slug
        from app.models.models import Organization, OrganizationMember, SubscriptionPlan, UserRole

        display = profile.get("name") or email.split("@")[0]
        org = Organization(
            name=f"{display}'s workspace",
            slug=make_org_slug(display, email),
        )
        db.add(org)
        await db.flush()
        user = User(
            email=email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            name=display,
            email_verified=True,
            organization_id=org.id,
            subscription_plan=SubscriptionPlan.free,
            role=UserRole.owner,
        )
        db.add(user)
        await db.flush()
        db.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role=UserRole.owner,
                invited_email=email,
                accepted_at=datetime.now(timezone.utc),
            )
        )
    else:
        user.email_verified = True

    await record_audit(db, user, "auth.sso_login", "user", user.id, {"provider": "google"})

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.commit()
    await db.refresh(user)

    from fastapi.responses import RedirectResponse
    from urllib.parse import quote

    # Fragment handoff avoids Referer/access-log leakage of tokens (vs query string).
    frontend = (settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")
    dest = (
        f"{frontend}/auth/sso/callback"
        f"#access_token={quote(access_token)}&refresh_token={quote(refresh_token)}"
    )
    return RedirectResponse(url=dest, status_code=302)


@router.post("/saml/metadata")
async def upload_saml_metadata(
    metadata_xml: str = Body(..., media_type="application/xml"),
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_SSO_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User does not belong to an organization")
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.saml_metadata_xml = metadata_xml
    await record_audit(db, current_user, "configuration.changed", "saml_metadata", org.id)
    await db.commit()
    return {"status": "uploaded"}


@router.post("/mfa/enroll", status_code=201)
async def enroll_mfa(
    payload: MFAEnrollIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.factor_type != "totp":
        raise HTTPException(status_code=400, detail="Only TOTP MFA is currently supported")
    import pyotp

    secret = pyotp.random_base32()
    factor = MFAFactor(
        user_id=current_user.id,
        factor_type="totp",
        secret_ref=encrypt_secret(secret),
        enabled=False,
    )
    db.add(factor)
    recovery_codes = [secrets.token_urlsafe(8) for _ in range(10)]
    for code in recovery_codes:
        db.add(
            MFARecoveryCode(
                user_id=current_user.id, code_hash=hashlib.sha256(code.encode()).hexdigest()
            )
        )
    await record_audit(db, current_user, "mfa.enrolled", "mfa_factor", factor.id)
    await db.commit()
    await db.refresh(factor)
    setup_uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.email, issuer_name="RAGInspector"
    )
    return {
        "factor_id": factor.id,
        "factor_type": factor.factor_type,
        "setup_uri": setup_uri,
        "recovery_codes": recovery_codes,
    }


@router.post("/mfa/{factor_id}/verify")
async def verify_mfa_factor(
    factor_id: str,
    payload: MFAVerifyIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MFAFactor).where(MFAFactor.id == factor_id, MFAFactor.user_id == current_user.id)
    )
    factor = result.scalar_one_or_none()
    if not factor:
        raise HTTPException(status_code=404, detail="MFA factor not found")
    import pyotp

    plaintext_secret = decrypt_secret(factor.secret_ref)
    if not pyotp.TOTP(plaintext_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    # Re-encrypt legacy plaintext secrets on successful verify.
    if not factor.secret_ref.startswith("enc:v1:"):
        factor.secret_ref = encrypt_secret(plaintext_secret)
    factor.enabled = True
    factor.verified_at = datetime.now(timezone.utc)
    device_token: str | None = None
    if payload.remember_device:
        device_token = secrets.token_urlsafe(32)
        db.add(
            RememberedDevice(
                user_id=current_user.id,
                device_hash=hashlib.sha256(device_token.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc).replace(
                    year=datetime.now(timezone.utc).year + 1
                ),
            )
        )
    await record_audit(db, current_user, "mfa.verified", "mfa_factor", factor.id)
    await db.commit()
    body: dict = {"status": "enabled"}
    if device_token:
        body["device_token"] = device_token
    return body


@router.delete("/mfa/{factor_id}", status_code=204)
async def admin_reset_mfa(
    factor_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MFAFactor).where(MFAFactor.id == factor_id, MFAFactor.user_id == current_user.id)
    )
    factor = result.scalar_one_or_none()
    if not factor:
        raise HTTPException(status_code=404, detail="MFA factor not found")
    await record_audit(db, current_user, "mfa.reset", "mfa_factor", factor.id)
    await db.delete(factor)
    await db.commit()

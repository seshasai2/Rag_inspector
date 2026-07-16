from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_scopes import api_key_allows_scope
from app.core.ip_allowlist import client_ip_from_headers, enforce_org_ip_allowlist
from app.core.jwt_denylist import is_access_jti_denied
from app.core.plan_gate import meets_min_plan, plan_forbidden_detail, plan_value
from app.core.security import decode_token, hash_api_key
from app.db.session import get_db
from app.models.models import APIKey, OrganizationMember, User

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Org routes that mutate membership / SSO / provisioning.
ORG_ADMIN_ROLES = ("owner", "admin")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        jti = payload.get("jti")
        if jti and is_access_jti_denied(str(jti)):
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception

    client_ip = client_ip_from_headers(
        x_forwarded_for=request.headers.get("X-Forwarded-For"),
        x_real_ip=request.headers.get("X-Real-IP"),
        peer=request.client.host if request.client else None,
    )
    if not await enforce_org_ip_allowlist(
        db, organization_id=user.organization_id, client_ip=client_ip
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client IP is not on the organization allowlist",
        )
    return user


async def get_user_from_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    key_hash = hash_api_key(api_key)
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
    )
    api_key_obj = result.scalar_one_or_none()
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )
    # Update last used
    api_key_obj.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    result = await db.execute(select(User).where(User.id == api_key_obj.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_api_scope(scope: str):
    async def checker(
        api_key: str = Security(api_key_header),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user = await get_user_from_api_key(api_key, db)
        key_hash = hash_api_key(api_key)
        result = await db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
        )
        key = result.scalar_one_or_none()
        if not key or not api_key_allows_scope(key.scopes, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key scope not permitted",
            )
        return user

    return checker


async def _accepted_org_member_role(db: AsyncSession, user: User) -> str | None:
    """Role from accepted organization membership, if any."""
    if not user.organization_id:
        return None
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == user.organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.accepted_at.isnot(None),
        )
    )
    member = result.scalar_one_or_none()
    if not member or not member.role:
        return None
    return member.role.value.lower()


def require_role(*roles: str):
    """
    RBAC gate: user must hold one of ``roles`` on ``User.role`` or as an
    accepted ``OrganizationMember``. Unauthorized callers get HTTP 403.
    """
    allowed = {r.lower() for r in roles}

    async def checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_role = (current_user.role.value if current_user.role else "").lower()
        if user_role in allowed:
            return current_user
        member_role = await _accepted_org_member_role(db, current_user)
        if member_role and member_role in allowed:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return checker


def require_min_plan(minimum: str):
    """
    Plan gate: user's subscription must be ``minimum`` or higher.
    Unauthorized plan → HTTP 403 with a consistent upgrade message.
    """

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        current = plan_value(current_user)
        if not meets_min_plan(current_user, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=plan_forbidden_detail(required=minimum, current=current),
            )
        return current_user

    return checker

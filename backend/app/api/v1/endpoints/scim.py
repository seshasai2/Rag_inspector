import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ORG_ADMIN_ROLES, require_min_plan, require_role
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.models import OrganizationMember, User, UserRole
from app.services.audit import record_audit

router = APIRouter()

_SCIM_PLAN = FEATURE_MIN_PLAN["scim"]


class SCIMUserIn(BaseModel):
    userName: EmailStr
    active: bool = True
    displayName: str | None = None


@router.get("/Users")
async def list_scim_users(
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_SCIM_PLAN)),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users),
        "itemsPerPage": limit,
        "Resources": [
            {"id": u.id, "userName": u.email, "displayName": u.name, "active": u.is_active}
            for u in users
        ],
    }


@router.post("/Users", status_code=201)
async def create_scim_user(
    payload: SCIMUserIn,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_SCIM_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User does not belong to an organization")
    existing = await db.execute(select(User).where(User.email == payload.userName.lower()))
    user = existing.scalar_one_or_none()
    if not user:
        user = User(
            organization_id=current_user.organization_id,
            email=payload.userName.lower(),
            name=payload.displayName or payload.userName,
            # Provisioned users authenticate via IdP/SCIM, not a shared password.
            password_hash=get_password_hash(secrets.token_urlsafe(48)),
            is_active=payload.active,
            email_verified=True,
            role=UserRole.viewer,
        )
        db.add(user)
        await db.flush()
        db.add(
            OrganizationMember(
                organization_id=current_user.organization_id, user_id=user.id, role=UserRole.viewer
            )
        )
    else:
        user.is_active = payload.active
        user.organization_id = current_user.organization_id
    await record_audit(
        db, current_user, "scim.user_provisioned", "user", user.id, {"email": user.email}
    )
    await db.commit()
    return {
        "id": user.id,
        "userName": user.email,
        "displayName": user.name,
        "active": user.is_active,
    }


@router.patch("/Users/{user_id}")
async def update_scim_user(
    user_id: str,
    payload: SCIMUserIn,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_SCIM_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = payload.active
    user.name = payload.displayName or user.name
    await record_audit(db, current_user, "scim.user_updated", "user", user.id)
    await db.commit()
    return {
        "id": user.id,
        "userName": user.email,
        "displayName": user.name,
        "active": user.is_active,
    }

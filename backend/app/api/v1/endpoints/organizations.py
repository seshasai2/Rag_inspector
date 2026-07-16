from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ORG_ADMIN_ROLES, get_current_user, require_min_plan, require_role
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import Organization, OrganizationMember, User, UserRole
from app.services.audit import record_audit

router = APIRouter()

ENTERPRISE_ROLES = {"owner", "admin", "engineer", "analyst", "viewer"}
_ORG_CONTROLS_PLAN = FEATURE_MIN_PLAN["org_controls"]
_TEAM_INVITES_PLAN = FEATURE_MIN_PLAN["team_invites"]


class MemberInviteIn(BaseModel):
    email: EmailStr
    role: str = "viewer"


class OrganizationControlsIn(BaseModel):
    allowed_domains: list[str] = []
    sso_required: bool = False
    mfa_required: bool = False


@router.get("/current")
async def current_organization(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if not current_user.organization_id:
        return None
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    return result.scalar_one_or_none()


@router.put("/controls")
async def update_controls(
    payload: OrganizationControlsIn,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_ORG_CONTROLS_PLAN)),
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
    org.allowed_domains = ",".join(payload.allowed_domains)
    org.sso_required = payload.sso_required
    org.mfa_required = payload.mfa_required
    await record_audit(
        db, current_user, "configuration.changed", "organization", org.id, payload.model_dump()
    )
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/members")
async def list_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    if not current_user.organization_id:
        return []
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == current_user.organization_id)
        .order_by(OrganizationMember.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/members", status_code=201)
async def invite_member(
    payload: MemberInviteIn,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_TEAM_INVITES_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    role = payload.role.lower()
    if role not in ENTERPRISE_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User does not belong to an organization")

    invite_email = payload.email.lower().strip()
    if invite_email == current_user.email.lower():
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    invitee_result = await db.execute(select(User).where(User.email == invite_email))
    invitee = invitee_result.scalar_one_or_none()

    # Reject duplicate pending/accepted memberships for this org + email/user.
    existing_q = select(OrganizationMember).where(
        OrganizationMember.organization_id == current_user.organization_id,
    )
    if invitee:
        existing_q = existing_q.where(
            (OrganizationMember.user_id == invitee.id)
            | (OrganizationMember.invited_email == invite_email)
        )
    else:
        existing_q = existing_q.where(OrganizationMember.invited_email == invite_email)
    existing = (await db.execute(existing_q)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User is already invited or a member")

    member = OrganizationMember(
        organization_id=current_user.organization_id,
        user_id=invitee.id if invitee else None,
        role=UserRole(role),
        invited_email=invite_email,
        accepted_at=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(member)
    await record_audit(
        db,
        current_user,
        "user.invited",
        "organization_member",
        member.id,
        {"email": invite_email, "role": role, "invitee_user_id": invitee.id if invitee else None},
    )
    await db.commit()
    await db.refresh(member)
    return member


class MemberRoleUpdate(BaseModel):
    role: str


@router.post("/members/accept")
async def accept_invite(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept pending org invites matching the current user's email."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.invited_email == current_user.email.lower(),
            OrganizationMember.accepted_at.is_(None),
        )
    )
    pending = list(result.scalars().all())
    if not pending:
        raise HTTPException(status_code=404, detail="No pending invites")
    now = datetime.now(timezone.utc)
    accepted = []
    for member in pending:
        member.user_id = current_user.id
        member.accepted_at = now
        if not current_user.organization_id:
            current_user.organization_id = member.organization_id
        accepted.append(member.id)
        await record_audit(
            db,
            current_user,
            "user.invite_accepted",
            "organization_member",
            member.id,
            {"organization_id": member.organization_id},
        )
    await db.commit()
    return {"accepted": accepted, "organization_id": current_user.organization_id}


@router.patch("/members/{member_id}")
async def update_member_role(
    member_id: str,
    payload: MemberRoleUpdate,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_TEAM_INVITES_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    role = payload.role.lower()
    if role not in ENTERPRISE_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == current_user.organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = UserRole(role)
    await record_audit(
        db, current_user, "user.role_changed", "organization_member", member.id, {"role": role}
    )
    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=204)
async def remove_member(
    member_id: str,
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_TEAM_INVITES_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == current_user.organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    await record_audit(db, current_user, "user.removed", "organization_member", member.id)
    await db.delete(member)
    await db.commit()
    return None

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.pagination import DEFAULT_LIMIT, AdminLimitParam
from app.db.session import get_db
from app.models.models import AnalysisJob, JobStatus, QueryTrace, User, WebhookEvent
from app.services.audit import AuditAction, record_audit

router = APIRouter()


class UserStatusUpdate(BaseModel):
    is_active: bool


class ImpersonationRequest(BaseModel):
    reason: str


def admin_emails() -> set[str]:
    return {
        email.strip().lower() for email in settings.SUPPORT_ADMIN_EMAILS.split(",") if email.strip()
    }


async def require_support_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.email.lower() not in admin_emails():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Support admin access required"
        )
    return current_user


@router.get("/summary")
async def support_summary(
    _: User = Depends(require_support_admin),
    db: AsyncSession = Depends(get_db),
):
    users = await db.scalar(select(func.count()).select_from(User))
    traces = await db.scalar(select(func.count()).select_from(QueryTrace))
    failed_jobs = await db.scalar(
        select(func.count()).select_from(AnalysisJob).where(AnalysisJob.status == JobStatus.failed)
    )
    return {
        "users": users or 0,
        "traces": traces or 0,
        "failed_jobs": failed_jobs or 0,
    }


@router.get("/users")
async def list_users(
    _: User = Depends(require_support_admin),
    db: AsyncSession = Depends(get_db),
    limit: AdminLimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(select(User).order_by(desc(User.created_at)).limit(limit))
    return [
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "organization_id": user.organization_id,
            "subscription_plan": user.subscription_plan.value,
            "subscription_status": (
                user.subscription_status.value if user.subscription_status else None
            ),
            "traces_this_month": user.traces_this_month,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
        }
        for user in result.scalars().all()
    ]


@router.get("/failed-jobs")
async def failed_jobs(
    _: User = Depends(require_support_admin),
    db: AsyncSession = Depends(get_db),
    limit: AdminLimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.status == JobStatus.failed)
        .order_by(desc(AnalysisJob.completed_at))
        .limit(limit)
    )
    return [
        {
            "id": job.id,
            "trace_id": job.trace_id,
            "status": job.status.value,
            "celery_task_id": job.celery_task_id,
            "error_message": job.error_message,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }
        for job in result.scalars().all()
    ]


@router.get("/webhooks")
async def recent_webhooks(
    _: User = Depends(require_support_admin),
    db: AsyncSession = Depends(get_db),
    limit: AdminLimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(WebhookEvent).order_by(desc(WebhookEvent.processed_at)).limit(limit)
    )
    return [
        {
            "id": event.id,
            "provider": event.provider,
            "provider_event_id": event.provider_event_id,
            "event_type": event.event_type,
            "processed_at": event.processed_at,
        }
        for event in result.scalars().all()
    ]


@router.post("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    admin_user: User = Depends(require_support_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = payload.is_active
    await record_audit(
        db,
        admin_user,
        AuditAction.SUPPORT_USER_STATUS,
        "user",
        user.id,
        {"is_active": payload.is_active},
    )
    await db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.post("/users/{user_id}/impersonation-token")
async def create_impersonation_token(
    user_id: str,
    payload: ImpersonationRequest,
    admin_user: User = Depends(require_support_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await record_audit(
        db,
        admin_user,
        AuditAction.SUPPORT_IMPERSONATION,
        "user",
        target.id,
        {"reason": payload.reason},
    )
    await db.commit()
    return {
        "status": "logged",
        "message": "Impersonation requires a separate break-glass token service in production.",
    }

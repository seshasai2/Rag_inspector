"""Audit log listing — filterable by action / target (Phase 5.9)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ORG_ADMIN_ROLES, require_min_plan, require_role
from app.core.pagination import DEFAULT_LIMIT, AdminLimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import AuditLog, User

router = APIRouter()

_AUDIT_PLAN = FEATURE_MIN_PLAN["audit_logs"]


def _serialize(row: AuditLog) -> dict:
    meta: dict = {}
    if row.metadata_json:
        try:
            meta = json.loads(row.metadata_json)
        except json.JSONDecodeError:
            meta = {"raw": row.metadata_json}
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "user_id": row.user_id,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "metadata": meta,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "created_at": row.created_at,
    }


@router.get("")
async def list_audit_logs(
    current_user: User = Depends(require_role(*ORG_ADMIN_ROLES)),
    _: User = Depends(require_min_plan(_AUDIT_PLAN)),
    db: AsyncSession = Depends(get_db),
    limit: AdminLimitParam = DEFAULT_LIMIT,
    action: Optional[str] = Query(None, description="Exact action filter, e.g. auth.login"),
    target_type: Optional[str] = Query(None, description="Exact target_type filter, e.g. api_key"),
    since: Optional[datetime] = Query(
        None, description="Only rows created at/after this time (UTC)"
    ),
):
    filters = []
    if current_user.organization_id:
        filters.append(AuditLog.organization_id == current_user.organization_id)
    else:
        filters.append(AuditLog.user_id == current_user.id)
    if action:
        filters.append(AuditLog.action == action)
    if target_type:
        filters.append(AuditLog.target_type == target_type)
    if since:
        filters.append(AuditLog.created_at >= since)

    result = await db.execute(
        select(AuditLog).where(*filters).order_by(desc(AuditLog.created_at)).limit(limit)
    )
    return [_serialize(row) for row in result.scalars().all()]

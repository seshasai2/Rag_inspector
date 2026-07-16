from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.plan_gate import FEATURE_MIN_PLAN, meets_min_plan, plan_forbidden_detail, plan_value
from app.db.session import get_db
from app.models.models import User, UserSettings
from app.schemas.schemas import UserSettingsOut, UserSettingsUpdate
from app.services.audit import record_audit

router = APIRouter()

_SLACK_PLAN = FEATURE_MIN_PLAN["slack_alerts"]


@router.get("", response_model=UserSettingsOut)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        s = UserSettings(user_id=current_user.id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    # Build response with Slack fields from User model
    response_data = {
        "ollama_url": s.ollama_url,
        "ollama_model": s.ollama_model,
        "grounding_threshold": s.grounding_threshold,
        "faithfulness_alert_threshold": s.faithfulness_alert_threshold,
        "enable_email_alerts": s.enable_email_alerts,
        "slack_webhook_url": current_user.slack_webhook_url,
        "slack_alert_enabled": current_user.slack_alert_enabled,
    }
    return response_data


@router.put("", response_model=UserSettingsOut)
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    s = result.scalar_one_or_none()
    if not s:
        s = UserSettings(user_id=current_user.id)
        db.add(s)

    if payload.ollama_url is not None:
        s.ollama_url = payload.ollama_url
    if payload.ollama_model is not None:
        s.ollama_model = payload.ollama_model
    if payload.grounding_threshold is not None:
        s.grounding_threshold = payload.grounding_threshold
    if payload.faithfulness_alert_threshold is not None:
        s.faithfulness_alert_threshold = payload.faithfulness_alert_threshold
    if payload.enable_email_alerts is not None:
        s.enable_email_alerts = payload.enable_email_alerts

    # Slack alerts: Starter+ (gate only when changing Slack fields)
    slack_touch = payload.slack_webhook_url is not None or payload.slack_alert_enabled is not None
    if slack_touch and not meets_min_plan(current_user, _SLACK_PLAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=plan_forbidden_detail(
                required=_SLACK_PLAN,
                current=plan_value(current_user),
            ),
        )
    if payload.slack_webhook_url is not None:
        current_user.slack_webhook_url = payload.slack_webhook_url
    if payload.slack_alert_enabled is not None:
        current_user.slack_alert_enabled = payload.slack_alert_enabled

    await record_audit(db, current_user, "configuration.changed", "settings", str(s.id))
    await db.commit()
    await db.refresh(s)
    return s

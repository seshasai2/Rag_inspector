import json
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_plan
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.core.security import encrypt_secret
from app.db.session import get_db
from app.models.models import IntegrationWebhook, User, WebhookDelivery
from app.services.audit import record_audit

router = APIRouter()

SUPPORTED_PROVIDERS = {"slack", "teams", "discord", "jira", "github", "gitlab", "pagerduty"}
_WEBHOOKS_PLAN = FEATURE_MIN_PLAN["integration_webhooks"]


class IntegrationWebhookIn(BaseModel):
    provider: str
    name: str = Field(min_length=1, max_length=255)
    webhook_url: str = Field(min_length=10, max_length=1024)
    events: list[str] = ["trust_score_breach", "weekly_report", "hallucination_spike"]
    is_active: bool = True


@router.get("/providers")
async def providers():
    return {"providers": sorted(SUPPORTED_PROVIDERS)}


@router.get("/webhooks")
async def list_webhooks(
    current_user: User = Depends(require_min_plan(_WEBHOOKS_PLAN)),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(IntegrationWebhook)
        .where(IntegrationWebhook.user_id == current_user.id)
        .order_by(IntegrationWebhook.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/webhooks", status_code=201)
async def create_webhook(
    payload: IntegrationWebhookIn,
    current_user: User = Depends(require_min_plan(_WEBHOOKS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    provider = payload.provider.lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported integration provider")
    # One-time plaintext for the customer; at-rest we store Fernet ciphertext.
    signing_secret = secrets.token_urlsafe(32)
    webhook = IntegrationWebhook(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        provider=provider,
        name=payload.name,
        webhook_url=payload.webhook_url,
        signing_secret_hash=encrypt_secret(signing_secret),
        events=json.dumps(payload.events),
        is_active=payload.is_active,
    )
    db.add(webhook)
    await record_audit(
        db,
        current_user,
        "configuration.changed",
        "integration_webhook",
        webhook.id,
        {"provider": provider},
    )
    await db.commit()
    await db.refresh(webhook)
    return {
        "id": webhook.id,
        "provider": webhook.provider,
        "name": webhook.name,
        "webhook_url": webhook.webhook_url,
        "events": payload.events,
        "is_active": webhook.is_active,
        "created_at": webhook.created_at,
        "signing_secret": signing_secret,
        "signing_secret_hint": "Store this secret now — it is not returned again.",
    }


@router.post("/webhooks/{webhook_id}/deliveries", status_code=202)
async def enqueue_delivery(
    webhook_id: str,
    event_type: str,
    payload: dict,
    current_user: User = Depends(require_min_plan(_WEBHOOKS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IntegrationWebhook).where(
            IntegrationWebhook.id == webhook_id, IntegrationWebhook.user_id == current_user.id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload_json=json.dumps(payload),
        status="pending",
    )
    db.add(delivery)
    await record_audit(
        db,
        current_user,
        "webhook.delivery_queued",
        "webhook_delivery",
        delivery.id,
        {"event_type": event_type},
    )
    await db.commit()
    from app.workers.tasks import deliver_webhook

    deliver_webhook.delay(delivery.id)
    return {"delivery_id": delivery.id, "status": "queued"}


@router.get("/webhook-deliveries")
async def list_deliveries(
    current_user: User = Depends(require_min_plan(_WEBHOOKS_PLAN)),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(WebhookDelivery)
        .join(IntegrationWebhook, IntegrationWebhook.id == WebhookDelivery.webhook_id)
        .where(IntegrationWebhook.user_id == current_user.id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: User = Depends(require_min_plan(_WEBHOOKS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IntegrationWebhook).where(
            IntegrationWebhook.id == webhook_id, IntegrationWebhook.user_id == current_user.id
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(
            webhook.webhook_url,
            json={
                "text": "RAGInspector test notification",
                "provider": webhook.provider,
                "event": "test",
            },
        )
    await record_audit(
        db,
        current_user,
        "integration.tested",
        "integration_webhook",
        webhook.id,
        {"status_code": resp.status_code},
    )
    await db.commit()
    return {"status": "sent", "status_code": resp.status_code}

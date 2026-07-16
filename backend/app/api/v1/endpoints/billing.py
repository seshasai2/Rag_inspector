import hashlib
import hmac
import json
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.models import SubscriptionPlan, SubscriptionStatus, User, WebhookEvent
from app.schemas.schemas import CreateSubscriptionRequest, SubscriptionOut
from app.services.audit import AuditAction, record_audit

router = APIRouter()
logger = structlog.get_logger()

# Single plan per tier — each shows both INR and USD prices
PLAN_MAP = {
    "starter_monthly": settings.RAZORPAY_PLAN_STARTER_MONTHLY,
    "starter_annual": settings.RAZORPAY_PLAN_STARTER_ANNUAL,
    "pro_monthly": settings.RAZORPAY_PLAN_PRO_MONTHLY,
    "pro_annual": settings.RAZORPAY_PLAN_PRO_ANNUAL,
    "enterprise_monthly": settings.RAZORPAY_PLAN_ENTERPRISE_MONTHLY,
    "enterprise_annual": settings.RAZORPAY_PLAN_ENTERPRISE_ANNUAL,
}

PLAN_NAME_MAP = {
    "starter_monthly": SubscriptionPlan.starter,
    "starter_annual": SubscriptionPlan.starter,
    "pro_monthly": SubscriptionPlan.pro,
    "pro_annual": SubscriptionPlan.pro,
    "enterprise_monthly": SubscriptionPlan.enterprise,
    "enterprise_annual": SubscriptionPlan.enterprise,
}


def get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")
    import razorpay

    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@router.get("/plans")
async def get_plans():
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_inr": 0,
                "price_usd": 0,
                "price_label": "Free",
                "traces_per_month": settings.FREE_TRACES_PER_MONTH,
                "features": [
                    "100 queries/month",
                    "Full instrumentation",
                    "Sentence-level grounding",
                    "No credit card required",
                ],
            },
            {
                "id": "starter_monthly",
                "name": "Starter",
                "price_inr": 1999,
                "price_usd": 24,
                "price_label": "₹1,999/mo · $24/mo",
                "traces_per_month": settings.STARTER_TRACES_PER_MONTH,
                "features": [
                    "10,000 queries/month",
                    "Trustworthiness dashboard",
                    "Slack hallucination alerts",
                    "90-day history",
                ],
            },
            {
                "id": "pro_monthly",
                "name": "Pro",
                "price_inr": 5999,
                "price_usd": 69,
                "price_label": "₹5,999/mo · $69/mo",
                "traces_per_month": settings.PRO_TRACES_PER_MONTH,
                "features": [
                    "100,000 queries/month",
                    "Automated fix recommendations",
                    "BM25 vs Vector comparison",
                    "Team access (5 members)",
                ],
            },
            {
                "id": "enterprise_monthly",
                "name": "Enterprise",
                "price_inr": 14999,
                "price_usd": 179,
                "price_label": "₹14,999/mo · $179/mo",
                "traces_per_month": settings.ENTERPRISE_TRACES_PER_MONTH,
                "features": [
                    "Unlimited traces",
                    "On-premise deployment",
                    "Custom failure classifiers",
                    "SLA guarantee",
                    "Customer-facing trustworthiness reports",
                ],
            },
        ]
    }


@router.post("/create-subscription")
async def create_subscription(
    payload: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan_id = PLAN_MAP.get(payload.plan)
    if not plan_id:
        raise HTTPException(status_code=400, detail="Invalid plan")

    client = get_razorpay_client()

    try:
        # Create or get customer
        if not current_user.razorpay_customer_id:
            customer = client.customer.create(
                {
                    "name": current_user.name,
                    "email": current_user.email,
                    "fail_existing": 0,
                }
            )
            current_user.razorpay_customer_id = customer["id"]
            await db.commit()

        # Create subscription
        subscription = client.subscription.create(
            {
                "plan_id": plan_id,
                "customer_notify": 1,
                "quantity": 1,
                "total_count": 12,
                "customer_id": current_user.razorpay_customer_id,
            }
        )

        current_user.razorpay_subscription_id = subscription["id"]
        current_user.subscription_status = SubscriptionStatus.trialing
        await record_audit(
            db,
            current_user,
            AuditAction.BILLING_SUBSCRIPTION_CREATED,
            "subscription",
            subscription["id"],
            {"plan": payload.plan},
        )
        await db.commit()

        return {
            "subscription_id": subscription["id"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "customer_id": current_user.razorpay_customer_id,
            "plan": payload.plan,
        }
    except Exception as e:
        logger.error("Razorpay subscription creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)}")


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    x_razorpay_event_id: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Verify webhook signature
    if settings.RAZORPAY_WEBHOOK_SECRET and not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature")
    if settings.RAZORPAY_WEBHOOK_SECRET and x_razorpay_signature:
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, x_razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(body)
    event_type = event.get("event")
    provider_event_id = x_razorpay_event_id or event.get("id")

    if provider_event_id:
        db.add(
            WebhookEvent(
                provider="razorpay",
                provider_event_id=provider_event_id,
                event_type=event_type or "unknown",
            )
        )
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            logger.info(
                "Duplicate Razorpay webhook ignored",
                event_id=provider_event_id,
                event_type=event_type,
            )
            return {"status": "ok", "duplicate": True}

    logger.info("Razorpay webhook received", event_type=event_type)

    if event_type == "subscription.activated":
        sub = event["payload"]["subscription"]["entity"]
        sub_id = sub["id"]
        plan_id = sub.get("plan_id", "")

        result = await db.execute(select(User).where(User.razorpay_subscription_id == sub_id))
        user = result.scalar_one_or_none()
        if user:
            previous = user.subscription_plan.value if user.subscription_plan else None
            if plan_id in [
                settings.RAZORPAY_PLAN_STARTER_MONTHLY,
                settings.RAZORPAY_PLAN_STARTER_ANNUAL,
            ]:
                user.subscription_plan = SubscriptionPlan.starter
            elif plan_id in [settings.RAZORPAY_PLAN_PRO_MONTHLY, settings.RAZORPAY_PLAN_PRO_ANNUAL]:
                user.subscription_plan = SubscriptionPlan.pro
            elif plan_id in [
                settings.RAZORPAY_PLAN_ENTERPRISE_MONTHLY,
                settings.RAZORPAY_PLAN_ENTERPRISE_ANNUAL,
            ]:
                user.subscription_plan = SubscriptionPlan.enterprise
            user.subscription_status = SubscriptionStatus.active
            await record_audit(
                db,
                user,
                AuditAction.BILLING_PLAN_CHANGED,
                "subscription",
                sub_id,
                {
                    "event": event_type,
                    "previous_plan": previous,
                    "new_plan": user.subscription_plan.value,
                    "plan_id": plan_id,
                },
            )
            await db.commit()

    elif event_type == "subscription.cancelled":
        sub_id = event["payload"]["subscription"]["entity"]["id"]
        result = await db.execute(select(User).where(User.razorpay_subscription_id == sub_id))
        user = result.scalar_one_or_none()
        if user:
            previous = user.subscription_plan.value if user.subscription_plan else None
            user.subscription_plan = SubscriptionPlan.free
            user.subscription_status = SubscriptionStatus.cancelled
            await record_audit(
                db,
                user,
                AuditAction.BILLING_PLAN_CHANGED,
                "subscription",
                sub_id,
                {
                    "event": event_type,
                    "previous_plan": previous,
                    "new_plan": SubscriptionPlan.free.value,
                },
            )
            await db.commit()

    elif event_type == "subscription.halted":
        sub_id = event["payload"]["subscription"]["entity"]["id"]
        result = await db.execute(select(User).where(User.razorpay_subscription_id == sub_id))
        user = result.scalar_one_or_none()
        if user:
            previous_status = user.subscription_status.value if user.subscription_status else None
            user.subscription_status = SubscriptionStatus.past_due
            await record_audit(
                db,
                user,
                AuditAction.BILLING_PLAN_CHANGED,
                "subscription",
                sub_id,
                {
                    "event": event_type,
                    "previous_status": previous_status,
                    "new_status": SubscriptionStatus.past_due.value,
                    "plan": user.subscription_plan.value if user.subscription_plan else None,
                },
            )
            await db.commit()

    elif event_type in {"payment.failed", "subscription.pending"}:
        sub = (event.get("payload") or {}).get("subscription", {}).get("entity") or {}
        payment = (event.get("payload") or {}).get("payment", {}).get("entity") or {}
        sub_id = sub.get("id") or payment.get("subscription_id")
        if sub_id:
            result = await db.execute(select(User).where(User.razorpay_subscription_id == sub_id))
            user = result.scalar_one_or_none()
            if user:
                previous_status = (
                    user.subscription_status.value if user.subscription_status else None
                )
                user.subscription_status = SubscriptionStatus.past_due
                await record_audit(
                    db,
                    user,
                    AuditAction.BILLING_PLAN_CHANGED,
                    "subscription",
                    sub_id,
                    {
                        "event": event_type,
                        "previous_status": previous_status,
                        "new_status": SubscriptionStatus.past_due.value,
                    },
                )

    await db.commit()
    return {"status": "ok"}


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.razorpay_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    client = get_razorpay_client()
    try:
        client.subscription.cancel(
            current_user.razorpay_subscription_id, {"cancel_at_cycle_end": 1}
        )
        current_user.subscription_status = SubscriptionStatus.cancelled
        await record_audit(
            db,
            current_user,
            AuditAction.BILLING_SUBSCRIPTION_CANCELLED,
            "subscription",
            current_user.razorpay_subscription_id,
        )
        await db.commit()
        return {"message": "Subscription will cancel at end of billing period"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(current_user: User = Depends(get_current_user)):
    return SubscriptionOut(
        subscription_plan=current_user.subscription_plan.value,
        subscription_status=(
            current_user.subscription_status.value if current_user.subscription_status else None
        ),
        subscription_current_period_end=current_user.subscription_current_period_end,
        razorpay_subscription_id=current_user.razorpay_subscription_id,
    )


@router.get("/usage")
async def billing_usage(current_user: User = Depends(get_current_user)):
    from app.api.v1.endpoints.ingest import PLAN_LIMITS

    plan = current_user.subscription_plan.value if current_user.subscription_plan else "free"
    limit = PLAN_LIMITS.get(plan, settings.FREE_TRACES_PER_MONTH)
    used = int(current_user.traces_this_month or 0)
    return {
        "subscription_plan": plan,
        "traces_used": used,
        "traces_limit": limit,
        "traces_remaining": max(0, limit - used),
        "utilization": round(used / limit, 4) if limit else None,
    }


@router.post("/verify-payment")
async def verify_payment(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm Razorpay checkout returned a subscription id (client-side verify)."""
    sub_id = (payload or {}).get("razorpay_subscription_id") or (payload or {}).get(
        "subscription_id"
    )
    if not sub_id:
        raise HTTPException(status_code=400, detail="razorpay_subscription_id required")
    current_user.razorpay_subscription_id = str(sub_id)
    if current_user.subscription_status is None:
        current_user.subscription_status = SubscriptionStatus.trialing
    await db.commit()
    return {
        "status": "recorded",
        "razorpay_subscription_id": current_user.razorpay_subscription_id,
        "subscription_plan": current_user.subscription_plan.value,
        "note": "Plan upgrades apply when subscription.activated webhook arrives.",
    }

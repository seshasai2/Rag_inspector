"""Subscription plan ranks and consistent upgrade / quota messages."""

from __future__ import annotations

from app.models.models import SubscriptionPlan, User

# free < starter < pro < enterprise
PLAN_RANK: dict[str, int] = {
    SubscriptionPlan.free.value: 0,
    SubscriptionPlan.starter.value: 1,
    SubscriptionPlan.pro.value: 2,
    SubscriptionPlan.enterprise.value: 3,
}

# Product feature → minimum plan (billing feature copy)
FEATURE_MIN_PLAN: dict[str, str] = {
    "slack_alerts": SubscriptionPlan.starter.value,
    "integration_webhooks": SubscriptionPlan.starter.value,
    "bm25_comparison": SubscriptionPlan.pro.value,
    "pipeline_compare": SubscriptionPlan.pro.value,
    "team_invites": SubscriptionPlan.pro.value,
    "monitoring": SubscriptionPlan.pro.value,
    "monitoring_run_now": SubscriptionPlan.enterprise.value,
    "regression_compare": SubscriptionPlan.pro.value,
    "regression_pre_deploy": SubscriptionPlan.enterprise.value,
    "benchmark": SubscriptionPlan.pro.value,
    "studio": SubscriptionPlan.pro.value,
    "investigator": SubscriptionPlan.pro.value,
    "org_controls": SubscriptionPlan.enterprise.value,
    "sso": SubscriptionPlan.enterprise.value,
    "scim": SubscriptionPlan.enterprise.value,
    "audit_logs": SubscriptionPlan.enterprise.value,
    "executive_reports": SubscriptionPlan.enterprise.value,
}


def plan_value(user: User) -> str:
    plan = getattr(user, "subscription_plan", None)
    if plan is None:
        return SubscriptionPlan.free.value
    return plan.value if hasattr(plan, "value") else str(plan)


def plan_rank(plan: str | SubscriptionPlan | None) -> int:
    if plan is None:
        return 0
    key = plan.value if isinstance(plan, SubscriptionPlan) else str(plan)
    return PLAN_RANK.get(key, 0)


def meets_min_plan(user: User, minimum: str) -> bool:
    return plan_rank(plan_value(user)) >= plan_rank(minimum)


def plan_forbidden_detail(*, required: str, current: str) -> str:
    """Consistent 403 body for feature gates (not quota)."""
    return (
        f"Plan upgrade required. This feature needs the {required} plan or higher "
        f"(current: {current})."
    )


def plan_quota_detail(*, limit: int) -> str:
    """Consistent 429 body for monthly ingest quota."""
    return f"Plan limit reached: monthly trace quota ({limit}) exceeded. Upgrade your plan."

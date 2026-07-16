"""Plan gating beyond ingest (Phase 5.3)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.deps import require_min_plan
from app.core.plan_gate import (
    FEATURE_MIN_PLAN,
    meets_min_plan,
    plan_forbidden_detail,
    plan_quota_detail,
    plan_rank,
)
from app.models.models import SubscriptionPlan


def _user(plan: SubscriptionPlan) -> MagicMock:
    user = MagicMock()
    user.subscription_plan = plan
    return user


def test_plan_rank_ordering():
    assert plan_rank("free") < plan_rank("starter") < plan_rank("pro") < plan_rank("enterprise")


def test_meets_min_plan():
    assert meets_min_plan(_user(SubscriptionPlan.pro), "pro") is True
    assert meets_min_plan(_user(SubscriptionPlan.pro), "enterprise") is False
    assert meets_min_plan(_user(SubscriptionPlan.starter), "starter") is True
    assert meets_min_plan(_user(SubscriptionPlan.free), "starter") is False


def test_forbidden_and_quota_messages_are_consistent():
    detail = plan_forbidden_detail(required="pro", current="free")
    assert detail.startswith("Plan upgrade required.")
    assert "pro" in detail
    assert "free" in detail

    quota = plan_quota_detail(limit=100)
    assert quota.startswith("Plan limit reached:")
    assert "100" in quota


@pytest.mark.asyncio
async def test_require_min_plan_rejects_free_for_pro_feature():
    checker = require_min_plan("pro")
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=_user(SubscriptionPlan.free))
    assert exc.value.status_code == 403
    assert exc.value.detail.startswith("Plan upgrade required.")


@pytest.mark.asyncio
async def test_require_min_plan_allows_enterprise_for_pro_feature():
    checker = require_min_plan("pro")
    user = _user(SubscriptionPlan.enterprise)
    assert await checker(current_user=user) is user


def test_feature_min_plan_map_covers_product_gates():
    assert FEATURE_MIN_PLAN["slack_alerts"] == "starter"
    assert FEATURE_MIN_PLAN["bm25_comparison"] == "pro"
    assert FEATURE_MIN_PLAN["team_invites"] == "pro"
    assert FEATURE_MIN_PLAN["sso"] == "enterprise"
    assert FEATURE_MIN_PLAN["scim"] == "enterprise"
    assert FEATURE_MIN_PLAN["executive_reports"] == "enterprise"

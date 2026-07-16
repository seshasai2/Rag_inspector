"""Tests for subscription plan model / enum alignment."""
from app.models.models import SubscriptionPlan


class TestSubscriptionPlanEnum:
    def test_expected_values(self):
        assert {plan.value for plan in SubscriptionPlan} == {
            "free",
            "starter",
            "pro",
            "enterprise",
        }

    def test_legacy_saas_removed(self):
        assert "saas" not in {plan.value for plan in SubscriptionPlan}
        assert not hasattr(SubscriptionPlan, "saas")

    def test_plan_limits_keys_match_enum(self):
        from app.api.v1.endpoints.ingest import PLAN_LIMITS

        assert set(PLAN_LIMITS.keys()) == {plan.value for plan in SubscriptionPlan}

    def test_billing_maps_to_current_plans(self):
        from app.api.v1.endpoints.billing import PLAN_NAME_MAP

        mapped = {plan.value for plan in PLAN_NAME_MAP.values()}
        assert mapped <= {plan.value for plan in SubscriptionPlan}
        assert "saas" not in mapped

"""Optional Sentry initialization (Phase 8.6)."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def init_sentry(*, celery: bool = False) -> bool:
    """Initialize Sentry when ``SENTRY_DSN`` is set. Returns True if initialized."""
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        return False

    import sentry_sdk

    integrations: list[Any] = []
    if celery:
        from sentry_sdk.integrations.celery import CeleryIntegration

        integrations.append(CeleryIntegration())
    else:
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        integrations.extend(
            [
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ]
        )

    production = settings.ENVIRONMENT.lower() == "production"
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.ENVIRONMENT,
        integrations=integrations,
        traces_sample_rate=0.1 if production else 1.0,
        send_default_pii=False,
    )
    return True

"""Shared SlowAPI rate limiter for auth and ingest surfaces."""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _testing_mode() -> bool:
    return os.getenv("TESTING", "").lower() in {"1", "true", "yes"} or os.getenv(
        "ENVIRONMENT", "development"
    ).lower() in {"test", "testing"}


# Disable limits in automated tests (CI / local pytest).
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not _testing_mode(),
    default_limits=[],
)

# --- Auth (per IP) ---
AUTH_REGISTER_LIMIT = "10/minute"
AUTH_LOGIN_LIMIT = "20/minute"
AUTH_REFRESH_LIMIT = "30/minute"
AUTH_PASSWORD_RESET_LIMIT = "5/minute"  # forgot + reset
AUTH_RESEND_VERIFY_LIMIT = "5/minute"
AUTH_VERIFY_EMAIL_LIMIT = "20/minute"

# --- Ingest (per IP; API key auth still applies) ---
INGEST_TRACE_LIMIT = "120/minute"
INGEST_BATCH_LIMIT = "30/minute"

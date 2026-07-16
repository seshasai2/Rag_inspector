"""Experimental / partial surfaces — do not demo as finished product features."""

# Status legend
# - live: safe to demo
# - login_gated: complete for enroll/verify; enforced at login when enabled
# - partial: code exists; incomplete UX or wiring
# - stub: schema/routes only
# - quarantined: intentionally hidden from product narrative

EXPERIMENTAL_SURFACES = {
    "billing_razorpay": {
        "status": "partial",
        "paths": ["/api/v1/billing/*"],
        "note": "Usage + verify-payment + payment.failed handling; live Razorpay keys still required.",
    },
    "enterprise_console_ui": {
        "status": "quarantined",
        "paths": ["/enterprise"],
        "note": "Honesty notice only; not a product demo surface.",
    },
    "mfa": {
        "status": "login_gated",
        "paths": ["/api/v1/identity/mfa/*"],
        "note": "TOTP enroll/verify with encrypted secrets; password alone cannot issue tokens when a factor is enabled.",
    },
    "sso_scim": {
        "status": "partial",
        "paths": ["/api/v1/identity/*", "/api/v1/scim/v2/*"],
        "note": "Google OAuth works when GOOGLE_OAUTH_* is set; other IdPs/SCIM remain stub/config-only.",
    },
    "slack_alerts": {
        "status": "partial",
        "paths": ["app/services/slack_alerts.py"],
        "note": "Worker may emit spike alerts when user Slack webhook is configured.",
    },
    "phase10_saas_surfaces": {
        "status": "live",
        "paths": [
            "/api/v1/knowledge/gaps",
            "/api/v1/autofix/*",
            "/api/v1/benchmark/*",
            "/api/v1/studio/*",
            "/api/v1/investigator/*",
            "/api/v1/documents/*",
            "/api/v1/monitoring/*",
            "/api/v1/regression/*",
        ],
        "note": "Phase 10 SaaS surfaces shipped in scoped form; see docs/IMPLEMENTED.md.",
    },
}


def experimental_manifest() -> dict:
    """Return a JSON-serializable manifest for docs and /ops introspection."""
    return EXPERIMENTAL_SURFACES

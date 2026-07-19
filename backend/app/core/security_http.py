"""HTTP security headers and CORS policy for the API.

See ``SECURITY.md`` (repo root) for the production review notes.
"""

from __future__ import annotations

from typing import Any

# API responses are JSON, not an HTML app — keep CSP restrictive.
# Razorpay / Next.js CSP belongs on the frontend (``frontend/next.config.js``).
API_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
}

HSTS_HEADER = "max-age=63072000; includeSubDomains; preload"

# Production CORS: explicit verbs/headers only (no wildcards).
PROD_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
PROD_CORS_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-API-Key",
    "X-Requested-With",
    "X-Request-ID",
]
PROD_CORS_EXPOSE_HEADERS = ["X-Request-ID"]


def normalize_origin(url: str) -> str:
    """CORS origins must match exactly — strip trailing slash."""
    return (url or "").strip().rstrip("/")


def cors_allow_origins(*, is_production: bool, frontend_url: str) -> list[str]:
    origin = normalize_origin(frontend_url)
    if is_production:
        return [origin] if origin else []
    extras = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:80",
        "http://localhost:13000",  # docker-compose.verify-ports.yml UI
        "http://127.0.0.1:3000",
        "http://127.0.0.1:13000",
        "http://127.0.0.1:52478",
    ]
    origins = [origin] if origin else []
    for item in extras:
        if item not in origins:
            origins.append(item)
    return origins


def cors_middleware_kwargs(*, is_production: bool, frontend_url: str) -> dict[str, Any]:
    """Keyword args for ``fastapi.middleware.cors.CORSMiddleware``."""
    kwargs: dict[str, Any] = {
        "allow_origins": cors_allow_origins(is_production=is_production, frontend_url=frontend_url),
        "allow_credentials": True,
    }
    if is_production:
        kwargs["allow_origin_regex"] = None
        kwargs["allow_methods"] = list(PROD_CORS_METHODS)
        kwargs["allow_headers"] = list(PROD_CORS_HEADERS)
        kwargs["expose_headers"] = list(PROD_CORS_EXPOSE_HEADERS)
    else:
        # Local Next.js / Compose verify-ports on localhost or 127.0.0.1 (any port)
        kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1):\d+"
        kwargs["allow_methods"] = ["*"]
        kwargs["allow_headers"] = ["*"]
        kwargs["expose_headers"] = list(PROD_CORS_EXPOSE_HEADERS)
    return kwargs


def apply_security_headers(response: Any, *, is_production: bool) -> Any:
    for key, value in API_SECURITY_HEADERS.items():
        response.headers[key] = value
    if is_production:
        response.headers["Strict-Transport-Security"] = HSTS_HEADER
    return response

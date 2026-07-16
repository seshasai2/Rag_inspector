# ADR 0002: Dual auth — JWT for humans, API keys for SDKs

- **Status:** Accepted  
- **Date:** 2026-07

## Context

Dashboard users need session-like access with MFA. Instrumentation SDKs and CI need non-interactive credentials.

## Decision

- Browser / operators: JWT access + refresh (optional MFA). Logout can denylist access `jti` in Redis.  
- Machines: `X-API-Key` with hashed storage and scopes.

## Alternatives considered

| Option | Why rejected for v1 |
|--------|---------------------|
| OAuth-only for all clients | Poor DX for Python SDK one-liners |
| mTLS for ingest | High friction for OSS adopters |
| Long-lived JWT in SDK | Hard to rotate; leaks like a password |

## Consequences

- Clear security model in docs and interviews.  
- Key rotation and audit logs become first-class.  
- SSO (Google) optional; SAML/SCIM remain experimental.

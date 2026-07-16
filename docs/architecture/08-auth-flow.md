# Authentication and authorization flows

RAGInspector supports two client auth modes: **JWT Bearer** for the dashboard (register / login / refresh / MFA) and **API keys** (`X-API-Key`) for SDK ingest. Enterprise orgs can require SSO and MFA.

```mermaid
sequenceDiagram
    autonumber
    participant U as Browser / SDK
    participant API as FastAPI
    participant DB as PostgreSQL
    participant IdP as OIDC / SAML IdP

    Note over U,API: Dashboard registration / login
    U->>API: POST /api/v1/auth/register
    API->>DB: create User + Organization
    API-->>U: 201 UserOut (verify email as needed)
    U->>API: POST /api/v1/auth/login
    alt MFA required
        API-->>U: mfa_required + challenge
        U->>API: POST /api/v1/auth/login/mfa
    end
    API->>DB: store refresh_token hash
    API-->>U: access_token + refresh_token

    Note over U,API: Token refresh / logout
    U->>API: POST /api/v1/auth/refresh
    API-->>U: new TokenResponse
    U->>API: POST /api/v1/auth/logout<br/>refresh + optional access_token
    API->>DB: revoke refresh_token (optional revoke_all_sessions)
    API->>API: Redis denylist access jti until exp

    Note over U,IdP: Enterprise SSO (optional)
    U->>API: POST /api/v1/identity/sso/{provider}/authorize
    API-->>U: authorize_url + state
    U->>IdP: browser redirect
    IdP->>API: GET callback + code
    API->>DB: link / create membership
    API-->>U: session tokens

    Note over U,API: SDK ingest
    U->>API: POST /api/v1/ingest/trace<br/>X-API-Key
    API->>DB: resolve key → user / pipeline
    API-->>U: 202 TraceIngestResponse
```

| Mechanism | Header / body | Typical clients |
|-----------|---------------|-----------------|
| Access JWT | `Authorization: Bearer <token>` | Next.js dashboard, curl |
| Access JWT denylist | Redis `jwt:deny:{jti}` on logout | Stolen access tokens rejected until TTL |
| Refresh JWT | `POST /auth/refresh` body | Token rotation |
| API key | `X-API-Key: ri_...` | Python SDK, CI ingest |
| Role gate | JWT claims + org membership | Admin, audit, SSO setup |
| Pipeline ACL | Owner **or** same-org accepted member | List/get/stats; mutations remain owner-only |

Rate limits (per IP, SlowAPI): register `10/min`, login `20/min`, refresh `30/min`, ingest `120/min`. See `app/core/rate_limit.py`.

See also: [SECURITY.md](../engineering/SECURITY.md), [API.md](../API.md).

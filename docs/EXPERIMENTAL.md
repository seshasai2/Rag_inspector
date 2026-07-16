# Experimental & Partial Features

See also `docs/ARCHITECTURE.md` (implemented vs deferred) and `backend/app/experimental.py`.

| Surface | Status | Notes |
|---------|--------|-------|
| Core ingest → analysis → dashboard | **Live** | Hiring demo path |
| Phase 10 SaaS (gaps, autofix, monitor, regression, benchmark, studio, investigator) | **Live** | Scoped; measured data only — see [IMPLEMENTED.md](IMPLEMENTED.md) |
| Razorpay billing | Partial | Usage/verify/webhooks; needs live keys |
| Google SSO | Partial | Live when `GOOGLE_OAUTH_*` set; other IdPs stub |
| Enterprise console UI | Quarantined | `/enterprise` honesty notice only |
| MFA TOTP | **Login-gated** | Enroll/verify encrypted; password alone cannot issue tokens when a factor is enabled |
| Slack alerts | Partial | Wired from analysis worker when webhook configured |
| SCIM / multi-IdP SSO | Stub | Config/storage only |

**Rule:** Never present stub/partial rows as finished enterprise features in interviews or README hero copy.

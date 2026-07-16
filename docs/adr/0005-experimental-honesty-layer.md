# ADR 0005: Experimental honesty layer

- **Status:** Accepted  
- **Date:** 2026-07

## Context

Partial enterprise surfaces (billing keys, SAML/SCIM) tempt demo inflation. Interviews and README hero copy must not claim unfinished product.

## Decision

Maintain `docs/EXPERIMENTAL.md` + `backend/app/experimental.py` inventory. Quarantine incomplete UI. Prefer a deep correct core debugger over shallow stubs.

## Alternatives considered

| Option | Why rejected |
|--------|----------------|
| Hide stubs silently | Reviewers discover and lose trust |
| Ship every stub as “done” | Portfolio anti-signal |
| Remove all enterprise code | Loses honest roadmap and security hooks already built |

## Consequences

- Strong hiring credibility.  
- SaaS “GA complete” claims are capped until SCIM/SAML finish.

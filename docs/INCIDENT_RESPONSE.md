# Incident Response Runbook

## Severity

- SEV1: customer data exposure, complete outage, billing/security compromise.
- SEV2: major feature outage, degraded ingestion/analysis, widespread webhook/report failures.
- SEV3: isolated bug or degraded non-critical workflow.

## First 15 Minutes

1. Confirm the symptom and affected scope.
2. Assign incident commander.
3. Freeze risky deploys.
4. Check `/api/v1/ops/ready`, logs, Sentry, queue depth, database health, and recent deploys.
5. Start a timeline.

## Containment

- Revoke exposed secrets.
- Disable compromised integrations.
- Suspend malicious accounts.
- Roll back the latest deploy if regression is likely.

## Recovery

- Restore service.
- Verify customer workflows.
- Run backup restore if data integrity is involved.
- Publish customer updates if contractual obligations require it.

## Postmortem

Document root cause, impact, detection gap, remediation, and owners.

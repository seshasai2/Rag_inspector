# Enterprise Compliance Posture

This repository includes product controls that support enterprise reviews, but a formal compliance program still requires company policies, evidence collection, and third-party review.

## SOC 2 Roadmap

- Define security, availability, and confidentiality controls.
- Centralize access reviews for production systems.
- Enable vulnerability scanning in CI.
- Track incidents, changes, and access grants.
- Collect evidence for backups, deploys, monitoring, and reviews.
- Engage an auditor when controls have operated long enough for the desired report period.

## DPA And Subprocessors

Prepare a Data Processing Addendum before handling customer production data. Maintain a public subprocessors list covering hosting, email, billing, error monitoring, analytics, and support tools.

## Data Retention

Recommended defaults:

- Audit logs: 1 year minimum.
- Query traces: plan-specific retention, configurable per enterprise account.
- Backups: 14-35 days, with restore tests.
- Webhook delivery logs: 30-90 days.

## Data Export And Deletion

Customers should be able to export traces, reports, audit logs, and billing metadata. Account deletion should remove or anonymize workspace data according to contract and legal retention requirements.

## Encryption

Use managed disk/database encryption at rest in production. Enforce TLS at every public edge. Store provider secrets only in a secret manager.

## Vulnerability Management

CI includes dependency, filesystem/container, and secret scanning. Production should add recurring scans, patch SLAs, and incident response ownership.

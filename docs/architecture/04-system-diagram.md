# System context (C4 Level 1)

High-level view of how customer RAG applications, operators, and identity providers interact with RAGInspector. The platform ingests traces, analyzes them asynchronously, and exposes grounding and metrics through a dashboard and REST API.

```mermaid
flowchart TB
    eng["ML / RAG Engineer"]
    ops["Platform Operator"]
    admin["Org Admin"]

    ri["RAGInspector<br/>ingest · analyze · trust metrics · grounding UI"]

    ragApp["Customer RAG Application<br/>Python + SDK"]
    idp["Identity Provider<br/>OIDC / SAML"]
    llm["LLM / HF APIs<br/>optional NLI / judges"]
    slack["Slack webhooks"]
    billing["Razorpay billing"]

    eng -->|JWT dashboard / API keys| ri
    ops -->|Compose / K8s · /ops/ready| ri
    admin -->|SSO · audit · billing| ri
    ragApp -->|POST /api/v1/ingest/trace<br/>X-API-Key| ri
    ri --> idp
    ri --> llm
    ri --> slack
    ri --> billing
```

See also: [ARCHITECTURE.md](../ARCHITECTURE.md), [05-container-diagram.md](05-container-diagram.md).

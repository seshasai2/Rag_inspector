# Hiring signal (pointer)

The detailed scorecard and interview assessment now live in **[PROJECT_GUIDE.md](../PROJECT_GUIDE.md)** (sections *Interview Preparation* and *Final Engineering Assessment*).

Quick checklist of what to defend from code:

| Signal | Where to look |
|--------|----------------|
| Business problem | README, PROJECT_GUIDE |
| System design | `docs/architecture/`, ADRs |
| Async ML offload | ADR 0001, `analysis_pipeline.py` |
| Grounding UX | `grounding-attribution.tsx`, `/queries/[id]` |
| Security basics | `SECURITY.md`, JWT/MFA/API keys |
| Ops | Compose/Helm, `/live`, `/ops/ready`, Prometheus |
| Honesty layer | `docs/EXPERIMENTAL.md` |
| Performance class | `docs/engineering/PERFORMANCE.md` |

**Do not** claim SAML/SCIM or live Razorpay as GA. Prefer a deep correct core over unfinished enterprise width.

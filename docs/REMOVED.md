# Documentation cleanup log

Record of files removed during repository humanization (2026-07-19). Kept so links and archaeology stay honest.

| Removed file | Reason | Replacement | Risk |
|--------------|--------|-------------|------|
| `PART2A_COMPLETION.md` | One-time sprint completion note | `CHANGELOG.md`, code history | Low — no unique product truth |
| `PART2B_COMPLETION.md` | One-time sprint completion note | `CHANGELOG.md` | Low |
| `PART3A1_COMPLETION.md` | One-time CI/Docker completion note | `docs/BUILD.md`, workflows | Low |
| `PART3A2_COMPLETION.md` | One-time K8s/ops completion note | `docs/KUBERNETES.md`, `docs/HELM.md` | Low |
| `AUDIT_REPORT.md` | Part 1 historical audit; stale claims | `PROJECT_GUIDE.md` | Low |
| `PROJECT_AUDIT.md` | Superseded enterprise audit narrative | `PROJECT_GUIDE.md` | Low |
| `ENTERPRISE_AUDIT_REPORT.md` | Historical audit; Docker-unavailable claims outdated | `PROJECT_GUIDE.md` | Low |
| `FINAL_ENGINEERING_REPORT.md` | Explicitly superseded; overstated readiness scores | `PROJECT_GUIDE.md` | Low |
| `ENGINEERING_COMPLETION_REPORT.md` | Explicitly superseded score card | `PROJECT_GUIDE.md` | Low |
| `ENGINEERING_EVIDENCE_PACKAGE.md` | Freeze package absorbed into guide | `PROJECT_GUIDE.md` | Medium — was prior canonical; guide now owns it |
| `HIRING_VERIFICATION_REPORT.md` | Partially superseded adversarial pass | `PROJECT_GUIDE.md` (Interview / Assessment) | Low |
| `VERIFICATION_REPORT.md` | Stale sprint gate counts | `docs/engineering/TESTING_STRATEGY.md` | Low |
| `TEST_REPORT.md` | Stale test inventory | `docs/engineering/TESTING_STRATEGY.md`, CI | Low |
| `PERFORMANCE_REPORT.md` | Older synthetic baseline tables | `docs/engineering/PERFORMANCE.md` | Low |
| `PERFORMANCE_BENCHMARK_REPORT.md` | 429 RCA + benches consolidated | `docs/engineering/PERFORMANCE.md` | Low |
| `VERIFIED_PERFORMANCE_REPORT.md` | Detail folded into engineering performance doc | `docs/engineering/PERFORMANCE.md` | Low |
| `frontend/coverage/**` | Generated HTML coverage (committed by mistake) | Run `npm test -- --coverage` locally | None |
| `frontend/test-results/**` | Playwright failure artifacts | Regenerated on e2e runs | None |

**Preserved on purpose:** ADRs, architecture diagrams, case studies, ops runbooks, PRD archive, demo pack, `SECURITY.md`, `ROADMAP.md`, `CHANGELOG.md`.

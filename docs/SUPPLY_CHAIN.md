# Software supply chain

## SBOM

```bash
python scripts/generate_sbom.py
# → artifacts/sbom/*-cyclonedx.json
# Prefer full graphs: install Anchore Syft (`syft`) on PATH
```

CI uploads SBOM artifacts on every PR (see `.github/workflows/ci.yml`).

## Dependency inventory

| Stack | Lockfile | Update process |
|-------|----------|----------------|
| Backend | `requirements.txt` via `requirements.in` + `uv pip compile` | Monthly + CVE-driven |
| Frontend | `package-lock.json` | `npm outdated` / Dependabot |
| SDK | `sdk/pyproject.toml` pins `httpx` | Release with SemVer |

## Image metadata / provenance

- Multi-stage Dockerfiles; runtime without compilers.
- CI builds with Buildx; release workflow archives images as release assets.
- Prefer pinning digests in production registries after promotion:
  `raginspector-backend@sha256:…`

## Vulnerability scanning

CI fails on:

- Trivy fs CRITICAL/HIGH (unfixed ignored optionally)
- pip-audit on `backend/requirements.txt`
- npm audit `--audit-level=high`
- Bandit medium+ on `app/`

Container image scan job runs Trivy on built images when Buildx artifacts available.

## Build provenance documentation

1. Source: git SHA (`GITHUB_SHA`)
2. Chart `appVersion` = root `VERSION`
3. Image tags: `VERSION` and git SHA recommended for prod promote
4. Evidence: CI artifacts (coverage, SBOM, Trivy SARIF)

Justification for waiving a CVE must be a PR comment + tracked exception (do not silence scanners silently).

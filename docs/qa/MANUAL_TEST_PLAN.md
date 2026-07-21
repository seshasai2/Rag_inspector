# Manual Test Plan (Phase 5)

Someone unfamiliar with the repo can execute every test below.
Prerequisites for most tests: stack up (`make bootstrap` or Compose) + `make seed` (or `python scripts/seed_demo.py --force`).

**Demo login:** `demo@example.com` / `DemoPass123!`  
**Demo API key:** `ri-demo_interview_seed_key_000000000001`  
**Default URLs:** API `http://localhost:8000` · UI `http://localhost:3000`  
(Windows verify-ports overlay may use `18000` / `13000` — check Compose ports.)

---

## MT-01 — Health & readiness

| Field | Value |
|-------|--------|
| Purpose | Confirm process and dependencies |
| Prerequisites | Containers running |
| Input | None |
| Steps | 1. `GET /live` 2. `GET /health` 3. `GET /api/v1/ops/ready` |
| Expected | 200; ready shows `database=ok`, `redis=ok` |
| Failure indicators | Connection refused; ready 503 |
| Logs | `docker compose logs backend redis db` |
| Recovery | `docker compose up -d`; wait for healthy |
| Time / Difficulty | 2 min / Easy |

## MT-02 — Demo login

| Field | Value |
|-------|--------|
| Purpose | Authenticate seeded user |
| Prerequisites | Seeded DB |
| Input | Demo credentials |
| Steps | Open `/auth/login` → enter email/password → submit |
| Expected | Redirect to `/dashboard`; cookies set |
| Failure indicators | 401 toast; stuck on login |
| Logs | backend auth logs; browser network `/auth/login` |
| Recovery | Re-seed; ensure `REQUIRE_EMAIL_VERIFICATION=false` |
| Time / Difficulty | 2 min / Easy |

## MT-03 — Dashboard metrics

| Field | Value |
|-------|--------|
| Purpose | Trust / cost / failure mix from seed |
| Prerequisites | MT-02 |
| Steps | Open `/dashboard`; select Demo RAG Pipeline |
| Expected | Non-empty cards; trust reflects seeded traces |
| Failure indicators | Zeros everywhere; spinner forever |
| Recovery | `seed_demo.py --force`; hard refresh |
| Time / Difficulty | 3 min / Easy |

## MT-04 — Query grounding detail

| Field | Value |
|-------|--------|
| Purpose | Sentence-level grounding UI |
| Prerequisites | MT-02 |
| Steps | `/queries` → open hallucination trace → hover sentences |
| Expected | Ungrounded sentences highlighted; chunks listed with BM25 |
| Failure indicators | Empty detail; no grounding_results |
| Recovery | Re-seed; check API `GET /queries/{id}` |
| Time / Difficulty | 5 min / Easy |

## MT-05 — Chunks heatmap

| Field | Value |
|-------|--------|
| Purpose | Flagged low-citation chunk |
| Steps | `/chunks` |
| Expected | `doc-onboarding-01` flagged / low citation rate |
| Time / Difficulty | 3 min / Easy |

## MT-06 — Knowledge gaps

| Field | Value |
|-------|--------|
| Purpose | Phase 10.1 UI |
| Steps | `/knowledge/gaps` |
| Expected | Gaps for API key rotation and Enterprise SLA |
| Time / Difficulty | 3 min / Easy |

## MT-07 — Autofix recommendations

| Field | Value |
|-------|--------|
| Purpose | Apply / dismiss / verify flow |
| Steps | `/autofix` → dismiss one → refresh → verify status |
| Expected | Status changes via API |
| Failure indicators | Empty list |
| Recovery | Re-seed |
| Time / Difficulty | 5 min / Medium |

## MT-08 — Documents freshness

| Field | Value |
|-------|--------|
| Purpose | Fresh / stale / critical docs |
| Steps | `/documents` |
| Expected | Three docs with mixed freshness |
| Time / Difficulty | 3 min / Easy |

## MT-09 — Monitoring history

| Field | Value |
|-------|--------|
| Purpose | Probe runs + alerts |
| Steps | `/monitoring` → view history; optional Run now |
| Expected | Prior runs with trust scores; alert on low trust |
| Time / Difficulty | 5 min / Medium |

## MT-10 — Regression compare

| Field | Value |
|-------|--------|
| Purpose | Pre-deploy delta |
| Steps | `/regression` → compare baseline vs candidate |
| Expected | Trust drop / hallucination rise visible |
| Time / Difficulty | 5 min / Medium |

## MT-11 — API key ingest (live path)

| Field | Value |
|-------|--------|
| Purpose | End-to-end ingest → worker |
| Prerequisites | Worker healthy; models optional (analysis may be slow) |
| Input | Demo API key + pipeline id from login/pipelines |
| Steps | See [API_EXAMPLES.md](API_EXAMPLES.md) ingest curl; wait; refresh `/queries` |
| Expected | New trace appears; status pending→completed (or failed with error) |
| Failure indicators | 401; stuck pending |
| Logs | `celery_worker` logs; `/ops/backlog` |
| Recovery | Restart worker; check Redis |
| Time / Difficulty | 5–15 min / Medium |

## MT-12 — Pipelines & settings

| Field | Value |
|-------|--------|
| Purpose | CRUD + cost assumptions |
| Steps | `/pipelines` edit cost; `/settings` change threshold; save |
| Expected | Persist after reload |
| Time / Difficulty | 5 min / Easy |

## MT-13 — Team / org

| Field | Value |
|-------|--------|
| Purpose | Org membership visible |
| Steps | `/team` |
| Expected | Acme Support Labs; demo user as owner |
| Time / Difficulty | 3 min / Easy |

## MT-14 — Executive reports

| Field | Value |
|-------|--------|
| Purpose | Report history / ROI surfaces |
| Steps | `/executive` |
| Expected | Seeded executive summary / history entry |
| Time / Difficulty | 3 min / Easy |

## MT-15 — Studio & Investigator

| Field | Value |
|-------|--------|
| Purpose | Heuristic tools respond |
| Steps | `/studio` analyze sample prompt; `/investigator` ask “What is our trust score?” |
| Expected | Structured response citing metrics (not empty error) |
| Time / Difficulty | 5 min / Medium |

## MT-16 — Benchmark

| Field | Value |
|-------|--------|
| Purpose | Measured benchmark on real traces |
| Steps | `/benchmark` run retrieval for Demo pipeline |
| Expected | Scores from stored traces |
| Time / Difficulty | 5 min / Medium |

## MT-17 — Invalid login

| Field | Value |
|-------|--------|
| Purpose | Auth failure path |
| Steps | Login with wrong password |
| Expected | Error message; no session |
| Time / Difficulty | 1 min / Easy |

## MT-18 — Logout

| Field | Value |
|-------|--------|
| Purpose | Session end |
| Steps | Logout → visit `/dashboard` |
| Expected | Redirect to login |
| Time / Difficulty | 2 min / Easy |

## MT-19 — Responsive smoke

| Field | Value |
|-------|--------|
| Purpose | Mobile layout |
| Steps | DevTools 375px width on dashboard + queries |
| Expected | Nav usable; no horizontal overflow blocking CTAs |
| Time / Difficulty | 5 min / Easy |

## MT-20 — Register new user

| Field | Value |
|-------|--------|
| Purpose | Onboarding path |
| Steps | `/auth/register` with unique email → complete onboarding if shown |
| Expected | Account created; can create pipeline |
| Time / Difficulty | 5 min / Medium |

---

## Suite timing

Full manual suite (MT-01–MT-20): ~60–90 minutes.  
Interview subset: MT-01, 02, 03, 04, 06, 08, 10, 11 (optional): ~15 minutes.

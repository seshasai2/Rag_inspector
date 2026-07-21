# End-to-End Workflows (Phase 8)

Each workflow must finish successfully on a seeded local stack unless noted.

## WF-01 — Interview happy path (no long ML wait)

1. `docker compose up -d` (+ migrate/seed).
2. Login demo user.
3. Dashboard → Queries → open hallucination → Chunks → Knowledge gaps → Documents → Regression → Executive.
4. Logout.

**Success:** All pages show seeded data within 10 minutes; no Celery required for seed rows.

## WF-02 — Registration → first pipeline

1. Register unique email (verification off).
2. Complete onboarding if prompted.
3. Create pipeline “My First RAG”.
4. Create API key; copy once.
5. Ingest sample payload with that key.
6. Wait for analysis (worker) or accept pending.
7. View query in list.

**Success:** Trace owned by new user; plan quota decremented.

## WF-03 — Live ingest → analyze → inspect

1. Login demo; note `PIPELINE_ID`.
2. `POST /ingest/trace` with demo API key.
3. Poll `GET /ops/backlog` until pending drops.
4. Open new query; confirm grounding fields when completed.

**Success:** `analysis_status=completed` (or documented failure if models OOM — see FAILURE_TESTING).

## WF-04 — Autofix loop

1. Open `/autofix`; note recommendation.
2. Apply or dismiss via UI.
3. Refresh; status persisted.
4. Optional verify endpoint after apply.

## WF-05 — Monitoring run

1. `/monitoring` enable/config already seeded.
2. Run now.
3. History gains a new run row.

## WF-06 — Regression pre-deploy

1. List snapshots (baseline + candidate seeded).
2. Compare; observe trust delta.
3. Optional `pre-deploy-check` API.

## WF-07 — Team invite (manual second user)

1. Register second user.
2. As demo owner, invite second email from `/team`.
3. Accept invite as second user.
4. Confirm membership list.

## WF-08 — Export / report history

1. `/executive` or `GET /reports/executive`.
2. Confirm history includes seeded executive JSON report.

## WF-09 — Delete resource

1. Create throwaway pipeline.
2. DELETE via UI/API.
3. Confirm gone from list; traces cascade.

## WF-10 — SDK demo

1. `pip install -e ./sdk`
2. `RAGINSPECTOR_API_KEY=ri-demo_interview_seed_key_000000000001 python examples/demo_send_trace.py`
3. Trace appears under demo account.

**Success:** Script exits 0; query list grows.

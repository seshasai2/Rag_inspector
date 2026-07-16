# Demo walkthrough (UI click-path)

Step-by-step walkthrough aligned with the seeded demo dataset. URLs assume local Compose defaults.

## 1. Sign in

1. Open http://localhost:3000/auth/login.
2. Email: `demo@example.com` — Password: `DemoPass123!`.
3. Land on dashboard or complete onboarding if prompted.

## 2. Dashboard overview

1. Route: `/dashboard`.
2. Confirm cards for trust score, hallucination cost, recent failure mix.
3. Note pipeline selector if multiple pipelines exist.

## 3. Pipelines

1. Route: `/pipelines`.
2. Open the primary demo pipeline.
3. Review stats: trust score, hallucination rate, query volume.
4. Optionally PATCH cost fields from Settings-linked pipeline edit.

## 4. Queries list → detail

1. Route: `/queries`.
2. Filter by failure type if UI provides filters (hallucination / retrieval_miss).
3. Open a detail page `/queries/[id]`.
4. Interact with grounding attribution: hover sentences, pin, scroll to chunk.
5. Expand BM25 comparison payload if shown.

## 5. Chunks quality

1. Route: `/chunks`.
2. Show flagged chunks (low citation rate).
3. Open summary metrics via API or summary panel.

## 6. Metrics

1. Route: `/metrics`.
2. Timeseries, BM25 comparison, latency breakdown.
3. Tie spikes to ingest bursts if you just posted traces.

## 7. Settings & keys

1. Route: `/settings`.
2. Create an API key if none; copy once.
3. Configure Slack webhook only if demonstrating alerts (optional).

## 8. Optional enterprise surfaces

Without blocking the core story, briefly open:

- `/team` — memberships
- `/enterprise` — SSO / controls when enabled
- `/monitoring` — alert rules

## 9. Sign out

Use shell logout or settings sign-out; confirm redirect to login.

## Success criteria

- At least one analyzed query with grounding highlights
- Non-zero trust score on dashboard
- Ingest of one new trace appears in list within ~30–90s (worker warm)

Related: [DEMO_DATASET.md](DEMO_DATASET.md), [FEATURE_WALKTHROUGH.md](FEATURE_WALKTHROUGH.md).

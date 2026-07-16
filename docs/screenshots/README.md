# Grounding screenshots (Phase 9.3)

## Canonical demo content

Static HTML render of the **seeded grounded trace** (exact strings from `demo_seed.py`):

- [grounding-attribution.html](grounding-attribution.html)
- [grounding-attribution.png](grounding-attribution.png) — committed demo asset for README

Open in a browser, or capture PNG:

```bash
# if Playwright is available
npx --yes playwright install chromium
npx --yes playwright screenshot docs/screenshots/grounding-attribution.html docs/screenshots/grounding-attribution.png --viewport-size=1200,700
```

## Live UI (preferred when stack is up)

1. `make up && make migrate && make seed`
2. Login `demo@example.com` / `DemoPass123!`
3. Open **Queries** → refund-window trace → hover grounded sentences
4. Save PNG as `docs/screenshots/query-detail-live.png` and link from README

Helpers: `scripts/capture_grounding_screenshot.ps1` / `.sh`

# Frontend E2E (Playwright)

Specs under `frontend/e2e/tests/`. Script: `npm run test:e2e` (see `frontend/package.json`).

## Install browsers (once)

```bash
cd frontend
npx playwright install chromium
```

## Run against local `next dev` (port 3000)

Do **not** leave a foreign process on `:3000`. Playwright no longer reuses an existing server unless `PLAYWRIGHT_REUSE=1`.

```bash
cd frontend
# Ensure API is up on :8000 (or set API_BASE_URL)
npm run test:e2e
```

## Run against Compose verify-ports (Windows)

UI `:13000`, API `:18000`:

```powershell
cd frontend
$env:PLAYWRIGHT_BASE_URL = "http://localhost:13000"
$env:API_BASE_URL = "http://localhost:18000"
$env:PLAYWRIGHT_SKIP_WEBSERVER = "1"
$env:DEMO_EMAIL = "demo@example.com"
$env:DEMO_PASSWORD = "DemoPass123!"
npm run test:e2e
```

## Specs

| File | Coverage |
|------|----------|
| `tests/auth.spec.ts` | Login/register UI; register + demo login when API healthy |
| `tests/dashboard.spec.ts` | Dashboard after login |
| `tests/navigation.spec.ts` | Queries + settings navigation |
| `tests/responsive.spec.ts` | Mobile viewport |
| `tests/errors.spec.ts` | 404 / invalid route handling |

## Known pitfall

If `/auth/login` redirects to `/login`, you are hitting the **wrong** app on that port. Point `PLAYWRIGHT_BASE_URL` at the RAGInspector UI (Compose verify-ports uses `http://localhost:13000`).

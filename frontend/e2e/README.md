# Frontend E2E (Playwright)

End-to-end tests live under `frontend/e2e/`. They are not wired into `package.json` yet so existing CI scripts stay unchanged.

## Add these scripts and dependency

In `frontend/package.json`, add:

```json
{
  "scripts": {
    "test:e2e": "playwright test -c e2e/playwright.config.ts"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0"
  }
}
```

Then install browsers:

```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium
```

## Run

Requires API + UI (for example `make up` from the repo root) and optional demo user from `make seed`.

```bash
cd frontend
# Use an already-running Next.js server:
PLAYWRIGHT_SKIP_WEBSERVER=1 DEMO_EMAIL=demo@example.com DEMO_PASSWORD=DemoPass123! \
  npx playwright test -c e2e/playwright.config.ts

# Or let Playwright start `npm run dev` (see playwright.config.ts webServer):
DEMO_EMAIL=demo@example.com DEMO_PASSWORD=DemoPass123! npm run test:e2e
```

## Specs

| File | Coverage |
|------|----------|
| `tests/auth.spec.ts` | Register (random email), login/logout (demo env) |
| `tests/dashboard.spec.ts` | Dashboard loads after login |
| `tests/navigation.spec.ts` | Queries + settings navigation |
| `tests/responsive.spec.ts` | Mobile viewport (390×844) |
| `tests/errors.spec.ts` | 404 / invalid route handling |

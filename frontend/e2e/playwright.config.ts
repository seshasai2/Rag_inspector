import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for RAGInspector frontend E2E.
 * Run from frontend/: npx playwright test -c e2e/playwright.config.ts
 *
 * Env:
 *   PLAYWRIGHT_BASE_URL  default http://localhost:3000
 *   DEMO_EMAIL           default demo@example.com
 *   DEMO_PASSWORD        default DemoPass123!
 *   API_BASE_URL         default http://localhost:8000 (reserved for API helpers)
 */
/**
 * Prefer an explicit URL. On Windows Compose verify-ports the UI is :13000.
 * Avoid silently reusing a foreign process on :3000 that redirects /auth/login → /login.
 */
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ||
  process.env.RAGINSPECTOR_UI_URL ||
  "http://localhost:3000";

const apiBase =
  process.env.API_BASE_URL ||
  process.env.RAGINSPECTOR_API_URL ||
  "http://localhost:8000";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // Compose/standalone Next can reset connections under heavy parallel goto() on Windows.
  workers: process.env.CI ? 2 : 1,
  reporter: [["list"], ["html", { open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  /* Expose for specs that import config metadata via env */
  metadata: { apiBase },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run dev",
        url: `${baseURL.replace(/\/$/, "")}/auth/login`,
        reuseExistingServer: process.env.PLAYWRIGHT_REUSE === "1",
        timeout: 120_000,
      },
});

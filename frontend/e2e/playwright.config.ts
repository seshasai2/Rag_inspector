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
const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
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
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});

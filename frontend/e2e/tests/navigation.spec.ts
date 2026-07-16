import { test, expect } from "@playwright/test";

const DEMO_EMAIL = process.env.DEMO_EMAIL || "demo@example.com";
const DEMO_PASSWORD = process.env.DEMO_PASSWORD || "DemoPass123!";
const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

async function apiHealthy(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/live`);
    return res.ok;
  } catch {
    return false;
  }
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/auth/login");
  await page
    .getByLabel(/email/i)
    .or(page.locator('input[type="email"]'))
    .first()
    .fill(DEMO_EMAIL);
  await page
    .getByLabel(/password/i)
    .or(page.locator('input[type="password"]'))
    .first()
    .fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: /sign in|log in|login/i }).click();
  await expect(page).not.toHaveURL(/\/auth\/login$/, { timeout: 20_000 });
}

test.describe("navigation", () => {
  test.beforeAll(async () => {
    test.skip(!(await apiHealthy()), "Backend required for navigation e2e");
  });

  test("navigates through queries and settings", async ({ page }) => {
    await login(page);
    await page.goto("/dashboard");

    const queriesNav = page.getByRole("link", { name: /queries/i }).first();
    if (await queriesNav.isVisible().catch(() => false)) {
      await queriesNav.click();
    } else {
      await page.goto("/queries");
    }
    await expect(page).toHaveURL(/\/queries/);

    await page.goto("/settings");
    await expect(page).toHaveURL(/\/settings/);
  });
});

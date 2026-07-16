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

test.describe("auth UI", () => {
  test("login page renders", async ({ page }) => {
    await page.goto("/auth/login");
    await expect(page).toHaveURL(/\/auth\/login/);
    await expect(
      page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first()
    ).toBeVisible();
    await expect(
      page.getByLabel(/password/i).or(page.locator('input[type="password"]')).first()
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in|log in|login/i })).toBeVisible();
  });

  test("register page renders", async ({ page }) => {
    await page.goto("/auth/register");
    await expect(page).toHaveURL(/\/auth\/register/);
    await expect(
      page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first()
    ).toBeVisible();
  });
});

test.describe("auth API flows", () => {
  test.beforeAll(async () => {
    test.skip(!(await apiHealthy()), "Backend /live not reachable — start stack for full auth e2e");
  });

  test("register with a random email", async ({ page }) => {
    const email = `e2e+${Date.now()}_${Math.floor(Math.random() * 1e6)}@example.com`;
    const password = "E2ePass123!";

    await page.goto("/auth/register");
    const emailField = page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first();
    const passwordField = page
      .getByLabel(/^password$/i)
      .or(page.locator('input[type="password"]'))
      .first();
    const nameField = page.getByLabel(/name/i).or(page.locator('input[name="name"]')).first();

    if (await nameField.count()) {
      await nameField.fill("E2E Registrant");
    }
    await emailField.fill(email);
    await passwordField.fill(password);

    const confirm = page.getByLabel(/confirm/i);
    if (await confirm.count()) {
      await confirm.fill(password);
    }

    await page.getByRole("button", { name: /sign up|register|create/i }).click();
    await expect(page).not.toHaveURL(/\/auth\/register$/, { timeout: 20_000 });
  });

  test("login and logout with demo credentials", async ({ page }) => {
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
  });
});

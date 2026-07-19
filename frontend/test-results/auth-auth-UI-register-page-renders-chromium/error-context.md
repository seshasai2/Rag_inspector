# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth.spec.ts >> auth UI >> register page renders
- Location: e2e\tests\auth.spec.ts:29:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:13000/auth/register
Call log:
  - navigating to "http://localhost:13000/auth/register", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | 
  3  | const DEMO_EMAIL = process.env.DEMO_EMAIL || "demo@example.com";
  4  | const DEMO_PASSWORD = process.env.DEMO_PASSWORD || "DemoPass123!";
  5  | const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";
  6  | 
  7  | async function apiHealthy(): Promise<boolean> {
  8  |   try {
  9  |     const res = await fetch(`${API_BASE}/live`);
  10 |     return res.ok;
  11 |   } catch {
  12 |     return false;
  13 |   }
  14 | }
  15 | 
  16 | test.describe("auth UI", () => {
  17 |   test("login page renders", async ({ page }) => {
  18 |     await page.goto("/auth/login");
  19 |     await expect(page).toHaveURL(/\/auth\/login/);
  20 |     await expect(
  21 |       page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first()
  22 |     ).toBeVisible();
  23 |     await expect(
  24 |       page.getByLabel(/password/i).or(page.locator('input[type="password"]')).first()
  25 |     ).toBeVisible();
  26 |     await expect(page.getByRole("button", { name: /sign in|log in|login/i })).toBeVisible();
  27 |   });
  28 | 
  29 |   test("register page renders", async ({ page }) => {
> 30 |     await page.goto("/auth/register");
     |                ^ Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:13000/auth/register
  31 |     await expect(page).toHaveURL(/\/auth\/register/);
  32 |     await expect(
  33 |       page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first()
  34 |     ).toBeVisible();
  35 |   });
  36 | });
  37 | 
  38 | test.describe("auth API flows", () => {
  39 |   test.beforeAll(async () => {
  40 |     test.skip(!(await apiHealthy()), "Backend /live not reachable — start stack for full auth e2e");
  41 |   });
  42 | 
  43 |   test("register with a random email", async ({ page }) => {
  44 |     const email = `e2e+${Date.now()}_${Math.floor(Math.random() * 1e6)}@example.com`;
  45 |     const password = "E2ePass123!";
  46 | 
  47 |     await page.goto("/auth/register");
  48 |     const emailField = page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first();
  49 |     const passwordField = page
  50 |       .getByLabel(/^password$/i)
  51 |       .or(page.locator('input[type="password"]'))
  52 |       .first();
  53 |     const nameField = page.getByLabel(/name/i).or(page.locator('input[name="name"]')).first();
  54 | 
  55 |     if (await nameField.count()) {
  56 |       await nameField.fill("E2E Registrant");
  57 |     }
  58 |     await emailField.fill(email);
  59 |     await passwordField.fill(password);
  60 | 
  61 |     const confirm = page.getByLabel(/confirm/i);
  62 |     if (await confirm.count()) {
  63 |       await confirm.fill(password);
  64 |     }
  65 | 
  66 |     await page.getByRole("button", { name: /sign up|register|create/i }).click();
  67 |     await expect(page).not.toHaveURL(/\/auth\/register$/, { timeout: 20_000 });
  68 |   });
  69 | 
  70 |   test("login and logout with demo credentials", async ({ page }) => {
  71 |     await page.goto("/auth/login");
  72 |     await page
  73 |       .getByLabel(/email/i)
  74 |       .or(page.locator('input[type="email"]'))
  75 |       .first()
  76 |       .fill(DEMO_EMAIL);
  77 |     await page
  78 |       .getByLabel(/password/i)
  79 |       .or(page.locator('input[type="password"]'))
  80 |       .first()
  81 |       .fill(DEMO_PASSWORD);
  82 |     await page.getByRole("button", { name: /sign in|log in|login/i }).click();
  83 |     await expect(page).not.toHaveURL(/\/auth\/login$/, { timeout: 20_000 });
  84 |   });
  85 | });
  86 | 
```
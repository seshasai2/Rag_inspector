# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: responsive.spec.ts >> responsive >> mobile viewport renders login form
- Location: e2e\tests\responsive.spec.ts:6:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:13000/auth/login
Call log:
  - navigating to "http://localhost:13000/auth/login", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | 
  3  | test.describe("responsive", () => {
  4  |   test.use({ viewport: { width: 390, height: 844 } });
  5  | 
  6  |   test("mobile viewport renders login form", async ({ page }) => {
> 7  |     await page.goto("/auth/login");
     |                ^ Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:13000/auth/login
  8  |     await expect(page.locator("body")).toBeVisible();
  9  |     await expect(
  10 |       page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first()
  11 |     ).toBeVisible();
  12 |     const box = await page.locator("body").boundingBox();
  13 |     expect(box?.width).toBeLessThanOrEqual(390);
  14 |   });
  15 | });
  16 | 
```
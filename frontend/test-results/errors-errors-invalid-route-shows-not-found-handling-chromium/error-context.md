# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: errors.spec.ts >> errors >> invalid route shows not-found handling
- Location: e2e\tests\errors.spec.ts:4:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:13000/this-route-should-not-exist-e2e-404
Call log:
  - navigating to "http://localhost:13000/this-route-should-not-exist-e2e-404", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | 
  3  | test.describe("errors", () => {
  4  |   test("invalid route shows not-found handling", async ({ page }) => {
> 5  |     const response = await page.goto("/this-route-should-not-exist-e2e-404");
     |                                 ^ Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:13000/this-route-should-not-exist-e2e-404
  6  |     expect(response).not.toBeNull();
  7  | 
  8  |     const status = response!.status();
  9  |     // Next.js may return 404 status or soft-render a not-found page with 200.
  10 |     expect([200, 404]).toContain(status);
  11 | 
  12 |     const bodyText = await page.locator("body").innerText();
  13 |     const hasNotFoundSignal =
  14 |       /404|not found|page doesn.?t exist|does not exist|missing/i.test(bodyText) ||
  15 |       status === 404;
  16 | 
  17 |     expect(hasNotFoundSignal).toBeTruthy();
  18 |   });
  19 | 
  20 |   test("deep invalid nested path does not crash the app", async ({ page }) => {
  21 |     await page.goto("/queries/not-a-real-id-zzzz");
  22 |     await expect(page.locator("body")).toBeVisible();
  23 |     // Should remain an app shell (login redirect, error banner, or not-found) — not a blank crash.
  24 |     const text = await page.locator("body").innerText();
  25 |     expect(text.length).toBeGreaterThan(0);
  26 |   });
  27 | });
  28 | 
```
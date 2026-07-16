import { test, expect } from "@playwright/test";

test.describe("errors", () => {
  test("invalid route shows not-found handling", async ({ page }) => {
    const response = await page.goto("/this-route-should-not-exist-e2e-404");
    expect(response).not.toBeNull();

    const status = response!.status();
    // Next.js may return 404 status or soft-render a not-found page with 200.
    expect([200, 404]).toContain(status);

    const bodyText = await page.locator("body").innerText();
    const hasNotFoundSignal =
      /404|not found|page doesn.?t exist|does not exist|missing/i.test(bodyText) ||
      status === 404;

    expect(hasNotFoundSignal).toBeTruthy();
  });

  test("deep invalid nested path does not crash the app", async ({ page }) => {
    await page.goto("/queries/not-a-real-id-zzzz");
    await expect(page.locator("body")).toBeVisible();
    // Should remain an app shell (login redirect, error banner, or not-found) — not a blank crash.
    const text = await page.locator("body").innerText();
    expect(text.length).toBeGreaterThan(0);
  });
});

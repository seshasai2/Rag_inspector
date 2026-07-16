import { test, expect } from "@playwright/test";

test.describe("responsive", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("mobile viewport renders login form", async ({ page }) => {
    await page.goto("/auth/login");
    await expect(page.locator("body")).toBeVisible();
    await expect(
      page.getByLabel(/email/i).or(page.locator('input[type="email"]')).first()
    ).toBeVisible();
    const box = await page.locator("body").boundingBox();
    expect(box?.width).toBeLessThanOrEqual(390);
  });
});

const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const base = "http://127.0.0.1:13000";

  page.on("response", async (res) => {
    if (res.url().includes("/api/v1/auth/") && ["POST", "GET"].includes(res.request().method())) {
      console.log("API", res.request().method(), res.status(), res.url().replace(base, ""));
    }
  });

  // Warm the app so Fast Refresh settles before auth.
  await page.goto(`${base}/auth/login`, { waitUntil: "networkidle", timeout: 90000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "e2e/artifacts/01-login.png", fullPage: true });

  await page.locator('input[type="email"]').fill("demo@example.com");
  await page.locator('input[type="password"]').fill("DemoPass123!");
  await page.getByRole("button", { name: /sign in/i }).click();

  await page.waitForURL((url) => !url.pathname.includes("/auth/login"), { timeout: 30000 });
  console.log("URL_AFTER_LOGIN", page.url());
  await page.waitForTimeout(2000);
  await page.screenshot({ path: "e2e/artifacts/02-after-login.png", fullPage: true });

  await page.goto(`${base}/dashboard`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "e2e/artifacts/03-dashboard.png", fullPage: true });

  await page.goto(`${base}/queries`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "e2e/artifacts/04-queries.png", fullPage: true });

  console.log("SHOTS_OK", page.url());
  await browser.close();
})().catch((e) => {
  console.error("CAPTURE_FAIL", e.message);
  process.exit(1);
});

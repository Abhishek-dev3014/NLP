import { test, expect } from "@playwright/test";
test("the supplied public MSN URL extracts and produces an article assessment", async ({
  page,
}) => {
  await page.goto("/analyze");
  await page.getByRole("tab", { name: "Analyze URL" }).click();
  await page
    .getByLabel("Public article URL")
    .fill(
      "https://www.msn.com/en-in/news/other/siddaramaiah-likely-to-meet-rahul-on-november-2/ar-AA2g31Lf?ocid=msedgntp&pc=U531",
    );
  await page.getByRole("button", { name: "Extract", exact: true }).click();
  await expect(page.getByLabel("Article headline")).toHaveValue(
    "Siddaramaiah likely to meet Rahul on November 2",
    { timeout: 35000 },
  );
  await expect(page.getByLabel("Article content")).toHaveValue(/Siddaramaiah/);
  await page
    .getByRole("button", { name: "Analyze article", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your analysis report" }),
  ).toBeVisible();
  await expect(
    page.getByText("Not independently verified", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".prediction-section strong")).not.toHaveText(
    "Not available",
  );
  await expect(
    page.getByRole("link", { name: "Open original source" }),
  ).toHaveAttribute("href", /msn.com.*ar-AA2g31Lf$/);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: "test-results/msn-report-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".app-main")).toHaveCSS("margin-left", "0px");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "test-results/msn-report-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
});

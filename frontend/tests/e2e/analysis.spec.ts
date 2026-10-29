import { test, expect } from "@playwright/test";
test("article → genuine FastAPI prediction → saved result → history → deletion", async ({
  page,
}) => {
  await page.goto("/analyze");
  await page.getByRole("button", { name: "Try an example" }).click();
  await expect(page.getByText(/Demonstration example written/)).toBeVisible();
  const responsePromise = page.waitForResponse(
    (r) =>
      r.url().includes("/api/analyze/text") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze article" }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const report = await response.json();
  await expect(page).toHaveURL(`/results/${report.id}`);
  await expect(
    page.getByRole("heading", { name: report.prediction.label, exact: true }),
  ).toBeVisible();
  await expect(page.getByText(report.headline, { exact: true })).toBeVisible();
  await expect(
    page.getByText(`${(report.prediction.confidence * 100).toFixed(1)}%`, {
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your analysis report" }),
  ).toBeVisible();
  await page.goto("/dashboard");
  await expect(page.getByText("Total articles analyzed")).toBeVisible();
  await page.goto("/history");
  await expect(
    page.getByRole("link", { name: report.headline, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: `Delete ${report.headline}` }).click();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(
    page.getByRole("heading", { name: "A fresh start for your research" }),
  ).toBeVisible();
});
test("mobile navigation, analyzer layout, and light theme work", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Analyze", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Analyze news with AI" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page
    .getByRole("button", { name: "Toggle light and dark theme" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

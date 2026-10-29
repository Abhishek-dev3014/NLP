import { test, expect } from "@playwright/test";
test("NLP lab returns real entities, lemmas and summary without saving history", async ({
  page,
}) => {
  await page.goto("/nlp-lab");
  await page.getByRole("button", { name: "Explore language" }).click();
  await expect(
    page.getByRole("heading", { name: "Understand the content" }),
  ).toBeVisible();
  await expect(
    page.locator(".entity-chip").filter({ hasText: "London" }),
  ).toBeVisible();
  await page.getByText("Explore the NLP · tokens, lemmas & grammar").click();
  const borrowed = page.getByRole("row").filter({ hasText: "borrowed" });
  await expect(
    borrowed.getByRole("cell", { name: "borrow", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Dependency parsing" }),
  ).toBeVisible();
  await page.getByText("Explore the NLP · tokens, lemmas & grammar").click();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: "test-results/nlp-lab-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.goto("/history");
  await expect(
    page.getByRole("heading", { name: "A fresh start for your research" }),
  ).toBeVisible();
});
test("long article gets a prediction and a claim can be investigated", async ({
  page,
}) => {
  await page.goto("/analyze");
  const sentence =
    "The federal government proposed a budget that would increase funding for public education next year.";
  await page
    .getByLabel("Article content")
    .fill(Array(13).fill(sentence).join(" "));
  await expect(
    page.getByText("Article screening", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Analyze article", exact: true })
    .click();
  await expect(
    page.getByText("Not independently verified", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Withheld", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Understand the content" }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: "test-results/article-report-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page
    .getByRole("button", { name: "Analyze this claim" })
    .first()
    .click();
  await expect(page).toHaveURL("/analyze");
  await expect(page.getByLabel("Article content")).toHaveValue(sentence);
});
test("model page separates the article benchmark from cross-domain accuracy", async ({
  page,
}) => {
  await page.goto("/model-performance");
  await expect(
    page.getByRole("heading", { name: "Full-article benchmark" }),
  ).toBeVisible();
  await expect(
    page.getByText("90% target reached on this benchmark"),
  ).toBeVisible();
  await expect(page.getByText("96.3%", { exact: true })).toBeVisible();
  await page
    .getByText("Calibration, label audit & previous experiments")
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Does that accuracy transfer to other news?",
    }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: "test-results/model-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".app-main")).toHaveCSS("margin-left", "0px");
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: "test-results/model-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});

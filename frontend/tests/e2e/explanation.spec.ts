import { test, expect } from "@playwright/test";

test("explanation connects model features to context and distinguishes linguistic cues", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/analyze");
  await page.getByRole("button", { name: "Try an example" }).click();
  await page
    .getByRole("button", { name: "Analyze article", exact: true })
    .click();
  const studio = page.locator(".explanation-studio");
  await expect(
    studio.getByRole("heading", { name: "Why did it get this result?" }),
  ).toBeVisible();
  const features = studio.locator(".explain-feature");
  expect(await features.count()).toBeGreaterThan(1);
  await features.nth(1).click();
  await expect(features.nth(1)).toHaveAttribute("aria-pressed", "true");
  await expect(studio.locator(".explain-excerpt mark")).toBeVisible();
  await studio.screenshot({
    path: "test-results/explanation-dark-desktop.png",
    animations: "disabled",
  });
  await studio
    .getByRole("button", { name: "Language cues", exact: true })
    .click();
  await expect(
    studio.getByRole("heading", { name: "Absolute claims" }),
  ).toBeVisible();
  await expect(
    studio.getByText(/not inputs to the current article classifier/),
  ).toBeVisible();
  await studio.screenshot({
    path: "test-results/explanation-cues.png",
    animations: "disabled",
  });
  await studio
    .getByRole("button", { name: "How NLP works", exact: true })
    .click();
  await expect(
    studio.getByRole("heading", { name: "Learned decision · Linear SVM" }),
  ).toBeVisible();
  await studio
    .getByRole("button", { name: "Words that influenced it", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Toggle light and dark theme" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await studio.screenshot({
    path: "test-results/explanation-light-desktop.png",
    animations: "disabled",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".app-main")).toHaveCSS("margin-left", "0px");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await studio.screenshot({
    path: "test-results/explanation-light-mobile.png",
    animations: "disabled",
  });
  await studio
    .getByRole("button", { name: "How NLP works", exact: true })
    .click();
  await studio.getByRole("link", { name: /Explore this article/ }).click();
  await expect(page).toHaveURL(/#content-inspection$/);
  await page
    .getByRole("heading", { name: "Why did it get this result?" })
    .scrollIntoViewIfNeeded();
  await studio.getByRole("link", { name: /Review the claims/ }).click();
  await expect(page).toHaveURL(/#claims-review$/);
});

test("Moon example explains urgency without claiming factual verification", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/analyze");
  await page
    .getByLabel("Article content")
    .fill(
      "A shocking report claims that astronauts have discovered a hidden city on the Moon where thousands of people have been living for decades. The story says a secret spacecraft photographed buildings, roads, and large underground factories. You won’t believe what happened next: anonymous insiders allegedly confirmed that world leaders have known about the settlement for years. The article claims the discovery is undeniable and that everyone will soon receive an invitation to travel there. However, the report provides no original photographs, mission records, named researchers, or published scientific findings. It asks readers to share before the story disappears and insists that its claims are guaranteed to be correct.",
    );
  await page
    .getByRole("button", { name: "Analyze article", exact: true })
    .click();
  const studio = page.locator(".explanation-studio");
  await studio
    .getByRole("button", { name: "share Toward misleading", exact: true })
    .click();
  await expect(
    studio.getByText(/The concern is this appeal to urgency/),
  ).toBeVisible();
  await expect(
    studio.getByText(/Rule-based phrase matching · regular expressions/),
  ).toBeVisible();
  await expect(studio.getByText("Linear SVM attribution")).toBeVisible();
  await page
    .getByRole("button", { name: "Toggle light and dark theme" })
    .click();
  await studio
    .locator(".explain-detail")
    .screenshot({
      path: "test-results/contextual-share-explanation.png",
      animations: "disabled",
    });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".app-main")).toHaveCSS("margin-left", "0px");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await studio
    .getByRole("button", { name: "story Toward misleading", exact: true })
    .click();
  await expect(
    studio.getByText(/No specific language problem was detected for/),
  ).toBeVisible();
});

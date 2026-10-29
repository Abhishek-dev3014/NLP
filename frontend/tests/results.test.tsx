import { fireEvent, render, screen } from "@testing-library/react";
import { vi, test, expect } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Results } from "@/components/results";
import { AppShell } from "@/components/shell";
import { EmptyState } from "@/components/common";
import type { Analysis } from "@/lib/types";
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}));
const actual: Analysis = {
  id: "test",
  headline: "Returned headline from API",
  text: "This returned article has shocking wording that deserves verification.",
  input_type: "text",
  source_url: null,
  created_at: "2026-01-01T12:00:00Z",
  prediction: {
    label: "Needs Further Verification",
    confidence: 0.52,
    probabilities: { credible: 0.48, misleading: 0.52 },
    model_name: "Test model",
    model_version: "test-v1",
    calibrated: false,
    in_domain: true,
    features: [],
    warnings: ["Uncalibrated output"],
    vocabulary_coverage: 0.5,
  },
  insights: {
    word_count: 10,
    character_count: 65,
    sentence_count: 1,
    average_sentence_length: 10,
    sentiment_score: 0,
    subjectivity_score: null,
    clickbait_indicator: 0,
    emotional_indicator: 1,
    certainty_indicator: 0,
    method: "Test heuristic",
  },
  highlights: [],
  claims: [],
  evidence: {
    status: "unconfigured",
    message: "External evidence not configured.",
    items: [],
  },
  explanation: "Returned explanation from API",
  recommendations: ["Check primary sources."],
};
test("renders returned results and disclosed uncertainty", () => {
  const client = new QueryClient();
  client.setQueryData(["analysis", "test"], actual);
  render(
    <QueryClientProvider client={client}>
      <Results id="test" />
    </QueryClientProvider>,
  );
  expect(screen.getByText(actual.headline)).toBeVisible();
  expect(screen.getByText("52.0%")).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Why did it get this result?" }),
  ).toBeVisible();
  expect(
    screen.getByText("No model feature contributions are available."),
  ).toBeVisible();
  expect(screen.getByText("External evidence not configured.")).toBeVisible();
});
test("mobile navigation exposes expanded links", async () => {
  render(
    <AppShell>
      <p>Content</p>
    </AppShell>,
  );
  const toggle = screen.getByRole("button", { name: "Open navigation" });
  toggle.click();
  expect(
    await screen.findByRole("button", { name: "Close navigation" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("navigation", { name: "Main navigation" }),
  ).toHaveClass("is-open");
});
test("empty state has a meaningful starting action", () => {
  render(<EmptyState />);
  expect(
    screen.getByRole("link", { name: /Analyze your first article/ }),
  ).toHaveAttribute("href", "/analyze");
});

test("explains actual feature direction, source context and independent language cues", () => {
  const report: Analysis = {
    ...actual,
    prediction: {
      ...actual.prediction,
      assessment_scope: "article_screening",
      label: "Potentially Misleading",
      features: [
        { term: "shocking", direction: "misleading", contribution: 1.2 },
        { term: "returned article", direction: "credible", contribution: -0.7 },
      ],
    },
    highlights: [
      {
        text: "shocking",
        start: 26,
        end: 34,
        kind: "emotional",
        reason: "Emotional wording alone does not establish falsehood.",
      },
    ],
  };
  const client = new QueryClient();
  client.setQueryData(["analysis", "test"], report);
  render(
    <QueryClientProvider client={client}>
      <Results id="test" />
    </QueryClientProvider>,
  );
  expect(
    screen.getByRole("button", { name: "shocking Toward misleading" }),
  ).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(
    screen.getByRole("button", { name: "returned article Toward credible" }),
  );
  expect(screen.getByText("↓ Pushes toward credible")).toBeVisible();
  expect(screen.getByText("BIGRAM · TWO-WORD FEATURE")).toBeVisible();
  expect(document.querySelector(".explain-excerpt mark")?.textContent).toBe(
    "returned article",
  );
  fireEvent.click(screen.getByRole("button", { name: "Language cues" }));
  expect(
    screen.getByText(/They are not inputs to the current article classifier/),
  ).toBeVisible();
  expect(
    screen.getAllByText(
      "No matches found. This does not establish credibility.",
    ),
  ).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: "How NLP works" }));
  expect(
    screen.getByRole("heading", { name: "Learned decision · Linear SVM" }),
  ).toBeVisible();
  expect(
    screen.getByText(/This saved report has uncalibrated confidence/),
  ).toBeVisible();
});

test("connects share to the actual urgency phrase, not an unrelated occurrence", () => {
  const text =
    "Researchers share data openly. A viral story says share before the story disappears.";
  const cueStart = text.indexOf("share before");
  const report: Analysis = {
    ...actual,
    text,
    prediction: {
      ...actual.prediction,
      assessment_scope: "article_screening",
      features: [
        { term: "share", contribution: 1.1, direction: "misleading" },
        { term: "story", contribution: 0.8, direction: "misleading" },
      ],
    },
    highlights: [
      {
        start: cueStart,
        end: cueStart + 12,
        text: "share before",
        kind: "clickbait",
        reason: "Urgency cue",
      },
    ],
  };
  const client = new QueryClient();
  client.setQueryData(["analysis", "test"], report);
  render(
    <QueryClientProvider client={client}>
      <Results id="test" />
    </QueryClientProvider>,
  );
  expect(
    screen.getByText(/The concern is this appeal to urgency/),
  ).toBeVisible();
  expect(
    screen.getByText(/Rule-based phrase matching · regular expressions/),
  ).toBeVisible();
  expect(
    screen.getByText(/This phrase may be quoted, criticized, or denied/),
  ).toBeVisible();
  const excerpt = document.querySelector(".explain-excerpt")!;
  expect(excerpt.textContent?.split("share").length).toBeGreaterThan(2);
  expect(excerpt.querySelector("mark")?.nextSibling?.textContent).toMatch(
    /^ before/,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "story Toward misleading" }),
  );
  expect(
    screen.getByText(/No specific language problem was detected for/),
  ).toBeVisible();
  expect(
    screen.queryByText(/The concern is this appeal to urgency/),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Linear SVM attribution")).toBeVisible();
});

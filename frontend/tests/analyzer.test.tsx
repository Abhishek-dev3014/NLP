import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, beforeEach, test, expect } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Analyzer } from "@/components/analyzer";
import { api } from "@/lib/api";
import type { Analysis } from "@/lib/types";
const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({
  api: {
    health: vi.fn(),
    analyze: vi.fn(),
    extractUrl: vi.fn(),
    extractFile: vi.fn(),
  },
}));
function setup() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <Analyzer />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.health).mockResolvedValue({
    status: "ok",
    model_loaded: true,
    evidence_configured: false,
  });
});
test("validates short content before making requests", async () => {
  setup();
  fireEvent.click(screen.getByRole("button", { name: "Analyze article" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "at least 12 words",
  );
  expect(api.analyze).not.toHaveBeenCalled();
});
test("switches input tabs and rejects unsupported documents", async () => {
  setup();
  fireEvent.click(screen.getByRole("tab", { name: "Analyze URL" }));
  expect(screen.getByLabelText("Public article URL")).toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: "Upload document" }));
  fireEvent.change(screen.getByLabelText("Upload article document"), {
    target: {
      files: [
        new File(["content"], "test.exe", { type: "application/octet-stream" }),
      ],
    },
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Choose a .txt or .pdf",
  );
  expect(api.extractFile).not.toHaveBeenCalled();
});
test("shows loading and server errors without invented progress", async () => {
  let rejectRequest: (error: Error) => void = () => {};
  vi.mocked(api.analyze).mockImplementation(
    () =>
      new Promise((_resolve, reject) => {
        rejectRequest = reject;
      }),
  );
  setup();
  fireEvent.click(screen.getByRole("button", { name: "Try an example" }));
  fireEvent.click(screen.getByRole("button", { name: "Analyze article" }));
  expect(await screen.findByText("Analyzing your content")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Analyzing article…" }),
  ).toBeDisabled();
  rejectRequest(new Error("Storage is unavailable."));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Storage is unavailable.",
  );
  expect(screen.queryByText("Analyzing your content")).not.toBeInTheDocument();
});
test("navigates to the actual returned report id", async () => {
  vi.mocked(api.analyze).mockResolvedValue({
    id: "actual-report-id",
  } as Analysis);
  setup();
  fireEvent.click(screen.getByRole("button", { name: "Try an example" }));
  expect(screen.getByText(/Demonstration example written/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Analyze article" }));
  await waitFor(() =>
    expect(push).toHaveBeenCalledWith("/results/actual-report-id"),
  );
});

test("URL extraction shows editable content and keeps source attribution", async () => {
  vi.mocked(api.extractUrl).mockResolvedValue({
    headline: "Retrieved article",
    text: "The council has published a new report about local schools and public transportation this week.",
    source_url: "https://public.example/story",
  });
  setup();
  fireEvent.click(screen.getByRole("tab", { name: "Analyze URL" }));
  fireEvent.change(screen.getByLabelText("Public article URL"), {
    target: { value: "https://public.example/story" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Extract" }));
  expect(await screen.findByDisplayValue("Retrieved article")).toBeVisible();
  expect(screen.getByLabelText("Article content")).toHaveValue(
    "The council has published a new report about local schools and public transportation this week.",
  );
});

test("blocked URL gives a usable paste-text fallback", async () => {
  vi.mocked(api.extractUrl).mockRejectedValue(
    new Error("This publisher blocks automated readers."),
  );
  setup();
  fireEvent.click(screen.getByRole("tab", { name: "Analyze URL" }));
  fireEvent.change(screen.getByLabelText("Public article URL"), {
    target: { value: "https://public.example/story" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Extract" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Paste article text instead" }),
  );
  expect(screen.getByLabelText("Article content")).toBeVisible();
});

import type {
  ArticleInput,
  Analysis,
  AnalysisList,
  DashboardStats,
  ModelMetrics,
  NLPAnalysis,
} from "./types";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(`/api${path}`, {
      ...options,
      credentials: "same-origin",
      signal: controller.signal,
      headers: {
        ...(options?.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...options?.headers,
      },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        typeof error.detail === "string"
          ? error.detail
          : "The request could not be completed. Please retry.",
        response.status,
      );
    }
    return response.status === 204 ? (undefined as T) : response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof Error && error.name === "AbortError"
        ? "This request timed out. Check history before submitting again."
        : "The backend could not be reached. Check that the API is running and retry.",
      0,
    );
  } finally {
    clearTimeout(timer);
  }
}
export const api = {
  health: () =>
    request<{
      status: string;
      model_loaded: boolean;
      evidence_configured: boolean;
    }>("/health"),
  explore: (text: string) =>
    request<NLPAnalysis>("/nlp/explore", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  analyze: (input: ArticleInput) =>
    request<Analysis>("/analyze/text", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  extractUrl: (url: string) =>
    request<{ headline: string; text: string; source_url: string }>(
      "/extract/url",
      { method: "POST", body: JSON.stringify({ url }) },
    ),
  extractFile: (file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<{ headline: string; text: string; source_url: null }>(
      "/extract/file",
      { method: "POST", body },
    );
  },
  analysis: (id: string) =>
    request<Analysis>(`/analyses/${encodeURIComponent(id)}`),
  analyses: (params: URLSearchParams) =>
    request<AnalysisList>(`/analyses?${params}`),
  remove: (id: string) =>
    request<void>(`/analyses/${encodeURIComponent(id)}`, { method: "DELETE" }),
  clear: () => request<void>("/analyses", { method: "DELETE" }),
  stats: () => request<DashboardStats>("/dashboard/stats"),
  metrics: () => request<ModelMetrics>("/model/metrics"),
};

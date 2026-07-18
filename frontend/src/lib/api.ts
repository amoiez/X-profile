// Typed API client. Surfaces the backend's consistent error envelope as ApiError.

import type {
  JobSummary,
  PaginatedJobs,
  ProgressResponse,
  ResultsResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  code: string;
  requestId: string | null;
  status: number;

  constructor(code: string, message: string, status: number, requestId: string | null) {
    super(message);
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError("NETWORK_ERROR", "Could not reach the server.", 0, null);
  }

  if (res.status === 204) return undefined as T;

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    const err = (body as { error?: { code: string; message: string; request_id: string | null } })?.error;
    throw new ApiError(
      err?.code || "INTERNAL_ERROR",
      err?.message || `Request failed (${res.status}).`,
      res.status,
      err?.request_id ?? null
    );
  }
  return body as T;
}

export interface CreateAnalysisInput {
  username: string;
  post_limit?: number;
  timezone?: string;
  force_refresh?: boolean;
}

export interface CreateImportedAnalysisInput {
  username: string;
  csv_text: string;
  timezone?: string;
  display_name?: string;
  followers_count?: number;
}

export const api = {
  createAnalysis: (input: CreateAnalysisInput) =>
    request<JobSummary>("/analyses", { method: "POST", body: JSON.stringify(input) }),

  createImportedAnalysis: (input: CreateImportedAnalysisInput) =>
    request<JobSummary>("/analyses/import", { method: "POST", body: JSON.stringify(input) }),

  getJob: (id: string) => request<JobSummary>(`/analyses/${id}`),

  getProgress: (id: string) => request<ProgressResponse>(`/analyses/${id}/progress`),

  getResults: (id: string) => request<ResultsResponse>(`/analyses/${id}/results`),

  listAnalyses: (page = 1, pageSize = 20) =>
    request<PaginatedJobs>(`/analyses?page=${page}&page_size=${pageSize}`),

  deleteAnalysis: (id: string) =>
    request<void>(`/analyses/${id}`, { method: "DELETE" }),

  refreshAnalysis: (id: string) =>
    request<JobSummary>(`/analyses/${id}/refresh`, { method: "POST" }),
};

// Browser timezone helper for submitting analyses.
export function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

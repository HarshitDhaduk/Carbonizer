/**
 * Browser-side, authenticated API client.
 *
 * Distinct from `src/lib/api.ts`, which is the unauthenticated SSR client used by
 * server components for the public dashboard. This one runs in the browser, injects
 * the JWT bearer token, and backs auth + the onboarding flow.
 */

import type {
  Attribution,
  AuthUser,
  Benchmark,
  ConnectProvider,
  ConnectResult,
  DataConnection,
  FootprintSummary,
  Nudge,
  OnboardingAnswers,
  OnboardingProfile,
  Questionnaire,
} from "./types";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

/** Typed error carrying the HTTP status and the API's problem detail. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT";
  token?: string | null;
  /** JSON body (mutually exclusive with `form`). */
  json?: unknown;
  /** form-urlencoded body (OAuth2 password grant). */
  form?: Record<string, string>;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(opts.form).toString();
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: body ?? null,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new ApiError(res.status, await extractError(res));
  }
  // 204 / empty bodies
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function extractError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown; title?: unknown };
    const detail = data.detail ?? data.title;
    if (typeof detail === "string") return detail;
  } catch {
    /* fall through */
  }
  return `Request failed (${res.status})`;
}

interface TokenResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}

export const clientApi = {
  registerUser: (email: string, password: string, region = "GB") =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      json: { email, password, region },
    }),

  loginUser: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      form: { username: email, password },
    }),

  getMe: (token: string) => request<AuthUser>("/auth/me", { token }),

  getOnboardingQuestions: (token?: string | null) =>
    request<Questionnaire>("/onboarding/questions", { token: token ?? null }),

  getOnboardingProfile: (token: string) =>
    request<OnboardingProfile>("/onboarding/profile", { token }),

  // autosave partial onboarding so a mid-flow close can resume
  saveOnboardingProgress: (
    token: string,
    answers: OnboardingAnswers,
    currentStep: number,
  ) =>
    request<OnboardingProfile>("/onboarding/progress", {
      method: "PUT",
      token,
      json: { answers, currentStep },
    }),

  submitEstimate: (token: string, answers: OnboardingAnswers) =>
    request<FootprintSummary>("/onboarding/estimate", {
      method: "POST",
      token,
      json: { answers },
    }),

  getFootprintSummary: (token: string, range = "12w") =>
    request<FootprintSummary>(`/footprint/summary?range=${range}`, { token }),

  getAttribution: (token: string) =>
    request<Attribution>("/footprint/attribution", { token }),

  getRecommendations: (token: string) =>
    request<Nudge[]>("/recommendations", { token }),

  getBenchmark: (token: string) =>
    request<Benchmark>("/community/benchmark", { token }),

  getConnections: (token: string) =>
    request<DataConnection[]>("/connections", { token }),

  // sandbox connect (bank | meter): imports records + returns the upgraded footprint
  linkSource: (token: string, provider: ConnectProvider) =>
    request<ConnectResult>(`/connections/${provider}/link`, {
      method: "POST",
      token,
    }),
};

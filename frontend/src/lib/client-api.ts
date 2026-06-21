/**
 * Browser-side, authenticated API client.
 *
 * Distinct from `src/lib/api.ts`, which is the unauthenticated SSR client used by
 * server components for the public dashboard. This one runs in the browser, uses
 * HttpOnly cookies for auth (set by /auth/login), and backs auth + onboarding.
 *
 * Why no token plumbing — Phase 2.1 of docs/IMPROVEMENT-PLAN.md moved JWTs into
 * `HttpOnly` cookies. The browser attaches the access cookie automatically; this
 * module just needs `credentials: "include"` and a CSRF header echo for state-
 * changing methods.
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

/** Resolve the API base URL.
 *
 * In the browser we ALWAYS prefer the same-origin path `/api/v1`. The deploy
 * proxies this through to the backend via a host-side rewrite (Vercel:
 * frontend/vercel.json; any reverse proxy works the same way). Same-origin
 * means cookies are first-party — third-party-cookie blockers (Safari ITP,
 * Brave, Firefox-strict) never block them.
 *
 * SSR (server components / Node-side) doesn't have a "current origin" to
 * relative-resolve against, so we honor `NEXT_PUBLIC_API_BASE_URL` there,
 * falling back to localhost for local dev.
 */
function resolveApiBase(): string {
  if (typeof window !== "undefined") return "/api/v1";
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  return (env ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
}

const API_BASE = resolveApiBase();

const CSRF_COOKIE = "cb_csrf";

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
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  /** JSON body (mutually exclusive with `form`). */
  json?: unknown;
  /** form-urlencoded body (OAuth2 password grant). */
  form?: Record<string, string>;
}

const STATE_CHANGING = new Set(["POST", "PUT", "DELETE", "PATCH"]);

/** Read a non-HttpOnly cookie by name. Returns null in SSR. */
function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${escaped}=([^;]*)`),
  );
  const value = match?.[1];
  return value !== undefined ? decodeURIComponent(value) : null;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  // CSRF double-submit: echo the cb_csrf cookie as a header on any state-
  // changing request. The backend rejects mismatches with 403.
  if (STATE_CHANGING.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(opts.form).toString();
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ?? null,
    credentials: "include",
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
  // Auth ---------------------------------------------------------------------
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

  /** Issue a CSRF cookie if missing. Called once at app boot. */
  ensureCsrf: () => request<void>("/auth/csrf"),

  logout: () => request<void>("/auth/logout", { method: "POST" }),

  refresh: () => request<TokenResponse>("/auth/refresh", { method: "POST" }),

  getMe: () => request<AuthUser>("/auth/me"),

  // Onboarding ---------------------------------------------------------------
  getOnboardingQuestions: () => request<Questionnaire>("/onboarding/questions"),

  getOnboardingProfile: () => request<OnboardingProfile>("/onboarding/profile"),

  saveOnboardingProgress: (answers: OnboardingAnswers, currentStep: number) =>
    request<OnboardingProfile>("/onboarding/progress", {
      method: "PUT",
      json: { answers, currentStep },
    }),

  submitEstimate: (answers: OnboardingAnswers) =>
    request<FootprintSummary>("/onboarding/estimate", {
      method: "POST",
      json: { answers },
    }),

  // Footprint + insights ----------------------------------------------------
  getFootprintSummary: (range = "12w") =>
    request<FootprintSummary>(`/footprint/summary?range=${range}`),

  getAttribution: () => request<Attribution>("/footprint/attribution"),

  getRecommendations: () => request<Nudge[]>("/recommendations"),

  getBenchmark: () => request<Benchmark>("/community/benchmark"),

  // Connections -------------------------------------------------------------
  getConnections: () => request<DataConnection[]>("/connections"),

  linkSource: (provider: ConnectProvider) =>
    request<ConnectResult>(`/connections/${provider}/link`, { method: "POST" }),
};

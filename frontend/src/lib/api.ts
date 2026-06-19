import type {
  Benchmark,
  DataConnection,
  FootprintSummary,
  Nudge,
} from "./types";
import {
  MOCK_BENCHMARK,
  MOCK_CONNECTIONS,
  MOCK_NUDGES,
  MOCK_SUMMARY,
} from "./mock-data";

/**
 * Client for the Python FastAPI backend (docs/API-DESIGN.md).
 *
 * - Set `NEXT_PUBLIC_API_BASE_URL` (e.g. http://localhost:8000/api/v1) to hit the
 *   live API. When unset, every call resolves to the local fixtures so the UI runs
 *   standalone.
 * - When the base URL *is* set but a request fails (backend down, timeout, bad
 *   payload), we fall back to the fixtures and warn — the dashboard should degrade,
 *   not crash. Set `NEXT_PUBLIC_API_STRICT=true` to surface errors instead.
 *
 * The backend serializes camelCase to match the types in ./types, so responses map
 * 1:1 — no transform layer needed.
 */

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
const USE_MOCKS = API_BASE === "";
const STRICT = process.env.NEXT_PUBLIC_API_STRICT === "true";
const TIMEOUT_MS = 8000;

export const apiMode: "live" | "mock" = USE_MOCKS ? "mock" : "live";

async function get<T>(path: string, fallback: T): Promise<T> {
  if (USE_MOCKS) return fallback;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
      // dashboard data is user-specific and time-sensitive
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (STRICT) throw err;
    // resilient dev fallback — keep the UI alive when the API is unavailable
    console.warn(
      `[carbonizer] API ${path} unavailable, using fallback data:`,
      err instanceof Error ? err.message : err,
    );
    return fallback;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  getFootprintSummary: (range = "12w") =>
    get<FootprintSummary>(`/footprint/summary?range=${range}`, MOCK_SUMMARY),

  getRecommendations: () => get<Nudge[]>(`/recommendations`, MOCK_NUDGES),

  getBenchmark: () => get<Benchmark>(`/community/benchmark`, MOCK_BENCHMARK),

  getConnections: () =>
    get<DataConnection[]>(`/connections`, MOCK_CONNECTIONS),
};

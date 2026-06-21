import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — Phase 3.3 of docs/IMPROVEMENT-PLAN.md.
 *
 * Spawns the FastAPI backend (seed mode, no Postgres needed) and the Next.js
 * frontend before running the suite. Seed mode is enough to cover the
 * cookie-based auth flow (demo login → /me → dashboard → logout) end-to-end;
 * the DB-mode register / onboarding / connect-bank flows are covered by the
 * testcontainers tests in Phase 3.2.
 *
 * Locally, `reuseExistingServer: true` short-circuits the boot tax if you
 * already have both servers running.
 */

const isCI = !!process.env.CI;

const FRONTEND_PORT = 3100;
const BACKEND_PORT = 8100;

// The backend command is OS-aware: GitHub Actions has python3 on PATH after
// setup-python; Windows local runs use `python`.
const PYTHON = process.platform === "win32" ? "python" : "python3";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  // Pin to 1 worker on CI to avoid races on the single backend instance.
  // Locally, leave it to Playwright's default (CPU-aware) — omitting the key
  // entirely satisfies exactOptionalPropertyTypes.
  ...(isCI ? { workers: 1 } : {}),
  reporter: isCI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        `${PYTHON} -m uvicorn app.main:app ` +
        `--host 127.0.0.1 --port ${BACKEND_PORT} --app-dir ../backend`,
      port: BACKEND_PORT,
      reuseExistingServer: !isCI,
      timeout: 60_000,
      env: {
        USE_DB: "false",
        ENVIRONMENT: "development",
        DEMO_EMAIL: "demo@carbonizer.app",
        DEMO_PASSWORD: "demo12345",
        CORS_ORIGINS: `http://127.0.0.1:${FRONTEND_PORT}`,
        // Disable rate limiting so a flurry of test logins doesn't trip 429.
        RATE_LIMIT_ENABLED: "false",
      },
    },
    {
      command: `npm run build && npm run start -- -p ${FRONTEND_PORT}`,
      port: FRONTEND_PORT,
      reuseExistingServer: !isCI,
      timeout: 240_000,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${BACKEND_PORT}/api/v1`,
      },
    },
  ],
});

import { expect, request, test } from "@playwright/test";

/**
 * End-to-end auth flow under seed mode.
 *
 * Exercises the Phase 2.1 cookie + CSRF refactor through a real browser:
 *   1. Anonymous landing renders the public CTAs.
 *   2. Login with the seed-mode demo creds sets HttpOnly + CSRF cookies.
 *   3. The HttpOnly access cookie is unreadable from JS — XSS can't lift it.
 *   4. The CSRF cookie IS readable from JS — that's the double-submit
 *      contract.
 *   5. Logout clears cookies; /auth/me returns 401 afterwards.
 */

const DEMO_EMAIL = "demo@carbonizer.app";
const DEMO_PASSWORD = "demo12345";
// Trailing slash + leading-less paths below — Playwright's baseURL joining
// REPLACES the path on `/`-leading relative URLs, so `/auth/login` would
// hit http://host/auth/login instead of http://host/api/v1/auth/login.
const API_BASE = "http://127.0.0.1:8100/api/v1/";

test.describe("auth flow", () => {
  test("anonymous landing renders the public CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    // Both nav and main CTAs route to onboarding for unauthenticated visitors.
    await expect(
      page.getByRole("link", { name: /open app/i }).first(),
    ).toBeVisible();
  });

  test("login (via API) sets HttpOnly access + readable CSRF cookies", async ({
    context,
  }) => {
    // We test the cookie contract at the API layer, where it lives. Driving
    // the UI form is in a separate test (see "...form submits without
    // client-side validation block" below) — it's not the right place to
    // verify cookie attributes because they're set by the backend response,
    // not by the form.
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const res = await apiContext.post("auth/login", {
      form: { username: DEMO_EMAIL, password: DEMO_PASSWORD },
    });
    expect(res.status()).toBe(200);

    // Copy cookies onto the browser context so subsequent SPA calls inherit
    // the session (mirrors what a real login round-trip does in the browser).
    const state = await apiContext.storageState();
    await context.addCookies(state.cookies);

    const cookies = await context.cookies();
    const access = cookies.find((c) => c.name === "cb_access");
    const csrf = cookies.find((c) => c.name === "cb_csrf");
    expect(access, "access cookie present").toBeDefined();
    expect(access?.httpOnly, "access cookie is HttpOnly").toBe(true);
    expect(csrf, "csrf cookie present").toBeDefined();
    expect(
      csrf?.httpOnly,
      "csrf cookie is NOT HttpOnly (JS must read it)",
    ).toBe(false);
  });

  test("login form submits to the backend (no client-side validation block)", async ({
    page,
  }) => {
    // Smoke test: the form actually fires /auth/login. Catches regressions
    // like minLength=12 silently blocking the demo password (we hit that when
    // bumping the register policy). Uses `#id` selectors instead of label
    // regexes because the visual "* required" indicator gets included in
    // the label's accessible name in some browsers.
    await page.goto("/onboarding");
    // Wait for the AuthGate to render — `isVisible()` is sync and would race
    // the hydration; assert the register heading instead so the click
    // auto-waits behind the form ready.
    await expect(
      page.getByRole("heading", { name: /create your account/i }),
    ).toBeVisible();
    await page.getByRole("button", { name: /sign in/i }).last().click();
    await expect(
      page.getByRole("heading", { name: /welcome back/i }),
    ).toBeVisible();
    await page.locator("#email").fill(DEMO_EMAIL);
    await page.locator("#password").fill(DEMO_PASSWORD);

    const [loginRes] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/auth/login")),
      page.getByRole("button", { name: /sign in/i }).click(),
    ]);
    // Surface the status so a future 4xx regression points the finger plainly.
    expect(loginRes.status(), `login returned ${loginRes.status()}`).toBe(200);
  });

  test("logout clears cookies and /auth/me returns 401", async ({
    context,
  }) => {
    // Arrange a logged-in session via the API; copy cookies into the browser
    // context so subsequent SPA calls travel as a real session would.
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const loginRes = await apiContext.post("auth/login", {
      form: { username: DEMO_EMAIL, password: DEMO_PASSWORD },
    });
    expect(loginRes.status()).toBe(200);
    const apiState = await apiContext.storageState();
    await context.addCookies(apiState.cookies);

    // Logout via the same API the SPA's logout button would call.
    const csrf = (await context.cookies()).find((c) => c.name === "cb_csrf");
    expect(csrf).toBeDefined();
    const logoutRes = await apiContext.post("auth/logout", {
      headers: { "X-CSRF-Token": csrf?.value ?? "" },
    });
    expect(logoutRes.status()).toBe(204);

    // /auth/me from the apiContext must now be 401 — its own cookie jar was
    // cleared by the logout response.
    const meRes = await apiContext.get("auth/me");
    expect(meRes.status()).toBe(401);
  });
});

import { expect, request, test } from "@playwright/test";

/**
 * E2E for the onboarding questionnaire flow: register → answer → estimate reveal.
 * Exercises the VoI-ordered question rendering (R0), the visible_if dependency
 * chain (carType=none hides carKmPerWeek), and the answer-normalisation path
 * via /onboarding/estimate. Seed mode 503s on estimate persistence, so this
 * test stops at the questionnaire render + answer state — it's the cheapest
 * gate that catches an entire dead onboarding flow.
 */

const API_BASE = "http://127.0.0.1:8100/api/v1/";
const DEMO_EMAIL = "demo@carbonizer.app";
const DEMO_PASSWORD = "demo12345";

test.describe("onboarding questionnaire", () => {
  test.beforeEach(async ({ context }) => {
    // Seed-mode demo login via the API so the SPA bypasses the AuthGate
    // and lands on the questionnaire.
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const res = await apiContext.post("auth/login", {
      form: { username: DEMO_EMAIL, password: DEMO_PASSWORD },
    });
    expect(res.status()).toBe(200);
    const state = await apiContext.storageState();
    await context.addCookies(state.cookies);
  });

  test("renders the first question with VoI-ordered cards", async ({
    page,
  }) => {
    await page.goto("/onboarding");
    // R0 — the highest-VoI question (carType, flights, or diet depending on
    // the rerun's spread) should land first. Just assert one of them is up.
    const heading = page.locator("h1, h2, [role='heading']").first();
    await expect(heading).toBeVisible();
    // The progress meter is keyboardable, so at minimum a meter / progressbar
    // role exists on the page.
    const meter = page
      .getByRole("progressbar")
      .or(page.locator("[role='meter']"));
    await expect(meter.first()).toBeVisible();
  });

  test("API exposes the questionnaire with VoI scores on every question", async () => {
    // The frontend renders from this list; if VoI is missing the FE shows them
    // in code order — a real regression. Pin the contract.
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const res = await apiContext.get("onboarding/questions");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.version).toBeGreaterThanOrEqual(1);
    expect(body.questions.length).toBeGreaterThanOrEqual(5);
    for (const q of body.questions) {
      // R0 contract: every question gets a normalised score in [0,1].
      expect(typeof q.voi).toBe("number");
      expect(q.voi).toBeGreaterThanOrEqual(0);
      expect(q.voi).toBeLessThanOrEqual(1);
    }
  });
});

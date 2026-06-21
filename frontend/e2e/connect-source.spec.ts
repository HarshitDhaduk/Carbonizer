import { expect, request, test } from "@playwright/test";

/**
 * Connect-source flow at the API layer: the SPA's "Connect bank" button hits
 * /connections/bank/link, which in seed mode 503s but in DB mode runs the full
 * ingestion → carbon → recompute → snapshot pipeline. The cheapest gate that
 * catches a broken sandbox-provider wiring is to assert seed-mode returns the
 * documented 503 with the expected detail copy — change-detector if someone
 * accidentally flips USE_DB or strips the guard.
 */

const API_BASE = "http://127.0.0.1:8100/api/v1/";
const DEMO_EMAIL = "demo@carbonizer.app";
const DEMO_PASSWORD = "demo12345";

test.describe("connect-source", () => {
  test("seed-mode bank link is 503, surfaces the documented detail", async () => {
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const login = await apiContext.post("auth/login", {
      form: { username: DEMO_EMAIL, password: DEMO_PASSWORD },
    });
    expect(login.status()).toBe(200);

    // Bearer-auth path so CSRF middleware is exempt — same path the OpenAPI
    // doc + machine clients use.
    const token = (await login.json()).accessToken;
    const res = await apiContext.post("connections/bank/link", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(503);
    const body = await res.json();
    expect(body.detail).toMatch(/database|use_db/i);
  });

  test("connections listing surfaces the three sandbox providers", async () => {
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const res = await apiContext.get("connections");
    expect(res.status()).toBe(200);
    const ids = (await res.json()).map((c: { id: string }) => c.id);
    expect(ids).toEqual(
      expect.arrayContaining(["bank", "telematics", "meter"]),
    );
  });
});

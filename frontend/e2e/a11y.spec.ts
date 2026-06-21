import AxeBuilder from "@axe-core/playwright";
import { expect, request, test } from "@playwright/test";

/**
 * Accessibility smoke — Phase 3.3 seeded; Phase 5.5 extended to cover an
 * authed surface (the dashboard) and to fail explicitly on color-contrast
 * regressions, the violation we caught + fixed in Phase 3.3.
 *
 * Gate: no `serious` / `critical` axe-core violations on any covered route.
 * Moderate / minor noise is tracked in docs/A11Y-REPORT.md, not blocked here.
 */

const DEMO_EMAIL = "demo@carbonizer.app";
const DEMO_PASSWORD = "demo12345";
const API_BASE = "http://127.0.0.1:8100/api/v1/";

type ImpactCount = Record<string, number>;

function blocking(
  violations: Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"],
) {
  return violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
}

function summary(
  violations: Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"],
): string {
  if (violations.length === 0) return "no blocking violations";
  const byRule: ImpactCount = {};
  for (const v of violations)
    byRule[v.id] = (byRule[v.id] ?? 0) + v.nodes.length;
  return violations
    .map((v) => `${v.id} (${v.impact}): ${v.help} — ${byRule[v.id]} node(s)`)
    .join("\n");
}

test.describe("accessibility (axe-core, WCAG 2 AA)", () => {
  test("landing page has no serious/critical violations", async ({ page }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const blockingViolations = blocking(results.violations);
    expect(blockingViolations, summary(blockingViolations)).toEqual([]);
  });

  test("auth gate has no serious/critical violations", async ({ page }) => {
    await page.goto("/onboarding");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const blockingViolations = blocking(results.violations);
    expect(blockingViolations, summary(blockingViolations)).toEqual([]);
  });

  test("dashboard (authed) has no serious/critical violations", async ({
    page,
    context,
  }) => {
    // Seed-mode demo login through the API so we can copy the cookies onto the
    // browser context — the SPA then renders the dashboard end-to-end.
    const apiContext = await request.newContext({ baseURL: API_BASE });
    const loginRes = await apiContext.post("auth/login", {
      form: { username: DEMO_EMAIL, password: DEMO_PASSWORD },
    });
    expect(loginRes.status()).toBe(200);
    const state = await apiContext.storageState();
    await context.addCookies(state.cookies);

    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const blockingViolations = blocking(results.violations);
    expect(blockingViolations, summary(blockingViolations)).toEqual([]);
  });

  test("color-contrast regression watchdog", async ({ page }) => {
    // Phase 3.3 caught `--text-lo` failing WCAG AA on the auth gate. This test
    // pins that contract specifically so a future token change can't reintroduce
    // it without a test failure pointing the finger at the rule.
    await page.goto("/onboarding");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withRules(["color-contrast"])
      .analyze();
    expect(results.violations, summary(results.violations)).toEqual([]);
  });
});

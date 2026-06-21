import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Accessibility smoke — Phase 3.3 of docs/IMPROVEMENT-PLAN.md (also seeds
 * the Phase 5 a11y baseline).
 *
 * Runs axe-core against the public surfaces that don't require auth. The gate
 * is `serious` + `critical` only — moderate / minor noise belongs in a focused
 * follow-up PR so this suite stays a high-signal blocker.
 */

test.describe("accessibility (axe-core, WCAG 2 AA)", () => {
  test("landing page has no serious/critical violations", async ({ page }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(
      blocking,
      blocking.map((v) => `${v.id} (${v.impact}): ${v.help}`).join("\n") ||
        "no blocking violations",
    ).toEqual([]);
  });

  test("auth gate has no serious/critical violations", async ({ page }) => {
    await page.goto("/onboarding");
    // Wait for the AuthGate to render (the auth-store probes /auth/me first).
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(
      blocking,
      blocking.map((v) => `${v.id} (${v.impact}): ${v.help}`).join("\n") ||
        "no blocking violations",
    ).toEqual([]);
  });
});

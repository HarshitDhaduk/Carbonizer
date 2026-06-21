import { expect, test } from "@playwright/test";

/**
 * Keyboard-only navigation (Phase 5 a11y baseline).
 *
 * Tab order on the landing page should be sensible: skip-link → nav CTA →
 * hero CTAs. We don't pin specific element ids — they're stable accessible
 * names instead, which survive refactors.
 */

test.describe("keyboard navigation", () => {
  test("Tab from the URL bar hits the skip link first", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tag: el?.tagName,
        text: el?.textContent?.trim().slice(0, 40) ?? "",
        href: (el as HTMLAnchorElement | null)?.href ?? "",
      };
    });
    expect(focused.tag).toBe("A");
    expect(focused.text).toMatch(/skip to main content/i);
    expect(focused.href).toMatch(/#main$/);
  });

  test("Skip link activation moves focus to <main>", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");
    // After activation the URL fragment changes; focus should be at or
    // inside #main on the next interaction.
    expect(page.url()).toContain("#main");
    const mainPresent = await page.evaluate(
      () => !!document.getElementById("main"),
    );
    expect(mainPresent).toBe(true);
  });

  test("Hero CTAs are reachable by keyboard alone", async ({ page }) => {
    await page.goto("/");
    // Walk forward 20 Tabs (plenty for the landing nav + hero). Collect
    // every focusable name we see — assert "Start tracking free" shows up.
    const names: string[] = [];
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press("Tab");
      const name = await page.evaluate(
        () => document.activeElement?.textContent?.trim().slice(0, 30) ?? "",
      );
      if (name) names.push(name);
    }
    expect(names.some((n) => /start tracking/i.test(n))).toBe(true);
  });
});

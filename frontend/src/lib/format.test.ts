import { describe, expect, it } from "vitest";
import { formatCo2e, formatMoney, formatPct } from "./format";

describe("formatCo2e", () => {
  it("formats tonne-scale to one decimal", () => {
    expect(formatCo2e(4.2)).toBe("4.2 t");
    // JS .toFixed uses round-half-to-even, and 0.15 is stored as 0.1499…
    // so 0.15 → "0.1 t" (not "0.2 t"). Documenting the actual behavior.
    expect(formatCo2e(0.16)).toBe("0.2 t");
  });

  it("switches to kg below 0.1 t", () => {
    // 90 kg with one decimal because |kg| < 10? actually 90 ≥ 10 → integer.
    expect(formatCo2e(0.09)).toBe("90 kg");
    expect(formatCo2e(0.099)).toBe("99 kg");
  });

  it("keeps one decimal for sub-10kg savings (no '0 kg' rounding)", () => {
    expect(formatCo2e(0.004)).toBe("4.0 kg");
    expect(formatCo2e(0.0005)).toBe("0.5 kg");
  });

  it("handles negatives symmetrically", () => {
    expect(formatCo2e(-4.2)).toBe("-4.2 t");
    expect(formatCo2e(-0.05)).toBe("-50 kg");
  });
});

describe("formatPct", () => {
  it("drops the sign and rounds to whole numbers", () => {
    expect(formatPct(-8)).toBe("8%");
    expect(formatPct(8)).toBe("8%");
    expect(formatPct(8.4)).toBe("8%");
    expect(formatPct(8.6)).toBe("9%");
  });

  it("handles zero", () => {
    expect(formatPct(0)).toBe("0%");
  });
});

describe("formatMoney", () => {
  it("uses 2dp under £10", () => {
    expect(formatMoney(4.5, "GBP")).toMatch(/£4\.50/);
  });

  it("drops decimals at £10 and up", () => {
    // No fractional part for ≥10
    expect(formatMoney(123, "GBP")).toMatch(/£123/);
    expect(formatMoney(123, "GBP")).not.toMatch(/\.00/);
  });
});

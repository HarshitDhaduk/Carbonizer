import { describe, expect, it } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  it("joins simple class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("drops falsy values", () => {
    expect(cn("foo", null, undefined, false, "", "bar")).toBe("foo bar");
  });

  it("applies clsx conditional shapes", () => {
    expect(cn("base", { active: true, disabled: false })).toBe("base active");
  });

  it("dedupes conflicting tailwind utilities (twMerge)", () => {
    // Whole point of twMerge over plain clsx — keep the later one.
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("handles arrays of inputs", () => {
    expect(cn(["foo", ["bar", { baz: true }]])).toBe("foo bar baz");
  });
});

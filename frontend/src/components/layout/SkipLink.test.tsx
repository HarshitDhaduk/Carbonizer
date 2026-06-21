import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SkipLink } from "./SkipLink";

describe("SkipLink", () => {
  it("renders an anchor targeting #main", () => {
    render(<SkipLink />);
    const link = screen.getByRole("link", { name: /skip to main content/i });
    expect(link).toHaveAttribute("href", "#main");
  });

  it("uses sr-only so it stays hidden until focused", () => {
    render(<SkipLink />);
    const link = screen.getByRole("link", { name: /skip to main content/i });
    // sr-only must be present; focus styles lift it on Tab. We assert the
    // mechanism (the class) rather than visual state, since jsdom doesn't
    // run :focus.
    expect(link.className).toMatch(/\bsr-only\b/);
  });
});

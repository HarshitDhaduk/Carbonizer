import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MethodBadge } from "./MethodBadge";

describe("MethodBadge", () => {
  it("labels activity / spend / estimated distinctly", () => {
    const { rerender } = render(<MethodBadge method="activity" />);
    expect(screen.getByText("Activity-based")).toBeInTheDocument();

    rerender(<MethodBadge method="spend" />);
    expect(screen.getByText("Spend-based")).toBeInTheDocument();

    rerender(<MethodBadge method="estimated" />);
    expect(screen.getByText("Estimated")).toBeInTheDocument();
  });

  it("shows 'Inferred' when imputed overrides the method", () => {
    // Per docs/IMPROVEMENT-PLAN R1: imputed (bank-as-hub) wins over the raw
    // method, because it tells the user *how* they got the figure.
    render(<MethodBadge method="estimated" imputed />);
    expect(screen.getByText("Inferred")).toBeInTheDocument();
    expect(screen.queryByText("Estimated")).not.toBeInTheDocument();
  });

  it("explains imputation in a tooltip", () => {
    render(<MethodBadge method="estimated" imputed />);
    const badge = screen.getByText("Inferred").closest("span");
    expect(badge).toHaveAttribute(
      "title",
      expect.stringContaining("bank") as unknown as string,
    );
  });
});

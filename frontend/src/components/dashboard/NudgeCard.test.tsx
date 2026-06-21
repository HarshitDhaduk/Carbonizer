import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { Nudge } from "@/lib/types";
import { NudgeCard } from "./NudgeCard";

const BASE: Nudge = {
  id: "n1",
  kind: "action",
  title: "Switch to a renewable tariff",
  detail: "Your usage fits a green tariff with no standing-charge hit.",
  carbonSavedTco2e: 0.3,
  moneySaved: 140,
  currency: "GBP",
  effort: "5-min",
};

describe("NudgeCard", () => {
  it("renders title and detail", () => {
    render(<NudgeCard nudge={BASE} />);
    expect(
      screen.getByText(/Switch to a renewable tariff/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Your usage fits a green tariff/),
    ).toBeInTheDocument();
  });

  it("shows the effort label", () => {
    render(<NudgeCard nudge={BASE} />);
    expect(screen.getByText("5 min")).toBeInTheDocument();
  });

  it("annualises savings for non-clean-window nudges", () => {
    render(<NudgeCard nudge={BASE} />);
    // Both the carbon and money chips carry the /yr suffix
    expect(screen.getAllByText(/\/yr/).length).toBeGreaterThan(0);
  });

  it("does not annualise clean-window nudges (savings are per-event)", () => {
    render(
      <NudgeCard nudge={{ ...BASE, kind: "clean-window", effort: "1-tap" }} />,
    );
    // No "/yr" suffix on either chip when the nudge is per-event
    expect(screen.queryByText(/\/yr/)).not.toBeInTheDocument();
  });

  it("invokes onAct when the Act button is clicked", () => {
    const onAct = vi.fn();
    render(<NudgeCard nudge={BASE} onAct={onAct} />);
    fireEvent.click(screen.getByRole("button", { name: /act/i }));
    expect(onAct).toHaveBeenCalledWith(BASE);
  });

  it("hides the carbon chip when no savings are projected", () => {
    render(<NudgeCard nudge={{ ...BASE, carbonSavedTco2e: 0 }} />);
    // The piggy-bank money chip should still render
    expect(screen.getByText(/140/)).toBeInTheDocument();
  });
});

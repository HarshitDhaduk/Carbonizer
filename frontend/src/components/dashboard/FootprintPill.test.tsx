import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { FootprintSummary } from "@/lib/types";
import { FootprintPill } from "./FootprintPill";

const BASE: FootprintSummary = {
  totalTco2e: 4.2,
  deltaPct: -8,
  trend: "down",
  status: "improving",
  targetTco2e: 3.5,
  health: 0.62,
  categories: [],
};

describe("FootprintPill", () => {
  it("shows the annualised total with CO₂e suffix", () => {
    render(<FootprintPill summary={BASE} />);
    expect(screen.getByText(/CO₂e/)).toBeInTheDocument();
    expect(screen.getByText(/Footprint · annualized/)).toBeInTheDocument();
  });

  it("renders the improving-status label", () => {
    render(<FootprintPill summary={BASE} />);
    expect(screen.getByText("Improving")).toBeInTheDocument();
  });

  it("flips to a warning label for a regressing footprint", () => {
    render(<FootprintPill summary={{ ...BASE, status: "regressing" }} />);
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
  });

  it("labels a seed footprint as Getting started", () => {
    render(<FootprintPill summary={{ ...BASE, status: "seed" }} />);
    expect(screen.getByText("Getting started")).toBeInTheDocument();
  });
});

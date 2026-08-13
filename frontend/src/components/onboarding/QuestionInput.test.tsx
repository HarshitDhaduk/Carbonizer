import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Question } from "@/lib/types";
import { QuestionInput } from "./QuestionInput";

/**
 * Keyboard + naming contract for the onboarding controls (audit/2026-08, M8/M9).
 *
 * These are custom `role="radio"` buttons rather than native inputs, so the
 * radio-group keyboard behaviour assistive tech is promised has to be
 * implemented rather than inherited.
 */

const DIET: Question = {
  id: "diet",
  type: "single",
  label: "Your diet",
  default: "average",
  options: [
    { value: "meat_heavy", label: "Meat with most meals" },
    { value: "average", label: "Average" },
    { value: "low_meat", label: "Low meat" },
  ],
};

const CAR_KM: Question = {
  id: "carKmPerWeek",
  type: "number",
  label: "How far do you drive a week?",
  default: 100,
  min: 0,
  max: 2000,
  step: 10,
  unit: "km",
};

describe("QuestionInput — single choice", () => {
  it("exposes exactly one tab stop for the whole group", () => {
    render(
      <QuestionInput question={DIET} value="average" onChange={() => {}} />,
    );
    const radios = screen.getAllByRole("radio");
    const tabbable = radios.filter((r) => r.getAttribute("tabindex") === "0");
    expect(radios).toHaveLength(3);
    expect(tabbable).toHaveLength(1);
    // The tab stop sits on the selected option.
    expect(tabbable[0]).toHaveAccessibleName("Average");
  });

  it("puts the tab stop on the first option when nothing is selected yet", () => {
    render(<QuestionInput question={DIET} value="" onChange={() => {}} />);
    const tabbable = screen
      .getAllByRole("radio")
      .filter((r) => r.getAttribute("tabindex") === "0");
    expect(tabbable).toHaveLength(1);
    expect(tabbable[0]).toHaveAccessibleName("Meat with most meals");
  });

  it("ArrowDown moves selection to the next option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <QuestionInput question={DIET} value="average" onChange={onChange} />,
    );
    screen.getByRole("radio", { name: "Average" }).focus();
    await user.keyboard("{ArrowDown}");
    expect(onChange).toHaveBeenCalledWith("low_meat");
  });

  it("ArrowUp moves selection to the previous option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <QuestionInput question={DIET} value="average" onChange={onChange} />,
    );
    screen.getByRole("radio", { name: "Average" }).focus();
    await user.keyboard("{ArrowUp}");
    expect(onChange).toHaveBeenCalledWith("meat_heavy");
  });

  it("wraps at the ends and supports Home/End", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <QuestionInput question={DIET} value="meat_heavy" onChange={onChange} />,
    );
    const first = screen.getByRole("radio", { name: "Meat with most meals" });

    first.focus();
    await user.keyboard("{ArrowUp}");
    expect(onChange).toHaveBeenLastCalledWith("low_meat");

    first.focus();
    await user.keyboard("{End}");
    expect(onChange).toHaveBeenLastCalledWith("low_meat");

    first.focus();
    await user.keyboard("{Home}");
    expect(onChange).toHaveBeenLastCalledWith("meat_heavy");
  });

  it("marks only the selected option aria-checked", () => {
    render(
      <QuestionInput question={DIET} value="low_meat" onChange={() => {}} />,
    );
    expect(screen.getByRole("radio", { name: "Low meat" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Average" })).not.toBeChecked();
  });
});

describe("QuestionInput — number", () => {
  it("names the slider after the question, not the unit", () => {
    render(<QuestionInput question={CAR_KM} value={120} onChange={() => {}} />);
    // Previously "Value in km" — meaningless to a screen-reader user who only
    // hears the control's own name.
    expect(
      screen.getByRole("slider", { name: "How far do you drive a week?" }),
    ).toHaveValue("120");
  });

  it("keeps the unit in aria-valuetext", () => {
    render(<QuestionInput question={CAR_KM} value={120} onChange={() => {}} />);
    expect(screen.getByRole("slider")).toHaveAttribute(
      "aria-valuetext",
      "120 km",
    );
  });
});

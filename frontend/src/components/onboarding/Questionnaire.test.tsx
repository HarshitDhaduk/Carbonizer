import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Question } from "@/lib/types";
import { Questionnaire } from "./Questionnaire";

const QUESTIONS: Question[] = [
  {
    id: "diet",
    type: "single",
    label: "How would you describe your diet?",
    voi: 0.7,
    default: "average",
    options: [
      { value: "average", label: "Average" },
      { value: "vegan", label: "Vegan" },
    ],
  },
  {
    id: "carKmPerWeek",
    type: "number",
    label: "Kilometres driven per week",
    voi: 0.5,
    default: 100,
    min: 0,
    max: 1000,
    step: 10,
  },
];

describe("Questionnaire", () => {
  it("renders a top-level h1 so the route has heading-level context", () => {
    render(
      <Questionnaire
        questions={QUESTIONS}
        submitting={false}
        onComplete={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 1, name: /day-0 footprint/i }),
    ).toBeInTheDocument();
  });

  it("renders the questionnaire progress meter (progressbar role)", () => {
    render(
      <Questionnaire
        questions={QUESTIONS}
        submitting={false}
        onComplete={vi.fn()}
      />,
    );
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("renders the first question by default", () => {
    render(
      <Questionnaire
        questions={QUESTIONS}
        submitting={false}
        onComplete={vi.fn()}
      />,
    );
    // The Diet question lands first because its VoI is higher. Query the
    // radiogroup rather than the raw text — the label also appears in the
    // sr-only live region that announces step changes.
    expect(
      screen.getByRole("radiogroup", {
        name: /how would you describe your diet/i,
      }),
    ).toBeInTheDocument();
  });

  it("announces the current step in a live region", () => {
    // Advancing swaps the question in place and leaves focus on Next, so
    // without this a screen-reader user gets no signal the content changed.
    const { container } = render(
      <Questionnaire
        questions={QUESTIONS}
        submitting={false}
        onComplete={vi.fn()}
      />,
    );
    const live = container.querySelector('[aria-live="polite"]');
    expect(live).toHaveTextContent(
      "Question 1 of 2: How would you describe your diet?",
    );
  });
});

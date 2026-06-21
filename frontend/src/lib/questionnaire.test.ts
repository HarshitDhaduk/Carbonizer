import { describe, expect, it } from "vitest";
import { isVisible, visibleQuestions } from "./questionnaire";
import type { Question } from "./types";

function q(
  id: string,
  visibleIf?: Question["visibleIf"],
  overrides: Partial<Question> = {},
): Question {
  return {
    id,
    label: id,
    type: "number",
    ...(visibleIf ? { visibleIf } : {}),
    ...overrides,
  } as Question;
}

describe("isVisible", () => {
  it("unconditional questions are always visible", () => {
    expect(isVisible(q("a"), {})).toBe(true);
    expect(isVisible(q("a"), { other: "anything" })).toBe(true);
  });

  it("equals: visible only when target matches exactly", () => {
    const carKm = q("carKmPerWeek", { questionId: "carType", equals: "petrol" });
    expect(isVisible(carKm, { carType: "petrol" })).toBe(true);
    expect(isVisible(carKm, { carType: "none" })).toBe(false);
    expect(isVisible(carKm, {})).toBe(false);
  });

  it("notEquals: hides when target matches the excluded value", () => {
    const showUnlessNone = q("carKmPerWeek", {
      questionId: "carType",
      notEquals: "none",
    });
    expect(isVisible(showUnlessNone, { carType: "none" })).toBe(false);
    expect(isVisible(showUnlessNone, { carType: "petrol" })).toBe(true);
    // Absent target: treated as "not none" — i.e. shown.
    expect(isVisible(showUnlessNone, {})).toBe(true);
  });

  it("anyOf: visible iff target is one of the allowed values", () => {
    const electricOrHybrid = q("evCharger", {
      questionId: "carType",
      anyOf: ["ev", "hybrid"],
    });
    expect(isVisible(electricOrHybrid, { carType: "ev" })).toBe(true);
    expect(isVisible(electricOrHybrid, { carType: "hybrid" })).toBe(true);
    expect(isVisible(electricOrHybrid, { carType: "petrol" })).toBe(false);
  });

  it("null in answers is treated as absent (matches backend semantics)", () => {
    // The wire format sends omitted answers as null; cast since the public
    // AnswerValue union doesn't include it but the runtime branch does.
    const showWhenPetrol = q("carKmPerWeek", {
      questionId: "carType",
      equals: "petrol",
    });
    expect(
      isVisible(showWhenPetrol, { carType: null as unknown as string }),
    ).toBe(false);
  });
});

describe("visibleQuestions", () => {
  it("preserves the questionnaire order, dropping hidden ones", () => {
    const questions: Question[] = [
      q("a"),
      q("carKmPerWeek", { questionId: "carType", equals: "petrol" }),
      q("z"),
    ];
    expect(visibleQuestions(questions, { carType: "none" }).map((x) => x.id)).toEqual(
      ["a", "z"],
    );
    expect(
      visibleQuestions(questions, { carType: "petrol" }).map((x) => x.id),
    ).toEqual(["a", "carKmPerWeek", "z"]);
  });
});

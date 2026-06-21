/** Onboarding-questionnaire domain types (docs/API-DESIGN.md §10). */

export type QuestionType = "single" | "number";

export interface QuestionOption {
  value: string;
  label: string;
}

/** Show a question only when another answer satisfies this condition. */
export interface VisibleIf {
  questionId: string;
  equals?: AnswerValue;
  notEquals?: AnswerValue;
  anyOf?: AnswerValue[];
}

export interface Question {
  id: string;
  type: QuestionType;
  label: string;
  /** present for `single` questions. */
  options?: QuestionOption[];
  /** present for `number` questions. */
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  /** optional helper text shown under the label. */
  help?: string;
  /** gates visibility on another answer (e.g. car km only if carType ≠ none). */
  visibleIf?: VisibleIf;
  /** R0: value-of-information 0..1 — how much answering shrinks footprint uncertainty. */
  voi?: number;
  default: AnswerValue;
}

export interface Questionnaire {
  version: number;
  questions: Question[];
}

/** A single-choice option key (string) or a numeric answer. */
export type AnswerValue = number | string;

/** Answers keyed by question id. */
export type OnboardingAnswers = Record<string, AnswerValue>;

export type OnboardingStatus = "in_progress" | "completed";

export interface OnboardingProfile {
  status: OnboardingStatus;
  completed: boolean;
  /** the step the user was on — used to resume a half-finished onboarding. */
  currentStep: number;
  answers: OnboardingAnswers | null;
}

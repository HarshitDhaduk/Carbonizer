import type { OnboardingAnswers, Question } from "./types";

/**
 * Evaluate a question's `visibleIf` against the current answers.
 * Mirrors the backend `estimator.is_visible` rule so the renderer and the
 * estimator never disagree about which questions are relevant.
 */
export function isVisible(q: Question, answers: OnboardingAnswers): boolean {
  const cond = q.visibleIf;
  if (!cond) return true;
  const other = answers[cond.questionId];
  // the API sends unused fields as null (not omitted), so treat null === absent
  if (cond.equals != null) return other === cond.equals;
  if (cond.notEquals != null) return other !== cond.notEquals;
  if (cond.anyOf != null) return cond.anyOf.includes(other as never);
  return true;
}

/** The subset of questions currently relevant, in order. */
export function visibleQuestions(
  questions: Question[],
  answers: OnboardingAnswers,
): Question[] {
  return questions.filter((q) => isVisible(q, answers));
}

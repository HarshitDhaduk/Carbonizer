import type { OnboardingAnswers, Question } from "@/lib/types";
import { visibleQuestions } from "@/lib/questionnaire";

/**
 * Read-only summary of the user's Day-0 onboarding answers.
 * Only renders questions that are *visible* given the current answer set, so the
 * "Car kilometres" row doesn't appear for a user who answered "No car".
 */
export function StartingProfileCard({
  questions,
  answers,
}: {
  questions: Question[];
  answers: OnboardingAnswers;
}) {
  return (
    <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
      <h2 className="mb-3 text-sm font-medium text-text-mid">
        Your starting profile
      </h2>
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {visibleQuestions(questions, answers).map((q) => (
          <div
            key={q.id}
            className="flex items-center justify-between gap-3 rounded-md bg-surface-2 px-3 py-2 text-sm"
          >
            <dt className="text-text-mid">{q.label}</dt>
            <dd className="text-right text-text-hi">
              {renderAnswer(q, answers[q.id])}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function renderAnswer(q: Question, value: unknown): string {
  if (q.type === "single") {
    const opt = q.options?.find((o) => o.value === value);
    return opt?.label ?? String(value ?? "—");
  }
  return `${value ?? "—"}${q.unit ? ` ${q.unit}` : ""}`;
}

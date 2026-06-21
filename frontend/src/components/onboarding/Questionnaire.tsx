"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import type { AnswerValue, OnboardingAnswers, Question } from "@/lib/types";
import { visibleQuestions } from "@/lib/questionnaire";
import { Button } from "@/components/ui/Button";
import { QuestionInput } from "./QuestionInput";
import { QuestionnaireProgress } from "./QuestionnaireProgress";

/**
 * Onboarding flow controller — one question per step + R0 progress meter.
 *
 * The step list is the *visible* subset (questions whose `visibleIf` passes), so
 * answering "No car" removes the car-km step and shortens the flow.
 */
export function Questionnaire({
  questions,
  submitting,
  onComplete,
  initialAnswers,
  initialStep = 0,
  onProgress,
}: {
  questions: Question[];
  submitting: boolean;
  onComplete: (answers: OnboardingAnswers) => void;
  /** saved answers to resume from (overlaid on defaults). */
  initialAnswers?: OnboardingAnswers;
  /** saved step to resume at. */
  initialStep?: number;
  /** fired on every answer/step change so the parent can autosave. */
  onProgress?: (answers: OnboardingAnswers, step: number) => void;
}) {
  const [step, setStep] = useState(initialStep);
  const [answers, setAnswers] = useState<OnboardingAnswers>(() => ({
    ...Object.fromEntries(questions.map((q) => [q.id, q.default])),
    ...(initialAnswers ?? {}),
  }));

  const visible = useMemo(
    () => visibleQuestions(questions, answers),
    [questions, answers],
  );
  const total = visible.length;
  const safeStep = Math.min(step, total - 1);
  const q = visible[safeStep]!;
  const isLast = safeStep === total - 1;
  const precision = answeredVoiPercent(visible, safeStep);

  const setAnswer = (value: AnswerValue) => {
    const updated = { ...answers, [q.id]: value };
    setAnswers(updated);
    onProgress?.(updated, safeStep);
  };

  const goTo = (nextStep: number, withAnswers: OnboardingAnswers = answers) => {
    setStep(nextStep);
    onProgress?.(withAnswers, nextStep);
  };

  const next = () =>
    isLast ? onComplete(answers) : goTo(Math.min(safeStep + 1, total - 1));
  const back = () => goTo(Math.max(0, safeStep - 1));
  const skip = () => {
    const updated = { ...answers, [q.id]: q.default };
    setAnswers(updated);
    if (isLast) onComplete(updated);
    else goTo(Math.min(safeStep + 1, total - 1), updated);
  };

  return (
    <div className="w-full max-w-md animate-fade-rise">
      <QuestionnaireProgress
        step={safeStep + 1}
        total={total}
        precision={precision}
      />
      <QuestionInput question={q} value={answers[q.id]!} onChange={setAnswer} />

      <div className="mt-8 flex items-center gap-3">
        <Button
          variant="ghost"
          size="lg"
          onClick={back}
          disabled={safeStep === 0 || submitting}
          aria-label="Previous question"
        >
          <ArrowLeft size={18} aria-hidden />
        </Button>
        <Button
          size="lg"
          className="flex-1"
          onClick={next}
          disabled={submitting}
        >
          {submitting ? "Calculating…" : isLast ? "See my footprint" : "Next"}
          {!submitting && <ArrowRight size={18} aria-hidden />}
        </Button>
      </div>

      {!isLast && (
        <button
          type="button"
          onClick={skip}
          disabled={submitting}
          className="mt-3 block w-full text-center text-sm text-text-lo transition-colors hover:text-text-mid"
        >
          Not sure — use a typical value
        </button>
      )}
    </div>
  );
}

/**
 * R0 — share of the questionnaire's total value-of-information answered so
 * far. Because high-VoI questions come first, this rises faster than the
 * linear step-count.
 */
function answeredVoiPercent(visible: Question[], stepIndex: number): number {
  const totalVoi = visible.reduce((s, v) => s + (v.voi ?? 0), 0) || 1;
  const answeredVoi = visible
    .slice(0, stepIndex + 1)
    .reduce((s, v) => s + (v.voi ?? 0), 0);
  return Math.round((answeredVoi / totalVoi) * 100);
}

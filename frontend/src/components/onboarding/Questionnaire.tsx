"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Check, Sparkles } from "lucide-react";
import type { AnswerValue, OnboardingAnswers, Question } from "@/lib/types";
import { visibleQuestions } from "@/lib/questionnaire";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

/**
 * One question per step, with a progress bar. Answers seed from each `default`.
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

  // recompute the relevant questions whenever answers change
  const visible = useMemo(
    () => visibleQuestions(questions, answers),
    [questions, answers],
  );
  const total = visible.length;
  const safeStep = Math.min(step, total - 1);
  const q = visible[safeStep]!;
  const isLast = safeStep === total - 1;
  const progress = Math.round(((safeStep + 1) / total) * 100);

  // R0: estimate precision = share of total value-of-information answered so far.
  // Because high-VoI questions come first, this climbs faster than step progress —
  // showing the footprint sharpens most from the first few answers.
  const totalVoi = visible.reduce((s, vq) => s + (vq.voi ?? 0), 0) || 1;
  const answeredVoi = visible
    .slice(0, safeStep + 1)
    .reduce((s, vq) => s + (vq.voi ?? 0), 0);
  const precision = Math.round((answeredVoi / totalVoi) * 100);

  const set = (value: AnswerValue) => {
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
    // "not sure" → accept the population default and advance
    const updated = { ...answers, [q.id]: q.default };
    setAnswers(updated);
    if (isLast) onComplete(updated);
    else goTo(Math.min(safeStep + 1, total - 1), updated);
  };

  return (
    <div className="animate-fade-rise w-full max-w-md">
      {/* progress */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between text-xs text-text-lo">
          <span>
            Step {safeStep + 1} of {total}
          </span>
          <span className="tnum">{progress}%</span>
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-pill bg-surface-2"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-pill bg-brand-500 transition-[width] duration-base ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-text-lo">
          <Sparkles size={11} aria-hidden className="text-brand-400" />
          Estimate precision{" "}
          <span className="text-text-mid tnum">{precision}%</span>
          <span className="text-text-lo">· most-important questions first</span>
        </p>
      </div>

      <fieldset key={q.id} className="animate-fade-rise">
        <legend className="font-display text-xl text-text-hi">{q.label}</legend>
        {q.help && <p className="mb-4 mt-1 text-sm text-text-lo">{q.help}</p>}
        {!q.help && <div className="mb-4" />}

        {q.type === "single" ? (
          <div role="radiogroup" aria-label={q.label} className="space-y-2">
            {(q.options ?? []).map((opt) => {
              const selected = answers[q.id] === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => set(opt.value)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-md border px-4 py-3 text-left transition-colors duration-fast",
                    selected
                      ? "border-brand-500 bg-brand-500/10 text-text-hi"
                      : "border-border-subtle bg-surface-1 text-text-mid hover:bg-surface-2",
                  )}
                >
                  {opt.label}
                  {selected && (
                    <Check size={16} aria-hidden className="text-brand-400" />
                  )}
                </button>
              );
            })}
          </div>
        ) : (
          <NumberQuestion
            value={Number(answers[q.id] ?? q.default)}
            min={q.min ?? 0}
            max={q.max ?? 100}
            step={q.step ?? 1}
            unit={q.unit}
            onChange={set}
          />
        )}
      </fieldset>

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
        <Button size="lg" className="flex-1" onClick={next} disabled={submitting}>
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

function NumberQuestion({
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string | undefined;
  onChange: (v: number) => void;
}) {
  return (
    <div className="rounded-md border border-border-subtle bg-surface-1 p-4">
      <div className="mb-3 text-center">
        <span className="font-display text-3xl text-text-hi tnum">{value}</span>
        {unit && <span className="ml-1 text-text-lo">{unit}</span>}
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-brand-500"
        aria-label={unit ? `Value in ${unit}` : "Value"}
        aria-valuetext={unit ? `${value} ${unit}` : `${value}`}
      />
      <div className="mt-1 flex justify-between text-[11px] text-text-lo tnum">
        <span>{min}</span>
        <span>
          {max}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
    </div>
  );
}

"use client";

import { Check } from "lucide-react";
import type { AnswerValue, Question } from "@/lib/types";
import { cn } from "@/lib/cn";

/**
 * Renders the input control for a single question — radio cards for
 * `type=single`, slider for `type=number`. Wrapped in a `<fieldset>` with the
 * question label as the legend so screen readers announce the group correctly.
 */
export function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: AnswerValue;
  onChange: (value: AnswerValue) => void;
}) {
  return (
    <fieldset key={question.id} className="animate-fade-rise">
      <legend className="font-display text-xl text-text-hi">
        {question.label}
      </legend>
      {question.help ? (
        <p className="mb-4 mt-1 text-sm text-text-lo">{question.help}</p>
      ) : (
        <div className="mb-4" />
      )}

      {question.type === "single" ? (
        <SingleChoice question={question} value={value} onChange={onChange} />
      ) : (
        <NumberQuestion
          value={Number(value ?? question.default)}
          min={question.min ?? 0}
          max={question.max ?? 100}
          step={question.step ?? 1}
          unit={question.unit}
          onChange={onChange}
        />
      )}
    </fieldset>
  );
}

function SingleChoice({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: AnswerValue;
  onChange: (value: AnswerValue) => void;
}) {
  return (
    <div role="radiogroup" aria-label={question.label} className="space-y-2">
      {(question.options ?? []).map((opt) => {
        const selected = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(opt.value)}
            className={cn(
              "flex w-full items-center justify-between rounded-md border px-4 py-3 text-left transition-colors duration-fast",
              selected
                ? "bg-brand-500/10 border-brand-500 text-text-hi"
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
        <span className="tnum font-display text-3xl text-text-hi">{value}</span>
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
      <div className="tnum mt-1 flex justify-between text-[11px] text-text-lo">
        <span>{min}</span>
        <span>
          {max}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
    </div>
  );
}

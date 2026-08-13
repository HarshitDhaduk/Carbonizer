"use client";

import { useRef } from "react";
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
          label={question.label}
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

/**
 * `role="radiogroup"` promises assistive tech a specific keyboard contract:
 * the group is a single tab stop, and arrows move *and* select within it.
 * These are `<button role="radio">` rather than native inputs (for the card
 * layout), so that contract has to be implemented — roving tabIndex plus
 * Arrow/Home/End below. Without it a screen-reader user is told to use arrows
 * that do nothing.
 */
function SingleChoice({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: AnswerValue;
  onChange: (value: AnswerValue) => void;
}) {
  const groupRef = useRef<HTMLDivElement>(null);
  const options = question.options ?? [];
  const selectedIndex = options.findIndex((o) => o.value === value);
  // Nothing selected yet → the first option carries the tab stop, so the group
  // is always reachable.
  const focusIndex = selectedIndex >= 0 ? selectedIndex : 0;

  const moveTo = (index: number) => {
    const next = options[(index + options.length) % options.length];
    if (!next) return;
    onChange(next.value);
    // Selection follows focus in this pattern, so move focus to match.
    groupRef.current
      ?.querySelectorAll<HTMLButtonElement>('[role="radio"]')
      [(index + options.length) % options.length]?.focus();
  };

  const onKeyDown = (
    e: React.KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    switch (e.key) {
      case "ArrowDown":
      case "ArrowRight":
        e.preventDefault();
        moveTo(index + 1);
        break;
      case "ArrowUp":
      case "ArrowLeft":
        e.preventDefault();
        moveTo(index - 1);
        break;
      case "Home":
        e.preventDefault();
        moveTo(0);
        break;
      case "End":
        e.preventDefault();
        moveTo(options.length - 1);
        break;
    }
  };

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={question.label}
      className="space-y-2"
    >
      {options.map((opt, index) => {
        const selected = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={index === focusIndex ? 0 : -1}
            onKeyDown={(e) => onKeyDown(e, index)}
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
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  /** The question text — this is the slider's accessible name. */
  label: string;
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
        // Name the control after the question, not "Value in km" — a
        // screen-reader user hears the name alone, and the <legend> that
        // carries the question isn't reliably announced as the control's name.
        aria-label={label}
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

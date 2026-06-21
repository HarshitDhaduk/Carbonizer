"use client";

import { Sparkles } from "lucide-react";

/**
 * Step counter + accuracy bar above the question — the R0 visual loop.
 *
 * `progress` is step / total (linear). `precision` is the R0 value-of-information
 * share answered so far, which climbs *faster* than `progress` because high-VoI
 * questions are first. The two together show "you're 1/8 done but your number is
 * already 60% accurate" — the engagement reframe.
 */
export function QuestionnaireProgress({
  step,
  total,
  precision,
}: {
  step: number;
  total: number;
  precision: number;
}) {
  const progress = Math.round((step / total) * 100);
  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center justify-between text-xs text-text-lo">
        <span>
          Step {step} of {total}
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
        <span className="tnum text-text-mid">{precision}%</span>
        <span className="text-text-lo">· most-important questions first</span>
      </p>
    </div>
  );
}

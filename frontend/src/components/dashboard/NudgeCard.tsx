"use client";

import { Zap, ArrowRight, Leaf, PiggyBank } from "lucide-react";
import type { Nudge } from "@/lib/types";
import { formatCo2e, formatMoney } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

const EFFORT_LABEL: Record<Nudge["effort"], string> = {
  "1-tap": "1 tap",
  "5-min": "5 min",
  setup: "Setup",
};

/**
 * "Do this next" — one high-impact action with the dual carbon + money saving
 * (docs/UI-UX-DESIGN.md §6.4). Clean-window nudges read as time-sensitive.
 */
export function NudgeCard({
  nudge,
  onAct,
}: {
  nudge: Nudge;
  onAct?: (nudge: Nudge) => void;
}) {
  const timely = nudge.kind === "clean-window";
  // clean-window savings are per-event ("now"), everything else is annualized
  const per = timely ? "" : " /yr";

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 rounded-lg border p-3.5",
        timely
          ? "border-info/40 bg-info/10"
          : "border-border-subtle bg-surface-1",
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        <span
          className={cn(
            "mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-md",
            timely ? "bg-info/15 text-info" : "bg-brand-500/15 text-brand-400",
          )}
        >
          <Zap size={18} aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-medium text-text-hi">
            <span className="truncate">{nudge.title}</span>
            <span className="shrink-0 rounded-pill bg-surface-2 px-2 py-0.5 text-[11px] font-normal text-text-lo">
              {EFFORT_LABEL[nudge.effort]}
            </span>
          </p>
          <p className="mt-0.5 truncate text-sm text-text-mid">{nudge.detail}</p>

          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {nudge.carbonSavedTco2e > 0 && (
              <span className="inline-flex items-center gap-1 rounded-pill bg-brand-500/10 px-2 py-0.5 text-xs text-brand-400 tnum">
                <Leaf size={12} aria-hidden />−{formatCo2e(nudge.carbonSavedTco2e)}
                {per}
              </span>
            )}
            {nudge.moneySaved > 0 && (
              <span className="inline-flex items-center gap-1 rounded-pill bg-surface-2 px-2 py-0.5 text-xs text-text-mid tnum">
                <PiggyBank size={12} aria-hidden />−
                {formatMoney(nudge.moneySaved, nudge.currency)}
                {per}
              </span>
            )}
          </div>
        </div>
      </div>

      <Button
        size="sm"
        variant={timely ? "primary" : "secondary"}
        className="shrink-0"
        onClick={() => onAct?.(nudge)}
      >
        Act <ArrowRight size={15} aria-hidden />
      </Button>
    </div>
  );
}

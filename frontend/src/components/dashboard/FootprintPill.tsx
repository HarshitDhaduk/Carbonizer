import type { FootprintSummary } from "@/lib/types";
import { formatCo2e } from "@/lib/format";
import { TrendDelta } from "@/components/ui/TrendDelta";
import { cn } from "@/lib/cn";

const STATUS_LABEL: Record<FootprintSummary["status"], string> = {
  seed: "Getting started",
  regressing: "Needs attention",
  plateau: "Holding steady",
  improving: "Improving",
  thriving: "Thriving",
};

/** Persistent header summary (docs/UI-UX-DESIGN.md §6.2). Live, tabular. */
export function FootprintPill({ summary }: { summary: FootprintSummary }) {
  const good = summary.status === "improving" || summary.status === "thriving";
  return (
    <div className="glass flex items-center justify-between gap-4 rounded-lg px-4 py-2.5">
      <div className="min-w-0">
        <p className="text-xs text-text-lo">Footprint · annualized</p>
        <p className="font-display text-xl text-text-hi tnum leading-tight">
          {formatCo2e(summary.totalTco2e)}{" "}
          <span className="text-sm font-normal text-text-lo">CO₂e</span>
        </p>
      </div>

      <div className="flex items-center gap-3">
        <TrendDelta
          trend={summary.trend}
          deltaPct={summary.deltaPct}
          suffix="vs last mo"
        />
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-xs font-medium",
            good
              ? "bg-brand-500/15 text-brand-400"
              : "bg-warning/15 text-warning",
          )}
        >
          <span
            aria-hidden
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              good ? "bg-brand-400" : "bg-warning",
            )}
          />
          {STATUS_LABEL[summary.status]}
        </span>
      </div>
    </div>
  );
}

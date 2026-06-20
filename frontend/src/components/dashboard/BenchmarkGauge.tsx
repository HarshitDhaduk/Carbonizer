import { ShieldCheck, Users } from "lucide-react";
import type { Benchmark } from "@/lib/types";
import { formatCo2e } from "@/lib/format";
import { cn } from "@/lib/cn";

/**
 * Peer benchmark vs. similar households (docs/UI-UX-DESIGN.md §6.5).
 * Framed positively; aggregates only — never another user's data.
 */
export function BenchmarkGauge({ benchmark }: { benchmark: Benchmark }) {
  const { youTco2e, averageTco2e, topTco2e, vsAveragePct } = benchmark;
  const max = Math.max(youTco2e, averageTco2e, topTco2e) * 1.15;
  const pct = (v: number) => `${Math.min(100, (v / max) * 100).toFixed(1)}%`;
  const below = vsAveragePct <= 0;

  return (
    <section
      aria-label="Comparison with similar households"
      className="rounded-lg border border-border-subtle bg-surface-1 p-3.5"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-sm text-text-mid">
          <Users size={14} aria-hidden /> Households like yours
        </span>
        <span
          className={cn(
            "text-sm font-medium",
            below ? "text-success" : "text-warning",
          )}
        >
          You&apos;re {Math.abs(Math.round(vsAveragePct))}%{" "}
          {below ? "below" : "above"} average
        </span>
      </div>

      <div className="relative h-2.5 rounded-pill bg-surface-2">
        <div
          className="absolute inset-y-0 left-0 rounded-pill bg-brand-500"
          style={{ width: pct(youTco2e) }}
        />
        {/* average marker */}
        <div
          className="h-4.5 absolute -top-1 w-0.5 bg-text-lo"
          style={{ left: pct(averageTco2e), height: "1.05rem" }}
          aria-hidden
        />
      </div>

      <div className="tnum mt-1.5 flex justify-between text-[11px] text-text-lo">
        <span>You · {formatCo2e(youTco2e)}</span>
        <span>Avg · {formatCo2e(averageTco2e)}</span>
        <span>Top 20% · {formatCo2e(topTco2e)}</span>
      </div>

      {benchmark.privacyAdjusted && (
        <p
          className="mt-2 flex items-center gap-1.5 text-[11px] text-text-lo"
          title="The average is corrected for who self-selects to connect data (inverse-propensity weighting) and released with differential privacy."
        >
          <ShieldCheck size={11} aria-hidden className="text-brand-400" />
          Privacy-protected · adjusted for who connects
        </p>
      )}
    </section>
  );
}

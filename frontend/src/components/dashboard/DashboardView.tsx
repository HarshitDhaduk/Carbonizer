"use client";

import { useEffect } from "react";
import type { Benchmark, FootprintSummary, Nudge } from "@/lib/types";
import { useBiomeStore } from "@/store/biome-store";
import { FootprintPill } from "./FootprintPill";
import { CategoryGrid } from "./CategoryGrid";
import { NudgeCard } from "./NudgeCard";
import { BenchmarkGauge } from "./BenchmarkGauge";
import { BiomeCanvas } from "@/components/biome/BiomeCanvas";

/**
 * Dashboard composition (docs/UI-UX-DESIGN.md §6.2). The 3D biome and the
 * cards read one source of truth via the biome store, hydrated from the
 * footprint summary on mount.
 */
export function DashboardView({
  summary,
  topNudge,
  benchmark,
}: {
  summary: FootprintSummary;
  topNudge: Nudge | undefined;
  benchmark: Benchmark;
}) {
  const hydrate = useBiomeStore((s) => s.hydrateFromSummary);

  useEffect(() => {
    hydrate(summary);
  }, [hydrate, summary]);

  return (
    <div className="animate-fade-rise space-y-4">
      <FootprintPill summary={summary} />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 3D hero */}
        <div className="min-h-[340px] rounded-card border border-border-subtle bg-surface-1 p-4 shadow-elev-1">
          <BiomeCanvas
            health={summary.health}
            status={summary.status}
            caption="3 trees planted this week from your reductions"
          />
        </div>

        {/* category cards */}
        <div className="flex flex-col justify-center">
          <CategoryGrid categories={summary.categories} />
        </div>
      </div>

      {/* do this next */}
      {topNudge && (
        <section aria-label="Recommended action">
          <h2 className="mb-2 text-sm font-medium text-text-mid">
            Do this next
          </h2>
          <NudgeCard nudge={topNudge} />
        </section>
      )}

      <BenchmarkGauge benchmark={benchmark} />
    </div>
  );
}

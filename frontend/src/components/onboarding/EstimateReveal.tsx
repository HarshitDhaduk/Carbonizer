"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import type { FootprintSummary } from "@/lib/types";
import { FootprintPill } from "@/components/dashboard/FootprintPill";
import { CategoryGrid } from "@/components/dashboard/CategoryGrid";
import { BiomeCanvas } from "@/components/biome/BiomeCanvas";
import { ConnectSources } from "@/components/connections/ConnectSources";
import { Button } from "@/components/ui/Button";
import { useBiomeStore } from "@/store/biome-store";

/**
 * The Day-0 reveal — reuses the dashboard components. The "connect bank" card
 * demonstrates Progressive Data Depth: linking imports transactions and the
 * footprint re-renders with categories upgraded estimated → spend.
 */
export function EstimateReveal({
  summary: initialSummary,
}: {
  summary: FootprintSummary;
}) {
  const hydrate = useBiomeStore((s) => s.hydrateFromSummary);
  const [summary, setSummary] = useState(initialSummary);

  // re-hydrate the biome whenever the summary changes (initial + post-connect)
  useEffect(() => {
    hydrate(summary);
  }, [hydrate, summary]);

  return (
    <div className="w-full max-w-2xl animate-fade-rise space-y-4">
      <header className="text-center">
        <span className="bg-brand-500/15 inline-flex items-center gap-1.5 rounded-pill px-3 py-1 text-xs font-medium text-brand-400">
          <Sparkles size={13} aria-hidden /> Your living world is born
        </span>
        <h1 className="mt-3 font-display text-2xl text-text-hi">
          Here&apos;s your starting footprint
        </h1>
        <p className="mt-1 text-sm text-text-mid">
          A first estimate from your answers. Connect a data source to refine it
          — each one makes your world more accurate and alive.
        </p>
      </header>

      <FootprintPill summary={summary} />

      <div className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <div className="mx-auto min-h-[320px] max-w-[420px]">
          <BiomeCanvas
            health={summary.health}
            status={summary.status}
            caption="Connect data below to make your world more accurate"
          />
        </div>
      </div>

      <CategoryGrid categories={summary.categories} />

      {/* Progressive Data Depth: connect real sources */}
      <section aria-label="Connect data sources" className="space-y-2">
        <h2 className="text-sm font-medium text-text-mid">Make it accurate</h2>
        <ConnectSources onSummary={setSummary} />
      </section>

      <Link href="/dashboard" className="block">
        <Button size="lg" className="w-full">
          Go to dashboard <ArrowRight size={18} aria-hidden />
        </Button>
      </Link>
    </div>
  );
}

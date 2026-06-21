"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Attribution,
  CategoryBreakdown,
  FootprintSummary,
} from "@/lib/types";
import { queries, queryKeys } from "@/lib/queries";
import { CATEGORY_HEX, CATEGORY_LABEL } from "@/lib/tokens";
import { formatCo2e } from "@/lib/format";
import { AppPage } from "@/components/layout/AppPage";
import { FootprintPill } from "@/components/dashboard/FootprintPill";
import { MethodBadge } from "@/components/ui/MethodBadge";
import { ConnectSources } from "@/components/connections/ConnectSources";

export function InsightsClient() {
  return (
    <AppPage title="Insights">
      <InsightsContent />
    </AppPage>
  );
}

function InsightsContent() {
  const qc = useQueryClient();
  const summary = useQuery(queries.footprintSummary());
  const attr = useQuery(queries.attribution());

  if (summary.error)
    return (
      <p className="text-sm text-danger">Couldn&apos;t load your insights.</p>
    );
  if (summary.isPending || !summary.data)
    return <div className="skeleton h-64 rounded-card" />;

  const data = summary.data;
  const max = Math.max(...data.categories.map((c) => c.tco2e), 0.001);
  const measured = data.categories.filter(
    (c) => c.method !== "estimated",
  ).length;
  const total = data.categories.length;

  function onConnected(next: FootprintSummary) {
    qc.setQueryData(queryKeys.footprint.summary(), next);
    void qc.invalidateQueries({ queryKey: queryKeys.footprint.all });
  }

  return (
    <div className="space-y-4">
      <FootprintPill summary={data} />

      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <h2 className="mb-3 text-sm font-medium text-text-mid">
          Where it comes from
        </h2>
        <div className="space-y-3">
          {[...data.categories]
            .sort((a, b) => b.tco2e - a.tco2e)
            .map((c) => (
              <CategoryBar key={c.category} c={c} max={max} />
            ))}
        </div>
      </section>

      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-text-mid">Data quality</h2>
          <span className="tnum rounded-pill bg-surface-2 px-2.5 py-1 text-xs text-text-mid">
            {measured}/{total} categories measured
          </span>
        </div>
        <p className="mt-2 text-sm text-text-mid">
          Measured categories use your real spending or metered usage. Estimated
          ones come from your onboarding answers — connect more sources to
          upgrade them.
        </p>
        <div className="mt-3">
          <ConnectSources onSummary={onConnected} />
        </div>
      </section>

      {attr.data && <AttributionPanel attr={attr.data} />}
    </div>
  );
}

function AttributionPanel({ attr }: { attr: Attribution }) {
  if (!attr.available) {
    return (
      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <h2 className="mb-1 text-sm font-medium text-text-mid">
          What&apos;s behind your changes
        </h2>
        <p className="text-sm text-text-mid">
          Connect your home energy to see how much of a change is your own usage
          versus the grid getting cleaner — so you&apos;re only credited for
          what you actually did.
        </p>
      </section>
    );
  }

  const behPct = Math.round(attr.behaviorShare * 100);
  const gridPct = 100 - behPct;
  const lower = attr.totalDeltaKg <= 0;

  return (
    <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
      <h2 className="mb-1 text-sm font-medium text-text-mid">
        What&apos;s behind your changes
      </h2>
      <p className="mb-3 text-sm text-text-mid">
        Over the last {attr.periodDays} days your energy emissions are{" "}
        <span className={lower ? "text-success" : "text-warning"}>
          {Math.abs(attr.totalDeltaKg)} kg {lower ? "lower" : "higher"}
        </span>
        . Here&apos;s how much was you versus the grid:
      </p>

      <div
        className="flex h-2.5 overflow-hidden rounded-pill bg-surface-2"
        role="img"
        aria-label={`${behPct}% your usage, ${gridPct}% grid intensity`}
      >
        <div className="h-full bg-brand-500" style={{ width: `${behPct}%` }} />
        <div
          className="bg-cat-energy/60 h-full"
          style={{ width: `${gridPct}%` }}
        />
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-text-lo">
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden />
          You · usage {behPct}%
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="bg-cat-energy/60 h-1.5 w-1.5 rounded-full"
            aria-hidden
          />
          Grid intensity {gridPct}%
        </span>
      </div>

      <p className="mt-3 text-sm text-text-mid">
        We credit you for the <span className="text-brand-400">{behPct}%</span>{" "}
        that&apos;s your behavior — the rest is the grid&apos;s changing carbon
        intensity, which isn&apos;t your doing.
      </p>
    </section>
  );
}

function CategoryBar({ c, max }: { c: CategoryBreakdown; max: number }) {
  const color = CATEGORY_HEX[c.category];
  const pct = Math.max(2, (c.tco2e / max) * 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 text-text-hi">
          <span
            aria-hidden
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: color }}
          />
          {CATEGORY_LABEL[c.category]}
        </span>
        <span className="tnum flex items-center gap-2 text-text-mid">
          {formatCo2e(c.tco2e)}
          <MethodBadge method={c.method} imputed={c.imputed ?? false} />
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-pill bg-surface-2">
        <div
          className="h-full rounded-pill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

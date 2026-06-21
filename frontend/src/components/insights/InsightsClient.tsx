"use client";

import { useEffect, useState } from "react";
import type {
  Attribution,
  CategoryBreakdown,
  FootprintSummary,
} from "@/lib/types";
import { clientApi } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
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
  const user = useAuthStore((s) => s.user);
  const [summary, setSummary] = useState<FootprintSummary | null>(null);
  const [attr, setAttr] = useState<Attribution | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let active = true;
    clientApi
      .getFootprintSummary()
      .then((s) => active && setSummary(s))
      .catch(() => active && setError("Couldn't load your insights."));
    clientApi
      .getAttribution()
      .then((a) => active && setAttr(a))
      .catch(() => {
        /* attribution is optional */
      });
    return () => {
      active = false;
    };
  }, [user]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!summary) return <div className="skeleton h-64 rounded-card" />;

  const max = Math.max(...summary.categories.map((c) => c.tco2e), 0.001);
  const measured = summary.categories.filter(
    (c) => c.method !== "estimated",
  ).length;
  const total = summary.categories.length;

  return (
    <div className="space-y-4">
      <FootprintPill summary={summary} />

      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <h2 className="mb-3 text-sm font-medium text-text-mid">
          Where it comes from
        </h2>
        <div className="space-y-3">
          {[...summary.categories]
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
          <ConnectSources onSummary={setSummary} />
        </div>
      </section>

      {attr && <AttributionPanel attr={attr} />}
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

"use client";

import { Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { queries } from "@/lib/queries";
import { AppPage } from "@/components/layout/AppPage";
import { NudgeCard } from "@/components/dashboard/NudgeCard";
import { ConnectSources } from "@/components/connections/ConnectSources";

export function ActClient() {
  return (
    <AppPage title="Act">
      <ActContent />
    </AppPage>
  );
}

function ActContent() {
  const nudges = useQuery(queries.recommendations());

  if (nudges.error)
    return (
      <p className="text-sm text-danger">Couldn&apos;t load your actions.</p>
    );
  if (nudges.isPending || !nudges.data)
    return <div className="skeleton h-64 rounded-card" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-mid">
        A few high-impact changes, ranked by the carbon and money they save.
      </p>

      {nudges.data.length > 0 ? (
        <div className="space-y-2.5">
          {nudges.data.map((n) => (
            <NudgeCard key={n.id} nudge={n} />
          ))}
        </div>
      ) : (
        <div className="rounded-card border border-border-subtle bg-surface-1 p-6 text-center">
          <span className="bg-brand-500/15 mx-auto mb-3 grid h-11 w-11 place-items-center rounded-full text-brand-400">
            <Sparkles size={20} aria-hidden />
          </span>
          <p className="font-medium text-text-hi">No actions yet</p>
          <p className="mt-1 text-sm text-text-mid">
            Connect a data source and we&apos;ll surface the changes with the
            biggest impact for you.
          </p>
        </div>
      )}

      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <h2 className="mb-2 text-sm font-medium text-text-mid">
          Better data, better advice
        </h2>
        <ConnectSources onSummary={() => {}} />
      </section>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import type { Nudge } from "@/lib/types";
import { clientApi } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
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
  const token = useAuthStore((s) => s.token);
  const [nudges, setNudges] = useState<Nudge[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    clientApi
      .getRecommendations(token)
      .then((n) => active && setNudges(n))
      .catch(() => active && setError("Couldn't load your actions."));
    return () => {
      active = false;
    };
  }, [token]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!nudges) return <div className="skeleton h-64 rounded-card" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-mid">
        A few high-impact changes, ranked by the carbon and money they save.
      </p>

      {nudges.length > 0 ? (
        <div className="space-y-2.5">
          {nudges.map((n) => (
            <NudgeCard key={n.id} nudge={n} />
          ))}
        </div>
      ) : (
        <div className="rounded-card border border-border-subtle bg-surface-1 p-6 text-center">
          <span className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-full bg-brand-500/15 text-brand-400">
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
